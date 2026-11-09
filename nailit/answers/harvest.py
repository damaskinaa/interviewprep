"""Deep question harvest for the Level 1 (model-candidate) bank.

Sources: web pages found with Tavily + Exa (scraped with Firecrawl), YouTube mock interviews and coach videos
(Firecrawl's YouTube transcript provider), and the existing library. Reddit, Glassdoor, LinkedIn and Blind are
used only as search snippets, never scraped. Questions (and any sample answers with a coach's verdict) are
extracted with an LLM, clustered by meaning, and counted by the number of independent sources.

    uv run python -m nailit.answers.harvest            # full run (caches every fetch, so reruns are cheap)
    uv run python -m nailit.answers.harvest --budget 600

Output: ~/NailIt/library/model_level/harvest/ (raw/, extracted.jsonl, canonical.json, report.md)
Keys come from the environment: TAVILY_API_KEY, EXA_API_KEY, FIRECRAWL_API_KEY, OPENAI_API_KEY.
"""
import argparse
import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml

from nailit import library
from nailit.llm import parse_json_object

ROLES = ["Service Delivery Manager", "Operations Manager", "Senior Operations Manager", "Program Manager",
         "Technical Program Manager", "Head of Operations", "Senior Project Manager", "Business Operations Manager",
         "Customer Support Operations Manager"]
COMPANIES = ["Amazon", "Google", "Meta", "Microsoft", "Stripe"]
NO_SCRAPE = ("linkedin.com", "glassdoor.", "reddit.com", "teamblind.com", "quora.com", "facebook.com", "instagram.com",
             "tiktok.com", "x.com", "twitter.com")
EXTRACT_MODEL = os.getenv("NAILIT_HARVEST_MODEL") or "gpt-5.4-mini"
EMBED_MODEL = "text-embedding-3-small"
OUT = library.home() / "library" / "model_level" / "harvest"


class Budget:
    def __init__(self, credits):
        self.left = credits

    def take(self, n):
        if self.left < n:
            return False
        self.left -= n
        return True


def _cache(kind, key):
    path = OUT / "raw" / kind / (hashlib.sha1(key.encode()).hexdigest()[:16] + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def cached(kind, key, fetch):
    path = _cache(kind, key)
    if path.exists():
        return json.loads(path.read_text())
    value = fetch()
    if value is not None:
        path.write_text(json.dumps(value))
    return value


def web_queries():
    queries = []
    for role in ROLES:
        queries += [f"{role} interview questions and answers", f"{role} behavioral interview questions asked"]
    for company in COMPANIES:
        for role in ("Program Manager", "Technical Program Manager", "Operations Manager", "Service Delivery Manager"):
            queries.append(f"{company} {role} interview questions")
    queries += ["Amazon bar raiser interview questions examples", "Amazon leadership principles interview questions list",
                "Meta program manager partnership interview questions", "Google program manager program sense questions",
                "head of operations startup interview questions", "fintech operations manager interview questions"]
    return queries


def video_queries():
    queries = []
    for role in ("program manager", "technical program manager", "operations manager", "service delivery manager",
                 "senior project manager", "head of operations"):
        queries += [f"{role} mock interview", f"{role} interview questions and answers"]
    queries += ["amazon behavioral mock interview leadership principles", "amazon bar raiser mock interview",
                "meta behavioral interview mock", "google behavioral interview mock googleyness",
                "ex-amazon bar raiser interview tips stories", "behavioral interview example answers senior manager"]
    return queries


def tavily(http, query):
    r = http.post("https://api.tavily.com/search", json={"api_key": os.environ["TAVILY_API_KEY"], "query": query,
                                                           "max_results": 8, "search_depth": "advanced"})
    r.raise_for_status()
    return [{"url": x["url"], "title": x.get("title", ""), "snippet": x.get("content", "")} for x in r.json().get("results", [])]


def exa(http, query):
    r = http.post("https://api.exa.ai/search", headers={"x-api-key": os.environ["EXA_API_KEY"]},
                  json={"query": query, "numResults": 8, "contents": {"highlights": True}})
    r.raise_for_status()
    return [{"url": x["url"], "title": x.get("title", ""), "snippet": " ".join(x.get("highlights") or [])}
            for x in r.json().get("results", [])]


def firecrawl(http, body, attempts=6):
    """Firecrawl with backoff: the plan allows few concurrent requests, so 429s are retried, not dropped."""
    for attempt in range(attempts):
        r = http.post("https://api.firecrawl.dev/v2/scrape", headers={"Authorization": "Bearer " + os.environ["FIRECRAWL_API_KEY"]},
                      json=body, timeout=180)
        if r.status_code == 429:
            time.sleep(float(r.headers.get("retry-after") or 0) or min(60, 5 * 2 ** attempt))
            continue
        r.raise_for_status()
        return r.json().get("data") or {}
    r.raise_for_status()


def jina_read(http, url):
    r = http.get("https://r.jina.ai/" + url, headers={"Authorization": "Bearer " + os.environ["JINA_API_KEY"],
                                                      "X-Return-Format": "markdown"}, timeout=90)
    r.raise_for_status()
    return r.text


def scrape_page(http, url):
    """Jina Reader first (fast, cheap); Firecrawl as the fallback for pages Jina can't render."""
    try:
        text = jina_read(http, url)
        if len(text) > 800:
            return {"url": url, "text": text[:60000], "title": "", "via": "jina"}
    except Exception:  # noqa: BLE001 - fall back to Firecrawl
        pass
    data = firecrawl(http, {"url": url, "formats": ["markdown"], "onlyMainContent": True, "maxAge": 7 * 86400 * 1000})
    return {"url": url, "text": (data.get("markdown") or "")[:60000], "title": (data.get("metadata") or {}).get("title", ""), "via": "firecrawl"}


def yt_search(http, query):
    data = firecrawl(http, {"alexandria": {"provider": "youtube-com", "capability": "videos/search_videos",
                                           "options": {"query": query}}})
    rows = ((data.get("alexandria") or [{}])[0].get("data") or {})
    items = rows.get("records") or rows.get("videos") or rows.get("items") or []
    return [{"video_id": v.get("video_id") or v.get("id"), "title": v.get("title", ""),
             "channel": (v.get("channel") or {}).get("name") if isinstance(v.get("channel"), dict) else v.get("channel_name")}
            for v in items if isinstance(v, dict) and (v.get("video_id") or v.get("id"))]


def yt_transcript(http, video_id):
    data = firecrawl(http, {"alexandria": {"provider": "youtube-com", "capability": "videos/video_transcript",
                                           "options": {"video_id": video_id, "language": "en"}}})
    row = ((data.get("alexandria") or [{}])[0].get("data") or {})
    return {"url": f"https://www.youtube.com/watch?v={video_id}", "title": row.get("title", ""), "text": (row.get("full_text") or "")[:60000]}


EXTRACT_PROMPT = """From this source about job interviews for roles like {roles}, extract:
1. every interview QUESTION an interviewer could ask (verbatim where possible; skip questions TO the interviewer
   unless the source lists them as questions for the candidate to ask, then mark kind "ask_them");
2. every SAMPLE ANSWER given in full in the source, with the question it answers, and the verdict if a coach or
   host rates it (e.g. "great answer", "this would fail").
Return JSON: {{"questions":[{{"q":"...","kind":"asked|example|ask_them","company":"... or ''","role":"... or ''"}}],
"answers":[{{"q":"...","answer":"...","verdict":"... or ''"}}]}}
Source title: {title}
Source text:
{text}"""


def extract(text, title):
    from openai import OpenAI
    client = OpenAI()
    out = {"questions": [], "answers": []}
    for start in range(0, min(len(text), 48000), 16000):
        chunk = text[start:start + 16000]
        if len(chunk) < 300:
            continue
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(model=EXTRACT_MODEL, response_format={"type": "json_object"},
                                                      messages=[{"role": "user", "content": EXTRACT_PROMPT.format(
                                                          roles=", ".join(ROLES[:5]), title=title, text=chunk)}])
                data = parse_json_object(resp.choices[0].message.content, {}) or {}
                out["questions"] += data.get("questions") or []
                out["answers"] += data.get("answers") or []
                break
            except Exception:  # noqa: BLE001 - retry, then skip this chunk
                time.sleep(2 * (attempt + 1))
    return out


def embed(texts):
    from openai import OpenAI
    client, vectors = OpenAI(), []
    for i in range(0, len(texts), 500):
        vectors += [d.embedding for d in client.embeddings.create(model=EMBED_MODEL, input=texts[i:i + 500]).data]
    return vectors


def cluster(items, threshold=0.84):
    import numpy as np
    vectors = np.array(embed([i["q"] for i in items]), dtype="float32")
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    centroids, groups = [], []
    for index, vector in enumerate(vectors):
        if centroids:
            sims = np.array(centroids) @ vector
            best = int(sims.argmax())
            if sims[best] >= threshold:
                groups[best].append(index)
                n = len(groups[best])
                centroids[best] = (centroids[best] * (n - 1) + vector) / n
                centroids[best] /= np.linalg.norm(centroids[best])
                continue
        centroids.append(vector)
        groups.append([index])
    canon = []
    for members in groups:
        rows = [items[i] for i in members]
        sources = sorted({r["source"] for r in rows})
        phrasing = sorted({r["q"].strip() for r in rows}, key=lambda q: (len(q) > 140, -sum(r["q"].strip() == q for r in rows), len(q)))
        canon.append({"question": phrasing[0], "variants": phrasing[1:8], "frequency": len(sources), "sources": sources[:20],
                      "companies": sorted({r.get("company") for r in rows if r.get("company")}),
                      "roles": sorted({r.get("role") for r in rows if r.get("role")}),
                      "kinds": sorted({r.get("kind") for r in rows if r.get("kind")})})
    return sorted(canon, key=lambda c: -c["frequency"])


def library_seed():
    lib = library.load_library()
    questions, ask = library._questions(lib["questions"])
    rows = [{"q": q["text"], "kind": "asked", "source": "library", "company": "", "role": ""} for q in questions]
    rows += [{"q": v, "kind": "asked", "source": "library", "company": "", "role": ""} for q in questions for v in q.get("variants") or []]
    rows += [{"q": q["text"], "kind": "ask_them", "source": "library", "company": "", "role": ""} for q in ask]
    bank = library.home() / "library" / "model_level" / "03_master_question_bank.md"
    if bank.exists():
        for line in bank.read_text().splitlines():
            m = re.match(r"^\|\s*([^|]{12,}\?)\s*\|", line)
            if m:
                rows.append({"q": m.group(1).strip(), "kind": "asked", "source": "model_level_03", "company": "", "role": ""})
    return rows


def main():
    parser = argparse.ArgumentParser(description="Deep question harvest")
    parser.add_argument("--budget", type=int, default=1500, help="Firecrawl credit cap")
    parser.add_argument("--max-pages", type=int, default=160)
    parser.add_argument("--max-videos", type=int, default=90)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    budget, http, log = Budget(args.budget), httpx.Client(timeout=90), []

    # 1. search
    hits, snippets, videos = {}, [], {}
    for query in web_queries():
        for engine in (tavily, exa):
            try:
                for hit in cached(engine.__name__, query, lambda: engine(http, query)) or []:
                    host = urlparse(hit["url"]).netloc.lower()
                    vid = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", hit["url"])
                    if "youtube" in host or "youtu.be" in host:
                        if vid:
                            videos.setdefault(vid.group(1), {"video_id": vid.group(1), "title": hit.get("title", "")})
                    elif any(b in host for b in NO_SCRAPE):
                        snippets.append({"url": hit["url"], "text": hit.get("snippet", ""), "title": hit.get("title", "")})
                    else:
                        hits.setdefault(hit["url"], hit)
            except Exception as error:  # noqa: BLE001
                log.append(f"search failed: {engine.__name__} {query}: {error}")
    for query in video_queries():
        if not budget.take(5):
            break
        try:
            for v in (cached("yt_search", query, lambda: yt_search(http, query)) or [])[:7]:
                videos.setdefault(v["video_id"], v)
        except Exception as error:  # noqa: BLE001
            log.append(f"video search failed: {query}: {error}")

    # 2. fetch
    pages = list(hits)[: args.max_pages]
    vids = list(videos)[: args.max_videos]

    def get_page(url):
        try:
            return cached("page", url, lambda: scrape_page(http, url))
        except Exception as error:  # noqa: BLE001
            log.append(f"scrape failed: {url}: {error}")

    def get_video(vid):
        if not _cache("video", vid).exists() and not budget.take(5):
            return None
        try:
            return cached("video", vid, lambda: yt_transcript(http, vid))
        except Exception as error:  # noqa: BLE001
            log.append(f"transcript failed: {vid}: {error}")

    with ThreadPoolExecutor(4) as pool:
        docs = [d for d in pool.map(get_page, pages) if d and len(d.get("text", "")) > 500]
    with ThreadPoolExecutor(2) as pool:
        docs += [d for d in pool.map(get_video, vids) if d and len(d.get("text", "")) > 500]
    docs += [{"url": s["url"], "title": s["title"], "text": s["text"]} for s in snippets if len(s.get("text", "")) > 80]

    # 3. extract
    def do_extract(doc):
        return doc, cached("extract", doc["url"] + str(len(doc["text"])), lambda: extract(doc["text"], doc.get("title", "")))

    rows, answers = library_seed(), []
    with ThreadPoolExecutor(8) as pool:
        for doc, data in pool.map(do_extract, docs):
            source = urlparse(doc["url"]).netloc + urlparse(doc["url"]).path if "youtube" not in doc["url"] else doc["url"]
            for q in (data or {}).get("questions") or []:
                if isinstance(q, dict) and isinstance(q.get("q"), str) and 10 < len(q["q"]) < 300:
                    rows.append({"q": q["q"], "kind": q.get("kind", "asked"), "company": q.get("company") or "",
                                 "role": q.get("role") or "", "source": source})
            for a in (data or {}).get("answers") or []:
                if isinstance(a, dict) and a.get("answer") and a.get("q"):
                    answers.append({**a, "source": doc["url"]})
    with open(OUT / "extracted.jsonl", "w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    (OUT / "sample_answers.json").write_text(json.dumps(answers, indent=1))

    # 4. cluster
    asked = [r for r in rows if r.get("kind") != "ask_them"]
    canon = cluster(asked)
    (OUT / "canonical.json").write_text(json.dumps(canon, indent=1))
    ask_canon = cluster([r for r in rows if r.get("kind") == "ask_them"]) if any(r.get("kind") == "ask_them" for r in rows) else []
    (OUT / "ask_them.json").write_text(json.dumps(ask_canon, indent=1))

    report = [f"# Question harvest · {time.strftime('%Y-%m-%d %H:%M')}",
              f"- web pages read: {sum(1 for d in docs if d['url'] in hits)}",
              f"- video transcripts: {sum(1 for d in docs if 'youtube' in d['url'])}",
              f"- search snippets (Reddit/Glassdoor/LinkedIn/Blind, not scraped): {len(snippets)}",
              f"- raw questions: {len(rows)} → canonical: {len(canon)} (asked) + {len(ask_canon)} (to ask them)",
              f"- asked by ≥ 2 independent sources: {sum(c['frequency'] >= 2 for c in canon)}",
              f"- sample answers captured (with any verdicts): {len(answers)}",
              f"- Firecrawl credits left of {args.budget}: {budget.left}", "", "## Top 40 by frequency"]
    report += [f"{i + 1}. ({c['frequency']}) {c['question']}" for i, c in enumerate(canon[:40])]
    report += ["", "## Errors", *log[:50]]
    (OUT / "report.md").write_text("\n".join(report))
    print("\n".join(report[:9]))


if __name__ == "__main__":
    main()

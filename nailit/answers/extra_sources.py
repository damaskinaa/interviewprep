"""Extra real-interview sources, all fetched the way each site allows (results land in the harvest page cache).

  * interviewing.io: its official agent copy (interviewing-io.agentsite.network), which the main site's robots.txt
    points AI agents to; behavioural / leadership mock transcripts and guides only.
  * Exponent (aced.io): public question bank pages for TPM / programme / operations / behavioural (robots: allow).
  * Hacker News: the official Algolia API; threads where candidates describe real behavioural and manager loops.

    uv run python -m nailit.answers.extra_sources
Then `uv run python -m nailit.answers.harvest --offline` extracts and reclusters everything.
"""
import re
import time

import httpx

from nailit.answers.harvest import _cache, cached

AGENTSITE = "https://interviewing-io.agentsite.network"
ACED_SITEMAP = "https://www.aced.io/sitemap.txt"
KEEP = re.compile(r"behavio|leader|manager|program|tpm|operations|star|conflict|tell-me|amazon-leadership|product|strategy|execution|estimation", re.I)
HN_QUERIES = ["behavioral interview program manager", "technical program manager interview", "amazon bar raiser interview",
              "amazon leadership principles interview", "operations manager interview", "meta behavioral interview",
              "google googleyness interview", "engineering manager behavioral interview", "interview loop TPM",
              "service delivery manager interview"]
UA = {"User-Agent": "NailIt personal interview practice (contact via repo owner)"}


def agentsite_urls(http):
    xml = http.get(AGENTSITE + "/sitemap.xml", headers=UA, timeout=60).text
    return [u for u in re.findall(r"<loc>([^<]+)", xml) if KEEP.search(u) and "/content/" in u]


def aced_urls(http):
    lines = http.get(ACED_SITEMAP, headers=UA, timeout=60, follow_redirects=True).text.split()
    roles = "tpm|program-manager|business-ops|product-ops|product-manager|project-manager|operations-manager|bizops"
    picked = [u for u in lines if re.search(rf"questions\?(type=behavioral|role=({roles}))"
                                            rf"|questions\?company=(amazon|google|meta|microsoft|stripe|aws|pfizer)[a-z-]*&role=({roles})"
                                            r"|questions\?company=[a-z-]+&role=tpm|amazon-leadership|/tpm$|business-operations", u)]
    first = re.compile(r"company=(amazon|google|meta|microsoft|stripe|aws|pfizer)|questions\?(type=behavioral|role=)")
    picked.sort(key=lambda u: not first.search(u))  # target companies and role pages before other companies' TPM pages
    return picked[:160]


def read(http, url):
    """Plain fetch for the agent copy; keyless Jina Reader for JS-rendered pages (polite: one at a time)."""
    if url.startswith(AGENTSITE):
        text = http.get(url, headers=UA, timeout=60).text
        text = re.sub(r"<[^>]+>", " ", text)
    else:
        time.sleep(3.5)  # keyless Jina allows ~20 requests/minute
        text = http.get("https://r.jina.ai/" + url, headers={"X-Return-Format": "markdown"}, timeout=90).text
    text = re.sub(r"[ \t]+", " ", text)
    return {"url": url, "text": text[:60000], "title": url.rsplit("/", 1)[-1], "via": "extra"}


def hn_threads(http):
    docs = []
    for q in HN_QUERIES:
        hits = http.get("https://hn.algolia.com/api/v1/search", params={"query": q, "tags": "story", "hitsPerPage": 8},
                        timeout=60).json()["hits"]
        for h in hits:
            if (h.get("num_comments") or 0) < 15:
                continue
            url = f"https://news.ycombinator.com/item?id={h['objectID']}"
            if _cache("page", url).exists():
                continue
            item = http.get(f"https://hn.algolia.com/api/v1/items/{h['objectID']}", timeout=60).json()
            texts = []

            def walk(node):
                if node.get("text"):
                    texts.append(re.sub(r"<[^>]+>", " ", node["text"]))
                for child in node.get("children") or []:
                    walk(child)
            walk(item)
            body = "\n\n".join(t for t in texts if len(t) > 120)
            if len(body) > 1500:
                cached("page", url, lambda: {"url": url, "text": body[:60000], "title": h["title"], "via": "hn"})
                docs.append(url)
            time.sleep(1)
    return docs


def main():
    http = httpx.Client(follow_redirects=True)
    added = {"interviewing.io": 0, "exponent": 0, "hn": 0}
    for label, urls in (("interviewing.io", agentsite_urls(http)), ("exponent", aced_urls(http))):
        for url in urls:
            if _cache("page", url).exists():
                continue
            try:
                doc = cached("page", url, lambda: read(http, url))
                if doc and len(doc["text"]) > 800:
                    added[label] += 1
            except Exception as error:  # noqa: BLE001
                print("skip", url, type(error).__name__)
        print(label, "pages added:", added[label], "of", len(urls), flush=True)
    added["hn"] = len(hn_threads(http))
    print("hn threads added:", added["hn"])


if __name__ == "__main__":
    main()

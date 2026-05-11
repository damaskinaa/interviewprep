from pathlib import Path
from docx import Document
import json
import re
import hashlib

ROOT = Path(__file__).parent
DOCTRINE_DIR = ROOT / "doctrine"
GENERATED_DIR = DOCTRINE_DIR / "generated"

DOCS = [
    {
        "id": "interview_bible",
        "file": DOCTRINE_DIR / "Interview_Bible_Consolidated.docx",
        "title": "Interview Bible Consolidated",
    },
    {
        "id": "supporting_strategy",
        "file": DOCTRINE_DIR / "Supporting_Strategy_Best_Practices_Guide.docx",
        "title": "Supporting Strategy And Best Practices Guide",
    },
]


def normalize(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_docx_in_order(path: Path) -> str:
    doc = Document(path)
    parts = []

    for block in doc.element.body:
        tag = block.tag.lower()

        if tag.endswith("}p"):
            texts = []
            for node in block.iter():
                if node.tag.lower().endswith("}t") and node.text:
                    texts.append(node.text)
            line = "".join(texts).strip()
            if line:
                parts.append(line)

        elif tag.endswith("}tbl"):
            for row in block.iter():
                if not row.tag.lower().endswith("}tr"):
                    continue

                cells = []
                for cell in row:
                    if not cell.tag.lower().endswith("}tc"):
                        continue

                    cell_texts = []
                    for node in cell.iter():
                        if node.tag.lower().endswith("}t") and node.text:
                            cell_texts.append(node.text)

                    value = " ".join("".join(cell_texts).split())
                    if value:
                        cells.append(value)

                if cells:
                    parts.append(" | ".join(cells))

    return normalize("\n".join(parts))


def is_heading(line: str) -> bool:
    s = line.strip()

    if not s:
        return False

    lowered = s.lower()

    if lowered.startswith("part "):
        return True

    if lowered.startswith("story "):
        return True

    if s in {
        "Tell me about yourself",
        "Why AWS",
        "Why Meta",
        "Why Google",
        "Why Pfizer or a regulated environment",
        "Why should we hire you",
        "Weakness",
        "Failure",
        "First 90 days",
    }:
        return True

    if s.isupper() and len(s) > 8:
        return True

    if lowered in {
        "how to use this document",
        "target role strategy",
        "hard evidence bank",
        "leadership themes to carry through every answer",
        "one minute opening narrative",
        "fully spoken high priority answers",
        "aws leadership principles evidence map",
        "practice prompts by role",
        "freeze recovery protocol",
        "fourteen day plan",
        "thirty day extension",
        "mode b pressure scoring",
        "language precision table",
    }:
        return True

    return False


def chunk_text(doc_id: str, title: str, text: str, max_chars: int = 1600):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks = []
    heading = title
    buffer = []

    def flush():
        nonlocal buffer
        body = normalize("\n".join(buffer))
        if body:
            chunk_id = f"{doc_id}_{len(chunks)+1:04d}"
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "doc_title": title,
                "heading": heading,
                "text": body,
                "sha256": hashlib.sha256(body.encode("utf8")).hexdigest(),
                "char_count": len(body),
            })
        buffer = []

    for line in lines:
        if is_heading(line):
            if buffer:
                flush()
            heading = line
            buffer = [line]
            continue

        if buffer and sum(len(x) for x in buffer) + len(line) > max_chars:
            flush()
            buffer = [heading, line] if heading != title else [line]
        else:
            buffer.append(line)

    flush()
    return chunks


def build_rules(full_text: str):
    return {
        "version": "nailit_doctrine_v1",
        "hard_rules": [
            "Open with the result or decision before context.",
            "Use I language for personal ownership. Use we only after naming personal contribution.",
            "Name the tradeoff. Say what was chosen, what was rejected, and why.",
            "Include result squared. Explain what the result made possible.",
            "Use specificity: context, stakeholder, constraint, method, metric, changed behavior.",
            "For failure answers, own the mistake cleanly, show recovery, show permanent system change, and prove it works.",
            "Use Hero Story for major behavioral answers: hook, situation, conflict, crossroads, hard part, result, result squared, insight.",
            "Use partner frame. Candidate presents evidence and assesses fit, not approval seeking.",
            "Do not apologize for pauses, gaps, or results.",
            "Use falling intonation and calm pace in delivery coaching.",
            "For influence without authority, show trust before the ask, data case, co design, and adoption.",
            "For process improvement, diagnose whether the issue is design, metric, capacity, ownership, or behavior.",
            "For data answers, question the metric itself and verify methodology.",
            "For technical program management, own dependency, scope, blockers, customer impact, and stakeholder alignment without pretending to code.",
            "Use trigger phrases to retrieve stories quickly under pressure.",
            "For people leadership, diagnose skill versus will and show capability created.",
            "For company targeting, tailor stories to role requirements and company interview model.",
            "Never invent metrics, dates, titles, volumes, awards, or revenue impact.",
            "If evidence is missing, mark it as needs confirmation.",
        ],
        "source_integrity": {
            "full_text_retained": True,
            "rule": "Structured rules index the source doctrine. They do not replace it.",
        },
    }


def main():
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks = []
    full_docs = {}

    for doc in DOCS:
        if not doc["file"].exists():
            raise FileNotFoundError(f"Missing file: {doc['file']}")

        text = read_docx_in_order(doc["file"])

        full_docs[doc["id"]] = {
            "title": doc["title"],
            "text": text,
            "sha256": hashlib.sha256(text.encode("utf8")).hexdigest(),
            "char_count": len(text),
        }

        (GENERATED_DIR / f"{doc['id']}_full_text.md").write_text(text, encoding="utf8")
        all_chunks.extend(chunk_text(doc["id"], doc["title"], text))

    full_combined = "\n\n".join(item["text"] for item in full_docs.values())
    rules = build_rules(full_combined)

    (GENERATED_DIR / "doctrine_full_text.json").write_text(
        json.dumps(full_docs, indent=2, ensure_ascii=False),
        encoding="utf8",
    )

    (GENERATED_DIR / "doctrine_chunks.json").write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False),
        encoding="utf8",
    )

    (GENERATED_DIR / "doctrine_rules.json").write_text(
        json.dumps(rules, indent=2, ensure_ascii=False),
        encoding="utf8",
    )

    print("Doctrine generated")
    print("Documents:", len(full_docs))
    print("Chunks:", len(all_chunks))
    print("Rules:", len(rules["hard_rules"]))
    print("Output:", GENERATED_DIR)


if __name__ == "__main__":
    main()

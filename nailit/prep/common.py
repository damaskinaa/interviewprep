import contextvars
import json
import re
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path

from nailit.llm import json_dumps

_current_results = ContextVar("nailit_current_results", default=None)


_current_progress_log = ContextVar("nailit_current_progress_log", default=None)


def _active_progress_log():
    active = _current_progress_log.get()
    if active is None:
        raise RuntimeError("Pipeline progress state is not initialized for this job.")
    return active


def log(stage, message, status="running"):
    event = {
        "time": datetime.now().isoformat(),
        "stage": stage,
        "message": message,
        "status": status,
    }
    _active_progress_log().append(event)
    print(f"[Stage {stage}] {message}")


def report_progress(progress_callback, stage, progress):
    if progress_callback:
        progress_callback(stage, progress)


def submit_with_context(executor, fn, *args):
    """Submit to a thread pool while keeping this job's ContextVar state (results/progress log)."""
    return executor.submit(contextvars.copy_context().run, fn, *args)


def safe_path_part(value, fallback="item"):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "").strip("_")
    return safe[:80] or fallback


def normalize_text(text):
    text = text or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def trim_text(text, max_chars):
    text = normalize_text(text)
    if len(text) <= max_chars:
        return text
    head_len = int(max_chars * 0.62)
    tail_len = max_chars - head_len
    return text[:head_len] + "\n\n[Middle content trimmed after evidence extraction to stay within model limits.]\n\n" + text[-tail_len:]


STAGE_QUALITY_INSTRUCTION = (
    "Think carefully and thoroughly before producing output. Do not rush. "
    "You must produce substantive specific content for this candidate and this role. "
    "Generic content is a failure."
)


def jd_signal_texts(jd_analysis):
    rows = []
    for key in ["must_prove_signals", "jd_signals", "top_responsibilities", "dangerous_gaps", "hidden_expectations"]:
        for item in as_list((jd_analysis or {}).get(key)):
            if isinstance(item, dict):
                text = item.get("signal") or item.get("responsibility") or item.get("gap") or item.get("expectation") or item.get("risk") or item.get("question") or item.get("jd_anchor")
            else:
                text = item
            text = normalize_text(text)
            if text and text not in rows:
                rows.append(text)
    return rows


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def count_words(text):
    return len(re.findall(r"\b\w+\b", text or ""))


SESSION_MODULES = {
    "company_intelligence",
    "role_intelligence",
    "candidate_profile",
    "gap_map",
    "interview_strategy",
    "prep_pack",
}


def session_workspace(session_id, module_name=None):
    base = Path("jobs") / safe_path_part(session_id, "session")
    if module_name:
        base = base / safe_path_part(module_name, "module")
    base.mkdir(parents=True, exist_ok=True)
    return base


def module_artifact_path(session_id, module_name):
    filename = "prep_pack.md" if module_name == "prep_pack" else f"{module_name}.json"
    return session_workspace(session_id, module_name) / filename


def read_module_artifact(session_id, module_name):
    path = module_artifact_path(session_id, module_name)
    if not path.exists():
        raise FileNotFoundError(f"Required module artifact missing: {module_name}")
    if path.suffix == ".md":
        return path.read_text(encoding="utf8")
    content = path.read_text(encoding="utf8")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Artifact '{module_name}' is corrupted or unreadable")


def write_module_json(session_id, module_name, data):
    path = module_artifact_path(session_id, module_name)
    path.write_text(json_dumps(data), encoding="utf8")
    return path


def write_module_markdown(session_id, module_name, markdown):
    path = module_artifact_path(session_id, module_name)
    path.write_text(markdown, encoding="utf8")
    return path


def markdown_list(items):
    lines = []
    for item in as_list(items):
        if isinstance(item, dict):
            safe_parts = []
            for k, v in item.items():
                key = str(k).lower()
                if (
                    key in {"id", "excerpt", "source_type", "source_manifest"}
                    or key.endswith("_id")
                    or "source_id" in key
                    or v in ("", [], None)
                ):
                    continue
                label = str(k).replace("_", " ").strip().title()
                safe_parts.append(f"{label}: {v}")
            text = "; ".join(safe_parts)
        else:
            text = str(item)
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)

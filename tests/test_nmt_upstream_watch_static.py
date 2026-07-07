import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


STATE_PATH = REPO_ROOT / "docs/nmt/_source_library/agnostic_methodology/UPSTREAM_NMT_SYNC_STATE.md"
PROMPT_PATH = REPO_ROOT / "docs/nmt/codex_prompts/11_UPSTREAM_NMT_SYNC_AUDIT.txt"
SCRIPT_PATH = REPO_ROOT / "scripts/check_nmt_upstream.py"
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/nmt-upstream-watch.yml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_upstream_watcher_files_exist():
    assert STATE_PATH.exists()
    assert PROMPT_PATH.exists()
    assert SCRIPT_PATH.exists()
    assert WORKFLOW_PATH.exists()


def test_sync_state_records_detection_only_policy():
    state = read(STATE_PATH)
    required = [
        "https://github.com/zamesin/Next-Move-Theory-Canon-and-Skills",
        "Default branch: main",
        "Last reviewed upstream SHA:",
        "Last checked date:",
        "Last integrated local commit:",
        "Detect automatically",
        "Review manually",
        "Update only after a separate sync-audit run",
        "Run methodology coverage tests before commit",
        "No auto-merge",
        "No auto-rewrite",
        "No silent concept deletion",
        "No inventing unavailable/paywalled methodology",
    ]
    missing = [term for term in required if term not in state]
    assert not missing, f"Missing sync-state terms: {missing}"


def test_manual_sync_audit_prompt_blocks_auto_adoption():
    prompt = read(PROMPT_PATH)
    required = [
        "compare the pinned upstream SHA to current upstream `main`",
        "list changed upstream files",
        "ORIGINAL_NMT_CORE_CHANGE",
        "SKILL_CHANGE",
        "DOC_ONLY_CHANGE",
        "NEW_CANON_CONCEPT",
        "RENAMED_CONCEPT",
        "REMOVED_OR_WEAKENED_CONCEPT",
        "UNAVAILABLE_SOURCE_REFERENCE",
        "No auto-merge",
        "No auto-rewrite",
        "No weakening original NMT core concepts",
        "No weakening Anastasia/team/book enhancement rules",
        "No inventing unavailable/paywalled methodology",
        "Methodology coverage ledger update if needed",
        "Static methodology coverage tests",
        "Full test suite",
        "CI",
        "Human approval required: yes",
        "BLOCKED or READY_TO_REVIEW",
        "Do not commit",
    ]
    missing = [term for term in required if term not in prompt]
    assert not missing, f"Missing prompt safeguards: {missing}"


def test_workflow_is_manual_and_scheduled_only():
    workflow = read(WORKFLOW_PATH)
    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert "cron:" in workflow
    assert "python-version: \"3.12\"" in workflow
    assert "python scripts/check_nmt_upstream.py" in workflow
    assert "pull_request" not in workflow
    assert "git push" not in workflow


def test_checker_script_is_detection_only():
    script = read(SCRIPT_PATH)
    forbidden = [
        "git commit",
        "git push",
        "subprocess",
        "write_text",
        ".write(",
        "Path.write",
        "apply_patch",
    ]
    present = [term for term in forbidden if term in script]
    assert not present, f"Watcher script must be read-only; found: {present}"
    file_write_patterns = [
        r"\bopen\s*\([^)]*,\s*['\"][wa]",
        r"\.open\s*\([^)]*mode\s*=\s*['\"][wa]",
    ]
    matched = [pattern for pattern in file_write_patterns if re.search(pattern, script)]
    assert not matched, f"Watcher script must not open local files for writing: {matched}"
    assert "urllib.request" in script
    assert "return 1" in script
    assert "return 0" in script
    assert "Manual review required" in script
    assert "no local files were modified" in script

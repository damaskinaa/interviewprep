#!/usr/bin/env python3
"""Detection-only watcher for upstream Next Move Theory Canon & Skills changes."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = (
    REPO_ROOT
    / "docs"
    / "nmt"
    / "_source_library"
    / "agnostic_methodology"
    / "UPSTREAM_NMT_SYNC_STATE.md"
)
DEFAULT_REPO_URL = "https://github.com/zamesin/Next-Move-Theory-Canon-and-Skills"
DEFAULT_BRANCH = "main"
API_BASE = "https://api.github.com"


def read_state() -> str:
    return STATE_PATH.read_text(encoding="utf-8")


def field_value(markdown: str, field_name: str, fallback: str = "UNKNOWN") -> str:
    pattern = rf"^\s*-\s*{re.escape(field_name)}:\s*(.+?)\s*$"
    match = re.search(pattern, markdown, flags=re.MULTILINE)
    if not match:
        return fallback
    value = match.group(1).strip()
    return value or fallback


def github_owner_repo(repo_url: str) -> tuple[str, str]:
    match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/#?]+)", repo_url)
    if not match:
        raise ValueError(f"Unsupported GitHub repository URL: {repo_url}")
    return match.group("owner"), match.group("repo").removesuffix(".git")


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nailit-nmt-upstream-watch",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def current_branch_sha(owner: str, repo: str, branch: str) -> str:
    data = fetch_json(f"{API_BASE}/repos/{owner}/{repo}/commits/{branch}")
    return data["sha"]


def changed_files(owner: str, repo: str, base_sha: str, head_sha: str) -> list[str]:
    if not base_sha or base_sha.upper() == "UNKNOWN":
        return []
    data = fetch_json(f"{API_BASE}/repos/{owner}/{repo}/compare/{base_sha}...{head_sha}")
    return [item["filename"] for item in data.get("files", [])]


def main() -> int:
    try:
        state = read_state()
        repo_url = field_value(state, "Upstream repository URL", DEFAULT_REPO_URL)
        branch = field_value(state, "Default branch", DEFAULT_BRANCH)
        last_reviewed = field_value(state, "Last reviewed upstream SHA")
        owner, repo = github_owner_repo(repo_url)
        current_sha = current_branch_sha(owner, repo, branch)

        print(f"Upstream repository: {repo_url}")
        print(f"Default branch: {branch}")
        print(f"Last reviewed SHA: {last_reviewed}")
        print(f"Current upstream SHA: {current_sha}")

        changed = last_reviewed.upper() == "UNKNOWN" or last_reviewed != current_sha
        print(f"Upstream changed: {'yes' if changed else 'no'}")

        if not changed:
            print("No manual review needed.")
            return 0

        compare_url = (
            f"{repo_url}/commits/{branch}"
            if last_reviewed.upper() == "UNKNOWN"
            else f"{repo_url}/compare/{last_reviewed}...{current_sha}"
        )
        print(f"Review URL: {compare_url}")

        files = changed_files(owner, repo, last_reviewed, current_sha)
        if files:
            print("Changed upstream files:")
            for filename in files:
                print(f"- {filename}")
        else:
            print("Changed upstream files: unavailable because no reviewed SHA is pinned.")

        print(
            "Manual review required: run "
            "docs/nmt/codex_prompts/11_UPSTREAM_NMT_SYNC_AUDIT.txt"
        )
        print("Watcher policy: detection only; no local files were modified.")
        return 1
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError) as exc:
        print(f"NMT upstream watcher failed: {exc}", file=sys.stderr)
        print("Manual review required because upstream status could not be verified.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

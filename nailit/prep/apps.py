"""Writes prep output to ~/NailIt/apps/<company>-<role>/ (research.md, jd_map.md, questions.md)."""
import logging
import re
from datetime import datetime, timezone

from nailit import library
from nailit.prep.common import as_list, normalize_text

logger = logging.getLogger(__name__)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "unknown"


def app_dir(session):
    path = library.home() / "apps" / f"{slug(session['company_name'])}-{slug(session['role_name'])}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def _write(session, name, lines):
    """Best effort: the module JSON is already saved, so a failed markdown export only logs."""
    try:
        path = app_dir(session) / name
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf8")
        return path
    except OSError as error:
        logger.warning("could not write %s: %s", name, error)
        return None


def write_research(session, result, sources):
    """External company facts with their fetch date; prep re-fetches every run instead of reusing them."""
    lines = [f"# {session['company_name']} — research", "", f"Generated {_today()}. Re-fetched on every prep run; never reused.", ""]
    for key, title in (("official_company_signals", "Official signals"), ("interview_process_signals", "Interview process"),
                       ("role_specific_signals", "Role signals"), ("directional_themes", "Directional themes (not facts)")):
        items = [i for i in as_list(result.get(key)) if isinstance(i, dict)]
        if items:
            lines += [f"## {title}", ""]
            lines += [f"- {normalize_text(i.get('signal') or i.get('theme'))} ({i.get('confidence', 'unknown')})" for i in items]
            lines.append("")
    lines += ["## Sources", ""]
    for source in sources:
        lines.append(f"- [{source.get('title') or source.get('url')}]({source.get('url')}) — fetched {source.get('fetched_at') or _today()}")
    return _write(session, "research.md", lines)


def _cell(text):
    return normalize_text(text).replace("|", "\\|")


def _story_for(competency, stories):
    wanted = normalize_text(competency).lower()

    def whole_words(short, long):
        return bool(short) and re.search(rf"(?<!\w){re.escape(short)}(?!\w)", long) is not None

    for story in stories:
        tags = [normalize_text(t).lower() for t in as_list(story.get("competencies")) + as_list(story.get("lp_tags"))]
        if wanted and any(whole_words(tag, wanted) or whole_words(wanted, tag) for tag in tags):
            return f"{story['id']} {story.get('title', '')}".strip()
    return "no story yet (gap)"


def write_jd_map(session, role_result, stories=None):
    """requirement → competency → story, with stories matched on competencies / lp_tags from stories.md."""
    if stories is None:
        try:
            stories = library.load_me()["stories"]["stories"]
        except library.LibraryError as error:
            logger.warning("jd_map without stories: %s", error.errors[:3])
            stories = []
    lines = [f"# {session['role_name']} at {session['company_name']} — JD map", "",
             "| Requirement | Competency | Story |", "|---|---|---|"]
    for seed in as_list(role_result.get("question_seeds")):
        if isinstance(seed, dict) and seed.get("maps_to_jd_line_or_requirement"):
            competency = normalize_text(seed.get("competency")) or "unspecified"
            row = (seed["maps_to_jd_line_or_requirement"], competency, _story_for(competency, stories))
            lines.append("| " + " | ".join(_cell(c) for c in row) + " |")
    return _write(session, "jd_map.md", lines)


def write_questions(session, strategy):
    lines = [f"# {session['company_name']} {session['role_name']} — questions", ""]
    for round_item in as_list(strategy.get("questions_by_round")):
        if not isinstance(round_item, dict):
            continue
        lines += [f"## {normalize_text(round_item.get('round_name')) or 'Round'}", ""]
        for item in as_list(round_item.get("questions")):
            if isinstance(item, dict) and item.get("question"):
                story = normalize_text(item.get("assigned_story"))
                lines.append(f"- {normalize_text(item['question'])}" + (f" — story: {story}" if story else ""))
        lines.append("")
    return _write(session, "questions.md", lines)

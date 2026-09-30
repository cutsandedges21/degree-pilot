"""J2 baseline: keyword lookup against the taxonomy, no model."""
import re

from model.jobs.j1 import Activity, Bullet, Course, parse_records
from model.jobs.j2 import Tag
from model.jobs.skills import Taxonomy


def _find(term: str, text: str) -> re.Match | None:
    """Whole-word, case-insensitive; spaces in `term` match any whitespace."""
    pattern = re.escape(term).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![\w+#]){pattern}(?![\w+#])", text, re.IGNORECASE)


def tag(item_text: str, taxonomy: Taxonomy) -> list[Tag]:
    records, _ = parse_records(item_text)
    if not records or not isinstance(records[0], (Course, Activity)):
        return []
    head = records[0]
    if isinstance(head, Course):
        text, quote = head.title, False
    else:
        parts = [head.title, head.org, head.role] + [r.text for r in records[1:] if isinstance(r, Bullet)]
        text, quote = "\n".join(parts), True
    tags = []
    for skill in taxonomy.skills:
        for keyword in skill.keywords:
            match = _find(keyword, text)
            if match:
                tags.append(Tag(skill.id, " ".join(match.group(0).split()) if quote else ""))
                break
    tags += [Tag("tool", tool) for tool in taxonomy.tools if _find(tool, text)]
    return tags

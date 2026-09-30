"""J1 baseline: regular expressions, no model."""
import re

from model.jobs.j1 import Activity, Bullet, Course, Deliverable, Record

_SEASON = r"(?:Fall|Autumn|Winter|Spring|Summer|Automne|Hiver|Été|Ete|Printemps)"
_TERM = (
    rf"(?:{_SEASON}\s+(?:Term\s+|Semester\s+|Session\s+)?\d{{4}}"
    rf"|\d{{4}}\s+{_SEASON}"
    r"|[AHE]\d{4}"
    rf"|\d{{4}}-\d{{2,4}}(?:\s+{_SEASON})?)"
)
_TERM_LINE = re.compile(
    rf"^\s*(?:(?:Term|Session|Semester)\s*:?\s*)?(?P<term>{_TERM})(?:\s{{2,}}|\t|\s*$)", re.IGNORECASE
)
_CODE = r"(?:[A-Z]{2,5}[ -]?\d{3,4}[A-Z]?\d?|\d{3}-[A-Z0-9]{3}-[A-Z0-9]{2})"
_COURSE_LINE = re.compile(rf"^\s*(?:(?P<term>(?i:{_TERM}))\s+)?(?P<code>{_CODE})(?=\s)(?P<rest>.*)$")
_LETTER_GRADE = re.compile(r"A\+|A|A-|B\+|B|B-|C\+|C|C-|D\+|D|D-|F|P|CR|NCR|W|INC|IP")
_INTEGER = re.compile(r"\d{1,3}%?")
_DECIMAL = re.compile(r"\d{1,2}\.\d{1,2}")


def _is_grade_or_number(token: str) -> bool:
    return bool(_LETTER_GRADE.fullmatch(token) or _INTEGER.fullmatch(token) or _DECIMAL.fullmatch(token))


def _course(match: re.Match, term: str) -> Course:
    tokens = match.group("rest").split()
    tail: list[str] = []
    while tokens and len(tail) < 4 and _is_grade_or_number(tokens[-1]):
        tail.insert(0, tokens.pop())
    letters = [t for t in tail if _LETTER_GRADE.fullmatch(t)]
    integers = [t for t in tail if _INTEGER.fullmatch(t)]
    decimals = [t for t in tail if _DECIMAL.fullmatch(t) and float(t) <= 6]
    grade = letters[0] if letters else next(
        (t for t in integers if t.endswith("%") or int(t.rstrip("%")) > 6), "")
    credits = decimals[0] if decimals else next(
        (t for t in integers if not t.endswith("%") and int(t) <= 6 and t != grade), "")
    # Tail tokens before the first one we used belong to the title ("Physics 2").
    used = [index for index, token in enumerate(tail) if token in (grade, credits)]
    title = tokens + tail[: min(used, default=len(tail))]
    return Course(match.group("code"), " ".join(title), match.group("term") or term, grade, credits)


def _transcript(text: str) -> list[Record]:
    records: list[Record] = []
    term = ""
    for line in text.splitlines():
        course = _COURSE_LINE.match(line)
        if course:
            records.append(_course(course, term))
        elif header := _TERM_LINE.match(line):
            term = header.group("term")
    return records


_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
_WHEN = rf"(?:(?:{_MONTH}\s+)?(?:19|20)\d{{2}}|Present|Current|Now)"
_DATES = re.compile(
    rf"{_WHEN}\s*(?:[-–—]|to)\s*{_WHEN}|{_MONTH}\s+(?:19|20)\d{{2}}|(?<!\d)(?:19|20)\d{{2}}(?!\d)",
    re.IGNORECASE,
)
_BULLET = re.compile(r"^\s*[•·▪◦●*–-]\s+(?P<text>\S.*)$")
_SPLIT = re.compile(r"\s+(?:at|@)\s+|\s*[|,]\s*|\s+[–—-]\s+|\t|\s{2,}")
_SECTIONS = {
    "experience": "job", "work experience": "job", "employment": "job", "professional experience": "job",
    "projects": "project", "leadership": "club", "activities": "club", "extracurricular activities": "club",
    "extracurriculars": "club", "volunteer": "volunteer", "volunteering": "volunteer",
    "volunteer experience": "volunteer", "awards": "award", "honors": "award", "honours": "award",
    "awards and honours": "award", "research": "research", "research experience": "research",
    "athletics": "sport", "sports": "sport",
    "education": None, "skills": None, "interests": None, "references": None, "certifications": None,
}
_KIND_WORDS = (
    (r"intern(?:ship)?s?", "internship"), (r"volunteer(?:s|ing)?", "volunteer"), (r"president", "club"),
    (r"captain", "sport"), (r"club", "club"), (r"society", "club"), (r"association", "club"),
    (r"council", "club"), (r"research", "research"), (r"project", "project"), (r"award", "award"),
    (r"scholarship", "award"),
)


def _activity(line: str, dates: re.Match, section: str) -> Activity:
    # Two spaces keep the text before and after the dates in separate parts.
    head = f"{line[: dates.start()]}  {line[dates.end():]}".strip(" \t|,–—-")
    parts = [part.strip() for part in _SPLIT.split(head) if part.strip()]
    lowered = head.lower()
    kind = next((k for pattern, k in _KIND_WORDS if re.search(rf"\b{pattern}\b", lowered)), section)
    return Activity(kind, parts[0] if parts else "", parts[1] if len(parts) > 1 else "",
                    dates.group(0).strip(), "")


def _resume(text: str) -> list[Record]:
    records: list[Record] = []
    section: str | None = "other"
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = stripped.rstrip(":").lower()
        if heading in _SECTIONS:
            section = _SECTIONS[heading]
            continue
        if section is None:
            continue
        bullet = _BULLET.match(line)
        if bullet:
            text_part = bullet.group("text").split("|")[0].strip()
            if text_part and records and isinstance(records[-1], (Activity, Bullet)):
                records.append(Bullet(text_part))
            continue
        dates = _DATES.search(stripped)
        if dates:
            records.append(_activity(stripped, dates, section))
        elif records and isinstance(records[-1], Bullet):
            records[-1] = Bullet(f"{records[-1].text} {stripped}")  # a wrapped bullet
    return records


_EXTRACTORS = {"transcript": _transcript, "resume": _resume}


def extract(text: str, doc_type: str) -> list[Record]:
    if doc_type not in _EXTRACTORS:
        raise ValueError(f"unknown doc type {doc_type!r}; expected one of {tuple(_EXTRACTORS)}")
    return _EXTRACTORS[doc_type](text)

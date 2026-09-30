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


_EXTRACTORS = {"transcript": _transcript}


def extract(text: str, doc_type: str) -> list[Record]:
    if doc_type not in _EXTRACTORS:
        raise ValueError(f"unknown doc type {doc_type!r}; expected one of {tuple(_EXTRACTORS)}")
    return _EXTRACTORS[doc_type](text)

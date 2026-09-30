"""J1 extract: document text in, one record per line out.

    C | code | title | term | grade | credits     a course
    A | kind | title | org | dates | role          an activity (job, club, project, ...)
    B | text                                       a bullet under the activity above
    D | name | weight | due                        a graded deliverable in a syllabus

Values are copied verbatim from the input (the copy rule); any value may be empty.
Normalizing grades, dates and credits is deterministic code's job, not J1's.
"""
from dataclasses import dataclass, fields
from typing import ClassVar

from model.jobs.normalize import contains_words

ACTIVITY_KINDS = ("job", "internship", "project", "club", "volunteer", "award", "research", "sport", "other")


class RecordError(ValueError):
    pass


@dataclass(frozen=True)
class Course:
    TAG: ClassVar[str] = "C"
    code: str = ""
    title: str = ""
    term: str = ""
    grade: str = ""
    credits: str = ""


@dataclass(frozen=True)
class Activity:
    TAG: ClassVar[str] = "A"
    kind: str = "other"
    title: str = ""
    org: str = ""
    dates: str = ""
    role: str = ""


@dataclass(frozen=True)
class Bullet:
    TAG: ClassVar[str] = "B"
    text: str = ""


@dataclass(frozen=True)
class Deliverable:
    TAG: ClassVar[str] = "D"
    name: str = ""
    weight: str = ""
    due: str = ""


Record = Course | Activity | Bullet | Deliverable
RECORD_TYPES = {cls.TAG: cls for cls in (Course, Activity, Bullet, Deliverable)}


def field_names(record_or_type) -> tuple[str, ...]:
    return tuple(f.name for f in fields(record_or_type))


def format_record(record: Record) -> str:
    values = [getattr(record, name) for name in field_names(record)]
    for value in values:
        if "|" in value or "\n" in value:
            raise RecordError(f"a value may not contain '|' or a line break: {value!r}")
    return " | ".join([record.TAG, *values]).rstrip()


def parse_record(line: str) -> Record:
    parts = [part.strip() for part in line.split("|")]
    record_type = RECORD_TYPES.get(parts[0])
    if record_type is None:
        raise RecordError(f"unknown record type {parts[0]!r}")
    names = field_names(record_type)
    if len(parts) - 1 != len(names):
        raise RecordError(f"{parts[0]} needs {len(names)} values, got {len(parts) - 1}")
    record = record_type(**dict(zip(names, parts[1:])))
    if isinstance(record, Activity) and record.kind not in ACTIVITY_KINDS:
        raise RecordError(f"unknown activity kind {record.kind!r}")
    return record


def parse_records(text: str) -> tuple[list[Record], list[str]]:
    """Records, plus one message per bad line. Blank lines and # comments are skipped."""
    records, errors = [], []
    for number, line in enumerate(text.split("\n"), 1):   # not splitlines(): values may hold \x0c
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            records.append(parse_record(line))
        except RecordError as error:
            errors.append(f"line {number}: {error}")
    return records, errors


def format_records(records: list[Record]) -> str:
    return "".join(format_record(record) + "\n" for record in records)


def copy_violations(record: Record, source: str) -> list[str]:
    """Values in `record` that don't appear in `source` as whole words (short values must
    also match case). An activity's kind is a label, not a copy."""
    return [
        f"{name}={getattr(record, name)!r}"
        for name in field_names(record)
        if name != "kind" and getattr(record, name) and not contains_words(source, getattr(record, name), match_case_if_short=True)
    ]

import pytest

from model.jobs.j1 import (
    Activity, Bullet, Course, Deliverable, RecordError,
    copy_violations, format_record, format_records, parse_record, parse_records,
)


def test_course_round_trip():
    course = Course("ECON 201", "Intermediate Microeconomics", "Fall 2025", "A-", "3.0")
    line = format_record(course)
    assert line == "C | ECON 201 | Intermediate Microeconomics | Fall 2025 | A- | 3.0"
    assert parse_record(line) == course


def test_empty_values_survive_round_trip():
    deliverable = Deliverable("Quiz 1", "10%", "")
    assert format_record(deliverable) == "D | Quiz 1 | 10% |"
    assert parse_record("D | Quiz 1 | 10% |") == deliverable
    assert parse_record("C | 603-101-MQ | Intro to College English |  | 78 | 2.00").term == ""


def test_activity_and_bullet():
    line = "A | club | Economics Society | Vanier College | 2024–2025 | President"
    assert parse_record(line) == Activity("club", "Economics Society", "Vanier College", "2024–2025", "President")
    assert parse_record("B | Organized 6 speaker events") == Bullet("Organized 6 speaker events")


@pytest.mark.parametrize("line", ["X | a", "C | too | few", "A | hobby | t | o | d | r", "B | a | b"])
def test_bad_lines_raise(line):
    with pytest.raises(RecordError):
        parse_record(line)


def test_values_cannot_hold_separators():
    with pytest.raises(RecordError):
        format_record(Bullet("a | b"))


def test_parse_records_skips_blanks_and_comments_and_reports_errors():
    records, errors = parse_records("# header\n\nC | A 1 | T | F | A | 3\nnonsense\n")
    assert records == [Course("A 1", "T", "F", "A", "3")]
    assert errors == ["line 4: unknown record type 'nonsense'"]


def test_format_records_ends_each_line():
    assert format_records([Bullet("x"), Bullet("y")]) == "B | x\nB | y\n"


def test_copy_rule_flags_values_not_in_source():
    source = "ECON 201  Intermediate Microeconomics  3.0  A-"
    course = Course("ECON 201", "Intermediate Microeconomics", "Fall 2025", "A-", "3.0")
    assert copy_violations(course, source) == ["term='Fall 2025'"]


def test_copy_rule_ignores_activity_kind():
    assert copy_violations(Activity("club", "Chess Club"), "Chess Club, 2024") == []

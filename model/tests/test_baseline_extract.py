import pytest

from model.baselines.extract import extract
from model.jobs.j1 import Course, copy_violations

US = """UNOFFICIAL TRANSCRIPT
Fall 2024
ECON 101   Principles of Microeconomics   3.00   A
MATH 151   Calculus I                     4.00   B+
Spring 2025
STAT 250   Introduction to Statistics     3.00   A-
"""

CA = """2024-2025 Winter
ECO101H1 Principles of Microeconomics 0.50 87 A
MAT135H1 Calculus I 0.50 72 B-
"""

CEGEP = """Autumn 2024
603-101-MQ  Introduction to College English  78  2.00
201-NYA-05  Calculus I  91  2.66
Winter 2025
360-124-VA  Introduction to Psychology  85  2.00
"""


def test_us_transcript():
    assert extract(US, "transcript") == [
        Course("ECON 101", "Principles of Microeconomics", "Fall 2024", "A", "3.00"),
        Course("MATH 151", "Calculus I", "Fall 2024", "B+", "4.00"),
        Course("STAT 250", "Introduction to Statistics", "Spring 2025", "A-", "3.00"),
    ]


def test_canadian_transcript_prefers_the_letter_grade():
    assert extract(CA, "transcript") == [
        Course("ECO101H1", "Principles of Microeconomics", "2024-2025 Winter", "A", "0.50"),
        Course("MAT135H1", "Calculus I", "2024-2025 Winter", "B-", "0.50"),
    ]


def test_cegep_transcript_uses_percent_grades():
    assert extract(CEGEP, "transcript") == [
        Course("603-101-MQ", "Introduction to College English", "Autumn 2024", "78", "2.00"),
        Course("201-NYA-05", "Calculus I", "Autumn 2024", "91", "2.66"),
        Course("360-124-VA", "Introduction to Psychology", "Winter 2025", "85", "2.00"),
    ]


def test_term_on_the_course_line():
    assert extract("Fall 2025 ECON 201 Intermediate Microeconomics 3.0 A-\n", "transcript") == [
        Course("ECON 201", "Intermediate Microeconomics", "Fall 2025", "A-", "3.0"),
    ]


def test_number_in_a_title_stays_in_the_title():
    assert extract("PHYS 102 Physics 2 3.00 B\n", "transcript")[0].title == "Physics 2"


def test_unknown_doc_type():
    with pytest.raises(ValueError):
        extract("", "poem")


@pytest.mark.parametrize("text", [US, CA, CEGEP])
def test_transcripts_obey_the_copy_rule(text):
    for record in extract(text, "transcript"):
        assert copy_violations(record, text) == []


from model.jobs.j1 import Activity, Bullet

RESUME = """Jordan Lee
jordan@example.com

EXPERIENCE
Data Analyst Intern, Shopify    May 2025 – Aug 2025
• Built SQL dashboards tracking weekly
  sales for 3 regions
• Presented findings to the marketing team

LEADERSHIP
President, Economics Society    Sep 2024 – Present
- Organized 6 speaker events for 120 members

SKILLS
Excel, SQL, Python
"""


def test_resume():
    assert extract(RESUME, "resume") == [
        Activity("internship", "Data Analyst Intern", "Shopify", "May 2025 – Aug 2025", ""),
        Bullet("Built SQL dashboards tracking weekly sales for 3 regions"),
        Bullet("Presented findings to the marketing team"),
        Activity("club", "President", "Economics Society", "Sep 2024 – Present", ""),
        Bullet("Organized 6 speaker events for 120 members"),
    ]


def test_resume_obeys_the_copy_rule():
    for record in extract(RESUME, "resume"):
        assert copy_violations(record, RESUME) == []


from model.jobs.j1 import Deliverable

SYLLABUS = """ECON 201 — Intermediate Microeconomics
Grading
Problem sets (5)          20%
Midterm Exam ........... 25%    Oct 21
Participation (10%)
Final Exam               45%    Dec 12, 2025
Total                    100%
A+  90–100%
"""


def test_syllabus():
    assert extract(SYLLABUS, "syllabus") == [
        Deliverable("Problem sets (5)", "20%", ""),
        Deliverable("Midterm Exam", "25%", "Oct 21"),
        Deliverable("Participation", "10%", ""),
        Deliverable("Final Exam", "45%", "Dec 12, 2025"),
    ]


def test_syllabus_obeys_the_copy_rule():
    for record in extract(SYLLABUS, "syllabus"):
        assert copy_violations(record, SYLLABUS) == []


def test_note_becomes_one_activity_with_bullets():
    assert extract("Finished my SQL project\nAnalyzed 10k rows of rent data\n", "note") == [
        Activity("other", "Finished my SQL project"),
        Bullet("Analyzed 10k rows of rent data"),
    ]

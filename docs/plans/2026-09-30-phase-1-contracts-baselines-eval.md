# Phase 1: Contracts, Baselines, Eval — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the text formats of the model's three jobs (J1 extract, J2 tag, J3 explain), build rule-based baselines for each, and score any solver on real labelled documents with `python -m model.eval --solver baseline`.

**Architecture:** `model/jobs/` owns each job's wire format and its checks (copy rule, known skills, fact check). `model/baselines/` answers each job with regexes, keyword lookups and templates. `model/eval/` loads real test documents from `DP_DATA_DIR/testsets/`, scores any `Solver` (text in, text out, the same interface the trained model will get), and prints a scorecard with bootstrap confidence intervals. `tools/pdftext/` turns PDFs into text with pdf.js, the same code the browser app will use.

**Tech Stack:** Python 3.13 standard library + pytest. Node 24 + pdfjs-dist (Mozilla, Apache-2.0). No HuggingFace, no model yet.

**Spec:** `docs/specs/2026-09-30-degreepilot-design.md` (sections "The model's three jobs" and "Verification").

**Execution:** inline, on branch `phase-1`. Each finished step is ticked (`- [x]`) and committed with its task. To resume after a break, start at the first unticked step.

---

## File structure

```
pyproject.toml                  pytest config, Python version
.gitattributes                  LF line endings (Kaggle runs Linux)
contracts/
  jobs.md                       the three formats, for humans (Task 7)
  skills.json                   20 skills + tool list J2 tags against (Task 4)
model/
  paths.py                      REPO_ROOT, CONTRACTS_DIR, data_dir(), testsets_dir()
  jobs/
    normalize.py                norm(), contains(): shared by copy rule and scorers
    j1.py                       Course/Activity/Bullet/Deliverable records, parse/format, copy rule
    skills.py                   taxonomy loader
    j2.py                       Tag, Item, gold.j2 blocks, tag checks
    j3.py                       Facts, parse/format, check_explanation()
  baselines/
    extract.py                  J1 by regex: transcript, resume, syllabus, note
    tag.py                      J2 by keyword lookup
    explain.py                  J3 by template
  solvers.py                    Solver protocol, BaselineSolver, get_solver()
  eval/
    bootstrap.py                percentile bootstrap CI
    score_j1.py                 record pairing, per-field counts
    score_j2.py                 tag-key counts
    score_j3.py                 fact-check pass rate
    testset.py                  EvalDoc, load_testset()
    j3cases.py                  J3 test inputs built from labelled docs
    __main__.py                 the scorecard CLI
    label.py                    prefill + check gold files
    intake.py                   add a document to the test set
  tests/                        one test file per module
tools/pdftext/
  lines.mjs                     pdf.js text items -> lines (pure; the app reuses it)
  extract.mjs                   CLI: PDF -> text
```

Every command below runs from the repo root in Git Bash:
`C:\Users\sport\OneDrive\Documents\CodingPersonal\degree-pilot`.

Every commit message ends with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
(pass it as a second `-m`).

---

### Task 1: Scaffolding

**Files:**
- Create: `pyproject.toml`, `.gitattributes`, `model/__init__.py`, `model/paths.py`
- Test: `model/tests/test_paths.py`

- [x] **Step 1: Create the venv and install pytest**

```bash
python -m venv .venv
.venv/Scripts/python -m pip install "pytest>=8"
```

Expected: `Successfully installed ... pytest-8.x`

- [x] **Step 2: Write `pyproject.toml` and `.gitattributes`**

```toml
[project]
name = "degreepilot-model"
version = "0.1.0"
description = "DegreePilot's model track: job contracts, baselines, evaluation, training"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
testpaths = ["model/tests"]
pythonpath = ["."]
```

```
* text=auto eol=lf
*.pdf binary
*.png binary
```

- [x] **Step 3: Write the failing test** `model/tests/test_paths.py`

```python
from model import paths


def test_data_dir_defaults_to_repo_data(monkeypatch):
    monkeypatch.delenv("DP_DATA_DIR", raising=False)
    assert paths.data_dir() == paths.REPO_ROOT / "data"


def test_data_dir_follows_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DP_DATA_DIR", str(tmp_path))
    assert paths.data_dir() == tmp_path
    assert paths.testsets_dir() == tmp_path / "testsets"


def test_contracts_dir_is_in_repo():
    assert paths.CONTRACTS_DIR == paths.REPO_ROOT / "contracts"
```

- [x] **Step 4: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_paths.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model'`

- [x] **Step 5: Write `model/__init__.py` and `model/paths.py`**

`model/__init__.py`:

```python
"""DegreePilot's model track."""
```

`model/paths.py`:

```python
"""Where DegreePilot keeps things on disk.

Large or private files (test documents, downloads, checkpoints) live under the data
directory, which is gitignored. Set DP_DATA_DIR to move it, e.g. outside OneDrive.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts"


def data_dir() -> Path:
    """DP_DATA_DIR if set, else <repo>/data. Read on every call so tests can change it."""
    return Path(os.environ.get("DP_DATA_DIR", REPO_ROOT / "data"))


def testsets_dir() -> Path:
    return data_dir() / "testsets"
```

- [x] **Step 6: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest -v`
Expected: 3 passed

- [x] **Step 7: Commit**

```bash
git add pyproject.toml .gitattributes model/__init__.py model/paths.py model/tests/test_paths.py
git commit -m "chore: add the Python project and data paths" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Normalization

**Files:**
- Create: `model/jobs/__init__.py`, `model/jobs/normalize.py`
- Test: `model/tests/test_normalize.py`

- [x] **Step 1: Write the failing test** `model/tests/test_normalize.py`

```python
from model.jobs.normalize import contains, norm


def test_collapses_whitespace_and_case():
    assert norm("  Intermediate \n  Microeconomics ") == "intermediate microeconomics"


def test_keeps_grade_signs_and_code_hyphens():
    assert norm("A-") == "a-"
    assert norm("B+") == "b+"
    assert norm("603-101-MQ") == "603-101-mq"


def test_trims_edge_punctuation():
    assert norm("(Fall 2025)") == "fall 2025"
    assert norm("• Built dashboards.") == "built dashboards"


def test_nfkc():
    assert norm("Ｆｉｎａｎｃｅ") == "finance"


def test_contains_across_line_breaks():
    assert contains("ECON 201\nIntermediate\nMicroeconomics", "intermediate microeconomics")
    assert not contains("ECON 201", "ECON 202")
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_normalize.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.jobs'`

- [x] **Step 3: Write the code**

`model/jobs/__init__.py`:

```python
"""The three jobs' wire formats and the checks on them."""
```

`model/jobs/normalize.py`:

```python
"""Text normalization shared by the copy rule and the scorers.

Two values are the same when they match after NFKC, casefolding, collapsing whitespace
and trimming punctuation from the ends. Inner punctuation stays: it carries meaning in
course codes (603-101-MQ) and grades (A-), so "-" and "+" are never trimmed.
"""
import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_EDGE = " .,;:!?\"'()[]{}*•·"


def norm(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    return _WHITESPACE.sub(" ", text).strip(_EDGE)


def contains(haystack: str, needle: str) -> bool:
    """True if `needle` appears in `haystack` once both are normalized."""
    return norm(needle) in norm(haystack)
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_normalize.py -v`
Expected: 5 passed

- [x] **Step 5: Commit**

```bash
git add model/jobs model/tests/test_normalize.py
git commit -m "feat(jobs): normalize values for the copy rule and scoring" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: J1 records

**Files:**
- Create: `model/jobs/j1.py`
- Test: `model/tests/test_j1.py`

- [x] **Step 1: Write the failing test** `model/tests/test_j1.py`

```python
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
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_j1.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.jobs.j1'`

- [x] **Step 3: Write `model/jobs/j1.py`**

```python
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

from model.jobs.normalize import contains

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
    for number, line in enumerate(text.splitlines(), 1):
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
    """Values in `record` that don't appear in `source`. An activity's kind is a label, not a copy."""
    return [
        f"{name}={getattr(record, name)!r}"
        for name in field_names(record)
        if name != "kind" and getattr(record, name) and not contains(source, getattr(record, name))
    ]
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_j1.py -v`
Expected: 12 passed

- [x] **Step 5: Commit**

```bash
git add model/jobs/j1.py model/tests/test_j1.py
git commit -m "feat(jobs): add the J1 record format and copy rule" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Skill taxonomy

**Files:**
- Create: `contracts/skills.json`, `model/jobs/skills.py`
- Test: `model/tests/test_skills.py`

- [x] **Step 1: Write the failing test** `model/tests/test_skills.py`

```python
import pytest

from model.jobs.skills import load_taxonomy, parse_taxonomy


def test_taxonomy_loads_with_unique_ids():
    taxonomy = load_taxonomy()
    assert len(taxonomy.skills) == 20
    assert {"writing", "quantitative", "leadership", "programming"} <= taxonomy.skill_ids
    assert {"SQL", "Excel", "Python"} <= set(taxonomy.tools)


def test_every_skill_has_keywords():
    for skill in load_taxonomy().skills:
        assert len(skill.keywords) >= 5, skill.id


def test_skill_lookup():
    assert load_taxonomy().skill("writing").name == "Written communication"


def _raw(*ids, keyword="x"):
    return {"skills": [{"id": i, "name": i, "description": "", "keywords": [keyword]} for i in ids], "tools": []}


def test_rejects_duplicate_ids():
    with pytest.raises(ValueError):
        parse_taxonomy(_raw("a", "a"))


def test_rejects_reserved_tool_id():
    with pytest.raises(ValueError):
        parse_taxonomy(_raw("tool"))


def test_rejects_uppercase_keywords():
    with pytest.raises(ValueError):
        parse_taxonomy(_raw("a", keyword="Excel"))
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_skills.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.jobs.skills'`

- [x] **Step 3: Write `contracts/skills.json`**

Keywords are whole words or phrases, lowercase. The J2 baseline matches them; the model
learns the skill ids.

```json
{
  "version": 1,
  "skills": [
    {"id": "writing", "name": "Written communication", "description": "Writing clear reports, essays and articles.",
     "keywords": ["writing", "written", "wrote", "essay", "essays", "composition", "report", "reports", "article", "articles", "blog", "newsletter", "journalism", "editor", "edited", "rhetoric", "literature", "english"]},
    {"id": "public_speaking", "name": "Presenting and public speaking", "description": "Speaking to groups: presentations, pitches, debates.",
     "keywords": ["presentation", "presentations", "presented", "public speaking", "speech", "debate", "pitch", "pitched", "speaker", "spoke", "oral", "emcee"]},
    {"id": "interpersonal", "name": "Interpersonal communication", "description": "Listening and talking one to one: interviews, counselling, networking.",
     "keywords": ["communication", "communications", "listening", "counselling", "counseling", "conversation", "interviewed", "interviewing", "networking", "relations"]},
    {"id": "quantitative", "name": "Quantitative reasoning", "description": "Mathematics and statistics.",
     "keywords": ["calculus", "algebra", "statistics", "statistical", "probability", "mathematics", "math", "maths", "econometrics", "quantitative", "differential equations", "discrete"]},
    {"id": "data_analysis", "name": "Data analysis", "description": "Turning data into findings: spreadsheets, dashboards, regressions.",
     "keywords": ["data", "dataset", "datasets", "analytics", "dashboard", "dashboards", "visualization", "visualisation", "regression", "spreadsheet", "spreadsheets", "statistics", "excel", "sql", "tableau"]},
    {"id": "programming", "name": "Programming", "description": "Writing software.",
     "keywords": ["programming", "programmed", "python", "java", "javascript", "software", "coding", "coded", "computer science", "algorithms", "website", "app", "database", "databases"]},
    {"id": "research", "name": "Research", "description": "Finding out what is known and testing what is not.",
     "keywords": ["research", "researched", "literature review", "thesis", "survey", "surveys", "methodology", "research methods", "investigated", "investigation", "fieldwork"]},
    {"id": "critical_thinking", "name": "Critical thinking and argument", "description": "Weighing ideas and building arguments.",
     "keywords": ["philosophy", "ethics", "logic", "argument", "arguments", "critical", "humanities", "theory", "debate"]},
    {"id": "problem_solving", "name": "Problem solving", "description": "Working through problems that have no set method.",
     "keywords": ["problem solving", "problem-solving", "solved", "troubleshooting", "troubleshot", "optimization", "optimized", "case competition", "hackathon", "puzzle"]},
    {"id": "lab_work", "name": "Lab and experimental work", "description": "Running experiments and lab procedures.",
     "keywords": ["laboratory", "lab", "labs", "experiment", "experiments", "experimental", "chemistry", "biology", "physics"]},
    {"id": "leadership", "name": "Leading people", "description": "Taking charge of a group and its results.",
     "keywords": ["president", "vice-president", "captain", "lead", "led", "leader", "leadership", "founder", "co-founder", "founded", "chair", "supervised", "supervisor", "manager", "head"]},
    {"id": "teamwork", "name": "Teamwork", "description": "Working well inside a group.",
     "keywords": ["team", "teams", "teammates", "collaborated", "collaboration", "collaborative", "group", "cooperated"]},
    {"id": "organization", "name": "Planning and organizing", "description": "Planning events, schedules and logistics.",
     "keywords": ["organized", "organised", "organizing", "planned", "planning", "coordinated", "coordinator", "coordinating", "scheduled", "scheduling", "logistics", "event", "events", "managed"]},
    {"id": "creativity", "name": "Creative work and design", "description": "Making original work: design, art, media.",
     "keywords": ["design", "designed", "art", "arts", "drawing", "painting", "music", "film", "photography", "creative", "illustrated", "illustration", "animation", "theatre", "theater", "sculpture"]},
    {"id": "teaching", "name": "Teaching and mentoring", "description": "Helping other people learn.",
     "keywords": ["tutor", "tutored", "tutoring", "taught", "teaching", "mentor", "mentored", "mentoring", "coach", "coached", "instructor", "education"]},
    {"id": "persuasion", "name": "Persuasion and sales", "description": "Changing minds: sales, marketing, fundraising, negotiation.",
     "keywords": ["sales", "sold", "marketing", "fundraising", "fundraised", "negotiated", "negotiation", "persuaded", "campaign", "campaigns", "advocacy", "recruited"]},
    {"id": "client_service", "name": "Serving customers and clients", "description": "Looking after customers, clients, patients or guests.",
     "keywords": ["customer", "customers", "client", "clients", "cashier", "server", "served", "hospitality", "retail", "receptionist", "patients", "guests"]},
    {"id": "financial", "name": "Money and budgeting", "description": "Budgets, accounting and financial decisions.",
     "keywords": ["budget", "budgets", "budgeting", "accounting", "finance", "financial", "treasurer", "bookkeeping", "invoices", "investment", "investments"]},
    {"id": "languages", "name": "Languages", "description": "Speaking, reading or translating a second language.",
     "keywords": ["french", "spanish", "german", "mandarin", "chinese", "arabic", "italian", "japanese", "portuguese", "bilingual", "translation", "translated", "français"]},
    {"id": "building", "name": "Hands-on technical work", "description": "Building, wiring, prototyping and repairing physical things.",
     "keywords": ["built", "build", "engineering", "circuit", "circuits", "cad", "prototype", "prototyped", "robotics", "electronics", "mechanical", "assembled", "repaired", "installed"]}
  ],
  "tools": ["Excel", "SQL", "Python", "RStudio", "Java", "JavaScript", "TypeScript", "C++", "C#", "HTML", "CSS", "React",
            "Tableau", "Power BI", "SPSS", "Stata", "MATLAB", "SAS", "AutoCAD", "SolidWorks", "Figma", "Photoshop",
            "Illustrator", "Canva", "Git", "Linux", "Google Analytics", "Salesforce", "QuickBooks", "WordPress"]
}
```

- [x] **Step 4: Write `model/jobs/skills.py`**

```python
"""The skill taxonomy J2 tags against, loaded from contracts/skills.json."""
import json
from dataclasses import dataclass
from functools import cache

from model.paths import CONTRACTS_DIR


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    description: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class Taxonomy:
    skills: tuple[Skill, ...]
    tools: tuple[str, ...]

    @property
    def skill_ids(self) -> frozenset[str]:
        return frozenset(skill.id for skill in self.skills)

    def skill(self, skill_id: str) -> Skill:
        for skill in self.skills:
            if skill.id == skill_id:
                return skill
        raise KeyError(skill_id)


def parse_taxonomy(raw: dict) -> Taxonomy:
    skills = []
    for entry in raw["skills"]:
        keywords = tuple(entry["keywords"])
        if any(keyword != keyword.lower() for keyword in keywords):
            raise ValueError(f"{entry['id']}: keywords must be lowercase")
        skills.append(Skill(entry["id"], entry["name"], entry["description"], keywords))
    ids = [skill.id for skill in skills]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate skill id")
    if "tool" in ids:
        raise ValueError("the id 'tool' is reserved for J2 tool lines")
    return Taxonomy(tuple(skills), tuple(raw["tools"]))


@cache
def load_taxonomy() -> Taxonomy:
    return parse_taxonomy(json.loads((CONTRACTS_DIR / "skills.json").read_text(encoding="utf-8")))
```

- [x] **Step 5: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_skills.py -v`
Expected: 6 passed

- [x] **Step 6: Commit**

```bash
git add contracts/skills.json model/jobs/skills.py model/tests/test_skills.py
git commit -m "feat(jobs): add the skill taxonomy J2 tags against" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: J2 tags and items

**Files:**
- Create: `model/jobs/j2.py`
- Test: `model/tests/test_j2.py`

- [x] **Step 1: Write the failing test** `model/tests/test_j2.py`

```python
import pytest

from model.jobs.j1 import Activity, Bullet, Course, Deliverable
from model.jobs.j2 import (
    Item, Tag, TagError, format_gold_j2, format_tags, items_from_records,
    parse_gold_j2, parse_tag, tag_violations,
)
from model.jobs.skills import load_taxonomy


def test_tag_round_trip():
    for line in ["quantitative", "leadership | President", "tool | SQL"]:
        assert format_tags([parse_tag(line)]) == line + "\n"


@pytest.mark.parametrize("line", ["tool", "a | b | c", " | x"])
def test_bad_tags_raise(line):
    with pytest.raises(TagError):
        parse_tag(line)


def test_keys_ignore_quotes_and_tool_case():
    assert Tag("leadership", "Led").key == "leadership"
    assert Tag("tool", "sql").key == Tag("tool", "SQL").key


def test_items_group_bullets_under_activities():
    course = Course("STAT 250", "Statistics")
    club = Activity("club", "Chess Club")
    records = [course, club, Bullet("Ran weekly games"), Deliverable("Quiz", "5%"), Bullet("orphan")]
    assert items_from_records(records) == [Item((course,)), Item((club, Bullet("Ran weekly games")))]


GOLD = (
    "C | STAT 250 | Statistics |  | A |\n"
    "  quantitative\n"
    "  data_analysis\n"
    "\n"
    "A | club | Chess Club |  |  | President\n"
    "B | Ran weekly games\n"
    "  leadership | President\n"
)


def test_gold_j2_round_trip():
    pairs, errors = parse_gold_j2(GOLD)
    assert errors == []
    assert [tag.key for tag in pairs[0][1]] == ["quantitative", "data_analysis"]
    assert pairs[1][0].records[1] == Bullet("Ran weekly games")
    assert pairs[1][1] == [Tag("leadership", "President")]
    assert format_gold_j2(pairs) == GOLD


def test_gold_j2_errors():
    _, errors = parse_gold_j2("  quantitative\nD | Quiz | 5% |\n  writing\n")
    assert errors == [
        "line 1: a tag before any record",
        "tags under a record that isn't a course or activity: D | Quiz | 5% |",
    ]


def test_tag_violations():
    taxonomy = load_taxonomy()
    source = "A | club | Chess Club |  |  | President\nB | Used Excel to track members\n"
    assert tag_violations(Tag("leadership", "President"), source, taxonomy) == []
    assert tag_violations(Tag("tool", "Excel"), source, taxonomy) == []
    assert tag_violations(Tag("juggling"), source, taxonomy) == ["unknown skill 'juggling'"]
    assert tag_violations(Tag("tool", "SQL"), source, taxonomy) == ["'SQL' is not in the input"]
    assert tag_violations(Tag("tool", "Notepad"), source + "Notepad", taxonomy) == ["unknown tool 'Notepad'"]
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_j2.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.jobs.j2'`

- [x] **Step 3: Write `model/jobs/j2.py`**

```python
"""J2 tag: one item (a course, or an activity with its bullets) in, what it shows out.

    skill_id                  a skill from contracts/skills.json
    skill_id | quoted words   the same, with the input words that justify it (activities)
    tool | Name               a tool from the taxonomy's list that the input names

Gold files (gold.j2) hold each item's J1 record lines followed by its tags, indented two
spaces, with a blank line between items.
"""
from dataclasses import dataclass

from model.jobs.j1 import Activity, Bullet, Course, Record, RecordError, format_records, parse_record
from model.jobs.normalize import contains, norm
from model.jobs.skills import Taxonomy


class TagError(ValueError):
    pass


@dataclass(frozen=True)
class Tag:
    skill: str        # a skill id, or "tool"
    value: str = ""   # the quote for a skill, the name for a tool

    @property
    def key(self) -> str:
        """What scoring compares. Quotes aren't scored; tool names ignore case."""
        return f"tool:{norm(self.value)}" if self.skill == "tool" else self.skill


@dataclass(frozen=True)
class Item:
    records: tuple[Record, ...]   # a Course, or an Activity followed by its Bullets

    @property
    def text(self) -> str:
        return format_records(list(self.records))


def format_tag(tag: Tag) -> str:
    return f"{tag.skill} | {tag.value}" if tag.value else tag.skill


def parse_tag(line: str) -> Tag:
    parts = [part.strip() for part in line.split("|")]
    if len(parts) > 2 or not parts[0]:
        raise TagError(f"bad tag line {line.strip()!r}")
    tag = Tag(parts[0], parts[1] if len(parts) == 2 else "")
    if tag.skill == "tool" and not tag.value:
        raise TagError("a tool line needs a name")
    return tag


def parse_tags(text: str) -> tuple[list[Tag], list[str]]:
    tags, errors = [], []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            tags.append(parse_tag(line))
        except TagError as error:
            errors.append(f"line {number}: {error}")
    return tags, errors


def format_tags(tags: list[Tag]) -> str:
    return "".join(format_tag(tag) + "\n" for tag in tags)


def _group(records: list[Record]) -> list[list[int]]:
    """Indices of each item's records. A deliverable closes the open activity."""
    groups, activity_open = [], False
    for index, record in enumerate(records):
        if isinstance(record, (Course, Activity)):
            groups.append([index])
            activity_open = isinstance(record, Activity)
        elif isinstance(record, Bullet) and activity_open:
            groups[-1].append(index)
        else:
            activity_open = False
    return groups


def items_from_records(records: list[Record]) -> list[Item]:
    return [Item(tuple(records[i] for i in group)) for group in _group(records)]


def parse_gold_j2(text: str) -> tuple[list[tuple[Item, list[Tag]]], list[str]]:
    records, tags_under, errors = [], {}, []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            if line[0] in " \t":
                if not records:
                    raise TagError("a tag before any record")
                tags_under.setdefault(len(records) - 1, []).append(parse_tag(line))
            else:
                records.append(parse_record(line))
        except (RecordError, TagError) as error:
            errors.append(f"line {number}: {error}")
    pairs, grouped = [], set()
    for group in _group(records):
        grouped.update(group)
        tags = [tag for index in group for tag in tags_under.get(index, [])]
        pairs.append((Item(tuple(records[i] for i in group)), tags))
    errors += [
        f"tags under a record that isn't a course or activity: {format_records([records[i]]).strip()}"
        for i in tags_under if i not in grouped
    ]
    return pairs, errors


def format_gold_j2(pairs: list[tuple[Item, list[Tag]]]) -> str:
    return "\n".join(item.text + "".join(f"  {format_tag(tag)}\n" for tag in tags) for item, tags in pairs)


def tag_violations(tag: Tag, source: str, taxonomy: Taxonomy) -> list[str]:
    problems = []
    if tag.skill == "tool":
        if norm(tag.value) not in {norm(tool) for tool in taxonomy.tools}:
            problems.append(f"unknown tool {tag.value!r}")
    elif tag.skill not in taxonomy.skill_ids:
        problems.append(f"unknown skill {tag.skill!r}")
    if tag.value and not contains(source, tag.value):
        problems.append(f"{tag.value!r} is not in the input")
    return problems
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_j2.py -v`
Expected: 9 passed

- [x] **Step 5: Commit**

```bash
git add model/jobs/j2.py model/tests/test_j2.py
git commit -m "feat(jobs): add the J2 tag format and gold blocks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: J3 facts and the fact check

**Files:**
- Create: `model/jobs/j3.py`
- Test: `model/tests/test_j3.py`

- [x] **Step 1: Write the failing test** `model/tests/test_j3.py`

```python
import pytest

from model.jobs.j3 import FactsError, check_explanation, format_facts, parse_facts
from model.jobs.skills import load_taxonomy

FACTS = """style: why_fit
career: Data Analyst
skill: Quantitative reasoning (High)
evidence: STAT 250 Introduction to Statistics, A
evidence: ECON 301 Econometrics, A-
"""


def test_parse_and_format_round_trip():
    facts = parse_facts(FACTS)
    assert facts.style == "why_fit"
    assert facts.values("evidence") == ["STAT 250 Introduction to Statistics, A", "ECON 301 Econometrics, A-"]
    assert format_facts(facts) == FACTS


@pytest.mark.parametrize("text", ["career: X\n", "style: poem\n", "style: gap\nhobby: x\n", "style: gap\ncareer\n"])
def test_bad_facts_raise(text):
    with pytest.raises(FactsError):
        parse_facts(text)


def test_supported_text_passes():
    text = "Data Analyst could fit you: your A in STAT 250 and A- in ECON 301 show quantitative reasoning."
    check = check_explanation(text, parse_facts(FACTS), load_taxonomy())
    assert check.unsupported == ()
    assert check.used == 4
    assert check.ok


def test_invented_course_grade_number_and_skill_are_caught():
    text = "Data Analyst fits: you got a B in MATH 101, beat 90% of peers, and show programming."
    check = check_explanation(text, parse_facts(FACTS), load_taxonomy())
    assert set(check.unsupported) == {"MATH 101", "101", "90", "B", "Programming"}
    assert not check.ok
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_j3.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.jobs.j3'`

- [x] **Step 3: Write `model/jobs/j3.py`**

```python
"""J3 explain: facts in, one to three plain sentences out.

The input is `key: value` lines. `style` comes first: why_fit, gap or action. Other keys:
career, skill, evidence (belongs to the skill above it), have, need, tool, action,
because, effort. The output may only state what the facts state.
"""
import re
from dataclasses import dataclass

from model.jobs.normalize import norm
from model.jobs.skills import Taxonomy

STYLES = ("why_fit", "gap", "action")
KEYS = ("career", "skill", "evidence", "have", "need", "tool", "action", "because", "effort")

_CODE = re.compile(r"\b[A-Z]{2,5} ?-?\d{3,4}[A-Z]?\d?\b|\b\d{3}-[A-Z0-9]{3}-[A-Z0-9]{2}\b")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_SIGNED_GRADE = re.compile(r"(?<![A-Za-z])[A-D][+-](?![A-Za-z0-9+-])")
_PLAIN_GRADE = re.compile(r"\b(?i:an?|grade of|got|earned)\s+([A-DF])(?=[\s,.;:)]|$)")
_TOKEN = re.compile(r"[^\s,;()]+")


class FactsError(ValueError):
    pass


@dataclass(frozen=True)
class Facts:
    style: str
    items: tuple[tuple[str, str], ...]

    def values(self, key: str) -> list[str]:
        return [value for k, value in self.items if k == key]


@dataclass(frozen=True)
class Check:
    unsupported: tuple[str, ...]   # claims in the text that the facts don't make
    used: int                      # how many facts the text mentions

    @property
    def ok(self) -> bool:
        return not self.unsupported and self.used >= 2


def parse_facts(text: str) -> Facts:
    style, items = None, []
    for line in text.splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not separator or not value:
            raise FactsError(f"expected 'key: value', got {line!r}")
        if key == "style":
            if style is not None or value not in STYLES:
                raise FactsError(f"bad style line {line!r}")
            style = value
        elif key in KEYS:
            items.append((key, value))
        else:
            raise FactsError(f"unknown key {key!r}")
    if style is None:
        raise FactsError("missing style")
    return Facts(style, tuple(items))


def format_facts(facts: Facts) -> str:
    return f"style: {facts.style}\n" + "".join(f"{key}: {value}\n" for key, value in facts.items)


def _handles(value: str) -> set[str]:
    """Ways a text can mention a fact: the value, its part before a comma, the value
    without a (level), or a course code inside it."""
    handles = {norm(value), norm(value.split(",")[0]), norm(re.sub(r"\s*\(.*?\)", "", value))}
    handles.update(norm(match.group(0)) for match in _CODE.finditer(value))
    return {handle for handle in handles if len(handle) >= 2}


def check_explanation(text: str, facts: Facts, taxonomy: Taxonomy) -> Check:
    facts_text = norm(" ".join(value for _, value in facts.items))
    fact_tokens = {norm(token) for _, value in facts.items for token in _TOKEN.findall(value)}
    output = norm(text)
    unsupported = [m.group(0) for m in _CODE.finditer(text) if norm(m.group(0)) not in facts_text]
    unsupported += [number for number in _NUMBER.findall(text) if number not in facts_text]
    grades = _SIGNED_GRADE.findall(text) + _PLAIN_GRADE.findall(text)
    unsupported += [grade for grade in grades if norm(grade) not in fact_tokens]
    unsupported += [
        skill.name for skill in taxonomy.skills
        if norm(skill.name) in output and norm(skill.name) not in facts_text
    ]
    used = sum(1 for _, value in facts.items if any(handle in output for handle in _handles(value)))
    return Check(tuple(unsupported), used)
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_j3.py -v`
Expected: 7 passed

- [x] **Step 5: Commit**

```bash
git add model/jobs/j3.py model/tests/test_j3.py
git commit -m "feat(jobs): add the J3 facts format and fact check" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: The contract document

**Files:**
- Create: `contracts/jobs.md`

- [x] **Step 1: Write `contracts/jobs.md`**

````markdown
# Job contracts

DegreePilot's model does three jobs. This file fixes the text each job reads and writes.
`model/jobs/` parses and checks these formats; the browser app will do the same.

The formats can change until Phase 4 generates training data from them. After that, a
change means regenerating the data and retraining.

## J1 extract

Reads a chunk of a transcript, résumé, syllabus or short note. Writes one record per
line, fields separated by ` | `.

| Record | Fields | Example |
|---|---|---|
| `C` course | code, title, term, grade, credits | `C \| ECON 201 \| Intermediate Microeconomics \| Fall 2025 \| A- \| 3.0` |
| `A` activity | kind, title, org, dates, role | `A \| club \| Economics Society \| Vanier College \| 2024–2025 \| President` |
| `B` bullet | text, belonging to the activity above | `B \| Organized 6 speaker events for 120 members` |
| `D` deliverable | name, weight, due | `D \| Midterm exam \| 25% \| Oct 21` |

1. **Copy, don't rewrite.** Every value except an activity's kind appears in the input as
   written, after normalization (NFKC, casefolded, whitespace collapsed, edge punctuation
   trimmed, never `-` or `+`). `Oct 21` stays `Oct 21`; turning it into a date is code's job.
2. Any value may be empty. No value contains `|` or a line break.
3. `kind` is one of: job, internship, project, club, volunteer, award, research, sport, other.
4. When a course shows both a percent and a letter grade, the grade is the letter.
5. A term printed above a block of courses belongs to every course in the block.

## J2 tag

Reads one item: a `C` line, or an `A` line with its `B` lines. Writes what it shows:

    quantitative                 a skill id from contracts/skills.json
    leadership | President       a skill id with the input words that justify it
    tool | SQL                   a tool from the list in contracts/skills.json

1. Skill ids and tool names come from `contracts/skills.json` only.
2. Quotes and tool names appear in the item's text.
3. Courses need no quotes; activities quote their evidence.

Gold files (`gold.j2`): each item's record lines, then its tags indented two spaces, a
blank line between items.

## J3 explain

Reads `key: value` facts and writes one to three plain sentences.

    style: why_fit
    career: Data Analyst
    skill: Quantitative reasoning (High)
    evidence: STAT 250 Introduction to Statistics, A
    evidence: ECON 301 Econometrics, A-

`style` comes first: `why_fit`, `gap` or `action`. Other keys: career, skill, evidence
(belongs to the skill above it), have, need, tool, action, because, effort.

`check_explanation` enforces:
1. Every course code, number, grade and skill name in the text appears in the facts.
2. The text uses at least two facts.

## Model framing (from Phase 2)

    <|job:extract|>transcript<|in|>…text…<|out|>…records…<|end|>
    <|job:tag|><|in|>…item…<|out|>…tags…<|end|>
    <|job:explain|><|in|>…facts…<|out|>…sentences…<|end|>
````

- [x] **Step 2: Commit**

```bash
git add contracts/jobs.md
git commit -m "docs(contracts): write down the three job formats" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: J1 baseline, transcripts

**Files:**
- Create: `model/baselines/__init__.py`, `model/baselines/extract.py`
- Test: `model/tests/test_baseline_extract.py`

- [x] **Step 1: Write the failing test** `model/tests/test_baseline_extract.py`

These fixtures are made up, and only tests see them. Real test documents come in Task 23.

```python
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
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_extract.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.baselines'`

- [x] **Step 3: Write the code**

`model/baselines/__init__.py`:

```python
"""Rule-based answers to J1–J3: the bar the model must beat, and its fallback."""
```

`model/baselines/extract.py`:

```python
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
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_extract.py -v`
Expected: 9 passed

- [x] **Step 5: Commit**

```bash
git add model/baselines model/tests/test_baseline_extract.py
git commit -m "feat(baselines): extract courses from US, Canadian and CEGEP transcripts" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: J1 baseline, résumés

**Files:**
- Modify: `model/baselines/extract.py` (add the résumé extractor and register it)
- Test: `model/tests/test_baseline_extract.py` (append)

- [x] **Step 1: Append the failing test** to `model/tests/test_baseline_extract.py`

```python
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
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_extract.py -v`
Expected: 2 new tests FAIL with `ValueError: unknown doc type 'resume'`

- [x] **Step 3: Add the résumé extractor** to `model/baselines/extract.py`, above `_EXTRACTORS`

```python
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
```

Then replace the `_EXTRACTORS` line with:

```python
_EXTRACTORS = {"transcript": _transcript, "resume": _resume}
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_extract.py -v`
Expected: 11 passed

- [x] **Step 5: Commit**

```bash
git add model/baselines/extract.py model/tests/test_baseline_extract.py
git commit -m "feat(baselines): extract activities and bullets from résumés" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: J1 baseline, syllabi and notes

**Files:**
- Modify: `model/baselines/extract.py` (add two extractors and register them)
- Test: `model/tests/test_baseline_extract.py` (append)

- [x] **Step 1: Append the failing test** to `model/tests/test_baseline_extract.py`

```python
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
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_extract.py -v`
Expected: 3 new tests FAIL with `ValueError: unknown doc type`

- [x] **Step 3: Add the extractors** to `model/baselines/extract.py`, above `_EXTRACTORS`

```python
_WEIGHT = re.compile(r"(?<![\d.])\d{1,3}(?:\.\d+)?\s?%")
_DUE = re.compile(
    rf"{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+(?:19|20)\d{{2}})?"
    rf"|\d{{1,2}}\s+{_MONTH}(?:\s+(?:19|20)\d{{2}})?"
    r"|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?|Week\s+\d{1,2}",
    re.IGNORECASE,
)
_NAME_EDGE = " \t:.-–—([]•*|"   # no ")" so "Problem sets (5)" keeps its bracket
_NOT_DELIVERABLES = {"total", "grade", "grades", "grading", "weight"}


def _syllabus(text: str) -> list[Record]:
    records: list[Record] = []
    for line in text.splitlines():
        weight = _WEIGHT.search(line)
        if not weight or float(weight.group(0).rstrip("% ")) > 100:
            continue
        before = line[: weight.start()].strip(_NAME_EDGE)
        name = re.split(r"\t|\s{2,}", before)[-1].strip(_NAME_EDGE) if before else ""
        if (not re.search(r"[A-Za-z]{2}", name) or _LETTER_GRADE.fullmatch(name)
                or name.lower() in _NOT_DELIVERABLES or len(name) > 80):
            continue
        due = _DUE.search(line[weight.end():]) or _DUE.search(before)
        records.append(Deliverable(name, weight.group(0), due.group(0) if due else ""))
    return records


def _note(text: str) -> list[Record]:
    lines = [line.strip().split("|")[0].strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return []
    return [Activity("other", lines[0]), *(Bullet(line) for line in lines[1:])]
```

Then replace the `_EXTRACTORS` line with:

```python
_EXTRACTORS = {"transcript": _transcript, "resume": _resume, "syllabus": _syllabus, "note": _note}
DOC_TYPES = tuple(_EXTRACTORS)
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_extract.py -v`
Expected: 14 passed

- [x] **Step 5: Commit**

```bash
git add model/baselines/extract.py model/tests/test_baseline_extract.py
git commit -m "feat(baselines): extract syllabus deliverables and notes" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: J2 baseline, keyword tagger

**Files:**
- Create: `model/baselines/tag.py`
- Test: `model/tests/test_baseline_tag.py`

- [x] **Step 1: Write the failing test** `model/tests/test_baseline_tag.py`

```python
from model.baselines.tag import tag
from model.jobs.j2 import Tag, tag_violations
from model.jobs.skills import load_taxonomy


def test_course_tags_come_from_the_title_without_quotes():
    item = "C | STAT 250 | Introduction to Statistics | Fall 2024 | A | 3.00\n"
    assert tag(item, load_taxonomy()) == [Tag("quantitative"), Tag("data_analysis")]


def test_activity_tags_quote_the_input():
    item = ("A | club | President | Economics Society | Sep 2024 – Present |\n"
            "B | Organized 6 events and a budget in Excel\n")
    assert tag(item, load_taxonomy()) == [
        Tag("data_analysis", "Excel"),
        Tag("leadership", "President"),
        Tag("organization", "Organized"),
        Tag("financial", "budget"),
        Tag("tool", "Excel"),
    ]


def test_tags_obey_the_quote_rule():
    taxonomy = load_taxonomy()
    item = "A | job | Cashier | Metro |  |\nB | Served 200 customers a day\n"
    tags = tag(item, taxonomy)
    assert Tag("client_service", "customers") in tags
    for t in tags:
        assert tag_violations(t, item, taxonomy) == []


def test_no_tags_for_non_items():
    assert tag("D | Quiz | 5% |\n", load_taxonomy()) == []
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_tag.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.baselines.tag'`

- [x] **Step 3: Write `model/baselines/tag.py`**

```python
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
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_tag.py -v`
Expected: 4 passed

- [x] **Step 5: Commit**

```bash
git add model/baselines/tag.py model/tests/test_baseline_tag.py
git commit -m "feat(baselines): tag skills and tools by keyword" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: J3 baseline, templates

**Files:**
- Create: `model/baselines/explain.py`
- Test: `model/tests/test_baseline_explain.py`

- [x] **Step 1: Write the failing test** `model/tests/test_baseline_explain.py`

```python
import pytest

from model.baselines.explain import explain
from model.jobs.j3 import check_explanation, parse_facts
from model.jobs.skills import load_taxonomy

FACTS = {
    "why_fit": ("style: why_fit\ncareer: Data Analyst\nskill: Quantitative reasoning (High)\n"
                "evidence: STAT 250 Introduction to Statistics, A\nevidence: ECON 301 Econometrics, A-\n"),
    "gap": "style: gap\ncareer: Data Analyst\nhave: Quantitative reasoning\nneed: Programming\ntool: SQL\n",
    "action": ("style: action\naction: Build a small SQL project with public housing data\n"
               "because: Data Analyst roles ask for SQL\neffort: 3 hours a week\n"),
}


@pytest.mark.parametrize("style", FACTS)
def test_templates_pass_the_fact_check(style):
    facts = parse_facts(FACTS[style])
    text = explain(facts)
    check = check_explanation(text, facts, load_taxonomy())
    assert check.ok, (text, check)


def test_wording():
    assert explain(parse_facts(FACTS["why_fit"])) == (
        "Data Analyst could fit you. Quantitative reasoning (High) shows in "
        "STAT 250 Introduction to Statistics (A) and ECON 301 Econometrics (A-).")
    assert explain(parse_facts(FACTS["gap"])) == (
        "For Data Analyst, you already show Quantitative reasoning. To get there, build Programming and SQL.")
    assert explain(parse_facts(FACTS["action"])) == (
        "Build a small SQL project with public housing data (3 hours a week). Data Analyst roles ask for SQL.")
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_explain.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.baselines.explain'`

- [x] **Step 3: Write `model/baselines/explain.py`**

```python
"""J3 baseline: fill-in templates. Passes the fact check by construction; reads stiffly."""
from model.jobs.j3 import Facts


def _join(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _evidence(value: str) -> str:
    """'STAT 250 Statistics, A' reads better as 'STAT 250 Statistics (A)'."""
    head, comma, tail = value.rpartition(",")
    return f"{head.strip()} ({tail.strip()})" if comma else value


def _skills_with_evidence(facts: Facts) -> list[tuple[str, list[str]]]:
    groups: list[tuple[str, list[str]]] = []
    for key, value in facts.items:
        if key == "skill":
            groups.append((value, []))
        elif key == "evidence" and groups:
            groups[-1][1].append(value)
    return groups


def explain(facts: Facts) -> str:
    career = next(iter(facts.values("career")), "This path")
    if facts.style == "why_fit":
        sentences = [f"{career} could fit you."]
        for skill, evidence in _skills_with_evidence(facts)[:2]:
            if evidence:
                sentences.append(f"{skill} shows in {_join([_evidence(e) for e in evidence[:2]])}.")
            else:
                sentences.append(f"{skill} is one of your strengths.")
        return " ".join(sentences)
    if facts.style == "gap":
        have = facts.values("have")
        need = facts.values("need") + facts.values("tool")
        sentences = [f"For {career}, you already show {_join(have)}." if have else f"For {career}, start with the basics."]
        if need:
            sentences.append(f"To get there, build {_join(need)}.")
        return " ".join(sentences)
    action = next(iter(facts.values("action")), "")
    effort = next(iter(facts.values("effort")), "")
    because = next(iter(facts.values("because")), "")
    sentence = f"{action} ({effort})." if effort else f"{action}."
    return f"{sentence} {because}." if because else sentence
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_baseline_explain.py -v`
Expected: 4 passed

- [x] **Step 5: Commit**

```bash
git add model/baselines/explain.py model/tests/test_baseline_explain.py
git commit -m "feat(baselines): explain with templates that pass the fact check" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: The solver interface

A solver answers the three jobs in their wire formats: text in, text out. The trained
model will be another solver with the same three methods.

**Files:**
- Create: `model/solvers.py`
- Test: `model/tests/test_solvers.py`

- [x] **Step 1: Write the failing test** `model/tests/test_solvers.py`

```python
import pytest

from model.solvers import get_solver


def test_baseline_solver_speaks_the_wire_formats():
    solver = get_solver("baseline")
    assert solver.name == "baseline"
    assert solver.extract("ECON 101 Principles 3.00 A\n", "transcript") == "C | ECON 101 | Principles |  | A | 3.00\n"
    assert solver.tag("C | STAT 250 | Statistics |  | A |\n") == "quantitative\ndata_analysis\n"
    text = solver.explain("style: gap\ncareer: Data Analyst\nhave: Teamwork\nneed: Programming\n")
    assert text.startswith("For Data Analyst")


def test_unknown_solver():
    with pytest.raises(KeyError):
        get_solver("gpt")
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_solvers.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.solvers'`

- [x] **Step 3: Write `model/solvers.py`**

```python
"""Solvers answer J1–J3 in the wire formats. The baseline is rules; the model comes later."""
from typing import Protocol

from model.baselines.explain import explain
from model.baselines.extract import extract
from model.baselines.tag import tag
from model.jobs.j1 import format_records
from model.jobs.j2 import format_tags
from model.jobs.j3 import parse_facts
from model.jobs.skills import load_taxonomy


class Solver(Protocol):
    name: str

    def extract(self, text: str, doc_type: str) -> str: ...

    def tag(self, item_text: str) -> str: ...

    def explain(self, facts_text: str) -> str: ...


class BaselineSolver:
    name = "baseline"

    def __init__(self) -> None:
        self.taxonomy = load_taxonomy()

    def extract(self, text: str, doc_type: str) -> str:
        return format_records(extract(text, doc_type))

    def tag(self, item_text: str) -> str:
        return format_tags(tag(item_text, self.taxonomy))

    def explain(self, facts_text: str) -> str:
        return explain(parse_facts(facts_text))


SOLVERS = {"baseline": BaselineSolver}


def get_solver(name: str) -> Solver:
    if name not in SOLVERS:
        raise KeyError(f"unknown solver {name!r}; known: {sorted(SOLVERS)}")
    return SOLVERS[name]()
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_solvers.py -v`
Expected: 2 passed

- [x] **Step 5: Commit**

```bash
git add model/solvers.py model/tests/test_solvers.py
git commit -m "feat: add the solver interface and the baseline solver" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: Bootstrap confidence intervals

Resample documents (not rows: rows in one document aren't independent) to show how much
a score could move with a different set of documents.

**Files:**
- Create: `model/eval/__init__.py`, `model/eval/bootstrap.py`
- Test: `model/tests/test_bootstrap.py`

- [x] **Step 1: Write the failing test** `model/tests/test_bootstrap.py`

```python
import math

from model.eval.bootstrap import bootstrap_ci


def test_constant_statistic_has_zero_width():
    assert bootstrap_ci([1, 2, 3], lambda sample: 5.0, n=50) == (5.0, 5.0)


def test_interval_brackets_the_mean_and_is_repeatable():
    units = list(range(20))

    def mean(sample):
        return sum(sample) / len(sample)

    low, high = bootstrap_ci(units, mean, n=500)
    assert low < mean(units) < high
    assert bootstrap_ci(units, mean, n=500) == (low, high)


def test_empty_units_give_nan():
    low, high = bootstrap_ci([], lambda sample: 1.0)
    assert math.isnan(low) and math.isnan(high)
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_bootstrap.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.eval'`

- [x] **Step 3: Write the code**

`model/eval/__init__.py`:

```python
"""Scoring solvers on real, hand-labelled documents."""
```

`model/eval/bootstrap.py`:

```python
"""Percentile bootstrap: how much a score could move with a different sample of documents."""
import math
import random
from collections.abc import Callable, Sequence


def bootstrap_ci(units: Sequence, statistic: Callable[[list], float], n: int = 1000,
                 seed: int = 0, alpha: float = 0.05) -> tuple[float, float]:
    if not units:
        return math.nan, math.nan
    rng = random.Random(seed)
    values = []
    for _ in range(n):
        value = statistic([units[rng.randrange(len(units))] for _ in units])
        if not math.isnan(value):
            values.append(value)
    if not values:
        return math.nan, math.nan
    values.sort()
    return values[int(alpha / 2 * (len(values) - 1))], values[round((1 - alpha / 2) * (len(values) - 1))]
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_bootstrap.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add model/eval model/tests/test_bootstrap.py
git commit -m "feat(eval): add bootstrap confidence intervals" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: J1 scorer

Pair each predicted record with the gold record of the same type that agrees on the most
fields, then count hits per field. A wrong value counts once as a false positive and once
as a false negative, so F1 = 2·TP / (2·TP + FP + FN).

**Files:**
- Create: `model/eval/score_j1.py`
- Test: `model/tests/test_score_j1.py`

- [x] **Step 1: Write the failing test** `model/tests/test_score_j1.py`

```python
from model.eval.score_j1 import J1Result, score_j1


def test_perfect_prediction():
    gold = "C | ECON 101 | Principles | Fall 2024 | A | 3.00\n"
    result = score_j1(gold, gold, "ECON 101 Principles Fall 2024 A 3.00")
    assert result.fields["C.code"].f1 == 1.0
    assert result.exact_rows == result.gold_rows == 1
    assert result.copy_violations == 0


def test_wrong_grade_counts_once_each_way():
    gold = "C | ECON 101 | Principles | Fall 2024 | A | 3.00\n"
    predicted = "C | ECON 101 | Principles | Fall 2024 | B | 3.00\n"
    result = score_j1(predicted, gold, "ECON 101 Principles Fall 2024 A B 3.00")
    grade = result.fields["C.grade"]
    assert (grade.tp, grade.fp, grade.fn) == (0, 1, 1)
    assert result.fields["C.title"].f1 == 1.0
    assert result.exact_rows == 0


def test_missing_and_extra_rows():
    gold = "C | ECON 101 | Principles |  | A |\nC | MATH 151 | Calculus I |  | B+ |\n"
    predicted = "C | ECON 101 | Principles |  | A |\nC | PHYS 101 | Physics |  | C |\n"
    code = score_j1(predicted, gold, "").fields["C.code"]
    assert (code.tp, code.fp, code.fn) == (1, 1, 1)


def test_unparseable_lines_are_counted():
    assert score_j1("garbage\n", "", "").unparseable == 1


def test_results_add_up():
    total = J1Result()
    total += score_j1("C | A 1 |  |  |  |\n", "C | A 1 |  |  |  |\n", "A 1")
    total += score_j1("", "C | B 2 |  |  |  |\n", "B 2")
    assert total.gold_rows == 2
    assert total.fields["C.code"].recall == 0.5
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_score_j1.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.eval.score_j1'`

- [x] **Step 3: Write `model/eval/score_j1.py`**

```python
"""J1 scoring: pair predicted and gold records, then count hits per record type and field."""
import math
from collections import defaultdict
from dataclasses import dataclass, field

from model.jobs.j1 import RECORD_TYPES, Record, copy_violations, field_names, parse_records
from model.jobs.normalize import norm


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def __iadd__(self, other: "Counts") -> "Counts":
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn
        return self

    @property
    def f1(self) -> float:
        denominator = 2 * self.tp + self.fp + self.fn
        return 2 * self.tp / denominator if denominator else math.nan

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else math.nan

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else math.nan


@dataclass
class J1Result:
    fields: defaultdict = field(default_factory=lambda: defaultdict(Counts))   # "C.code" -> Counts
    exact_rows: int = 0
    gold_rows: int = 0
    unparseable: int = 0
    copy_violations: int = 0

    def __iadd__(self, other: "J1Result") -> "J1Result":
        for key, counts in other.fields.items():
            self.fields[key] += counts
        self.exact_rows += other.exact_rows
        self.gold_rows += other.gold_rows
        self.unparseable += other.unparseable
        self.copy_violations += other.copy_violations
        return self


def _agreement(a: Record, b: Record) -> int:
    """Non-empty fields with equal values. An activity's kind alone never pairs two rows."""
    return sum(
        1 for name in field_names(a)
        if name != "kind" and getattr(a, name) and norm(getattr(a, name)) == norm(getattr(b, name))
    )


def pair_records(predicted: list[Record], gold: list[Record]) -> list[tuple[Record | None, Record | None]]:
    pairs: list[tuple[Record | None, Record | None]] = []
    for tag in RECORD_TYPES:
        p = [r for r in predicted if r.TAG == tag]
        g = [r for r in gold if r.TAG == tag]
        options = sorted(
            ((_agreement(a, b), i, j) for i, a in enumerate(p) for j, b in enumerate(g)),
            key=lambda option: (-option[0], option[1], option[2]),
        )
        used_p: set[int] = set()
        used_g: set[int] = set()
        for score, i, j in options:
            if score == 0:
                break
            if i not in used_p and j not in used_g:
                used_p.add(i)
                used_g.add(j)
                pairs.append((p[i], g[j]))
        pairs += [(p[i], None) for i in range(len(p)) if i not in used_p]
        pairs += [(None, g[j]) for j in range(len(g)) if j not in used_g]
    return pairs


def score_j1(predicted_text: str, gold_text: str, source: str) -> J1Result:
    predicted, errors = parse_records(predicted_text)
    gold, gold_errors = parse_records(gold_text)
    if gold_errors:
        raise ValueError(f"gold file has errors: {gold_errors[:3]}")
    result = J1Result(gold_rows=len(gold), unparseable=len(errors))
    result.copy_violations = sum(len(copy_violations(record, source)) for record in predicted)
    for p, g in pair_records(predicted, gold):
        record = p or g
        for name in field_names(record):
            predicted_value = norm(getattr(p, name)) if p else ""
            gold_value = norm(getattr(g, name)) if g else ""
            counts = result.fields[f"{record.TAG}.{name}"]
            if predicted_value and predicted_value == gold_value:
                counts.tp += 1
            else:
                counts.fp += bool(predicted_value)
                counts.fn += bool(gold_value)
        if p and g and all(norm(getattr(p, n)) == norm(getattr(g, n)) for n in field_names(p)):
            result.exact_rows += 1
    return result
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_score_j1.py -v`
Expected: 5 passed

- [x] **Step 5: Commit**

```bash
git add model/eval/score_j1.py model/tests/test_score_j1.py
git commit -m "feat(eval): score J1 per record field" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: J2 scorer

**Files:**
- Create: `model/eval/score_j2.py`
- Test: `model/tests/test_score_j2.py`

- [x] **Step 1: Write the failing test** `model/tests/test_score_j2.py`

```python
from model.eval.score_j2 import J2Result, score_j2
from model.jobs.j1 import Course
from model.jobs.j2 import Item, Tag
from model.jobs.skills import load_taxonomy

ITEM = Item((Course("STAT 250", "Statistics"),))


def test_counts_keys():
    gold = [Tag("quantitative"), Tag("data_analysis")]
    result = score_j2("quantitative\nwriting\n", gold, ITEM, load_taxonomy())
    assert (result.counts.tp, result.counts.fp, result.counts.fn) == (1, 1, 1)
    assert result.bad_tags == 0


def test_counts_bad_tags():
    result = score_j2("juggling\ntool | SQL\na | b | c\n", [], ITEM, load_taxonomy())
    assert result.bad_tags == 3


def test_results_add_up():
    total = J2Result()
    total += score_j2("quantitative\n", [Tag("quantitative")], ITEM, load_taxonomy())
    total += score_j2("", [Tag("writing")], ITEM, load_taxonomy())
    assert (total.items, total.counts.tp, total.counts.fn) == (2, 1, 1)
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_score_j2.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.eval.score_j2'`

- [x] **Step 3: Write `model/eval/score_j2.py`**

```python
"""J2 scoring: compare tag keys per item. Skill ids and tools count; quotes don't."""
from dataclasses import dataclass, field

from model.eval.score_j1 import Counts
from model.jobs.j2 import Item, Tag, parse_tags, tag_violations
from model.jobs.skills import Taxonomy


@dataclass
class J2Result:
    counts: Counts = field(default_factory=Counts)
    items: int = 0
    bad_tags: int = 0   # unparseable lines, unknown ids, quotes not in the input

    def __iadd__(self, other: "J2Result") -> "J2Result":
        self.counts += other.counts
        self.items += other.items
        self.bad_tags += other.bad_tags
        return self


def score_j2(predicted_text: str, gold_tags: list[Tag], item: Item, taxonomy: Taxonomy) -> J2Result:
    predicted, errors = parse_tags(predicted_text)
    bad = len(errors) + sum(1 for tag in predicted if tag_violations(tag, item.text, taxonomy))
    p = {tag.key for tag in predicted}
    g = {tag.key for tag in gold_tags}
    return J2Result(Counts(len(p & g), len(p - g), len(g - p)), 1, bad)
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_score_j2.py -v`
Expected: 3 passed

- [x] **Step 5: Commit**

```bash
git add model/eval/score_j2.py model/tests/test_score_j2.py
git commit -m "feat(eval): score J2 by tag keys" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 17: J3 scorer

**Files:**
- Create: `model/eval/score_j3.py`
- Test: `model/tests/test_score_j3.py`

- [x] **Step 1: Write the failing test** `model/tests/test_score_j3.py`

```python
from model.eval.score_j3 import J3Result, score_j3
from model.jobs.j3 import parse_facts
from model.jobs.skills import load_taxonomy


def test_pass_and_fail():
    facts = parse_facts("style: action\naction: Build a SQL project\nbecause: Analysts use SQL\neffort: 3 hours\n")
    total = J3Result()
    total += score_j3("Build a SQL project (3 hours). Analysts use SQL.", facts, load_taxonomy())
    total += score_j3("Build a SQL project in 9 hours.", facts, load_taxonomy())
    assert (total.cases, total.passed) == (2, 1)
    assert total.failures == [("Build a SQL project in 9 hours.", ("9",))]
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_score_j3.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.eval.score_j3'`

- [x] **Step 3: Write `model/eval/score_j3.py`**

```python
"""J3 scoring: does each explanation pass the fact check?"""
from dataclasses import dataclass, field

from model.jobs.j3 import Facts, check_explanation
from model.jobs.skills import Taxonomy

KEEP_FAILURES = 5


@dataclass
class J3Result:
    cases: int = 0
    passed: int = 0
    facts_used: int = 0
    failures: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)   # (text, unsupported)

    def __iadd__(self, other: "J3Result") -> "J3Result":
        self.cases += other.cases
        self.passed += other.passed
        self.facts_used += other.facts_used
        self.failures = (self.failures + other.failures)[:KEEP_FAILURES]
        return self


def score_j3(text: str, facts: Facts, taxonomy: Taxonomy) -> J3Result:
    check = check_explanation(text, facts, taxonomy)
    return J3Result(1, int(check.ok), check.used, [] if check.ok else [(text, check.unsupported)])
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_score_j3.py -v`
Expected: 1 passed

- [x] **Step 5: Commit**

```bash
git add model/eval/score_j3.py model/tests/test_score_j3.py
git commit -m "feat(eval): score J3 by fact-check pass rate" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 18: Test-set loader and J3 cases

Test documents live in `<DP_DATA_DIR>/testsets/<family>/<doc_id>/` as `text.txt`, plus
`gold.j1` and `gold.j2` once labelled. J3 has no gold text: its test inputs are built from
the labelled J2 tags using a toy table of careers. The real career engine (O*NET) comes in
the app phase.

**Files:**
- Create: `model/eval/testset.py`, `model/eval/j3cases.py`
- Test: `model/tests/test_testset.py`

- [x] **Step 1: Write the failing test** `model/tests/test_testset.py`

```python
from model.eval.j3cases import build_cases
from model.eval.testset import EvalDoc, load_testset
from model.jobs.j3 import Facts, format_facts, parse_facts
from model.jobs.skills import load_taxonomy


def test_loads_docs_in_family_order(tmp_path):
    for family, doc_id in [("syllabus", "s1"), ("transcript", "t2"), ("transcript", "t1")]:
        folder = tmp_path / family / doc_id
        folder.mkdir(parents=True)
        (folder / "text.txt").write_text(f"{doc_id} text", encoding="utf-8")
    (tmp_path / "transcript" / "t1" / "gold.j1").write_text("C | X 100 |  |  |  |\n", encoding="utf-8")
    (tmp_path / "resume" / "no-text-yet").mkdir(parents=True)
    docs = load_testset(tmp_path)
    assert [(d.family, d.doc_id) for d in docs] == [("transcript", "t1"), ("transcript", "t2"), ("syllabus", "s1")]
    assert docs[0].gold_j1 == "C | X 100 |  |  |  |\n"
    assert docs[0].gold_j2 is None


def test_missing_root_gives_no_docs(tmp_path):
    assert load_testset(tmp_path / "nope") == []


def test_cases_from_one_labelled_course():
    gold_j2 = "C | STAT 250 | Statistics |  | A |\n  quantitative\n  data_analysis\n"
    cases = build_cases([EvalDoc("transcript", "t1", "", None, gold_j2)], load_taxonomy())
    assert len(cases) == 12   # 4 careers use these skills, 3 cases each
    assert cases[0] == Facts("why_fit", (
        ("career", "Data Analyst"),
        ("skill", "Quantitative reasoning (Developing)"), ("evidence", "STAT 250 Statistics, A"),
        ("skill", "Data analysis (Developing)"), ("evidence", "STAT 250 Statistics, A"),
    ))
    assert cases[1] == Facts("gap", (
        ("career", "Data Analyst"), ("have", "Quantitative reasoning"), ("have", "Data analysis"),
        ("need", "Programming"),
    ))
    assert cases[2].style == "action"
    assert all(parse_facts(format_facts(case)) == case for case in cases)
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_testset.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.eval.j3cases'`

- [x] **Step 3: Write `model/eval/testset.py`**

The class is `EvalDoc`, not `TestDoc`: pytest would try to collect a class named `Test*`.

```python
"""Load the real test documents from <testsets>/<family>/<doc_id>/."""
from dataclasses import dataclass
from pathlib import Path

from model.paths import testsets_dir

FAMILIES = ("transcript", "resume", "syllabus")


@dataclass(frozen=True)
class EvalDoc:
    family: str
    doc_id: str
    text: str
    gold_j1: str | None
    gold_j2: str | None


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def load_testset(root: Path | None = None) -> list[EvalDoc]:
    root = root or testsets_dir()
    docs = []
    for family in FAMILIES:
        folder = root / family
        if not folder.is_dir():
            continue
        for doc_dir in sorted(p for p in folder.iterdir() if (p / "text.txt").exists()):
            docs.append(EvalDoc(family, doc_dir.name, (doc_dir / "text.txt").read_text(encoding="utf-8"),
                                _read(doc_dir / "gold.j1"), _read(doc_dir / "gold.j2")))
    return docs
```

- [x] **Step 4: Write `model/eval/j3cases.py`**

```python
"""J3 test inputs built from labelled documents, using a toy career table."""
from model.eval.testset import EvalDoc
from model.jobs.j1 import Course
from model.jobs.j2 import Item, parse_gold_j2
from model.jobs.j3 import Facts
from model.jobs.skills import Taxonomy

CAREERS = {
    "Data Analyst": ("quantitative", "data_analysis", "programming"),
    "Financial Analyst": ("quantitative", "financial", "data_analysis"),
    "Software Developer": ("programming", "problem_solving", "teamwork"),
    "Communications Specialist": ("writing", "public_speaking", "interpersonal"),
    "Research Assistant": ("research", "writing", "data_analysis"),
    "Teacher": ("teaching", "public_speaking", "organization"),
    "Project Coordinator": ("organization", "leadership", "teamwork"),
    "Sales Representative": ("persuasion", "client_service", "interpersonal"),
    "Lab Technician": ("lab_work", "research", "quantitative"),
    "Graphic Designer": ("creativity", "client_service", "organization"),
}


def _evidence(item: Item) -> str:
    head = item.records[0]
    if isinstance(head, Course):
        label = " ".join(value for value in (head.code, head.title) if value)
        return f"{label}, {head.grade}" if head.grade else label
    return f"{head.title}, {head.org}" if head.org else head.title


def _level(count: int) -> str:
    return "High" if count >= 3 else "Moderate" if count == 2 else "Developing"


def build_cases(docs: list[EvalDoc], taxonomy: Taxonomy) -> list[Facts]:
    cases = []
    for doc in docs:
        if not doc.gold_j2:
            continue
        pairs, _ = parse_gold_j2(doc.gold_j2)
        evidence: dict[str, list[str]] = {}
        for item, tags in pairs:
            for tag in tags:
                if tag.skill != "tool":
                    evidence.setdefault(tag.skill, []).append(_evidence(item))
        for career, skills in CAREERS.items():
            have = [s for s in skills if s in evidence]
            need = [s for s in skills if s not in evidence]
            if not have:
                continue
            fit = [("career", career)]
            for skill_id in have[:2]:
                fit.append(("skill", f"{taxonomy.skill(skill_id).name} ({_level(len(evidence[skill_id]))})"))
                fit += [("evidence", e) for e in evidence[skill_id][:2]]
            cases.append(Facts("why_fit", tuple(fit)))
            if need:
                cases.append(Facts("gap", (("career", career),
                                           *(("have", taxonomy.skill(s).name) for s in have),
                                           *(("need", taxonomy.skill(s).name) for s in need))))
                first = taxonomy.skill(need[0]).name.lower()
                cases.append(Facts("action", (("action", f"Start a small project that builds {first}"),
                                              ("because", f"{career} roles ask for {first}"),
                                              ("effort", "3 hours a week"))))
    return cases
```

- [x] **Step 5: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_testset.py -v`
Expected: 3 passed

- [x] **Step 6: Commit**

```bash
git add model/eval/testset.py model/eval/j3cases.py model/tests/test_testset.py
git commit -m "feat(eval): load test documents and build J3 cases from their labels" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 19: The scorecard CLI

`python -m model.eval --solver baseline` scores every labelled document and prints each
number with its 95% interval and the spec's bar (J1 code and grade 0.95, other J1 fields
0.90, J2 precision 0.80, J3 pass rate 0.98).

**Files:**
- Create: `model/eval/__main__.py`
- Test: `model/tests/test_eval_cli.py`

- [x] **Step 1: Write the failing test** `model/tests/test_eval_cli.py`

```python
from model.eval.__main__ import main


def test_scorecard_on_a_tiny_testset(tmp_path, capsys):
    doc = tmp_path / "transcript" / "t1"
    doc.mkdir(parents=True)
    (doc / "text.txt").write_text("Fall 2024\nSTAT 250 Statistics 3.00 A\n", encoding="utf-8")
    (doc / "gold.j1").write_text("C | STAT 250 | Statistics | Fall 2024 | A | 3.00\n", encoding="utf-8")
    (doc / "gold.j2").write_text("C | STAT 250 | Statistics | Fall 2024 | A | 3.00\n  quantitative\n", encoding="utf-8")
    assert main(["--testsets", str(tmp_path), "--samples", "20"]) == 0
    out = capsys.readouterr().out
    assert "1 docs (transcript 1)" in out
    assert "C.code" in out and "ok (bar 0.95)" in out
    assert "J2 tag (1 docs, 1 items)" in out
    assert "J3 explain (9 cases)" in out


def test_empty_testset_says_so(tmp_path, capsys):
    assert main(["--testsets", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "no labelled documents yet" in out
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_eval_cli.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.eval.__main__'`

- [x] **Step 3: Write `model/eval/__main__.py`**

```python
"""Scorecard: python -m model.eval --solver baseline [--testsets PATH] [--samples N]"""
import argparse
import math
import sys
from collections import Counter
from pathlib import Path

from model.eval.bootstrap import bootstrap_ci
from model.eval.j3cases import build_cases
from model.eval.score_j1 import J1Result, score_j1
from model.eval.score_j2 import J2Result, score_j2
from model.eval.score_j3 import J3Result, score_j3
from model.eval.testset import load_testset
from model.jobs.j1 import RECORD_TYPES, field_names
from model.jobs.j2 import parse_gold_j2
from model.jobs.j3 import format_facts
from model.jobs.skills import load_taxonomy
from model.solvers import get_solver

# Bars from the design spec's Verification section.
J1_BARS = {"C.code": 0.95, "C.grade": 0.95}
J1_DEFAULT_BAR = 0.90
J2_PRECISION_BAR = 0.80
J3_PASS_BAR = 0.98


def _total(results, empty):
    total = empty()
    for result in results:
        total += result
    return total


def _num(value: float) -> str:
    return "  —  " if math.isnan(value) else f"{value:.2f}"


def _interval(units, statistic, samples: int) -> str:
    low, high = bootstrap_ci(units, statistic, n=samples)
    return "      —     " if math.isnan(low) else f"[{low:.2f}, {high:.2f}]"


def _verdict(value: float, bar: float) -> str:
    return "—" if math.isnan(value) else f"{'ok' if value >= bar else 'MISS'} (bar {bar:.2f})"


def report_j1(results: list[J1Result], samples: int) -> list[str]:
    if not results:
        return ["J1 extract: no labelled documents yet"]
    total = _total(results, J1Result)
    lines = [f"J1 extract ({len(results)} docs, {total.gold_rows} gold rows)",
             f"  {'field':<12}{'F1':>6}  {'95% CI':<14}{'P':>6}{'R':>6}  bar"]
    for tag, record_type in RECORD_TYPES.items():
        for name in field_names(record_type):
            key = f"{tag}.{name}"
            counts = total.fields.get(key)
            if not counts or counts.tp + counts.fp + counts.fn == 0:
                continue
            ci = _interval(results, lambda sample, k=key: _total(sample, J1Result).fields[k].f1, samples)
            lines.append(f"  {key:<12}{_num(counts.f1):>6}  {ci:<14}{_num(counts.precision):>6}"
                         f"{_num(counts.recall):>6}  {_verdict(counts.f1, J1_BARS.get(key, J1_DEFAULT_BAR))}")
    lines.append(f"  rows exactly right {total.exact_rows}/{total.gold_rows} · unparseable lines "
                 f"{total.unparseable} · copy-rule breaks {total.copy_violations}")
    return lines


def report_j2(results: list[J2Result], samples: int) -> list[str]:
    if not results:
        return ["J2 tag: no labelled items yet"]
    total = _total(results, J2Result)
    counts = total.counts
    ci = _interval(results, lambda sample: _total(sample, J2Result).counts.precision, samples)
    return [f"J2 tag ({len(results)} docs, {total.items} items)",
            f"  precision {_num(counts.precision)} {ci} · recall {_num(counts.recall)} · F1 {_num(counts.f1)}"
            f" · bad tags {total.bad_tags} · {_verdict(counts.precision, J2_PRECISION_BAR)}"]


def report_j3(results: list[J3Result], samples: int) -> list[str]:
    if not results:
        return ["J3 explain: no cases yet (they come from gold.j2 labels)"]
    total = _total(results, J3Result)
    rate = total.passed / total.cases
    ci = _interval(results, lambda sample: _total(sample, J3Result).passed / len(sample), samples)
    lines = [f"J3 explain ({total.cases} cases)",
             f"  pass rate {rate:.2f} {ci} · facts used {total.facts_used / total.cases:.1f} on average"
             f" · {_verdict(rate, J3_PASS_BAR)}"]
    lines += [f"  failed: {text!r} -> {list(unsupported)}" for text, unsupported in total.failures]
    return lines


def run(solver_name: str, testsets: Path | None, samples: int) -> str:
    taxonomy = load_taxonomy()
    solver = get_solver(solver_name)
    docs = load_testset(testsets)
    j1 = [score_j1(solver.extract(doc.text, doc.family), doc.gold_j1, doc.text)
          for doc in docs if doc.gold_j1 is not None]
    j2 = []
    for doc in docs:
        if doc.gold_j2 is None:
            continue
        pairs, errors = parse_gold_j2(doc.gold_j2)
        if errors:
            raise SystemExit(f"{doc.family}/{doc.doc_id}/gold.j2: {errors[:3]}")
        j2.append(_total((score_j2(solver.tag(item.text), tags, item, taxonomy) for item, tags in pairs),
                         J2Result))
    j3 = [score_j3(solver.explain(format_facts(facts)), facts, taxonomy) for facts in build_cases(docs, taxonomy)]
    families = ", ".join(f"{family} {count}" for family, count in sorted(Counter(d.family for d in docs).items()))
    lines = [f"DegreePilot scorecard · solver {solver.name} · {len(docs)} docs ({families or 'none'})", ""]
    lines += report_j1(j1, samples) + [""] + report_j2(j2, samples) + [""] + report_j3(j3, samples)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m model.eval", description="Score a solver on the real test documents.")
    parser.add_argument("--solver", default="baseline")
    parser.add_argument("--testsets", type=Path, default=None, help="default: DP_DATA_DIR/testsets")
    parser.add_argument("--samples", type=int, default=1000, help="bootstrap resamples")
    args = parser.parse_args(argv)
    print(run(args.solver, args.testsets, args.samples))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_eval_cli.py -v`
Expected: 2 passed

- [x] **Step 5: Run the whole suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: 83 passed

- [x] **Step 6: Commit**

```bash
git add model/eval/__main__.py model/tests/test_eval_cli.py
git commit -m "feat(eval): print a scorecard with intervals and bars" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 20: PDF text with pdf.js

The browser app will read PDFs with pdf.js, so test documents (and, in Phase 4, training
documents) go through the same code. `lines.mjs` is pure so the app can import it as is.

**Files:**
- Create: `tools/pdftext/package.json`, `tools/pdftext/lines.mjs`, `tools/pdftext/extract.mjs`
- Test: `tools/pdftext/lines.test.mjs`, `tools/pdftext/extract.test.mjs`

- [x] **Step 1: Create the package and install pdf.js**

`tools/pdftext/package.json`:

```json
{
  "name": "degreepilot-pdftext",
  "private": true,
  "type": "module",
  "scripts": { "test": "node --test" }
}
```

```bash
cd tools/pdftext && npm install pdfjs-dist && cd ../..
```

Expected: `added N packages`; `package.json` now lists `pdfjs-dist` under dependencies.

- [x] **Step 2: Write the failing tests**

`tools/pdftext/lines.test.mjs`:

```js
import assert from 'node:assert/strict'
import test from 'node:test'
import { itemsToLines } from './lines.mjs'

const item = (str, x, y, width, height = 10) => ({ str, transform: [height, 0, 0, height, x, y], width })

test('orders lines top to bottom and items left to right', () => {
  const lines = itemsToLines([item('world', 37, 700, 25), item('second', 10, 680, 30), item('hello', 10, 700, 25)])
  assert.deepEqual(lines, ['hello world', 'second'])
})

test('wide gaps become tabs, narrow gaps spaces, touching items nothing', () => {
  const lines = itemsToLines([item('A', 0, 0, 10), item('B', 10.5, 0, 10), item('C', 23, 0, 10), item('D', 50, 0, 10)])
  assert.deepEqual(lines, ['AB C\tD'])
})

test('skips whitespace-only items and keeps a slightly shifted item on its line', () => {
  assert.deepEqual(itemsToLines([item('x', 0, 100, 5), item('  ', 5, 100, 5), item('y', 7, 102, 5)]), ['x y'])
})
```

`tools/pdftext/extract.test.mjs` builds a real one-page PDF in memory:

```js
import assert from 'node:assert/strict'
import test from 'node:test'
import { pdfToText } from './extract.mjs'

function makePdf(lines) {
  const content = lines.map(({ x, y, text }) => `BT /F1 12 Tf ${x} ${y} Td (${text}) Tj ET`).join('\n')
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]
  let pdf = '%PDF-1.4\n'
  const offsets = []
  objects.forEach((body, index) => {
    offsets.push(pdf.length)
    pdf += `${index + 1} 0 obj\n${body}\nendobj\n`
  })
  const xref = pdf.length
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  pdf += offsets.map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`
  return new TextEncoder().encode(pdf)
}

test('keeps table columns apart with tabs', async () => {
  const pdf = makePdf([
    { x: 72, y: 720, text: 'ECON 201' }, { x: 200, y: 720, text: 'Intermediate Microeconomics' }, { x: 450, y: 720, text: 'A-' },
    { x: 72, y: 700, text: 'MATH 151' }, { x: 200, y: 700, text: 'Calculus I' }, { x: 450, y: 700, text: 'B+' },
  ])
  assert.equal(await pdfToText(pdf), 'ECON 201\tIntermediate Microeconomics\tA-\nMATH 151\tCalculus I\tB+')
})

test('a PDF with no text gives an empty string', async () => {
  assert.equal(await pdfToText(makePdf([])), '')
})
```

- [x] **Step 3: Run them to see them fail**

Run: `cd tools/pdftext && npm test; cd ../..`
Expected: FAIL, `Cannot find module ... lines.mjs`

- [x] **Step 4: Write `tools/pdftext/lines.mjs`**

```js
// pdf.js text items -> lines of text. Pure, so the browser app can reuse it unchanged.
// Items on the same baseline (within half their height) form one line, left to right.
// A gap wider than the text height becomes a tab, so table columns stay apart; a
// smaller visible gap becomes a space.

export function itemsToLines(items) {
  const rows = []
  for (const item of items) {
    if (!item.str || !item.str.trim()) continue
    const height = Math.abs(item.transform[3]) || item.height || 10
    const x = item.transform[4]
    const y = item.transform[5]
    let row = rows.find((candidate) => Math.abs(candidate.y - y) <= height / 2)
    if (!row) {
      row = { y, items: [] }
      rows.push(row)
    }
    row.items.push({ x, width: item.width, str: item.str, height })
  }
  rows.sort((a, b) => b.y - a.y) // PDF y grows upward
  return rows.map((row) => {
    row.items.sort((a, b) => a.x - b.x)
    let line = ''
    let end = null
    for (const piece of row.items) {
      if (end !== null) {
        const gap = piece.x - end
        line += gap > piece.height ? '\t' : gap > piece.height * 0.15 ? ' ' : ''
      }
      line += piece.str
      end = piece.x + piece.width
    }
    return line.replace(/[ \t]+$/, '')
  })
}
```

- [x] **Step 5: Write `tools/pdftext/extract.mjs`**

```js
// Usage: node tools/pdftext/extract.mjs <file.pdf>
// Prints the text, one line per PDF line. Exits 2 if the PDF has no text layer (a scan).
import { readFile } from 'node:fs/promises'
import { pathToFileURL } from 'node:url'
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs'
import { itemsToLines } from './lines.mjs'

GlobalWorkerOptions.workerSrc = import.meta.resolve('pdfjs-dist/legacy/build/pdf.worker.mjs')

export async function pdfToText(data) {
  // pdf.js 6 frees a document through its loading task, not the document itself.
  const task = getDocument({ data, verbosity: 0, isEvalSupported: false })
  try {
    const doc = await task.promise
    const pages = []
    for (let number = 1; number <= doc.numPages; number++) {
      const page = await doc.getPage(number)
      const content = await page.getTextContent()
      pages.push(itemsToLines(content.items).join('\n'))
    }
    return pages.filter((page) => page).join('\n')
  } finally {
    await task.destroy()
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const path = process.argv[2]
  if (!path) {
    console.error('usage: node extract.mjs <file.pdf>')
    process.exit(1)
  }
  const text = await pdfToText(new Uint8Array(await readFile(path)))
  if (!text.trim()) {
    console.error('no text layer (a scanned PDF?)')
    process.exit(2)
  }
  process.stdout.write(text + '\n')
}
```

- [x] **Step 6: Run the tests to see them pass**

Run: `cd tools/pdftext && npm test; cd ../..`
Expected: `pass 5`, `fail 0`. pdf.js may print a warning about `DOMMatrix` or canvas on stderr; text extraction doesn't need them.

- [x] **Step 7: Commit**

`node_modules/` is already gitignored; commit the lockfile.

```bash
git add tools/pdftext/package.json tools/pdftext/package-lock.json tools/pdftext/*.mjs
git commit -m "feat(tools): extract PDF text with pdf.js, as the browser will" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 21: The labelling CLI

Labelling from scratch is slow, so the CLI pre-fills each gold file from the baseline.
Moss corrects it in the editor, then runs `check`.

**Files:**
- Create: `model/eval/label.py`
- Test: `model/tests/test_label.py`

- [x] **Step 1: Write the failing test** `model/tests/test_label.py`

```python
from model.eval.label import check, main, prefill_j1, prefill_j2


def _doc(tmp_path, text, family="transcript"):
    doc = tmp_path / family / "doc1"
    doc.mkdir(parents=True)
    (doc / "text.txt").write_text(text, encoding="utf-8")
    return doc


def test_prefill_j1_writes_baseline_rows_once(tmp_path):
    doc = _doc(tmp_path, "Fall 2024\nECON 101 Principles 3.00 A\n")
    path = prefill_j1(doc)
    assert "C | ECON 101 | Principles | Fall 2024 | A | 3.00\n" in path.read_text(encoding="utf-8")
    path.write_text("# edited\n", encoding="utf-8")
    prefill_j1(doc)
    assert path.read_text(encoding="utf-8") == "# edited\n"


def test_prefill_j2_tags_the_gold_rows(tmp_path):
    doc = _doc(tmp_path, "STAT 250 Statistics 3.00 A\n")
    prefill_j1(doc)
    text = prefill_j2(doc).read_text(encoding="utf-8")
    assert "C | STAT 250 | Statistics |  | A | 3.00\n  quantitative\n  data_analysis\n" in text


def test_check_finds_copy_and_tag_problems(tmp_path):
    doc = _doc(tmp_path, "STAT 250 Statistics 3.00 A\n")
    (doc / "gold.j1").write_text("C | STAT 250 | Statistics | Fall 2031 | A | 3.00\n", encoding="utf-8")
    (doc / "gold.j2").write_text("C | STAT 250 | Statistics |  | A | 3.00\n  juggling\n", encoding="utf-8")
    assert check(doc) == [
        "gold.j1 not in text.txt: term='Fall 2031'",
        "gold.j2 Statistics: unknown skill 'juggling'",
    ]


def test_check_passes_prefilled_files(tmp_path, capsys):
    doc = _doc(tmp_path, "STAT 250 Statistics 3.00 A\n")
    prefill_j1(doc)
    prefill_j2(doc)
    assert main(["check", str(doc)]) == 0
    assert capsys.readouterr().out.strip() == "ok"
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_label.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.eval.label'`

- [x] **Step 3: Write `model/eval/label.py`**

```python
"""Label test documents: prefill gold files from the baseline, then check them after editing.

    python -m model.eval.label j1 <doc_dir>      write gold.j1 from the baseline (if missing)
    python -m model.eval.label j2 <doc_dir>      write gold.j2 from gold.j1 + the baseline tagger
    python -m model.eval.label check <doc_dir>   list problems in the gold files
"""
import argparse
import sys
from pathlib import Path

from model.baselines.extract import extract
from model.baselines.tag import tag
from model.jobs.j1 import copy_violations, format_records, parse_records
from model.jobs.j2 import format_gold_j2, items_from_records, parse_gold_j2, tag_violations
from model.jobs.skills import load_taxonomy

J1_HEADER = """\
# Make these rows match the document, then run: python -m model.eval.label check <this folder>
# C | code | title | term | grade | credits    (percent and letter both shown? use the letter)
# A | kind | title | org | dates | role        kind: job internship project club volunteer award research sport other
# B | one bullet under the activity above
# D | name | weight | due
# Copy values exactly as they appear in text.txt. Leave a value empty if the document doesn't show it.
"""

J2_HEADER = """\
# Under each record, list what it shows, indented two spaces. Delete wrong tags, add missing ones.
#   skill_id                   courses
#   skill_id | words           activities: the record words that justify the skill
#   tool | Name                a tool the record names
# Skill ids: {ids}
"""


def prefill_j1(doc_dir: Path) -> Path:
    target = doc_dir / "gold.j1"
    if not target.exists():
        text = (doc_dir / "text.txt").read_text(encoding="utf-8")
        target.write_text(J1_HEADER + format_records(extract(text, doc_dir.parent.name)), encoding="utf-8")
    return target


def prefill_j2(doc_dir: Path) -> Path:
    target = doc_dir / "gold.j2"
    if not target.exists():
        taxonomy = load_taxonomy()
        records, errors = parse_records((doc_dir / "gold.j1").read_text(encoding="utf-8"))
        if errors:
            raise SystemExit(f"fix gold.j1 first: {errors[:3]}")
        pairs = [(item, tag(item.text, taxonomy)) for item in items_from_records(records)]
        header = J2_HEADER.format(ids=", ".join(skill.id for skill in taxonomy.skills))
        target.write_text(header + format_gold_j2(pairs), encoding="utf-8")
    return target


def check(doc_dir: Path) -> list[str]:
    taxonomy = load_taxonomy()
    text = (doc_dir / "text.txt").read_text(encoding="utf-8")
    problems = []
    if (doc_dir / "gold.j1").exists():
        records, errors = parse_records((doc_dir / "gold.j1").read_text(encoding="utf-8"))
        problems += [f"gold.j1 {error}" for error in errors]
        for record in records:
            problems += [f"gold.j1 not in text.txt: {value}" for value in copy_violations(record, text)]
    if (doc_dir / "gold.j2").exists():
        pairs, errors = parse_gold_j2((doc_dir / "gold.j2").read_text(encoding="utf-8"))
        problems += [f"gold.j2 {error}" for error in errors]
        for item, tags in pairs:
            label = getattr(item.records[0], "title", "")
            for t in tags:
                problems += [f"gold.j2 {label}: {problem}" for problem in tag_violations(t, item.text, taxonomy)]
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m model.eval.label")
    parser.add_argument("action", choices=["j1", "j2", "check"])
    parser.add_argument("doc_dir", type=Path)
    args = parser.parse_args(argv)
    if args.action == "j1":
        print(prefill_j1(args.doc_dir))
    elif args.action == "j2":
        print(prefill_j2(args.doc_dir))
    else:
        problems = check(args.doc_dir)
        print("\n".join(problems) if problems else "ok")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_label.py -v`
Expected: 4 passed

- [x] **Step 5: Commit**

```bash
git add model/eval/label.py model/tests/test_label.py
git commit -m "feat(eval): prefill and check gold labels" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 22: Adding documents to the test set

**Files:**
- Create: `model/eval/intake.py`
- Test: `model/tests/test_intake.py`

- [x] **Step 1: Write the failing test** `model/tests/test_intake.py`

```python
import json
import shutil

import pytest

from model.eval.intake import PDFTEXT, intake


def _minimal_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = "%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


def test_intake_local_text_file(tmp_path):
    source = tmp_path / "My Transcript.txt"
    source.write_text("ECON 101 Principles 3.00 A\n", encoding="utf-8")
    root = tmp_path / "testsets"
    doc = intake("transcript", str(source), root=root)
    assert doc == root / "transcript" / "my-transcript"
    assert (doc / "text.txt").read_text(encoding="utf-8") == "ECON 101 Principles 3.00 A\n"
    entry = json.loads((root / "manifest.json").read_text(encoding="utf-8"))[0]
    assert entry["source"] == "local"
    assert entry["family"] == "transcript"
    assert len(entry["sha256"]) == 64


def test_intake_refuses_duplicates_and_unknown_families(tmp_path):
    source = tmp_path / "a.txt"
    source.write_text("x", encoding="utf-8")
    intake("resume", str(source), root=tmp_path / "t")
    with pytest.raises(SystemExit):
        intake("resume", str(source), root=tmp_path / "t")
    with pytest.raises(SystemExit):
        intake("poem", str(source), root=tmp_path / "t")


@pytest.mark.skipif(not (shutil.which("node") and (PDFTEXT.parent / "node_modules").exists()),
                    reason="needs node and tools/pdftext dependencies")
def test_intake_pdf_extracts_text(tmp_path):
    pdf = tmp_path / "t.pdf"
    pdf.write_bytes(_minimal_pdf("ECON 101 Principles"))
    doc = intake("transcript", str(pdf), root=tmp_path / "t")
    assert (doc / "text.txt").read_text(encoding="utf-8").strip() == "ECON 101 Principles"
```

- [x] **Step 2: Run it to see it fail**

Run: `.venv/Scripts/python -m pytest model/tests/test_intake.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'model.eval.intake'`

- [x] **Step 3: Write `model/eval/intake.py`**

```python
"""Add a test document: python -m model.eval.intake <family> <path-or-url> [--id ID] [--note TEXT]

Copies or downloads the document into <testsets>/<family>/<id>/, writes text.txt (PDFs go
through tools/pdftext, the same pdf.js code the browser will use) and records it in
<testsets>/manifest.json. A URL is recorded so a public document can be fetched again; a
local file is recorded as "local" and never committed.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from model.eval.testset import FAMILIES
from model.paths import REPO_ROOT, testsets_dir

PDFTEXT = REPO_ROOT / "tools" / "pdftext" / "extract.mjs"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "doc"


def pdf_to_text(pdf: Path) -> str:
    result = subprocess.run(["node", str(PDFTEXT), str(pdf)], capture_output=True, text=True, encoding="utf-8")
    if result.returncode == 2:
        raise SystemExit(f"{pdf.name} has no text layer (a scan?). Save its text as a .txt file instead.")
    if result.returncode != 0:
        raise SystemExit(f"PDF text extraction failed: {result.stderr.strip()}")
    return result.stdout


def _fetch(source: str, target: Path) -> None:
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "degreepilot-testset/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            target.write_bytes(response.read())
    else:
        shutil.copyfile(source, target)


def intake(family: str, source: str, doc_id: str | None = None, note: str = "", root: Path | None = None) -> Path:
    if family not in FAMILIES:
        raise SystemExit(f"family must be one of {FAMILIES}")
    root = root or testsets_dir()
    is_url = source.startswith(("http://", "https://"))
    name = source.rstrip("/").rsplit("/", 1)[-1] if is_url else Path(source).name
    suffix = ".pdf" if name.lower().endswith(".pdf") else ".txt"
    doc_dir = root / family / (doc_id or slug(Path(name).stem))
    if doc_dir.exists():
        raise SystemExit(f"{doc_dir} already exists; pick another --id")
    doc_dir.mkdir(parents=True)
    try:
        target = doc_dir / f"source{suffix}"
        _fetch(source, target)
        text = pdf_to_text(target) if suffix == ".pdf" else target.read_text(encoding="utf-8")
        (doc_dir / "text.txt").write_text(text, encoding="utf-8")
    except BaseException:
        shutil.rmtree(doc_dir)
        raise
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    manifest.append({"id": doc_dir.name, "family": family, "source": source if is_url else "local",
                     "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "note": note})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return doc_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m model.eval.intake")
    parser.add_argument("family", choices=FAMILIES)
    parser.add_argument("source", help="a file path or an http(s) URL")
    parser.add_argument("--id", dest="doc_id")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)
    print(intake(args.family, args.source, args.doc_id, args.note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 4: Run it to see it pass**

Run: `.venv/Scripts/python -m pytest model/tests/test_intake.py -v`
Expected: 3 passed (the PDF test needs Task 20's `npm install`)

- [x] **Step 5: Run everything**

Run: `.venv/Scripts/python -m pytest -q && (cd tools/pdftext && npm test)`
Expected: `90 passed`, then `pass 5`

- [x] **Step 6: Commit**

```bash
git add model/eval/intake.py model/tests/test_intake.py
git commit -m "feat(eval): add documents to the test set from a file or URL" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 23: Collect, label and score real documents (Moss + Claude)

This task is part code-free legwork, part Moss's time. Target: **at least 100 real rows per
family** (spec), so roughly 5 transcripts, 10 résumés and 10 syllabi.

**Files:**
- Create: `model/eval/manifest.public.json`, `docs/research/<date>-baseline-scorecard.md`
- Modify: `README.md` (status line)

- [x] **Step 1: Find public documents (Claude)**

Web-search for PDFs with a text layer, and note each URL:
- Transcripts: `"sample transcript" registrar pdf` for US and Canadian universities; `relevé de notes cégep exemple` and `CEGEP transcript sample` for Quebec.
- Résumés: `"sample resume" career centre pdf` (university career-centre guides hold several each).
- Syllabi: `course syllabus pdf "grading" "midterm"` across subjects.

Skip anything behind a login, and anything that is a scanned image (`intake` will refuse it).

- [x] **Step 2: Intake each document**

```bash
.venv/Scripts/python -m model.eval.intake transcript "<url>" --id <short-name> --note "<school, page it came from>"
.venv/Scripts/python -m model.eval.intake resume "<url>" --id <short-name> --note "<source>"
.venv/Scripts/python -m model.eval.intake syllabus "<url>" --id <short-name> --note "<course, school>"
```

Moss's own documents (optional, and they stay local): export the Omnivox transcript and a
résumé as PDF, then:

```bash
.venv/Scripts/python -m model.eval.intake transcript "C:/path/to/transcript.pdf" --id moss-vanier
```

> **Status (2026-09-30):** 15 public documents are in `data/testsets/` with draft `gold.j1` files (5 résumés, 8 York syllabi, 2 transcript samples). Next is Moss: add their own transcript and résumé, trim the two long résumé guides, then label (Step 3).

- [ ] **Step 3: Label (Moss, about 1–3 hours)**

For each document folder under `data/testsets/<family>/<id>/`:

```bash
.venv/Scripts/python -m model.eval.label j1 data/testsets/transcript/<id>
```

Open the printed `gold.j1` next to `text.txt`, fix every row, then:

```bash
.venv/Scripts/python -m model.eval.label check data/testsets/transcript/<id>
```

Repeat until it prints `ok`. For transcripts and résumés, do the same with `j2` (syllabi
need only `j1`).

- [ ] **Step 4: Score the baseline**

```bash
.venv/Scripts/python -m model.eval --solver baseline
```

Expected: a scorecard with every J1 field, J2 and J3 filled in. Misses are fine: this is
the bar the model has to beat.

- [ ] **Step 5: Record the results**

Copy the scorecard into `docs/research/<today>-baseline-scorecard.md` under a heading, with
the document counts per family and one line on where the baseline fails most (read the
worst field's rows).

Copy the public part of the manifest (entries whose `source` is a URL) into
`model/eval/manifest.public.json`, so the test set can be downloaded again:

```bash
.venv/Scripts/python -c "import json, pathlib; m = json.loads(pathlib.Path('data/testsets/manifest.json').read_text(encoding='utf-8')); pathlib.Path('model/eval/manifest.public.json').write_text(json.dumps([e for e in m if e['source'] != 'local'], indent=2) + '\n', encoding='utf-8')"
```

In `README.md`, change the status line to:

```markdown
**Status:** Phase 1 of 6 done (contracts, baselines, eval). Next: Phase 2, tokenizer and model.
```

- [ ] **Step 6: Commit**

```bash
git add model/eval/manifest.public.json docs/research README.md
git commit -m "docs: record the baseline scorecard on real documents" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 24: Phase review

Per the spec, each phase ends with a two-agent review on Sonnet, sized for the Pro plan's
five-hour limit.

- [ ] **Step 1: Run the review workflow**

Launch a Workflow with two read-only agents (`model: 'sonnet'`, `effort: 'medium'`),
each returning `{findings: [{file, line, problem, fix, severity}]}`:

1. **Correctness:** "Read `contracts/jobs.md`, then every file in `model/` and
   `tools/pdftext/`. Find code that disagrees with the contract, checks that can pass bad
   output (copy rule, tag checks, fact check), and scoring that miscounts. Read-only. Cite
   file:line."
2. **Premortem:** "It is Phase 4 and the J1–J3 training data turned out useless. Using
   `docs/specs/2026-09-30-degreepilot-design.md`, `contracts/jobs.md` and the scorecard in
   `docs/research/`, find what in Phase 1 caused it: formats a small model will struggle to
   emit, labels that are ambiguous, test sets too small or too uniform. Read-only. At most
   6 findings, most severe first."

- [ ] **Step 2: Fix what holds up**

Verify each finding against the code before changing anything. Fix the real ones with a
test first, run `.venv/Scripts/python -m pytest -q`, and commit each fix separately.

---

## Self-review against the spec

| Spec requirement | Task |
|---|---|
| J1–J3 formats and job tokens | 3, 5, 6, 7 |
| Copy rule for J1; ids and quotes for J2; fact check for J3 | 3, 5, 6 |
| A non-model baseline for every job | 8–12 |
| Real test documents only; ≥100 rows per family; labelling CLI pre-filled from the baseline | 21, 22, 23 |
| pdf.js for test text, same code as the browser; scanned PDFs refused | 20, 22 |
| J1 field-level F1 with bars 0.95 (code, grade) / 0.90; J2 precision 0.8; J3 98% | 15–19 |
| Confidence intervals | 14, 19 |
| Quebec CEGEP transcript layout | 8 |
| 2-agent review at the end of the phase | 24 |

Deferred on purpose: Moss's rating of 50 J3 samples (needs model output, Phase 4); the
real O*NET career engine (app phase); `DP_DATA_DIR` outside OneDrive (decide before
Phase 2 downloads).

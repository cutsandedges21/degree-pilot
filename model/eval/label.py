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
from model.jobs.j1 import Activity, copy_violations, format_records, parse_records
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
            activity = isinstance(item.records[0], Activity)
            for t in tags:
                problems += [f"gold.j2 {label}: {problem}"
                             for problem in tag_violations(t, item.text, taxonomy, activity)]
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

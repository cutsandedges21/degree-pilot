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
    j1 = []
    for doc in docs:
        if doc.gold_j1 is None:
            continue
        try:
            j1.append(score_j1(solver.extract(doc.text, doc.family), doc.gold_j1, doc.text))
        except ValueError as error:
            raise SystemExit(f"{doc.family}/{doc.doc_id}/gold.j1: {error}") from error
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

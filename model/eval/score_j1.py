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

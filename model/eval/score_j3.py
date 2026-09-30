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

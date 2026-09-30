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

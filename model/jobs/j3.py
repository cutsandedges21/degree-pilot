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
_NUMBER = re.compile(r"(?<![\d.,])\d+(?:[.,]\d+)*(?!\d)")   # whole numbers only: "2" is not in "250"
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
    for line in text.split("\n"):
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
        elif style is None:
            raise FactsError("style must come first")
        elif key in KEYS:
            if key == "evidence" and not any(k == "skill" for k, _ in items):
                raise FactsError("evidence must follow a skill")
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
    fact_numbers = {number for _, value in facts.items for number in _NUMBER.findall(value)}
    unsupported += [number for number in _NUMBER.findall(text) if number not in fact_numbers]
    grades = _SIGNED_GRADE.findall(text) + _PLAIN_GRADE.findall(text)
    unsupported += [grade for grade in grades if norm(grade) not in fact_tokens]
    unsupported += [
        skill.name for skill in taxonomy.skills
        if norm(skill.name) in output and norm(skill.name) not in facts_text
    ]
    used = sum(1 for _, value in facts.items if any(handle in output for handle in _handles(value)))
    return Check(tuple(unsupported), used)

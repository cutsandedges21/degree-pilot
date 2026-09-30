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

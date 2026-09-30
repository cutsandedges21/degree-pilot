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

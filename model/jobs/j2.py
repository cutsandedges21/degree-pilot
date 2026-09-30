"""J2 tag: one item (a course, or an activity with its bullets) in, what it shows out.

    skill_id                  a skill from contracts/skills.json
    skill_id | quoted words   the same, with the input words that justify it (activities)
    tool | Name               a tool from the taxonomy's list that the input names

Gold files (gold.j2) hold each item's J1 record lines followed by its tags, indented two
spaces, with a blank line between items.
"""
from dataclasses import dataclass

from model.jobs.j1 import Activity, Bullet, Course, Record, RecordError, format_records, parse_record
from model.jobs.normalize import contains_words, norm
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
    for number, line in enumerate(text.split("\n"), 1):
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
    for number, line in enumerate(text.split("\n"), 1):
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


def tag_violations(tag: Tag, source: str, taxonomy: Taxonomy, activity: bool = False) -> list[str]:
    """Problems with one tag. Tool names and quotes must appear as whole words, and an
    activity's skill tags must quote their evidence (contract J2 rules 2 and 3)."""
    problems = []
    if tag.skill == "tool":
        if norm(tag.value) not in {norm(tool) for tool in taxonomy.tools}:
            problems.append(f"unknown tool {tag.value!r}")
    elif tag.skill not in taxonomy.skill_ids:
        problems.append(f"unknown skill {tag.skill!r}")
    elif activity and not tag.value:
        problems.append("activity tags need a quote from the item")
    if tag.value and len(norm(tag.value)) < 2:
        problems.append(f"quote {tag.value!r} is too short")
    elif tag.value and not contains_words(source, tag.value):
        problems.append(f"{tag.value!r} is not in the input")
    return problems

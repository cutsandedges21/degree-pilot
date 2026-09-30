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

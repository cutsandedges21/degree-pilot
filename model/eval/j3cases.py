"""J3 test inputs built from labelled documents, using a toy career table."""
from model.eval.testset import EvalDoc
from model.jobs.j1 import Course
from model.jobs.j2 import Item, parse_gold_j2
from model.jobs.j3 import Facts
from model.jobs.skills import Taxonomy

CAREERS = {
    "Data Analyst": ("quantitative", "data_analysis", "programming"),
    "Financial Analyst": ("quantitative", "financial", "data_analysis"),
    "Software Developer": ("programming", "problem_solving", "teamwork"),
    "Communications Specialist": ("writing", "public_speaking", "interpersonal"),
    "Research Assistant": ("research", "writing", "data_analysis"),
    "Teacher": ("teaching", "public_speaking", "organization"),
    "Project Coordinator": ("organization", "leadership", "teamwork"),
    "Sales Representative": ("persuasion", "client_service", "interpersonal"),
    "Lab Technician": ("lab_work", "research", "quantitative"),
    "Graphic Designer": ("creativity", "client_service", "organization"),
}


def _evidence(item: Item) -> str:
    head = item.records[0]
    if isinstance(head, Course):
        label = " ".join(value for value in (head.code, head.title) if value)
        return f"{label}, {head.grade}" if head.grade else label
    return f"{head.title}, {head.org}" if head.org else head.title


def _level(count: int) -> str:
    return "High" if count >= 3 else "Moderate" if count == 2 else "Developing"


def build_cases(docs: list[EvalDoc], taxonomy: Taxonomy) -> list[Facts]:
    cases = []
    for doc in docs:
        if not doc.gold_j2:
            continue
        pairs, _ = parse_gold_j2(doc.gold_j2)
        evidence: dict[str, list[str]] = {}
        for item, tags in pairs:
            text = _evidence(item)
            if not text:   # an item with no code, title or org can't be cited
                continue
            for tag in tags:
                if tag.skill != "tool":
                    evidence.setdefault(tag.skill, []).append(text)
        for career, skills in CAREERS.items():
            have = [s for s in skills if s in evidence]
            need = [s for s in skills if s not in evidence]
            if not have:
                continue
            fit = [("career", career)]
            for skill_id in have[:2]:
                fit.append(("skill", f"{taxonomy.skill(skill_id).name} ({_level(len(evidence[skill_id]))})"))
                fit += [("evidence", e) for e in evidence[skill_id][:2]]
            cases.append(Facts("why_fit", tuple(fit)))
            if need:
                cases.append(Facts("gap", (("career", career),
                                           *(("have", taxonomy.skill(s).name) for s in have),
                                           *(("need", taxonomy.skill(s).name) for s in need))))
                first = taxonomy.skill(need[0]).name.lower()
                cases.append(Facts("action", (("action", f"Start a small project that builds {first}"),
                                              ("because", f"{career} roles ask for {first}"),
                                              ("effort", "3 hours a week"))))
    return cases

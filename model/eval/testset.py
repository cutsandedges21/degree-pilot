"""Load the real test documents from <testsets>/<family>/<doc_id>/."""
from dataclasses import dataclass
from pathlib import Path

from model.paths import testsets_dir

FAMILIES = ("transcript", "resume", "syllabus")


@dataclass(frozen=True)
class EvalDoc:
    family: str
    doc_id: str
    text: str
    gold_j1: str | None
    gold_j2: str | None


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def load_testset(root: Path | None = None) -> list[EvalDoc]:
    root = root or testsets_dir()
    docs = []
    for family in FAMILIES:
        folder = root / family
        if not folder.is_dir():
            continue
        for doc_dir in sorted(p for p in folder.iterdir() if (p / "text.txt").exists()):
            docs.append(EvalDoc(family, doc_dir.name, (doc_dir / "text.txt").read_text(encoding="utf-8"),
                                _read(doc_dir / "gold.j1"), _read(doc_dir / "gold.j2")))
    return docs

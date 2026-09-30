"""Add a test document: python -m model.eval.intake <family> <path-or-url> [--id ID] [--note TEXT]

Copies or downloads the document into <testsets>/<family>/<id>/, writes text.txt (PDFs go
through tools/pdftext, the same pdf.js code the browser will use) and records it in
<testsets>/manifest.json. A URL is recorded so a public document can be fetched again; a
local file is recorded as "local" and never committed.
"""
import argparse
import hashlib
import json
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from model.eval.testset import FAMILIES
from model.paths import REPO_ROOT, testsets_dir

PDFTEXT = REPO_ROOT / "tools" / "pdftext" / "extract.mjs"
USER_AGENT = "degreepilot-testset/0.1"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "doc"


def pdf_to_text(pdf: Path) -> str:
    result = subprocess.run(["node", str(PDFTEXT), str(pdf)], capture_output=True, text=True, encoding="utf-8")
    if result.returncode == 2:
        raise SystemExit(f"{pdf.name} has no text layer (a scan?). Save its text as a .txt file instead.")
    if result.returncode != 0:
        raise SystemExit(f"PDF text extraction failed: {result.stderr.strip()}")
    return result.stdout


def _fetch(source: str, target: Path) -> None:
    if not source.startswith(("http://", "https://")):
        shutil.copyfile(source, target)
        return
    request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            target.write_bytes(response.read())
    except urllib.error.URLError as error:
        # Some university servers send an incomplete certificate chain. Python can't
        # complete it; curl on Windows checks against the system store, which can.
        # Verification stays on either way.
        if not isinstance(error.reason, ssl.SSLCertVerificationError) or not shutil.which("curl"):
            raise
        subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                        "--user-agent", USER_AGENT, "-o", str(target), source], check=True)


def intake(family: str, source: str, doc_id: str | None = None, note: str = "", root: Path | None = None) -> Path:
    if family not in FAMILIES:
        raise SystemExit(f"family must be one of {FAMILIES}")
    root = root or testsets_dir()
    is_url = source.startswith(("http://", "https://"))
    name = source.rstrip("/").rsplit("/", 1)[-1] if is_url else Path(source).name
    suffix = ".pdf" if name.lower().endswith(".pdf") else ".txt"
    doc_dir = root / family / (doc_id or slug(Path(name).stem))
    if doc_dir.exists():
        raise SystemExit(f"{doc_dir} already exists; pick another --id")
    doc_dir.mkdir(parents=True)
    try:
        target = doc_dir / f"source{suffix}"
        _fetch(source, target)
        text = pdf_to_text(target) if suffix == ".pdf" else target.read_text(encoding="utf-8")
        (doc_dir / "text.txt").write_text(text, encoding="utf-8")
    except BaseException:
        shutil.rmtree(doc_dir)
        raise
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    manifest.append({"id": doc_dir.name, "family": family, "source": source if is_url else "local",
                     "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "note": note})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return doc_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m model.eval.intake")
    parser.add_argument("family", choices=FAMILIES)
    parser.add_argument("source", help="a file path or an http(s) URL")
    parser.add_argument("--id", dest="doc_id")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)
    print(intake(args.family, args.source, args.doc_id, args.note))
    return 0


if __name__ == "__main__":
    sys.exit(main())

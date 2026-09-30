import json
import shutil

import pytest

from model.eval.intake import PDFTEXT, intake


def _minimal_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = "%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


def test_intake_local_text_file(tmp_path):
    source = tmp_path / "My Transcript.txt"
    source.write_text("ECON 101 Principles 3.00 A\n", encoding="utf-8")
    root = tmp_path / "testsets"
    doc = intake("transcript", str(source), root=root)
    assert doc == root / "transcript" / "my-transcript"
    assert (doc / "text.txt").read_text(encoding="utf-8") == "ECON 101 Principles 3.00 A\n"
    entry = json.loads((root / "manifest.json").read_text(encoding="utf-8"))[0]
    assert entry["source"] == "local"
    assert entry["family"] == "transcript"
    assert len(entry["sha256"]) == 64


def test_intake_refuses_duplicates_and_unknown_families(tmp_path):
    source = tmp_path / "a.txt"
    source.write_text("x", encoding="utf-8")
    intake("resume", str(source), root=tmp_path / "t")
    with pytest.raises(SystemExit):
        intake("resume", str(source), root=tmp_path / "t")
    with pytest.raises(SystemExit):
        intake("poem", str(source), root=tmp_path / "t")


@pytest.mark.skipif(not (shutil.which("node") and (PDFTEXT.parent / "node_modules").exists()),
                    reason="needs node and tools/pdftext dependencies")
def test_intake_pdf_extracts_text(tmp_path):
    pdf = tmp_path / "t.pdf"
    pdf.write_bytes(_minimal_pdf("ECON 101 Principles"))
    doc = intake("transcript", str(pdf), root=tmp_path / "t")
    assert (doc / "text.txt").read_text(encoding="utf-8").strip() == "ECON 101 Principles"


def test_fetch_falls_back_to_curl_when_the_certificate_chain_is_incomplete(tmp_path, monkeypatch):
    import ssl
    import urllib.error
    from pathlib import Path

    from model.eval import intake as intake_module

    def refuse(*args, **kwargs):
        raise urllib.error.URLError(ssl.SSLCertVerificationError("unable to get local issuer certificate"))

    calls = []

    def fake_run(command, check):
        calls.append(command)
        Path(command[command.index("-o") + 1]).write_bytes(b"hello")

    monkeypatch.setattr(intake_module.urllib.request, "urlopen", refuse)
    monkeypatch.setattr(intake_module.subprocess, "run", fake_run)
    monkeypatch.setattr(intake_module.shutil, "which", lambda name: "curl")
    target = tmp_path / "doc.txt"
    intake_module._fetch("https://example.org/doc.txt", target)
    assert target.read_bytes() == b"hello"
    assert calls[0][0] == "curl" and "--fail" in calls[0]

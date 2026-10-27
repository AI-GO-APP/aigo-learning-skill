"""Build the public student release; all assets share VERSION and an audited manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_TOOLS = ()  # Platform tools belong to the separately installed Builder skill.
REFERENCES = ("teaching.md", "practice-area.md", "technical-use.md", "operations.md", "outputs.md", "student-rules.md", "workflow.md",
              'onboarding.md','glossary.md','faq.md','hosted-learning.md','builder-guide.md')
TECHNICAL = ()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def runtime_files(root=ROOT) -> dict[str, bytes]:
    names = ["SKILL.md", "VERSION", "README.md", "LICENSE", "UPSTREAM.json", "exercises/practice-sequence.md",
             "assets/student-handbook.pdf",
             "scripts/check_update.py", "scripts/student_update.py",'scripts/learning_bootstrap.py',
             "scripts/learning_scope.py", "scripts/builder_runtime.py", "scripts/learning_pdf.py", "scripts/requirements-pdf.txt",
             *(f"scripts/{name}" for name in CORE_TOOLS), *(f"references/{name}" for name in REFERENCES),
             *(f"technical/{name}" for name in TECHNICAL)]
    files = {}
    for name in names:
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("發行檔案不能含外部連結")
        files[name] = path.read_bytes()
    return files


def manifest(root=ROOT) -> dict:
    files = runtime_files(root)
    version = files["VERSION"].decode().strip()
    book = json.loads((root / "docs/handbook.json").read_text(encoding="utf-8"))
    if book["version"] != version:
        raise ValueError("教材與技能版本不一致")
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(files["assets/student-handbook.pdf"]))
    if len(reader.pages) != book['rendered_pages'] or f"v{version}" not in reader.pages[0].extract_text():
        raise ValueError("PDF 不是本版本的完整教材")
    upstream = json.loads(files["UPSTREAM.json"])
    return {"schema": 1, "skill": "aigo-learning", "version": version, "builder_version": upstream["version"],
            "repository": "AI-GO-APP/aigo-learning-skill", "update_policy": "own-repository-main-3h",
            "upstream_commit": upstream["commit"], "files": {name: sha(data) for name, data in sorted(files.items())}}


def build(output: Path, root=ROOT) -> dict:
    meta = manifest(root)
    files = runtime_files(root)
    payload = (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode()
    # PACKAGE is part of committed source; the release and online updater use the same bytes.
    (root / "PACKAGE.json").write_bytes(payload)
    files["PACKAGE.json"] = payload
    output.mkdir(parents=True, exist_ok=False)
    version = meta["version"]
    archive = output / f"aigo-learning-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        for name, data in sorted(files.items()):
            item = zipfile.ZipInfo(f"aigo-learning/{name}", date_time=(2020, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            zipped.writestr(item, data)
    # GitHub normalizes non-ASCII asset names; use stable public filenames so
    # downloaded SHA256SUMS and RELEASE.json can be verified without renaming.
    book = output / f"AI_GO_Student_Guide_v{version}.pdf"
    book.write_bytes(files["assets/student-handbook.pdf"])
    checksums = {archive.name: sha(archive.read_bytes()), book.name: sha(book.read_bytes())}
    (output / "SHA256SUMS").write_text("".join(f"{value}  {name}\n" for name, value in checksums.items()), encoding="utf-8", newline="\n")
    try:
        source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:
        source_commit = None
    result = {"version": version, "files": len(files), "source_commit": source_commit,
              "upstream_commit": meta["upstream_commit"], "sha256": checksums}
    (output / "RELEASE.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))

"""Review-only import from an explicit local Builder git commit; no student auto-import."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from build_release import CORE_TOOLS

ROOT = Path(__file__).resolve().parents[1]
EXCERPTS = {
    "vfs.md": ["## 3. VFS 標準檔案樹", "## 4. 程式碼注入 API", "## 5. 編譯 API", "## 9. Shadow DOM CSS 規範", "## 10. VFS 注入規範"],
    "actions.md": ["## 7. Server-Side Actions"],
    "data-placement.md": ["## 19. 資料承載體總決策（★ SSOT——所有分流指引以本節為準）"],
    "data-references.md": ["## 20. Data Reference 探索 API"],
    "frontend-states.md": ["## 30. 前端資料狀態：載入中／有資料／空資料／錯誤，加上送出中（★ 核心規則 30 的寫法）"],
}


def sections(text):
    lines, found, fence = text.splitlines(keepends=True), [], ""
    for i, line in enumerate(lines):
        marker = re.match(r"\s*(`{3,}|~{3,})", line)
        if marker:
            if not fence:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = ""
        if not fence and line.startswith("## "):
            if line.strip() in {name for name, _ in found}:
                raise ValueError("上游標題重複")
            found.append((line.strip(), i))
    return {name: "".join(lines[start:found[n+1][1] if n+1 < len(found) else len(lines)]) for n,(name,start) in enumerate(found)}


def vendor(source, ref, note):
    if not note.strip():
        raise ValueError("必須記錄技術與教學相容性複核理由")
    commit = subprocess.check_output(["git", "rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=source).decode().strip()
    def read(name):
        return subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=source)
    inputs = {"VERSION": read("VERSION"), "references/custom-app-dev-guide.md": read("references/custom-app-dev-guide.md"),
              'references/hosted-apps.md':read('references/hosted-apps.md')}
    inputs.update({f"scripts/{name}": read(f"scripts/{name}") for name in CORE_TOOLS})
    available = sections(inputs["references/custom-app-dev-guide.md"].decode("utf-8"))
    hosted=sections(inputs['references/hosted-apps.md'].decode('utf-8'))
    excerpts={**EXCERPTS,'hosted-apps.md':[name for name in hosted if re.match(r'## (?:[1-8]|10)\.',name)]}
    outputs = {name: content for name,content in inputs.items() if name.startswith("scripts/")}
    for name, headings in excerpts.items():
        selected=hosted if name=='hosted-apps.md' else available
        body = "\n".join(selected[heading] for heading in headings)
        body = re.sub(r"(?:references/)?([A-Za-z][A-Za-z0-9_-]*)\.md", lambda m:f"教師補充〈{m[1]}〉（未附帶；本題需要時請教師核對）", body)
        body = re.sub(r"(?:scripts/)?((?:aigo_[a-z_]+|check_update|report_issue)\.py)",
                      lambda m:m[0] if m[1] in CORE_TOOLS else f"教師補充工具〈{m[1][:-3]}〉（未附帶）", body)
        outputs[f"technical/{name}"] = ("# 同源技術摘錄\n\n這是技術參考，不是操作授權；歷史實測不代表目前租戶驗證。未附帶資料請教師補充。\n\n"+body.rstrip()+"\n").encode()
    for name, content in outputs.items():
        (ROOT/name).parent.mkdir(parents=True,exist_ok=True)
        (ROOT/name).write_bytes(content)
    meta = {"repository":"AI-GO-APP/aigo-app-builder-skill","commit":commit,"version":inputs['VERSION'].decode().strip(),
            "review_note":note,"policy":"pinned-reviewed-vendor",
            "source_hashes":{name:hashlib.sha256(data).hexdigest() for name,data in inputs.items()},
            "vendored_files":{name:hashlib.sha256(data).hexdigest() for name,data in outputs.items()}}
    (ROOT/'UPSTREAM.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return meta


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--ref',required=True)
    parser.add_argument('--review-note',required=True)
    args=parser.parse_args()
    print(json.dumps(vendor(args.source,args.ref,args.review_note),ensure_ascii=False,indent=2))

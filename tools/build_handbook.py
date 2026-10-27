"""A4 landscape, flat presentation typography; editable source in docs/handbook.json."""
from __future__ import annotations

import argparse
import io
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]


def build(source: Path, output: Path, *, replace=False) -> dict:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import Paragraph
    from pypdf import PdfReader
    data = json.loads(source.read_text(encoding="utf-8"))
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if data["version"] != version:
        raise ValueError("教材版本與技能不一致")
    if output.exists() and not replace:
        raise FileExistsError(output)
    font_root = Path("C:/Windows/Fonts")
    regular, bold = font_root / "msjh.ttc", font_root / "msjhbd.ttc"
    if not regular.is_file() or not bold.is_file():
        raise ValueError("教學指南建置需要可嵌入的繁體字型 msjh.ttc / msjhbd.ttc；可在本機建置後交付已驗證 PDF")
    pdfmetrics.registerFont(TTFont("Guide", str(regular), subfontIndex=0))
    pdfmetrics.registerFont(TTFont("GuideBold", str(bold), subfontIndex=0))
    navy, orange, ink, muted = [colors.HexColor(x) for x in ("#17313E", "#AD4C1C", "#263B46", "#566872")]
    width, height = landscape(A4)
    styles = {
        "title": ParagraphStyle("title", fontName="GuideBold", fontSize=32, leading=42, textColor=navy, wordWrap="CJK"),
        "body": ParagraphStyle("body", fontName="Guide", fontSize=17, leading=26, textColor=ink, wordWrap="CJK"),
        "prompt": ParagraphStyle("prompt", fontName="Guide", fontSize=17, leading=26, textColor=navy, wordWrap="CJK"),
        "intro": ParagraphStyle("intro", fontName="Guide", fontSize=17, leading=26, textColor=muted, wordWrap="CJK"),
        "label": ParagraphStyle("label", fontName="GuideBold", fontSize=17, leading=26, textColor=orange, wordWrap="CJK"),
        "tree": ParagraphStyle("tree", fontName="Guide", fontSize=12, leading=17, textColor=muted, wordWrap="CJK"),
    }
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(width, height), invariant=1, pageCompression=1)
    canvas.setTitle(data["title"])
    canvas.setAuthor("AI GO")
    checks = []

    body_bottom = 112
    def draw(text, x, top, w, kind="body", bottom=None):
        bottom = body_bottom if bottom is None else bottom
        markup = escape(text).replace("\n", "<br/>")
        markup = re.sub(r"(?:\.[A-Za-z][\w-]*/|[A-Za-z][\w-]*/)[A-Za-z0-9_./-]+", r"<nobr>\g<0></nobr>", markup)
        markup = markup.replace("AI GO", "<nobr>AI GO</nobr>")
        paragraph = Paragraph(markup, styles[kind])
        _, h = paragraph.wrap(w, height)
        if top - h < bottom:
            raise ValueError(f"第 {len(checks)+1} 頁文字超出區域：{text[:32]} ({top-h:.1f} < {bottom})")
        paragraph.drawOn(canvas, x, top - h)
        return top - h

    for index, page in enumerate(data["pages"], 1):
        body_bottom = 134 if page.get("links") else 112
        if not page.get("prompt"):
            raise ValueError(f"每個 AI 操作頁都需有範例提示詞：{index}")
        canvas.setFillColor(orange)
        canvas.setFont("GuideBold", 14)
        canvas.drawString(46, height - 33, f"STEP {page['step']}  /  AI GO 學員指南")
        top = draw(page["title"], 46, height - 49, width - 92, "title")
        top = draw(page["intro"], 46, top - 12, width - 92, "intro") - 23
        x_left, x_right = 46, 426
        w_left, w_right = 338, width - 472
        left = draw("你要做的事", x_left, top, w_left, "label") - 9
        for n, text in enumerate(page["steps"], 1):
            left = draw(f"{n}. {text}", x_left, left, w_left) - 13
        right = draw("貼給 AI 的範例提示詞", x_right, top, w_right, "label") - 9
        right = draw(page["prompt"], x_right, right, w_right, "prompt")
        # Folder structure is supporting evidence; a short block can sit below the prompt.
        if page.get("tree"):
            right = draw("\n".join(page["tree"]), x_right, right - 18, w_right, "tree")
        bottom_text = "完成後應看到：" + page["success"]
        draw(bottom_text, 46, 83, width - 92, "intro", bottom=28)
        canvas.setFont("Guide", 9)
        canvas.setFillColor(muted)
        canvas.drawString(46, 17, f"aigo-learning v{version}  |  規則：{' / '.join(page['rules'])}")
        canvas.drawRightString(width - 46, 17, f"{index} / {len(data['pages'])}")
        for n, (label, url) in enumerate(page.get("links", [])):
            # The source link is a footnote, separate from the main 17pt teaching content.
            label = label + " ↗"
            x = 46 + n * 220
            canvas.setFont("Guide", 10)
            canvas.drawString(x, 105, label)
            canvas.linkURL(url, (x, 103, x + pdfmetrics.stringWidth(label, "Guide", 10), 117), relative=0)
        checks.append({"page": index, "step": page["step"], "left_bottom": round(left, 2), "right_bottom": round(right, 2)})
        canvas.showPage()
    canvas.save()
    content = stream.getvalue()
    reader = PdfReader(io.BytesIO(content))
    if len(reader.pages) != len(data["pages"]):
        raise ValueError("PDF 頁數不符")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    return {"pages": len(reader.pages), "version": version, "layout": "A4 landscape, presentation style", "geometry": checks,
            "visual_review": "pending"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "docs/handbook.json")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/student-handbook.pdf")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output, replace=args.replace), ensure_ascii=False))

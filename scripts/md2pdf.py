"""Markdown 讲义 → PDF：第一页是标题和可点目录，书签按标题层级生成，A4，带页码。

用法：python3 md2pdf.py <讲义.md> <输出.pdf> [--toc-depth 1|2|3] [--chapter-breaks]
- 先渲染成一份保留目录的普通 HTML（放临时目录，图片改成绝对 file URL），再用无头 Chrome 打印。
- 目录条目多时自动分两栏、缩小字号；超过 70 条就只列到放得下的层级（书签里仍然是全部标题）。
- --chapter-breaks：每个 ## 章节从新的一页开始。
"""
import argparse
import html
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chrome  # noqa: E402
import mdcommon  # noqa: E402

FONT = '-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif'
CSS = """
@page{size:A4;margin:16mm 15mm 17mm;@bottom-center{content:counter(page) " / " counter(pages);font:9pt FONT;color:#8c959f}}
@page:first{@bottom-center{content:none}}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;color:#1f2328;font:10.5pt/1.7 FONT}
.cover{break-after:page}
.cover h1{font-size:21pt;line-height:1.3;color:#1F4E79;margin:0 0 10pt}
.cover>p{margin:0 0 6pt;color:#3d444d}
nav.toc{margin-top:14pt;border-top:1.5px solid #1F4E79;padding-top:8pt}
.toc-title{font-size:13pt;font-weight:700;color:#1F4E79;margin:0 0 6pt}
.toc-list{columns:var(--cols);column-gap:22pt;font-size:var(--fs)}
.toc-list a{display:block;break-inside:avoid;color:#1f2328;text-decoration:none;padding:1.2pt 0;line-height:1.45}
.toc-list a.l1{font-weight:600;margin-top:3.5pt}
.toc-list a.l2{padding-left:13pt;color:#3d444d}
.toc-list a.l3{padding-left:26pt;color:#59636e}
.toc-note{margin-top:10pt;font-size:9pt;color:#59636e}
h1,h2,h3,h4{line-height:1.35;font-weight:600;break-after:avoid}
main h1{font-size:18pt}
h2{font-size:15.5pt;border-bottom:1px solid #d1d9e0;padding-bottom:3pt;margin:18pt 0 8pt}
h3{font-size:12.5pt;margin:14pt 0 6pt}
h4{font-size:11pt;margin:12pt 0 5pt}
p,ul,ol,table,blockquote,pre{margin:0 0 8pt}
ul,ol{padding-left:1.6em}li{margin:1.5pt 0}
a{color:#0969da;text-decoration:none}
code{font:88% "SF Mono",Menlo,Consolas,monospace;background:#eff1f3;padding:.1em .35em;border-radius:4px;word-break:break-word}
pre{background:#f6f8fa;border:1px solid #e1e6eb;padding:8pt 10pt;border-radius:5px;white-space:pre-wrap;word-break:break-word;line-height:1.45;font-size:8.8pt}
pre code{background:none;padding:0;font-size:inherit}
table{border-collapse:collapse;width:100%;font-size:9.3pt}
thead{display:table-header-group}tr{break-inside:avoid}
th,td{border:1px solid #d1d9e0;padding:4pt 7pt;vertical-align:top;text-align:left}
th{background:#f6f8fa}
blockquote{padding:5pt 10pt;border-left:3.5px solid #d1d9e0;background:#fafbfc;color:#3d444d;break-inside:avoid;border-radius:0 5px 5px 0}
blockquote>:last-child{margin-bottom:0}
blockquote.why{border-color:#1F4E79;background:#eef4fa}blockquote.why>p:first-child>b{color:#1F4E79}
blockquote.say{border-color:#2F6B4F;background:#eef6f1}blockquote.say>p:first-child>b{color:#2F6B4F}
blockquote.warn{border-color:#A93226;background:#fbefed}blockquote.warn>p:first-child>b{color:#A93226}
.tag{display:inline-block;font-size:8pt;font-weight:700;line-height:1;padding:2.5pt 5pt;border-radius:7pt;color:#fff;vertical-align:1pt;white-space:nowrap}
.tag.det{background:#2F6B4F}.tag.agent{background:#B7791F}.tag.guard{background:#A93226}
img{display:block;max-width:100%;max-height:245mm;width:auto;height:auto;margin:0 auto;border:1px solid #d1d9e0;border-radius:4px}
p:has(>img){break-inside:avoid;margin:10pt 0 3pt}
p.caption{font-size:9pt;color:#59636e;text-align:center}
sub{font-size:8.5pt;color:#59636e}
hr{border:0;border-top:1px solid #d1d9e0;margin:14pt 0}
""".replace("FONT", FONT)


def auto_depth(entries, limit=70):
    for d in (3, 2, 1):
        if sum(1 for e in entries if e[0] <= d) <= limit:
            return d
    return 1


def toc_block(entries, depth):
    shown = [e for e in entries if e[0] <= depth]
    n = len(shown)
    cols, fs = (1, "10.5pt") if n <= 28 else (2, "9.5pt" if n <= 50 else "9pt")
    links = "".join(f'<a class="l{lv}" href="#{html.escape(aid)}">{html.escape(label)}</a>' for lv, label, aid in shown)
    note = "点目录里的标题可以跳到对应章节；PDF 阅读器的书签栏里也能按标题跳转。"
    if len(shown) < len(entries):
        note += f"（这里只列到第 {depth} 级，书签里有全部标题。）"
    return (f'<nav class="toc" style="--cols:{cols};--fs:{fs}"><p class="toc-title">目录</p>'
            f'<div class="toc-list">{links}</div><p class="toc-note">{note}</p></nav>'), n


def build(md_path, pdf_path, toc_depth=None, chapter_breaks=False):
    md_path, pdf_path = Path(md_path), Path(pdf_path)
    d = mdcommon.build(md_path)
    depth = toc_depth or auto_depth(d["entries"])
    toc, n = toc_block(d["entries"], depth)
    head = mdcommon.rewrite_src(d["head"], md_path.parent)
    body = mdcommon.rewrite_src(d["body"], md_path.parent)
    css = CSS + ("main h2{break-before:page}" if chapter_breaks else "")
    page = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<title>{html.escape(d["title"])}</title><style>{css}</style></head><body>'
            f'<section class="cover">{head}{toc}</section><main>{body}</main></body></html>')
    with tempfile.TemporaryDirectory(prefix="guide-pdf-") as tmp:
        src, out = Path(tmp) / "print.html", Path(tmp) / "out.pdf"
        src.write_text(page, encoding="utf-8")
        if not chrome.print_pdf(chrome.file_url(src), out):
            raise SystemExit("PDF 生成失败：Chrome 没写出文件")
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(pdf_path))
    return pdf_path, n


def main():
    ap = argparse.ArgumentParser(description="Markdown 讲义转 PDF（第一页可点目录 + 书签）")
    ap.add_argument("md")
    ap.add_argument("pdf")
    ap.add_argument("--toc-depth", type=int, choices=(1, 2, 3))
    ap.add_argument("--chapter-breaks", action="store_true")
    a = ap.parse_args()
    out, n = build(a.md, a.pdf, a.toc_depth, a.chapter_breaks)
    msg = f"wrote {out}  目录 {n} 条"
    try:
        import fitz
        with fitz.open(out) as doc:
            msg += f" · {doc.page_count} 页 · 书签 {len(doc.get_toc())} 个"
    except ImportError:
        pass
    print(msg)


if __name__ == "__main__":
    main()

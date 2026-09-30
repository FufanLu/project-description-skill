"""交付前的校验。有 ERROR 时退出码为 1。

用法：
  python3 check_guide.py <输出根目录> <讲义名>
      全套检查：md/<讲义名>.md、<讲义名>.html、PDF版/<讲义名>.pdf、配图/，再截三张 HTML 图
  python3 check_guide.py --md <讲义.md> [--no-images]
      只查一份 md（模板自检用 --no-images）
选项：
  --shots <目录>   截图放哪（默认新建一个临时目录）
  --no-shots       不截图
  --numbers        列出正文里带数字的行，逐个核对出处用

查什么：
  md   每个 #锚点 都有 <a id>；锚点不重复；标题上面有锚点；有「## 目录」块；图片都在；** 加粗都生效
  html 侧栏每条都能跳；图片都在
  pdf  没有空白页；有书签；第一页的目录可点、目标页存在
"""
import argparse
import html
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mdcommon  # noqa: E402

ANCHOR = re.compile(r'<a\s+id=["\']([^"\']+)["\']')
MD_IMG = re.compile(r'!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
HTML_IMG = re.compile(r'<img\b[^>]*?\bsrc=["\']([^"\']+)["\']')


class Report:
    def __init__(self):
        self.errors = self.warns = 0

    def section(self, title):
        print(f"\n[{title}]")

    def ok(self, msg):
        print(f"  OK     {msg}")

    def warn(self, msg):
        self.warns += 1
        print(f"  WARN   {msg}")

    def err(self, msg):
        self.errors += 1
        print(f"  ERROR  {msg}")


def blank_code(lines):
    """围栏代码块里的行换成空行（行号不变），行内代码去掉。"""
    out, fence = [], None
    for ln in lines:
        m = re.match(r"^\s*(`{3,}|~{3,})", ln)
        if fence:
            out.append("")
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not ln.strip()[len(m.group(1)):]:
                fence = None
            continue
        if m:
            fence = m.group(1)
            out.append("")
            continue
        out.append(re.sub(r"`[^`\n]*`", "", ln))
    return out


def brief(nums, limit=12):
    s = "、".join(str(n) for n in nums[:limit])
    return s + ("……" if len(nums) > limit else "")


def check_md(md_path, r, images=True, numbers=False):
    r.section(f"Markdown · {md_path}")
    if not md_path.exists():
        r.err("文件不存在")
        return 0
    raw = md_path.read_text(encoding="utf-8").split("\n")
    lines = blank_code(raw)

    anchors = {}
    for i, ln in enumerate(lines, 1):
        for aid in ANCHOR.findall(ln):
            if aid in anchors:
                r.err(f"锚点重复：{aid}（第 {anchors[aid]} 行和第 {i} 行）")
            anchors.setdefault(aid, i)
            if not re.fullmatch(r"[A-Za-z0-9_.:-]+", aid):
                r.warn(f"第 {i} 行的锚点 {aid} 不是纯 ASCII，有的阅读器跳不过去")

    missing = []
    for i, ln in enumerate(lines, 1):
        for target in re.findall(r"\]\(#([^)\s]+)\)", ln) + re.findall(r'href=["\']#([^"\']+)', ln):
            if target not in anchors:
                missing.append((i, target))
    n_links = sum(len(re.findall(r"\]\(#[^)\s]+\)", ln)) for ln in lines)
    if missing:
        for i, t in missing[:20]:
            r.err(f"第 {i} 行链接 #{t} 找不到对应的 <a id=\"{t}\">")
    else:
        r.ok(f"{n_links} 个内部链接都有对应锚点（共 {len(anchors)} 个锚点）")

    toc_line = next((i for i, ln in enumerate(lines, 1) if ln.strip() == mdcommon.TOC_HEADING), None)
    if toc_line is None:
        r.err("没有「## 目录」块：HTML 侧栏和 PDF 第一页都靠它")
        toc_targets = set()
    else:
        _, entries, _ = mdcommon.split_toc("\n".join(raw))
        toc_targets = {e[2] for e in entries}
        r.ok(f"目录块在第 {toc_line} 行，{len(entries)} 条")

    no_anchor, chapters_missing = [], []
    for i, ln in enumerate(lines, 1):
        if not re.match(r"^#{2,6} ", ln) or ln.strip() == mdcommon.TOC_HEADING:
            continue
        j = i - 2
        while j >= 0 and not lines[j].strip():
            j -= 1
        ids = ANCHOR.findall(lines[j]) if j >= 0 else []
        if not ids:
            no_anchor.append(i)
        elif ln.startswith("## ") and toc_targets and not set(ids) & toc_targets:
            chapters_missing.append(i)
    if no_anchor:
        r.warn(f"{len(no_anchor)} 个标题上一行没有 <a id> 锚点：第 {brief(no_anchor)} 行")
    if chapters_missing:
        r.warn(f"{len(chapters_missing)} 个 ## 章节不在目录块里：第 {brief(chapters_missing)} 行")

    if images:
        srcs = [(i, s) for i, ln in enumerate(lines, 1) for s in MD_IMG.findall(ln) + HTML_IMG.findall(ln)]
        bad = [(i, s) for i, s in srcs if (p := mdcommon.local_path(s, md_path.parent)) is not None and not p.exists()]
        for i, s in bad:
            r.err(f"第 {i} 行的图片不存在：{s}")
        if srcs and not bad:
            r.ok(f"{len(srcs)} 张图片路径都在")

    md = mdcommon.md_parser()
    bold_bad = []
    for i, ln in enumerate(lines, 1):
        if ln.count("**") < 2 or ln.count("**") % 2:
            continue
        out = re.sub(r"<code>.*?</code>", "", md.renderInline(ln))
        if "**" in out:
            bold_bad.append(i)
    for i in bold_bad:
        r.err(f"第 {i} 行的 ** 加粗没生效（以标点开头或结尾的加粗改用 <b>）：{raw[i - 1].strip()[:60]}")
    if not bold_bad:
        r.ok("加粗都能正常渲染")

    holes = [i for i, ln in enumerate(lines, 1) if re.search(r"\{[^{}\n]*[\u4e00-\u9fff][^{}\n]*\}", ln)]
    if holes:
        r.warn(f"{len(holes)} 行还有模板占位 {{…}} 没填：第 {brief(holes)} 行")

    if numbers:
        r.section("正文里带数字的行（逐个核对出处）")
        in_toc = False
        for i, (ln, orig) in enumerate(zip(lines, raw), 1):
            s = orig.strip()
            if s == mdcommon.TOC_HEADING:
                in_toc = True
            elif s.startswith("<a id="):
                in_toc = False
            if in_toc or not ln.strip() or s.startswith(("#", "<a id=", "<sub>", "![", "<i>图", "|---", "| ---")):
                continue
            text = re.sub(r"<[^>]+>|\]\([^)]*\)", "", s)
            probe = re.sub(r"^\d+\.\s|\b[WQ]\d+\b|图\s*\d+|第\s*\d+(?:[–-]\d+)?\s*[章步节页行]|\b\d+(?:\.\d+)+(?=[）)\s])", "", text)
            if re.search(r"\d", probe):
                print(f"  L{i}: {text[:110]}")
    return len(anchors)


def check_html(html_path, r):
    r.section(f"HTML · {html_path}")
    if not html_path.exists():
        r.err("文件不存在")
        return []
    text = html_path.read_text(encoding="utf-8")
    ids = set(re.findall(r'\bid="([^"]+)"', text))
    aside = re.search(r"<aside\b.*?</aside>", text, re.S)
    if not aside:
        r.err("没有左侧目录 <aside>：请用 md2html_sidebar.py 生成")
        return []
    hrefs = [h for h in re.findall(r'href="#([^"]+)"', aside.group(0)) if h != "top"]
    bad = [h for h in hrefs if h not in ids]
    for h in bad[:20]:
        r.err(f"侧栏链接 #{h} 在页面里找不到")
    if not bad:
        r.ok(f"侧栏 {len(hrefs)} 条都能跳")
    srcs = HTML_IMG.findall(text)
    missing = [s for s in srcs if (p := mdcommon.local_path(s, html_path.parent)) is not None and not p.exists()]
    for s in missing:
        r.err(f"图片不存在：{s}")
    if srcs and not missing:
        r.ok(f"{len(srcs)} 张图片都在")
    return hrefs


def check_pdf(pdf_path, r, n_headings=None):
    r.section(f"PDF · {pdf_path}")
    if not pdf_path.exists():
        r.err("文件不存在")
        return
    try:
        import fitz
    except ImportError:
        r.err("没装 PyMuPDF：pip install pymupdf")
        return
    with fitz.open(pdf_path) as doc:
        n = doc.page_count
        blank = [i + 1 for i, p in enumerate(doc)
                 if not p.get_text().strip() and not p.get_images() and not p.get_drawings()]
        if blank:
            r.err(f"空白页：第 {brief(blank)} 页")
        else:
            r.ok(f"{n} 页，没有空白页")
        toc = doc.get_toc()
        if not toc:
            r.err("没有书签：打印时要带 --generate-pdf-document-outline（md2pdf.py 已经带了）")
        else:
            extra = f"（md 里 {n_headings} 个标题）" if n_headings else ""
            r.ok(f"书签 {len(toc)} 个{extra}")
            if n_headings and len(toc) < n_headings * 0.8:
                r.warn("书签明显比标题少，检查标题层级")
        links = [ln for ln in doc[0].get_links() if ln.get("kind") in (fitz.LINK_GOTO, fitz.LINK_NAMED)]
        bad = [ln for ln in links if not 0 <= ln.get("page", -1) < n]
        if not links:
            r.err("第一页没有可点的目录链接")
        elif bad:
            r.err(f"第一页有 {len(bad)} 个链接指向不存在的页")
        else:
            r.ok(f"第一页 {len(links)} 个目录链接都能跳")


def check_figures(root, name, n_md_images, r):
    r.section(f"配图 · {root / '配图'}")
    folder = root / "配图"
    if not folder.is_dir():
        r.err("没有 配图/ 目录")
        return
    project = name[:-2] if name.endswith("讲义") else name
    mine = sorted(p for p in folder.iterdir() if p.name.startswith(project) and p.suffix.lower() == ".png")
    if not mine:
        r.err(f"配图/ 里没有以「{project}」开头的 PNG")
        return
    small = []
    try:
        from PIL import Image
        for p in mine:
            with Image.open(p) as im:
                if im.width < 2000:
                    small.append(f"{p.name}（{im.width}px）")
    except ImportError:
        pass
    r.ok(f"{len(mine)} 张 PNG（md 里引用了 {n_md_images} 张图）")
    if len(mine) < n_md_images:
        r.warn("配图比正文里的图少：每张图都要单独放一份高清版")
    if small:
        r.warn("这些图宽度不到 2000px，可能不是 2 倍图：" + "、".join(small))


def shot_at(html_path, anchor, png, width=1440, height=900):
    """截某个锚点附近的一屏。无头 Chrome 滚动后截图是白的，所以不滚动：
    临时复制一份页面（<base> 指回原目录，图片照样能加载），用 transform 把正文往上挪。"""
    import chrome
    text = html_path.read_text(encoding="utf-8")
    base = html_path.parent.resolve().as_uri() + "/"
    js = ("<script>addEventListener('load',function(){var t=document.getElementById(%s);"
          "var w=document.querySelector('.wrap')||document.body;"
          "if(t){w.style.transform='translateY('+(16-t.getBoundingClientRect().top)+'px)';}});</script>") % json.dumps(anchor)
    text = text.replace("<head>", f'<head><base href="{html.escape(base)}">', 1).replace("</body>", js + "</body>", 1)
    with tempfile.TemporaryDirectory(prefix="guide-shot-") as tmp:
        page = Path(tmp) / "shot.html"
        page.write_text(text, encoding="utf-8")
        return chrome.screenshot(chrome.file_url(page), png, width, height)


def take_shots(html_path, hrefs, shots, r):
    import chrome
    from svg2png import is_blank
    r.section(f"截图 · {shots}")
    shots.mkdir(parents=True, exist_ok=True)
    url = chrome.file_url(html_path)
    # 无头 Chrome 的窗口最窄 500px，给 390 也会按 500 排版；500 已经触发窄屏样式（≤ 900px）
    plan = [("shot_top.png", lambda p: chrome.screenshot(url, p, 1440, 900), "开头 · 1440 宽"),
            ("shot_narrow.png", lambda p: chrome.screenshot(url, p, 500, 900, scale=2), "开头 · 500 宽（窄屏）")]
    picks = []
    if len(hrefs) > 2:
        picks = [("shot_mid.png", hrefs[len(hrefs) // 2]), ("shot_late.png", hrefs[-2])]
    for fname, aid in picks:
        plan.append((fname, lambda p, aid=aid: shot_at(html_path, aid, p), f"#{aid} 附近 · 1440 宽"))
    for fname, fn, desc in plan:
        png = shots / fname
        if fn(png) and not is_blank(png):
            r.ok(f"{png}  （{desc}）")
        else:
            r.err(f"截图失败或白屏：{fname}（{desc}）")
    print("  用 Read 打开上面的截图看一眼：侧栏、标题、图片、表格、引用块有没有错位")


def main():
    ap = argparse.ArgumentParser(description="讲义交付前校验")
    ap.add_argument("root", nargs="?", help="输出根目录")
    ap.add_argument("name", nargs="?", help="讲义名，比如 某项目讲义（不带扩展名）")
    ap.add_argument("--md", help="只查这一份 md")
    ap.add_argument("--no-images", action="store_true")
    ap.add_argument("--shots")
    ap.add_argument("--no-shots", action="store_true")
    ap.add_argument("--numbers", action="store_true")
    a = ap.parse_args()
    r = Report()

    if a.md:
        check_md(Path(a.md), r, images=not a.no_images, numbers=a.numbers)
    elif a.root and a.name:
        root = Path(a.root).expanduser()
        md_path = root / "md" / f"{a.name}.md"
        check_md(md_path, r, numbers=a.numbers)
        text = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        body = "\n".join(blank_code(text.split("\n")))
        n_headings = len(re.findall(r"^#{1,6} ", body, re.M)) - (1 if mdcommon.TOC_HEADING in body else 0)
        n_images = len(set(MD_IMG.findall(body)))
        html_path = root / f"{a.name}.html"
        hrefs = check_html(html_path, r)
        check_pdf(root / "PDF版" / f"{a.name}.pdf", r, n_headings)
        check_figures(root, a.name, n_images, r)
        docx = sorted(root.glob(f"{a.name}*.docx"))
        if docx:
            r.warn("发现 Word 文件（这套流程不做 Word）：" + "、".join(p.name for p in docx))
        if not a.no_shots and html_path.exists():
            shots = Path(a.shots) if a.shots else Path(tempfile.mkdtemp(prefix="guide-shots-"))
            take_shots(html_path, hrefs, shots, r)
    else:
        ap.error("要么给 <输出根目录> <讲义名>，要么给 --md <文件>")

    print(f"\n结果：{r.errors} 个 ERROR，{r.warns} 个 WARN")
    sys.exit(1 if r.errors else 0)


if __name__ == "__main__":
    main()

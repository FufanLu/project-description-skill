"""讲义 Markdown 的公共处理：拆目录块、渲染、锚点归位、图片路径改写、标签和引用块上色。

md2html_sidebar.py、md2pdf.py、check_guide.py 共用。写法约定见 references/output-and-checks.md。
"""
import html
import os
import re
from pathlib import Path
from urllib.parse import quote, unquote

from markdown_it import MarkdownIt

TOC_HEADING = "## 目录"
# 【确定性】这类标签在 HTML / PDF 里显示成彩色小标签；别的【】原样保留
TAGS = {"确定性": "det", "Agent": "agent", "LLM": "agent", "护栏": "guard", "人在回路": "guard"}

TOC_ITEM = re.compile(r"^(\s*)[-*+] \[(.+)\]\(#([^)\s]+)\)\s*$")
ANCHOR_RUN = re.compile(r'<p>\s*((?:<a\s+id=["\'][^"\']+["\']\s*>\s*</a>\s*)+)</p>\s*(<h([1-6])>)?')
SPLIT = re.compile(r"(<pre\b.*?</pre>|<code\b.*?</code>|<[^>]+>)", re.S)
TAG_RE = re.compile("【(" + "|".join(map(re.escape, TAGS)) + ")】")
CALLOUT = re.compile(r"<blockquote>\s*<p><b>(.*?)</b>", re.S)
CAPTION = re.compile(r"<p>(<i>(?:(?!</i>).)*</i>)</p>", re.S)
IMG_SRC = re.compile(r'(<img\b[^>]*?\bsrc=")([^"]+)(")')


def md_parser():
    return MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def plain(md, s):
    """一小段行内 Markdown 转纯文字（去掉反引号、转义、加粗）。"""
    return strip_tags(md.renderInline(s))


def split_toc(text):
    """把讲义拆成 (head, entries, body)。

    head    = 「# 标题」到「## 目录」之前（标题、导语、元信息）
    entries = 目录块里的条目 [(层级 1-3, 文字, 锚点)]；缩进 0 / 2 / 4 个空格对应 1 / 2 / 3 级
    body    = 目录块之后的全部。目录块到下一个 <a id= 行或下一个 ## 标题为止。
    没有目录块时 head 只含标题，entries 为空。
    """
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.strip() == TOC_HEADING), None)
    if start is None:
        t = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), -1)
        return "\n".join(lines[:t + 1]), [], "\n".join(lines[t + 1:])
    end, entries = start + 1, []
    while end < len(lines) and not lines[end].lstrip().startswith("<a id=") and not lines[end].startswith("## "):
        m = TOC_ITEM.match(lines[end])
        if m:
            level = min(3, len(m.group(1).expandtabs(4)) // 2 + 1)
            entries.append((level, m.group(2), m.group(3)))
        end += 1
    return "\n".join(lines[:start]), entries, "\n".join(lines[end:])


def title_of(text):
    return next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), "讲义")


def hoist_anchors(h):
    """<p><a id="x"></a></p><h2>…  →  <h2 id="x">…；后面没有标题的锚点变成空 div。"""
    def fix(m):
        ids = re.findall(r'id=["\']([^"\']+)', m.group(1))
        if m.group(2):
            extra = "".join(f'<a id="{i}"></a>' for i in ids[1:])
            return f'<h{m.group(3)} id="{ids[0]}">{extra}'
        return "".join(f'<div class="anchor" id="{i}"></div>' for i in ids) + "\n"
    h = ANCHOR_RUN.sub(fix, h)
    n = [0]

    def auto(m):
        n[0] += 1
        return f'<h{m.group(1)} id="auto-{n[0]}">'
    return re.sub(r"<h([2-4])>", auto, h)


def colorize_tags(h):
    parts = SPLIT.split(h)
    for i in range(0, len(parts), 2):  # 偶数位是正文文字，奇数位是标签和代码
        parts[i] = TAG_RE.sub(lambda m: f'<span class="tag {TAGS[m.group(1)]}">{m.group(1)}</span>', parts[i])
    return "".join(parts)


def callout_kind(title):
    t = strip_tags(title)
    if t.startswith("为什么"):
        return "why"
    if any(k in t for k in ("这样说", "一句话", "答案")):
        return "say"
    if any(k in t for k in ("注意", "需要你", "请确认", "雷区", "边界", "别", "不要", "核不到")):
        return "warn"
    return "note"


def decorate(h):
    h = hoist_anchors(h)
    h = colorize_tags(h)
    h = CALLOUT.sub(lambda m: f'<blockquote class="callout {callout_kind(m.group(1))}">\n<p><b>{m.group(1)}</b>', h)
    return CAPTION.sub(r'<p class="caption">\1</p>', h)


def entries_from_headings(h):
    return [(int(m.group(1)) - 1, strip_tags(m.group(3)), m.group(2))
            for m in re.finditer(r'<h([23]) id="([^"]+)">(.*?)</h\1>', h, re.S)]


def build(md_path):
    """读一份讲义 md，返回 dict(title, head, entries, body)。head / body 是 HTML。"""
    text = Path(md_path).read_text(encoding="utf-8")
    md = md_parser()
    head_md, raw_entries, body_md = split_toc(text)
    head, body = decorate(md.render(head_md)), decorate(md.render(body_md))
    entries = [(lv, plain(md, label), aid) for lv, label, aid in raw_entries] or entries_from_headings(body)
    return dict(title=plain(md, title_of(text)), head=head, entries=entries, body=body)


def rewrite_src(h, md_dir, out_dir=None):
    """图片的相对路径按 md 所在目录解析，再改成相对 out_dir 的路径；out_dir=None 时改成绝对 file URL。"""
    md_dir = Path(md_dir).resolve()

    def fix(m):
        src = html.unescape(m.group(2))
        if re.match(r"^[a-z][a-z0-9+.-]*:", src, re.I) or src.startswith(("/", "#")):
            return m.group(0)
        p = (md_dir / unquote(src)).resolve()
        if out_dir is None:
            new = p.as_uri()
        else:
            new = quote(os.path.relpath(p, Path(out_dir).resolve()).replace(os.sep, "/"))
        return m.group(1) + html.escape(new, quote=True) + m.group(3)
    return IMG_SRC.sub(fix, h)


def image_srcs(h):
    return [html.unescape(s) for s in re.findall(r'<img\b[^>]*?\bsrc="([^"]+)"', h)]


def local_path(src, base_dir):
    """把 HTML 里的图片 src 还原成磁盘路径；网络地址返回 None。"""
    if src.startswith("file://"):
        return Path(unquote(src[7:]))
    if re.match(r"^[a-z][a-z0-9+.-]*:", src, re.I):
        return None
    return (Path(base_dir) / unquote(src)).resolve()

"""画图的公共部分：配色、字体、文字宽度估算、自动换行、写 SVG（可顺手转 PNG）。

figlib.py（框图）和 seqdiag.py（时序图）都从这里取。
宽度是估算：中文按 1 个字号宽，西文按 0.56 个字号宽（等宽字体 0.61）。
"""
import re
from pathlib import Path
from xml.sax.saxutils import escape

# 颜色和讲义里的标签一一对应：蓝 = 主流程，绿 = 确定性 / 存储，橙 = Agent / LLM，红 = 护栏 / 人，灰 = 占位
BLUE, INK, MUTED = "#1F4E79", "#1E2833", "#5A6676"
AMBER, GREEN, RED, GRAY = "#B7791F", "#2F6B4F", "#A93226", "#7A828C"
SOFT = {BLUE: "#F4F8FC", AMBER: "#FBF3E4", GREEN: "#F3F8F5", RED: "#FFF7F6", GRAY: "#F4F5F6"}  # 浅底
EDGE = {BLUE: "#A8BFD6", AMBER: "#E0C28A", GREEN: "#9CC3AE", RED: "#E3B5AF", GRAY: "#C3C8CE"}  # 浅边框
FONT = "'PingFang SC','Hiragino Sans GB','Noto Sans CJK SC','Microsoft YaHei',sans-serif"
MONO = "'SF Mono','Menlo','Consolas',monospace"

# 避头尾：这些标点不放行首 / 行尾
NO_LINE_START = set("，。、；：？！）」』》〉】,.;:?!)]}%…—·")
NO_LINE_END = set("（「『《〈【([{")
_TOKEN = re.compile(r"[A-Za-z0-9_./()\-=:*<>{}\[\]'\"@#+%|,≥≤~^$&!?;]+| |.")


def char_w(ch, size, mono=False):
    return size if ord(ch) > 0x2E7F else size * (0.61 if mono else 0.56)


def text_w(s, size, mono=False):
    return sum(char_w(c, size, mono) for c in s)


def wrap(s, max_px, size, mono=False):
    """按像素宽度换行。西文单词不拆开，标点守避头尾。支持 \\n 强制换行。"""
    out = []
    for para in str(s).split("\n"):
        out.extend(_wrap_one(para, max_px, size, mono) or [""])
    return out


def _wrap_one(s, max_px, size, mono):
    lines, cur, w = [], "", 0.0
    for tok in _TOKEN.findall(s):
        tw = text_w(tok, size, mono)
        if w + tw > max_px and cur:
            if tok[0] in NO_LINE_START:        # 标点贴在上一行末尾，宁可略超
                cur += tok
                w += tw
                continue
            carry = ""
            while cur and cur[-1] in NO_LINE_END:  # 开括号跟到下一行
                carry, cur = cur[-1] + carry, cur[:-1]
            if cur.strip():
                lines.append(cur.rstrip())
            cur, w = carry, text_w(carry, size, mono)
            if tok == " ":
                continue
        if tw > max_px:                          # 超长单词：逐字拆
            for c in tok:
                cw = char_w(c, size, mono)
                if w + cw > max_px and cur:
                    lines.append(cur)
                    cur, w = "", 0.0
                cur += c
                w += cw
            continue
        cur += tok
        w += tw
    if cur.strip():
        lines.append(cur.rstrip())
    return lines


def keep_spaces(s):
    """SVG 会把连续空格合成一个：行首、行尾和连续的空格换成不换行空格。"""
    return re.sub(r"(?<= ) |^ | $", " ", s)


def svg_text(x, y, s, size=15, color=INK, weight="normal", anchor="start", family=FONT):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(keep_spaces(str(s)))}</text>')


def svg_rect(x, y, w, h, fill="#FFFFFF", stroke=BLUE, sw=1.5, rx=10, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def markers(colors):
    """每种颜色一个箭头 marker，id = ah-<色值>；另加一个起点箭头 ahs。"""
    out = "".join(
        f'<marker id="ah-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in sorted(colors))
    out += (f'<marker id="ahs" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{BLUE}"/></marker>')
    return out


def save(W, H, body, stem, colors=(BLUE,), png=True, scale=2):
    """写 <stem>.svg；png=True 时再用无头 Chrome 截成 <stem>.png（scale 倍）。返回 svg 路径。"""
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(W)}" height="{int(H)}" viewBox="0 0 {int(W)} {int(H)}">'
           f'<defs>{markers(set(colors) | {BLUE})}</defs><rect width="{int(W)}" height="{int(H)}" fill="#FFFFFF"/>'
           + "".join(body) + "</svg>")
    svg_path = stem.parent / (stem.name + ".svg")
    svg_path.write_text(svg, encoding="utf-8")
    if png:
        from svg2png import svg_to_png
        svg_to_png(svg_path, scale=scale)
    return svg_path

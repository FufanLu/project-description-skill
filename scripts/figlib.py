"""框图小工具：系统结构图、状态机、进程 / 目录图都用它画。

用法见 examples/make_arch.py 和 examples/make_state.py。
坐标全部手写：先画一版，截成 PNG 用 Read 看一眼，再调。
"""
from svgbase import (BLUE, INK, MUTED, AMBER, GREEN, RED, GRAY, SOFT, EDGE, FONT, MONO,  # noqa: F401
                     wrap, text_w, svg_text, svg_rect, save)


class Fig:
    def __init__(self, W, title=None, subtitle=None):
        """W = 画布宽（px）。给了 title / subtitle 就画在顶部（y = 52 / 86），正文从 y ≈ 110 开始。"""
        self.W, self.out, self.colors = W, [], {BLUE}
        if title:
            self.text(W / 2, 52, title, size=30, color=BLUE, weight="bold", anchor="middle")
        if subtitle:
            self.text(W / 2, 86, subtitle, size=16, color=MUTED, anchor="middle")

    # ------------------------------------------------------------ 基本图元
    def rect(self, x, y, w, h, fill="#FFFFFF", stroke=BLUE, sw=1.5, rx=10, dash=None):
        self.out.append(svg_rect(x, y, w, h, fill, stroke, sw, rx, dash))

    def text(self, x, y, s, size=15, color=INK, weight="normal", anchor="start", family=FONT):
        """连续空格会自动换成不换行空格，树形图可以直接用空格对齐（配等宽字体）。"""
        self.out.append(svg_text(x, y, s, size, color, weight, anchor, family))

    def width(self, s, size, mono=False):
        return text_w(s, size, mono)

    def lines(self, x, y, s, max_px, size=14, color=INK, lh=None, bullet=False, bullet_color=BLUE):
        """自动换行的一段字；bullet=True 时首行前加圆点。返回最后一行之后的 y。"""
        lh = lh or size + 6
        indent = 16 if bullet else 0
        for i, ln in enumerate(wrap(s, max_px - indent, size)):
            if bullet and i == 0:
                self.text(x, y, "•", size=size, color=bullet_color, weight="bold")
            self.text(x + indent, y, ln, size=size, color=color)
            y += lh
        return y

    def tag(self, x_right, y, s, fill=BLUE, size=12.5):
        """右端对齐 x_right 的实心小标签（「确定性」「护栏」这类）。返回宽度。"""
        w = self.width(s, size) + 18
        self.rect(x_right - w, y - 15, w, 22, fill=fill, stroke=fill, rx=11)
        self.text(x_right - w / 2, y + 1, s, size=size, color="#FFFFFF", weight="bold", anchor="middle")
        return w

    def chip(self, x, y, s, color=BLUE, fill="#E4EDF6", size=13.5, mono=True):
        """左端对齐的圆角小块，用来列表名、模块名。返回宽度。"""
        w = self.width(s, size, mono=mono) + 18
        self.rect(x, y, w, 26, fill=fill, stroke=fill, rx=13, sw=1)
        self.text(x + 9, y + 18, s, size=size, color=color, family=MONO if mono else FONT,
                  weight="bold" if mono else "normal")
        return w

    def band(self, x, y, w, h, label, color=BLUE):
        """左侧的层名色带，label 里用 \\n 换行。"""
        self.rect(x, y, w, h, fill=color, stroke=color, rx=8)
        parts = label.split("\n")
        y0 = y + h / 2 - (len(parts) - 1) * 11 + 6
        for i, ln in enumerate(parts):
            self.text(x + w / 2, y0 + i * 22, ln, size=16, color="#FFFFFF", weight="bold", anchor="middle")

    def legend(self, x, y, items, size=12.5):
        """一排实心小标签做图例，items = [(文字, 颜色), ...]。返回结束的 x。"""
        for s, col in items:
            w = self.width(s, size) + 18
            self.rect(x, y - 15, w, 22, fill=col, stroke=col, rx=11)
            self.text(x + w / 2, y + 1, s, size=size, color="#FFFFFF", weight="bold", anchor="middle")
            x += w + 10
        return x

    # ------------------------------------------------------------ 面板
    def panel_height(self, w, body, size=13.5, bullet=False):
        lh = size + 6
        n = sum(len(wrap(b, w - 24 - (16 if bullet else 0), size)) for b in body)
        return 48 + n * lh + 6

    def panel(self, x, y, w, title, body=(), h=None, color=BLUE, fill=None, stroke=None, dash=None,
              size=13.5, title_mono=False, bullet=False):
        """带标题的方框，body 是若干段文字（自动换行）。h 不给就按内容算。返回实际高度。"""
        h = h or self.panel_height(w, body, size, bullet)
        self.rect(x, y, w, h, fill=fill or SOFT.get(color, "#FFFFFF"), stroke=stroke or EDGE.get(color, color), dash=dash)
        self.text(x + 12, y + 25, title, size=14.5, color=color, weight="bold", family=MONO if title_mono else FONT)
        yy = y + 48
        for b in body:
            yy = self.lines(x + 12, yy, b, w - 24, size=size, color=INK, lh=size + 6, bullet=bullet, bullet_color=color)
        return h

    # ------------------------------------------------------------ 连线
    def arrow(self, pts, color=BLUE, width=2, dash=None, start=False):
        """折线箭头，pts = [(x, y), ...]；start=True 时起点也画箭头。"""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        s = ' marker-start="url(#ahs)"' if start else ""
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.out.append(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}"{d}'
                        f' marker-end="url(#ah-{color[1:]})"{s}/>')
        self.colors.add(color)

    def path(self, d, color=BLUE, width=2, dash=None, arrow=True):
        """任意 SVG path（比如弧线 M x0,y0 Q cx,cy x1,y1），arrow=True 时终点画箭头。"""
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="url(#ah-{color[1:]})"' if arrow else ""
        self.out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{da}{m}/>')
        self.colors.add(color)

    # ------------------------------------------------------------ 输出
    def render(self, H, stem, png=True, scale=2):
        """写 <stem>.svg，png=True 时再截 <stem>.png。stem 可以带目录，比如 out/img/demo_arch。"""
        return save(self.W, H, self.out, stem, colors=self.colors, png=png, scale=scale)

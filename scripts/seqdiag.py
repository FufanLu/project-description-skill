"""时序图：泳道 + 消息 + 说明框 + 循环框。

用法见 examples/make_seq.py。
- 消息自动编号（圆圈里的数字）。消息文字里别再写 ①②，会重复编号。
- 长说明放 act 框，不放消息的 sub；act 框跨两三条以上泳道，不然会挤成一列。
- 一张图 10–15 条消息为宜，再长就拆成两张。
"""
from svgbase import (BLUE, INK, MUTED, AMBER, GREEN, RED, GRAY, SOFT, EDGE, FONT, MONO,  # noqa: F401
                     wrap, text_w, svg_text, svg_rect, save)

LEGEND = [("确定性", GREEN), ("Agent / LLM", AMBER), ("护栏 / 人在回路", RED)]
LEGEND_NOTE = "实线 = 请求 · 虚线 = 返回"

# act 框的几种样式：kind="why" 用来放「为什么这样切」，kind="guard" 放失败和兜底
BOX = {
    "plain": dict(color=BLUE, fill=SOFT[BLUE], stroke=EDGE[BLUE], dash=None),
    "why": dict(color=BLUE, fill="#FFFFFF", stroke=EDGE[BLUE], dash="7 5"),
    "guard": dict(color=RED, fill=SOFT[RED], stroke=EDGE[RED], dash="7 5"),
    "agent": dict(color=AMBER, fill=SOFT[AMBER], stroke=EDGE[AMBER], dash=None),
    "store": dict(color=GREEN, fill=SOFT[GREEN], stroke=EDGE[GREEN], dash=None),
}


class Seq:
    def __init__(self, W, lanes, title, subtitle="", legend=LEGEND, legend_note=LEGEND_NOTE, top=None):
        """lanes = [dict(key=, title=, sub=, color=), ...]，从左到右等宽排开。legend=None 不画图例。
        top = 泳道头的 y；不给就按有没有副标题、图例自动定。"""
        if top is None:
            top = 140 if (legend or legend_note) else (110 if subtitle else 84)
        self.W, self.lanes, self.out, self.colors = W, lanes, [], {BLUE}
        self.L, self.R = 60, 60
        self.sp = (W - self.L - self.R) / len(lanes)
        self.cx = {ln["key"]: self.L + self.sp * (i + 0.5) for i, ln in enumerate(lanes)}
        self.idx = {ln["key"]: i for i, ln in enumerate(lanes)}
        self.title, self.subtitle, self.top = title, subtitle, top
        self.legend, self.legend_note = legend, legend_note
        self.y = top + 110
        self.loops, self.num = [], 0

    # ------------------------------------------------------------ 图元
    def rect(self, x, y, w, h, fill, stroke, sw=1.4, rx=10, dash=None):
        self.out.append(svg_rect(x, y, w, h, fill, stroke, sw, rx, dash))

    def text(self, x, y, s, size=16, color=INK, weight="normal", anchor="start", family=FONT):
        self.out.append(svg_text(x, y, s, size, color, weight, anchor, family))

    def badge(self, x, y, s, color):
        w = text_w(s, 12.5) + 16
        self.rect(x, y - 14, w, 20, color, color, rx=10)
        self.text(x + w / 2, y + 1, s, size=12.5, color="#FFFFFF", weight="bold", anchor="middle")
        return w

    def span_x(self, a, b, pad=18):
        ia, ib = sorted((self.idx[a], self.idx[b]))
        return self.L + self.sp * ia + pad, self.L + self.sp * (ib + 1) - pad

    def _number(self, x, y, color):
        self.num += 1
        self.out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12.5" fill="{color}"/>')
        self.text(x, y + 5, str(self.num), size=13.5, color="#FFFFFF", weight="bold", anchor="middle", family=MONO)

    # ------------------------------------------------------------ 元素
    def msg(self, a, b, label, sub=None, dashed=False, color=BLUE, number=True):
        """一条消息。a == b 时画成自调用的小回环。dashed=True 表示返回。"""
        self.colors.add(color)
        y = self.y + 36
        d = ' stroke-dasharray="7 5"' if dashed else ""
        lw = text_w(label, 16.5)
        if a == b:
            x0 = self.cx[a]
            self.out.append(f'<path d="M{x0 + 6:.1f},{y - 8} H{x0 + 46:.1f} V{y + 14} H{x0 + 10:.1f}" fill="none" '
                            f'stroke="{color}" stroke-width="2.2"{d} marker-end="url(#ah-{color[1:]})"/>')
            lx = x0 + 60
            if number:
                self._number(lx + 12.5, y - 1, color)
                lx += 33
            self.text(lx, y + 4, label, size=16.5, color=color, weight="bold")
            h, sub_x, sub_anchor, sub_w = 58, x0 + 60, "start", self.sp * 1.4
        else:
            x0, x1 = self.cx[a], self.cx[b]
            dirn = 1 if x1 > x0 else -1
            self.out.append(f'<line x1="{x0 + 6 * dirn:.1f}" y1="{y}" x2="{x1 - 8 * dirn:.1f}" y2="{y}" stroke="{color}" '
                            f'stroke-width="2.2"{d} marker-end="url(#ah-{color[1:]})"/>')
            mid = (x0 + x1) / 2
            if number:
                gx = mid - (33 + lw) / 2          # 圆圈 + 文字整体居中
                self._number(gx + 12.5, y - 16, color)
                self.text(gx + 33, y - 11, label, size=16.5, color=color, weight="bold")
            else:
                self.text(mid, y - 11, label, size=16.5, color=color, weight="bold", anchor="middle")
            h, sub_x, sub_anchor, sub_w = 58, mid, "middle", abs(x1 - x0) + self.sp * 0.6
        if sub:
            for i, ln in enumerate(wrap(sub, sub_w, 14.5)):
                self.text(sub_x, y + 24 + i * 20 + (8 if a == b else 0), ln, size=14.5, color=MUTED, anchor=sub_anchor)
                h += 20
        self.y += h + (10 if a == b else 0)

    def act(self, over, title, lines=(), kind="plain", badges=(), size=15, **style):
        """说明框。over = 一条泳道的 key，或 (起, 止) 两条泳道。
        lines 里每项一条圆点；以 ~ 开头的不加圆点。badges = [("确定性", GREEN), ...] 画在右上角。
        kind 见 BOX；也可以直接传 color / fill / stroke / dash 覆盖。"""
        st = dict(BOX[kind])
        st.update(style)
        color = st["color"]
        a, b = over if isinstance(over, tuple) else (over, over)
        x0, x1 = self.span_x(a, b, pad=16 if a != b else 10)
        w = x1 - x0
        body = []
        for it in lines:
            bullet = not it.startswith("~")
            for i, ln in enumerate(wrap(it.lstrip("~"), w - (40 if bullet else 28), size)):
                body.append((bullet and i == 0, ln, bullet))
        h = 44 + len(body) * (size + 7) + (6 if body else -8)
        y = self.y + 8
        self.rect(x0, y, w, h, st["fill"], st["stroke"], dash=st.get("dash"))
        self.text(x0 + 14, y + 27, title, size=16, color=color, weight="bold")
        bx = x1 - 12
        for s, col in reversed(list(badges)):
            bx -= text_w(s, 12.5) + 16
            self.badge(bx, y + 24, s, col)
            bx -= 6
        yy = y + 54
        for first, ln, bullet in body:
            if first:
                self.text(x0 + 16, yy, "•", size=size, color=color, weight="bold")
            self.text(x0 + (32 if bullet else 16), yy, ln, size=size, color=INK)
            yy += size + 7
        self.y = y + h + 8

    def loop_start(self, label, a, b, color=BLUE):
        """循环 / 分组框的开始：框住 a 到 b 这几条泳道，直到 loop_end()。可以嵌套。"""
        self.loops.append((label, a, b, self.y + 4, color, len(self.loops)))
        self.y += 34

    def loop_end(self):
        label, a, b, y0, color, depth = self.loops.pop()
        x0, x1 = self.span_x(a, b, pad=4 + 12 * depth)  # 嵌套的框往里缩，边框不重合
        y1 = self.y + 8
        self.rect(x0, y0, x1 - x0, y1 - y0, "none", color, sw=1.8, rx=12, dash="9 6")
        tw = text_w(label, 14.5) + 24
        self.rect(x0, y0, tw, 28, color, color, rx=10)
        self.text(x0 + 12, y0 + 19, label, size=14.5, color="#FFFFFF", weight="bold")
        self.y = y1 + 10

    def phase(self, label, color=MUTED):
        """横跨全图的分隔线，标一个阶段名。"""
        y = self.y + 22
        self.out.append(f'<line x1="{self.L:.1f}" y1="{y}" x2="{self.W - self.R:.1f}" y2="{y}" stroke="{color}" '
                        f'stroke-width="1.2" stroke-dasharray="3 5"/>')
        tw = text_w(label, 14) + 20
        self.rect(self.L, y - 14, tw, 26, "#FFFFFF", color, sw=1.2, rx=13)
        self.text(self.L + 10, y + 5, label, size=14, color=color, weight="bold")
        self.y += 44

    def gap(self, h):
        self.y += h

    # ------------------------------------------------------------ 输出
    def _head(self, H):
        out = [svg_text(self.W / 2, 54, self.title, 31, BLUE, "bold", "middle")]
        if self.subtitle:
            out.append(svg_text(self.W / 2, 88, self.subtitle, 16, MUTED, "normal", "middle"))
        if self.legend or self.legend_note:
            items = list(self.legend or [])
            total = sum(text_w(s, 12.5) + 16 + 12 for s, _ in items) + (text_w(self.legend_note, 13.5) + 8 if self.legend_note else 0)
            x = self.W / 2 - total / 2
            saved, self.out = self.out, out
            for s, col in items:
                x += self.badge(x, 114, s, col) + 12
            if self.legend_note:
                self.text(x + 8, 115, self.legend_note, size=13.5, color=MUTED)
            out, self.out = self.out, saved
        for ln in self.lanes:
            c = self.cx[ln["key"]]
            w = self.sp - 22
            col = ln.get("color", BLUE)
            out.append(f'<line x1="{c:.1f}" y1="{self.top + 76}" x2="{c:.1f}" y2="{H - 30}" stroke="#C6D3E1" '
                       f'stroke-width="1.6" stroke-dasharray="4 5"/>')
            out.append(svg_rect(c - w / 2, self.top, w, 76, "#FFFFFF", col, 2, 12))
            out.append(svg_text(c, self.top + (32 if ln.get("sub") else 44), ln["title"], 17, col, "bold", "middle"))
            if ln.get("sub"):
                out.append(svg_text(c, self.top + 56, ln["sub"], 13, MUTED, "normal", "middle", MONO))
        return out

    def render(self, stem, png=True, scale=2):
        """写 <stem>.svg，png=True 时再截 <stem>.png。返回 svg 路径。"""
        if self.loops:
            raise RuntimeError("还有没关上的 loop_start()")
        H = int(self.y + 50)
        return save(self.W, H, self._head(H) + self.out, stem, colors=self.colors, png=png, scale=scale)

"""示例：三层系统结构图（虚构的短链接服务 ShortLink）。

用法：python3 make_arch.py [输出目录]
产出 <输出目录>/demo_arch.svg 和 demo_arch.png。
真实讲义里，每个方框都要对应仓库里真实存在的模块，每个数字都要有出处。
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figlib import Fig, BLUE, MUTED, GREEN, RED, GRAY  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "project-description-demo")

W = 1600
f = Fig(W, "ShortLink 系统结构图（虚构示例）",
        "三层：接入 → 服务 → 存储 · 真实讲义里每个方框都对应仓库里的一个模块，数字都有出处")
X0, X1 = 152, W - 24
CW = X1 - X0

# ---------------------------------------------------------------- 接入层
y1, h1 = 116, 146
f.band(24, y1, 112, h1, "接入层")
f.rect(X0, y1, CW, h1, stroke="#8AA4BF")
f.text(X0 + 20, y1 + 31, "api/ · HTTP 入口", size=19, color=BLUE, weight="bold")
f.text(X0 + 196, y1 + 31, "只做参数校验和鉴权，不直接碰存储", size=14, color=MUTED)
f.tag(X1 - 16, y1 + 27, "3 个路由", fill="#5B7FA3")
routes = [("GET /{code}", ["跳转：查短码，返回 302 或 410"]),
          ("POST /links", ["创建：校验目标地址，生成 6 位短码"]),
          ("GET /links/{code}/stats", ["统计：按天聚合点击数"])]
pw = (CW - 40 - 2 * 16) / 3
for i, (t, body) in enumerate(routes):
    f.panel(X0 + 20 + i * (pw + 16), y1 + 50, pw, t, body, h=80, title_mono=True)

# ---------------------------------------------------------------- 层间连线
def link(y_top, y_bot, label, color=BLUE):
    x = X0 + CW / 2
    f.arrow([(x, y_top + 2), (x, y_bot - 4)], color=color, width=2.4)
    f.text(x + 16, (y_top + y_bot) / 2 + 5, label, size=14, color=MUTED)


y2 = y1 + h1 + 56
link(y1 + h1, y2, "函数调用（同一进程）")

# ---------------------------------------------------------------- 服务层
mods = [("shortener", ["生成短码：自增 id 转 62 进制", "撞上已有短码就重试"], BLUE),
        ("redirect", ["先查缓存，没命中查库", "查到后回填缓存"], BLUE),
        ("stats", ["点击事件先进内存队列", "每 5 s 批量落库"], GREEN),
        ("ratelimit", ["按 IP 限流", "超限返回 429"], RED)]
mw = (CW - 40 - 3 * 16) / 4
mh = max(f.panel_height(mw, body, bullet=True) for _, body, _ in mods)
h2 = 50 + mh + 20
f.band(24, y2, 112, h2, "服务层")
f.rect(X0, y2, CW, h2, stroke="#8AA4BF")
f.text(X0 + 20, y2 + 31, "service/ · 业务逻辑", size=19, color=BLUE, weight="bold")
f.text(X0 + 212, y2 + 31, "纯逻辑放 domain/，读写都经过 repo/ 接口", size=14, color=MUTED)
for i, (t, body, col) in enumerate(mods):
    f.panel(X0 + 20 + i * (mw + 16), y2 + 50, mw, t, body, h=mh, color=col, title_mono=True, bullet=True)

y3 = y2 + h2 + 56
link(y2 + h2, y3, "repo/ 接口：换存储不改业务代码", color=GREEN)

# ---------------------------------------------------------------- 存储层
stores = [("Redis", ["缓存 link:{code}，600 s 过期"], GREEN, None),
          ("MySQL", ["links 表、clicks 表"], GREEN, None),
          ("对象存储（占位）", ["导出报表，还没实现"], GRAY, "6 4")]
sw = (CW - 2 * 16) / 3
h3 = max(f.panel_height(sw, body) for _, body, _, _ in stores)
f.band(24, y3, 112, h3, "存储层", color=GREEN)
for i, (t, body, col, dash) in enumerate(stores):
    f.panel(X0 + i * (sw + 16), y3, sw, t, body, h=h3, color=col, dash=dash)
lx = f.legend(X0, y3 + h3 + 44, [("主流程", BLUE), ("存储 / 确定性", GREEN), ("护栏", RED), ("占位", GRAY)])
f.text(lx + 6, y3 + h3 + 45, "虚线框 = 还没实现", size=13.5, color=MUTED)

print(f.render(y3 + h3 + 76, OUT / "demo_arch"))

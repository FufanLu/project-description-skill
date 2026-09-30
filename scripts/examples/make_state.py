"""示例：状态机图（虚构的短链接生命周期）。

用法：python3 make_state.py [输出目录]
产出 <输出目录>/demo_state.svg 和 demo_state.png。
上面的弧线 = 前进，下面的虚线 = 退回；箭头颜色 = 唯一有权发这条命令的角色。
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from figlib import Fig, BLUE, INK, MUTED, GREEN, RED, AMBER, GRAY, SOFT, MONO  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "project-description-demo")

W = 1600
f = Fig(W, "短链的生命周期：4 个状态（虚构示例）", "箭头上是命令名和唯一有权发它的角色 · 实线 = 前进 · 虚线 = 退回")
ACTOR = {"用户": RED, "管理员": AMBER, "定时任务": GREEN}
x = f.legend(W / 2 - 150, 128, list(ACTOR.items()))

states = [("PENDING", "待审核", "刚创建，还不能跳转", GRAY),
          ("ACTIVE", "生效", "可以跳转，点击计入统计", GREEN),
          ("EXPIRED", "过期", "跳转返回 410，数据保留", AMBER),
          ("ARCHIVED", "归档", "只读，30 天后清理", GRAY)]
pitch = (W - 80) / len(states)
nw, ny, nh = 250, 270, 132
cx = [40 + pitch * i + pitch / 2 for i in range(len(states))]
for i, (code, name, promise, col) in enumerate(states):
    x0 = cx[i] - nw / 2
    f.rect(x0, ny, nw, nh, fill=SOFT[col], stroke=col, sw=2.2, rx=12)
    f.text(cx[i], ny + 32, code, size=17, color=col, weight="bold", anchor="middle", family=MONO)
    f.text(cx[i], ny + 58, name, size=16, color=INK, weight="bold", anchor="middle")
    f.lines(x0 + 16, ny + 94, promise, nw - 32, size=14.5, color=INK, lh=21)

# 前进：节点上方的弧线
fwd = [("approve", "管理员 · 目标地址通过检查", "管理员"),
       ("expire", "定时任务 · 到了过期时间", "定时任务"),
       ("archive", "定时任务 · 过期满 7 天", "定时任务")]
for i, (cmd, cond, actor) in enumerate(fwd):
    col = ACTOR[actor]
    x0, x1, mid = cx[i] + 50, cx[i + 1] - 50, (cx[i] + cx[i + 1]) / 2
    f.path(f"M{x0:.1f},{ny - 2} Q{mid:.1f},{ny - 64} {x1:.1f},{ny - 4}", color=col, width=2.4)
    f.text(mid, ny - 80, cmd, size=15, color=col, weight="bold", anchor="middle", family=MONO)
    f.text(mid, ny - 58, cond, size=13.5, color=MUTED, anchor="middle")

# 退回：节点下方的折线
bot = ny + nh
lane_a, lane_b = bot + 56, bot + 120
f.arrow([(cx[1] - 30, bot + 2), (cx[1] - 30, lane_a), (cx[0] + 30, lane_a), (cx[0] + 30, bot + 6)],
        color=RED, width=2.2, dash="8 5")
f.text((cx[0] + cx[1]) / 2, lane_a + 26, "edit（用户）：改了目标地址，重新审核", size=14, color=RED, anchor="middle")
f.arrow([(cx[2], bot + 2), (cx[2], lane_b), (cx[1] + 30, lane_b), (cx[1] + 30, bot + 6)],
        color=RED, width=2.2, dash="8 5")
f.text((cx[1] + cx[2]) / 2, lane_b + 26, "renew（用户）：续期，回到生效", size=14, color=RED, anchor="middle")

# 底部两块说明
py, gap = lane_b + 64, 20
pw = (W - 80 - gap) / 2
notes = [("每条命令先过三道检查（domain/link.py，纯函数）", BLUE,
          ["角色有没有权发这条命令 → Forbidden", "当前状态允不允许 → InvalidTransition",
           "version 对不对 → VersionConflict；通过后 version + 1，写一条事件"]),
         ("为什么用状态机，不用几个布尔字段", RED,
          ["布尔字段会拼出没人设计过的组合，比如「已过期又待审核」",
           "合法的转移列在一张表里，别处想改状态只能调这个函数"])]
ph = max(f.panel_height(pw, body, size=14.5, bullet=True) for _, _, body in notes)
for k, (title, col, body) in enumerate(notes):
    f.panel(40 + k * (pw + gap), py, pw, title, body, h=ph, color=col, size=14.5, bullet=True)

print(f.render(py + ph + 36, OUT / "demo_state"))

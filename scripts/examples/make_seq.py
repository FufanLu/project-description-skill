"""示例：四泳道时序图（虚构的短链跳转链路）。

用法：python3 make_seq.py [输出目录]
产出 <输出目录>/demo_seq.svg 和 demo_seq.png。
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seqdiag import Seq, BLUE, GREEN, RED  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "project-description-demo")
DET, GUARD = ("确定性", GREEN), ("护栏", RED)

s = Seq(1600, [
    dict(key="u", title="浏览器", sub="用户点短链"),
    dict(key="r", title="redirect 服务", sub="service/redirect.py"),
    dict(key="c", title="Redis", sub="link:{code}", color=GREEN),
    dict(key="d", title="MySQL", sub="links 表", color=GREEN),
], "链路一：一次跳转（虚构示例）", "先查缓存，没命中再查库并回填 · 圆圈编号 = 消息顺序",
    legend=[DET, GUARD])  # 图例只放这张图用到的标签

s.msg("u", "r", "GET /abc123")
s.act(("r", "c"), "入口检查", [
    "短码必须是 6 位 62 进制字符，不合法直接 404，不查存储",
    "按 IP 限流，超限返回 429"], badges=[DET, GUARD])
s.msg("r", "c", "GET link:abc123")
s.msg("c", "r", "没命中", dashed=True)
s.loop_start("缓存没命中才走这一段", "r", "d")
s.msg("r", "d", "按短码查一行", "SELECT target, status, expire_at FROM links WHERE code = ?")
s.msg("d", "r", "一行记录", dashed=True)
s.msg("r", "c", "回填缓存", "SET link:abc123 … EX 600")
s.loop_end()
s.act(("r", "d"), "状态闸门", [
    "status 不是 ACTIVE，或者已过 expire_at → 410，不跳转",
    "点击事件放进内存队列，由 stats 批量落库，不拖慢这次跳转"], kind="guard", badges=[GUARD])
s.msg("r", "u", "302 Location: <目标地址>", dashed=True)
s.act(("u", "d"), "为什么这样切", [
    "读多写少：大部分跳转只碰 Redis",
    "缓存设 600 s 过期兜底：改了目标地址时删缓存失败，最多读 10 分钟旧值"],
    kind="why", badges=[("为什么", BLUE)])

print(s.render(OUT / "demo_seq"))

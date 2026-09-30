"""自测：用 examples/ 把整条链路跑一遍，产物放临时目录，不写进 skill 目录。

画图 → 截 PNG → 拷配图 → 示例 md → 侧栏 HTML → PDF → 校验整套产物 → 校验讲义骨架 → 仓库全貌脚本。
用法：python3 selftest.py [--out 目录]
全部通过时退出码为 0。换了机器、改了脚本，先跑一遍。
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
EX = HERE / "examples"
NAME = "示例项目讲义"
FIGS = [("demo_arch", "系统结构图"), ("demo_state", "短链生命周期"), ("demo_seq", "链路一_一次跳转")]


def run(args, label, quiet=False):
    print(f"\n==> {label}", flush=True)
    r = subprocess.run([sys.executable, *map(str, args)], stdout=subprocess.DEVNULL if quiet else None)
    if r.returncode:
        sys.exit(f"\n自测失败：{label}")


def main():
    ap = argparse.ArgumentParser(description="整条链路自测")
    ap.add_argument("--out", help="产物目录（默认新建临时目录）")
    a = ap.parse_args()
    out = Path(a.out).expanduser().resolve() if a.out else Path(tempfile.mkdtemp(prefix="guide-selftest-"))
    if out == SKILL or SKILL in out.parents:
        sys.exit("产物别放进 skill 目录，换一个 --out")
    img, figs, md_dir = out / "img", out / "配图", out / "md"
    for d in (img, figs, md_dir, out / "PDF版"):
        d.mkdir(parents=True, exist_ok=True)

    for script in ("make_arch.py", "make_state.py", "make_seq.py"):
        run([EX / script, img], f"画图：{script}")
    for stem, cn in FIGS:
        for ext in (".png", ".svg"):
            shutil.copy(img / f"{stem}{ext}", figs / f"示例项目_{cn}{ext}")
    md = md_dir / f"{NAME}.md"
    shutil.copy(EX / "sample_guide.md", md)
    run([HERE / "md2html_sidebar.py", md, out / f"{NAME}.html"], "生成侧栏 HTML")
    run([HERE / "md2pdf.py", md, out / "PDF版" / f"{NAME}.pdf"], "生成 PDF")
    run([HERE / "check_guide.py", out, NAME, "--shots", out / "_shots"], "校验整套产物")
    run([HERE / "check_guide.py", "--md", SKILL / "templates" / "guide-skeleton.md", "--no-images"], "校验讲义骨架（骨架里的 {…} 占位是故意留的，那条 WARN 正常）")
    run([HERE / "repo_facts.py", SKILL], "仓库全貌脚本（对 skill 目录自己跑）", quiet=True)

    print(f"\n自测通过。产物在：{out}\n先双击看：{out / (NAME + '.html')}")


if __name__ == "__main__":
    main()

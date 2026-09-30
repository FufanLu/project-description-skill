"""SVG 转 2 倍 PNG（无头 Chrome 截图）。

用法：python3 svg2png.py a.svg [b.svg ...] [--scale 2]
PNG 写在 SVG 旁边、同名。尺寸从 SVG 根节点的 width / height 读。
截出来是全白就加大 virtual-time-budget 重试一次，还白就报错。
"""
import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chrome  # noqa: E402


def svg_size(svg):
    m = re.search(r"<svg\b[^>]*>", svg)
    head = m.group(0) if m else ""
    w = re.search(r'\bwidth="(\d+(?:\.\d+)?)', head)
    h = re.search(r'\bheight="(\d+(?:\.\d+)?)', head)
    if not (w and h):
        raise ValueError("SVG 根节点上要写明 width 和 height（纯数字）")
    return round(float(w.group(1))), round(float(h.group(1)))


def is_blank(png):
    from PIL import Image
    with Image.open(png) as im:
        lo, _ = im.convert("L").getextrema()
    return lo > 245


def svg_to_png(svg_path, png_path=None, scale=2):
    svg_path = Path(svg_path).resolve()
    png_path = Path(png_path) if png_path else svg_path.with_suffix(".png")
    svg = svg_path.read_text(encoding="utf-8")
    svg = re.sub(r"^\s*<\?xml[^>]*\?>", "", svg)
    W, H = svg_size(svg)
    with tempfile.TemporaryDirectory(prefix="guide-svg-") as tmp:
        page, shot = Path(tmp) / "page.html", Path(tmp) / "shot.png"
        page.write_text('<!doctype html><html><head><meta charset="utf-8"><style>'
                        'html,body{margin:0;padding:0;background:#fff;overflow:hidden}svg{display:block}'
                        f'</style></head><body>{svg}</body></html>', encoding="utf-8")
        for budget in (3000, 8000):
            if chrome.screenshot(chrome.file_url(page), shot, W, H, scale=scale, budget=budget) and not is_blank(shot):
                break
        else:
            raise RuntimeError(f"截图失败或是白屏：{svg_path}")
        png_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(shot), str(png_path))
    from PIL import Image
    with Image.open(png_path) as im:
        if im.size != (W * scale, H * scale):
            print(f"  注意：{png_path.name} 实际 {im.size[0]}x{im.size[1]}，应为 {W * scale}x{H * scale}", file=sys.stderr)
    print(f"ok {png_path}  ({W}x{H} @{scale}x)")
    return png_path


def main():
    ap = argparse.ArgumentParser(description="SVG 转 PNG（无头 Chrome）")
    ap.add_argument("svg", nargs="+")
    ap.add_argument("--scale", type=int, default=2)
    a = ap.parse_args()
    for s in a.svg:
        svg_to_png(s, scale=a.scale)


if __name__ == "__main__":
    main()

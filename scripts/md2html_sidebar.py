"""Markdown 讲义 → 单文件 HTML：左侧固定目录，滚动时高亮当前章节，窄屏收成「目录」按钮。

用法：python3 md2html_sidebar.py <讲义.md> <输出.html>
- md 里的「## 目录」块挪进左侧栏（没有目录块就用 ## / ### 标题生成）。
- 图片路径按输出位置重新算：md 在 md/ 里写 ../img/x.png，html 在根目录就变成 img/x.png。
- 点图片在新标签页打开原图。
"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mdcommon  # noqa: E402

CSS = """
:root{color-scheme:light;--side:290px;--ink:#1f2328;--muted:#59636e;--rule:#d1d9e0;--link:#0969da;--hi:#ddf4ff;--soft:#f6f8fa;
--blue:#1F4E79;--blue-soft:#eef4fa;--green:#2F6B4F;--green-soft:#eef6f1;--amber:#B7791F;--red:#A93226;--red-soft:#fbefed}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:#fff;color:var(--ink);font:16px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif}
aside{position:fixed;top:0;left:0;bottom:0;width:var(--side);overflow-y:auto;background:var(--soft);border-right:1px solid var(--rule);padding:18px 12px 40px;font-size:14px;line-height:1.45;z-index:10}
aside .doc-title{display:block;font-weight:700;font-size:15px;color:var(--ink);padding:4px 8px 12px;border-bottom:1px solid var(--rule);margin-bottom:10px}
aside a{display:block;color:var(--ink);text-decoration:none;padding:5px 8px;border-radius:6px}
aside a.l1{font-weight:600;margin-top:6px}
aside a.l2{padding-left:22px;color:var(--muted);font-size:13.5px}
aside a.l3{padding-left:36px;color:var(--muted);font-size:13px}
aside a:hover{background:#eaeef2}
aside a.on{background:var(--hi);color:var(--link)}
aside a:focus-visible,#toggle:focus-visible{outline:2px solid var(--link);outline-offset:1px}
main{margin-left:var(--side)}
.wrap{max-width:920px;margin:0 auto;padding:32px 36px 90px}
h1{font-size:2em;border-bottom:1px solid var(--rule);padding-bottom:.3em;margin:.2em 0 .6em}
h2{font-size:1.5em;border-bottom:1px solid var(--rule);padding-bottom:.3em;margin:1.6em 0 .7em}
h3{font-size:1.25em;margin:1.4em 0 .6em}
h4{font-size:1.05em;margin:1.2em 0 .5em}
h1,h2,h3,h4{line-height:1.35;font-weight:600}
[id]{scroll-margin-top:14px}
main a{color:var(--link);text-decoration:none}main a:hover{text-decoration:underline}
p,ul,ol,table,blockquote,pre{margin:0 0 14px}
ul,ol{padding-left:2em}li+li{margin-top:.2em}
code{font:85% "SF Mono",Menlo,Consolas,monospace;background:#eff1f3;padding:.15em .4em;border-radius:6px}
pre{background:var(--soft);padding:14px 16px;border-radius:6px;overflow:auto;line-height:1.5}
pre code{background:none;padding:0;font-size:13px}
table{border-collapse:collapse;display:block;overflow:auto;max-width:100%}
th,td{border:1px solid var(--rule);padding:6px 12px;vertical-align:top}
th{background:var(--soft);font-weight:600;text-align:left}tr:nth-child(2n) td{background:#fafbfc}
blockquote{padding:8px 16px;color:#3d444d;border-left:4px solid var(--rule);background:#fafbfc;border-radius:0 6px 6px 0}
blockquote>:last-child{margin-bottom:0}
blockquote.why{border-color:var(--blue);background:var(--blue-soft)}blockquote.why>p:first-child>b{color:var(--blue)}
blockquote.say{border-color:var(--green);background:var(--green-soft)}blockquote.say>p:first-child>b{color:var(--green)}
blockquote.warn{border-color:var(--red);background:var(--red-soft)}blockquote.warn>p:first-child>b{color:var(--red)}
.tag{display:inline-block;font-size:12px;font-weight:700;line-height:1;padding:4px 8px;border-radius:10px;color:#fff;vertical-align:2px;white-space:nowrap}
.tag.det{background:var(--green)}.tag.agent{background:var(--amber)}.tag.guard{background:var(--red)}
p.fig{margin:18px 0 6px}p.fig a{display:block;cursor:zoom-in}
img{display:block;max-width:100%;height:auto;border:1px solid var(--rule);border-radius:6px}
p.caption{color:var(--muted);font-size:14px}
sub{font-size:12.5px;color:var(--muted)}
hr{border:0;border-top:1px solid var(--rule);margin:28px 0}
#toggle{display:none}
@media (max-width:900px){
  aside{transform:translateX(-100%);transition:transform .2s;box-shadow:2px 0 12px rgba(0,0,0,.12)}
  body.open aside{transform:none}
  main{margin-left:0}
  .wrap{padding:56px 16px 80px}
  #toggle{display:block;position:fixed;top:10px;left:10px;z-index:20;border:1px solid var(--rule);background:#fff;border-radius:8px;padding:6px 12px;font:14px -apple-system,"PingFang SC",sans-serif;color:var(--ink);cursor:pointer}
}
@media print{aside,#toggle{display:none}main{margin-left:0}.wrap{max-width:none;padding:0}}
"""

JS = """
(function(){
  var links = Array.prototype.slice.call(document.querySelectorAll('aside a[href^="#"]:not(.doc-title)'));
  var targets = links.map(function(a){ return document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1))); });
  var side = document.querySelector('aside'), btn = document.getElementById('toggle');
  var current = -1, queued = false;
  function update(){
    queued = false;
    var y = window.scrollY + 24, idx = 0;
    for (var i = 0; i < targets.length; i++) { if (targets[i] && targets[i].getBoundingClientRect().top + window.scrollY <= y) idx = i; }
    if (idx === current) return;
    current = idx;
    links.forEach(function(a, i){ a.classList.toggle('on', i === idx); });
    var a = links[idx];
    if (a) { var top = a.offsetTop, h = side.clientHeight;
      if (top < side.scrollTop + 60 || top > side.scrollTop + h - 80) side.scrollTop = top - h / 3; }
  }
  function schedule(){ if (!queued) { queued = true; requestAnimationFrame(update); } }
  window.addEventListener('scroll', schedule, {passive: true});
  window.addEventListener('resize', schedule);
  update();
  function setOpen(open){ document.body.classList.toggle('open', open); btn.setAttribute('aria-expanded', open ? 'true' : 'false'); }
  btn.addEventListener('click', function(){ setOpen(!document.body.classList.contains('open')); });
  document.querySelector('main').addEventListener('click', function(){ setOpen(false); });
  links.forEach(function(a){ a.addEventListener('click', function(){ setOpen(false); }); });
})();
"""


def link_images(h):
    def fix(m):
        src = re.search(r'src="([^"]+)"', m.group(1)).group(1)
        return f'<p class="fig"><a href="{src}" target="_blank" rel="noopener" title="在新标签页打开原图">{m.group(1)}</a></p>'
    return re.sub(r"<p>(<img\b[^>]*>)</p>", fix, h)


def build(md_path, out_path):
    md_path, out_path = Path(md_path), Path(out_path)
    d = mdcommon.build(md_path)
    parts = []
    for part in (d["head"], d["body"]):
        parts.append(link_images(mdcommon.rewrite_src(part, md_path.parent, out_path.parent)))
    side = [f'<a class="doc-title" href="#top">{html.escape(d["title"])}</a>']
    for level, label, aid in d["entries"]:
        side.append(f'<a class="l{level}" href="#{html.escape(aid)}">{html.escape(label)}</a>')
    page = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(d["title"])}</title><style>{CSS}</style></head><body>'
            '<button id="toggle" type="button" aria-controls="toc" aria-expanded="false">目录</button>'
            f'<aside id="toc" aria-label="目录">{"".join(side)}</aside>'
            f'<main><div class="wrap" id="top">{parts[0]}{parts[1]}</div></main>'
            f'<script>{JS}</script></body></html>')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    missing = [s for s in mdcommon.image_srcs(page)
               if (p := mdcommon.local_path(s, out_path.parent)) is not None and not p.exists()]
    for s in missing:
        print(f"  注意：图片不存在 {s}", file=sys.stderr)
    return out_path, len(d["entries"])


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    out, n = build(sys.argv[1], sys.argv[2])
    print(f"wrote {out}  侧栏 {n} 条")


if __name__ == "__main__":
    main()

# 踩坑记录

出了怪问题先看这里。新踩到的坑补在对应小节。

## 画图

- **SVG 会合并连续空格。** 树形图、靠空格对齐的文字会挤在一起。连续空格要换成不换行空格 ` `。`svgbase.svg_text()` 已经自动处理。
- **时序图重复编号。** `msg()` 自动画圆圈编号，消息文字里再写 ①② 就重复了。只用自动编号。
- **说明挤成一列。** act 框只跨一条泳道时，长句被切成很多短行。长说明放 act 框，并让它跨两三条以上泳道。
- **标点落单。** 句号、右括号单独落在行首。`svgbase.wrap()` 做了避头尾；手动断行时注意。
- **图例和图对不上。** 图例只放这张图用到的标签（`Seq(..., legend=[...])`）。
- **图里的数字没有出处。** 找不到出处的数字不画进图。

## 无头 Chrome

- **中文路径加 `#锚点` 打不开。** 带中文文件名、又带 `#锚点` 的 file URL，不做百分号编码就白屏。用 `Path.as_uri()` 或 `urllib.parse.quote`；`chrome.file_url()` 已经处理。
- **滚动后截图是白的。** 带 `#锚点` 打开、页面真的滚动了，截出来是一张白图；页面有 `scroll-behavior:smooth` 时干脆不滚。要截中间某一屏，别靠滚动：`check_guide.py` 用一份临时副本（`<base>` 指回原目录）加 `transform` 把正文往上挪。
- **偶尔白屏、进程挂住。** 加 `--virtual-time-budget`；截图或打印完按 profile 路径 `pkill`，否则进程一直挂着。`chrome.py` 每次用临时 profile、跑完清理，`svg2png.py` 截到全白会加大预算重试一次。
- **窗口最窄 500px。** `--window-size=390,…` 实际按 500 宽排版，截出来右边被裁。看窄屏就用 500 宽，已经能触发 ≤ 900px 的窄屏样式。
- **视口比窗口矮 87px。** 新版无头模式下 `innerHeight` = 窗口高 − 87。固定尺寸的 SVG 截图不受影响；页面用 `100vh` 布局时会差一截。
- **macOS 没有 `timeout` 命令。** 别写 `timeout 60 chrome …`。超时用 Python 的 subprocess 加轮询（`chrome.py` 就是这么做的）。

## Markdown 和 PDF

- **中文加粗遇到标点失效。** 以标点开头或结尾的加粗（`**「承诺」**`、`**必须先迁移。**`）紧挨着中文时不生效，改用 `<b>`。`check_guide.py` 会报出来。
- **单独一行的 `<a id>` 会被包进 `<p>`。** 生成 HTML 时脚本把 id 挪到下一个标题上，不会多出空段落，PDF 里的链接也落在标题上。
- **表格错列。** 单元格里的 `|` 要写成 `\|`。
- **PDF 里代码被截断。** 打印样式用了 `pre-wrap` 自动换行，但别在代码块里写特别长的行。
- **书签丢空格。** 手写 HTML 时用 `<span>` 包标题编号，书签会变成「0怎么读」。标题写纯文字「0 怎么读」。
- **目录太长挤出第一页。** 超过 70 条时 `md2pdf.py` 只列到放得下的层级；也可以用 `--toc-depth 2` 手动指定。

## 环境

- **本机没有 LibreOffice。** 不要依赖 soffice，也不做 Word。
- **cloc 不一定装了。** `repo_facts.py` 自己数行数；装了 cloc 可以复核。
- **依赖。** Python 3.9+，`pip install markdown-it-py pymupdf pillow`，外加 Google Chrome。换了机器先跑 `scripts/selftest.py`。
- **Chrome 不在默认位置。** 设环境变量 `CHROME=<可执行文件路径>`；Linux 上会自动找 `google-chrome` / `chromium`。

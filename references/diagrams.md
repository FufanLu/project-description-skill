# 画图

每张图都要能追到代码。用 Python 生成 SVG，再用无头 Chrome 截成 2 倍 PNG。

## 要画哪些图

| 图 | 用什么画 | 回答什么问题 |
|---|---|---|
| 系统结构图 | `figlib.Fig`，分层框图 | 有哪些模块、分几层、谁调谁 |
| 核心模型图 | `figlib.Fig`，状态机或数据模型 | 有哪些状态、谁能触发哪个转移 |
| 链路时序图（每条链路一张） | `seqdiag.Seq` | 一次请求经过谁、按什么顺序、哪里会失败 |
| 进程与磁盘图（可选） | `figlib.Fig`，树形 | 在机器上是哪些进程、哪些目录 |

示例都在 `scripts/examples/`：`make_arch.py`（三层结构图）、`make_state.py`（状态机）、`make_seq.py`（四泳道时序图）。先跑一遍看效果：

```bash
python3 "$SKILL/scripts/examples/make_seq.py" <临时目录>   # 产出 demo_seq.svg 和 .png；不给目录就放系统临时目录
```

## 原则

- 每个方框是仓库里真实存在的模块、文件、表或进程。
- 每个数字都有出处。找不到出处就不画。
- 标题说清这张图回答什么问题；副标题一句话说怎么看（颜色、线型、编号的意思）。
- 一张图只回答一个问题。塞不下就拆。

## 颜色约定

和讲义里的标签一致：

| 颜色 | 常量 | 含义 |
|---|---|---|
| 蓝 | `BLUE` | 主流程、请求 |
| 绿 | `GREEN` | 确定性代码、存储 |
| 橙 | `AMBER` | Agent / LLM |
| 红 | `RED` | 护栏、人在回路、失败 |
| 灰 | `GRAY` | 占位、还没实现（配虚线框） |

实线 = 请求或前进；虚线 = 返回、退回或可选。浅底色和浅边框在 `SOFT[颜色]`、`EDGE[颜色]` 里。

## 工作方式

1. 在 scratchpad 建一个 `make_figs.py`：

   ```python
   import os, sys
   sys.path.insert(0, os.path.expanduser("~/.claude/skills/project-description/scripts"))
   from figlib import Fig, BLUE, GREEN, AMBER, RED, GRAY, MUTED, SOFT, EDGE, MONO
   from seqdiag import Seq

   OUT = os.path.expanduser("<输出根目录>/img")
   ```

2. 一张图一段代码，最后 `render(...)`，同时写出 SVG 和 2 倍 PNG。文件名用 ASCII，带项目简称前缀：`xx_arch`、`xx_model`、`xx_seq1`。
3. 用 Read 看 PNG，改坐标，再跑。
4. 定稿后拷到 配图/，用中文名：

   ```bash
   cp "$ROOT/img/xx_arch.png" "$ROOT/配图/{项目名}_系统结构图.png"
   cp "$ROOT/img/xx_arch.svg" "$ROOT/配图/{项目名}_系统结构图.svg"
   ```

只想把现成的 SVG 转 PNG：`python3 "$SKILL/scripts/svg2png.py" a.svg b.svg`。

## API 速查

### Fig（scripts/figlib.py）

| 方法 | 用途 |
|---|---|
| `Fig(W, title, subtitle)` | 画布。标题在 y=52，副标题在 y=86，正文从 y≈110 开始 |
| `rect(x, y, w, h, fill, stroke, dash=)` | 方框 |
| `text(x, y, s, size, color, weight, anchor, family)` | 文字；连续空格自动保留 |
| `lines(x, y, s, max_px, size, bullet=)` | 自动换行的一段字，返回下一行的 y |
| `panel(x, y, w, title, body, h=, color=, dash=, bullet=)` | 带标题的方框；不给 h 就按内容算高度 |
| `panel_height(w, body, size, bullet)` | 先算高度，让一排面板等高 |
| `band(x, y, w, h, label)` | 左侧的层名色带，label 里用 `\n` 换行 |
| `tag(x_right, y, s, fill)` | 右对齐的实心小标签 |
| `chip(x, y, s)` | 圆角小块，列表名、模块名 |
| `legend(x, y, items)` | 一排图例，`items = [(文字, 颜色)]` |
| `arrow(pts, color, dash=)` | 折线箭头 |
| `path(d, color, dash=)` | 任意路径，弧线用 `M x0,y0 Q cx,cy x1,y1` |
| `render(H, stem)` | 写 `<stem>.svg` 和 `<stem>.png`；stem 可以带目录 |

### Seq（scripts/seqdiag.py）

| 方法 | 用途 |
|---|---|
| `Seq(W, lanes, title, subtitle, legend=)` | `lanes = [dict(key=, title=, sub=, color=)]`；legend 只放这张图用到的标签，`None` 不画 |
| `msg(a, b, label, sub=, dashed=, color=)` | 一条消息，自动编号；`a == b` 画成自调用 |
| `act(over, title, lines, kind=, badges=)` | 说明框。`over` 是一条泳道或 `(起, 止)`；`kind` 是 plain / why / guard / agent / store；`lines` 里以 `~` 开头的不加圆点 |
| `loop_start(label, a, b)` / `loop_end()` | 循环或分组框，可以嵌套 |
| `phase(label)` | 横跨全图的阶段分隔线 |
| `gap(h)` | 空一段 |
| `render(stem)` | 写 SVG 和 PNG |

## 布局经验

- 画布宽 1600–1800。
- 时序图 4–6 条泳道。角色太多就合并次要的。
- 消息只用自动编号。文字里别再写 ①②，会重复编号。
- 长说明放 act 框，不放消息的 sub；act 框至少跨两三条泳道，不然会挤成一列。
- 一张时序图 10–15 条消息。再长就拆成两张，或者用 `phase()` 分段。
- 「为什么这样切」放在时序图最后一个 `kind="why"` 的框里，跨满全部泳道。
- 结构图每层 3–6 个框。同一排用 `panel_height()` 算出最高的，让它们等高。
- 状态机：状态排一行；前进画在上方（弧线），退回画在下方（虚线折线）；箭头颜色表示谁能触发。
- 树形图（目录、进程树）用等宽字体 `MONO`，靠空格对齐。

## 自检

看 PNG 时查：

- 文字有没有溢出方框、互相重叠。
- 有没有标点单独落在行首。
- 编号连不连续、有没有重复。
- 颜色和图例是否一致；图例里有没有这张图没用到的标签。
- 图里的每个数字能不能在 facts.md 里找到。

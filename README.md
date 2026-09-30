# project-description

一个 [Claude Code](https://claude.com/claude-code) 的 skill：给一个本地代码仓库做一份面向面试的项目讲义。

对 Claude 说「给 ~/code/某项目 做一份面试讲义」，它会：

1. **先看代码**：统计语言与行数、模块、git 历史、测试和部署痕迹。每个数字、常量、表名、文件名都到代码里核实；核不到的写明，推断标成「我的理解」。
2. **画图**：系统结构图、核心模型图（状态机等）、每条关键链路一张时序图。每张图都能追到代码。
3. **写讲义**：项目介绍、底层概念、核心模型（先用生活例子讲清概念）、每条链路一章；每个机制后面附「为什么这样设计」。
4. **面试准备**：角色说明（事实不清就列出来请你确认）、2–3 分钟讲稿、6 组挖坑提问、雷区清单。
5. **输出并校验**：带左侧目录的本地 HTML、Markdown 原文、带书签的 PDF；交付前自动检查锚点、图片、加粗、空白页和书签，并截图看版式。

## 产出长什么样

```
<输出根目录>/
├── <项目名>讲义.html      ← 双击打开：左侧固定目录，滚动高亮当前章节，窄屏收成「目录」按钮
├── PDF版/<项目名>讲义.pdf ← 第一页是可点目录，带 PDF 书签
├── 配图/                  ← 单独的高清图（中文文件名）
├── md/<项目名>讲义.md     ← Markdown 原文，GitHub、VS Code、Typora 里目录都能跳
└── img/                   ← html 用的图
```

讲义的章节：0 怎么读 → 1 项目介绍 → 2 核心模型 → 3…N 关键链路 → 为什么这样设计（W1…Wn）→ 面试准备 → 附录：代码索引。骨架见 `templates/guide-skeleton.md`，示例见 `scripts/examples/sample_guide.md`。

## 安装

```bash
git clone https://github.com/FufanLu/project-description-skill.git ~/.claude/skills/project-description
```

## 依赖

- Python 3.9+
- `pip install markdown-it-py pymupdf pillow`
- Google Chrome（用无头模式截图、打印 PDF）。不在默认位置时，设环境变量 `CHROME=<可执行文件路径>`。

装好后跑一次自测，把整条链路（画图 → PNG → HTML → PDF → 校验）走一遍，产物放在系统临时目录：

```bash
python3 ~/.claude/skills/project-description/scripts/selftest.py
```

## 用法

在 Claude Code 里说：

> 给 ~/code/my-project 做一份面试讲义，放到 ~/Documents/面试讲义/

有简历上这个项目的原话，一起贴上，挖坑题和雷区表会照着原话出。

## 目录

```
SKILL.md                     流程和质量清单
references/
  structure.md               讲义结构与写法
  why-questions.md           「为什么这样设计」怎么写
  interview-prep.md          角色、讲稿、挖坑、雷区
  diagrams.md                画图说明与 API
  output-and-checks.md       输出格式、Markdown 约定、校验
  pitfalls.md                踩坑记录
templates/guide-skeleton.md  讲义骨架
scripts/
  repo_facts.py              摸清仓库全貌（只读）
  figlib.py / seqdiag.py     框图 / 时序图（生成 SVG）
  svg2png.py                 SVG 转 2 倍 PNG
  md2html_sidebar.py         md 转左侧目录的 HTML
  md2pdf.py                  md 转带书签的 PDF
  check_guide.py             交付前校验 + 截图
  selftest.py                整条链路自测
  examples/                  三张示例图 + 示例讲义（虚构项目）
```

在 macOS 上测过；Linux 上 Chrome 能找到就能用，没测过。

## 致谢

面试准备部分（讲稿、6 组挖坑提问、雷区清单）参考了 [interview-experience-breakdown](https://github.com/00menghui00/interview-experience-breakdown)（MIT）。

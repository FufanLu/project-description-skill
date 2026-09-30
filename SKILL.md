---
name: project-description
description: 给本地代码仓库做一份面向面试的项目讲义。先看代码、核实每个事实，再画系统结构图、核心模型图和链路时序图，写「为什么这样设计」追问、讲稿、挖坑题和雷区表；输出左侧带目录的本地 HTML、Markdown 原文和带书签的 PDF。用户给出仓库路径，并说「给这个项目做讲义」「面试讲义」「项目拆解」「把项目讲清楚」「帮我准备这个项目的面试」这类话时使用。
---

# 项目面试讲义

用户给一个本地仓库路径，要一份拿去面试用的讲义。讲义回答三件事：这个项目是什么；关键链路怎么走；每个设计为什么这样做。最后是面试准备。

下文的 `$SKILL` 指这个 skill 的目录（默认 `~/.claude/skills/project-description`）。shell 变量不会跨 Bash 调用保留，每条命令前都带上 `SKILL=…`，或者直接写完整路径。

## 硬规矩

1. **代码是事实的来源。** README、设计文档只用来定位。数字、常量、表名、阈值、文件名，都要在代码里找到。
2. **核不到就写明。** 文档里有、代码里没有的，写「文档里有、代码里没找到」。推断写「我的理解」。不编。
3. **图能追到代码。** 每个方框对应真实的模块或文件，每个数字有出处。找不到出处的数字不进图。
4. **角色按事实写。** 仓库看不出来的（谁写的、团队几个人、有没有上线），列出来请用户确认，不替用户编经历。
5. **只读仓库。** 不改代码、不提交、不装依赖。要跑测试或启动服务，先问用户。
6. **不做 Word。** 主格式是左侧带目录的本地 HTML，另附 Markdown 原文和带书签的 PDF。
7. **校验通过才交付。** `check_guide.py` 0 个 ERROR，截图也看过。

## 开始前

一次问清，已经给了的不再问：

- **仓库路径**（必需）。
- **输出根目录**。没给就问。示例：`~/Documents/面试讲义/`。多个项目可以共用一个根目录，文件名用项目名区分。
- **简历上写这个项目的原话**（可选）。有了，挖坑题和雷区表就照着原话出。
- **面向什么岗位**（可选），决定侧重点。Agent 岗多讲模型怎么接入、上下文、护栏；后端岗多讲一致性、并发、存储。

## 流程

### 第 1 步：摸清全貌（先别写）

```bash
SKILL=~/.claude/skills/project-description
python3 "$SKILL/scripts/repo_facts.py" <仓库路径>
```

它列出：语言与行数、顶层目录、构建文件与模块、入口候选、git 历史（提交数、作者、时间跨度、Co-Authored-By、提交说明里记的测试结果）、测试用例数和跑过的痕迹、文档与 ADR、部署痕迹、注释里的理由线索。

然后自己补：

- README、docs/ 只扫目录和标题，知道该去哪看代码就够了。
- 模块之间谁依赖谁：看构建文件里的依赖和 import。
- 测试数以测试框架自己的统计为准。只收集不运行的命令（比如 `pytest --collect-only -q`）可以直接跑；真跑测试先问用户。
- 部署：Dockerfile、CI、云配置、线上地址、监控。没有就写「没找到部署痕迹」。

把事实记进 scratchpad（没有就用系统临时目录）里的 `facts.md`，一条一行：数字 + 出处（`文件:行号` 或命令）。后面写讲义，数字只从这里取。

### 第 2 步：找核心模型、关键链路和理由

- **核心模型**：状态机（枚举 + 转移函数）、数据模型（表结构、迁移文件）或事件契约（DTO、schema）。挑最能代表这个项目的一个。
- **关键链路**：从入口读起（路由、CLI 命令、消息消费者、定时任务），挑 3–5 条：一个请求或一次任务从进来到结束。每条记下经过的文件和函数。
- **理由**：代码注释 > ADR、设计文档 > 提交说明、PR 描述 > 测试名 > 我的理解。每条理由记出处。repo_facts.py 最后一节列了理由线索最多的文件，先读那些。
- **标签**：每个机制标一类：【确定性】纯代码逻辑；【Agent】或【LLM】调模型的地方；【护栏】会拒绝、退回、暂停、要人介入的地方。项目里没有模型调用，就只用确定性和护栏，或者换成项目自己的分类，在第 0 章说明。

### 第 3 步：定大纲

按 `references/structure.md` 的顺序排章节，一条关键链路一章。大纲不用等用户确认，直接写；拿不准的事实先记下，交付时一起问。

### 第 4 步：画图

在 scratchpad 写一个 `make_figs.py`，用 `$SKILL/scripts/figlib.py`（框图）和 `seqdiag.py`（时序图）。至少三类：系统结构图、核心模型图、每条链路一张时序图。示例在 `scripts/examples/`，API 和布局经验见 `references/diagrams.md`。

- 图输出到 `<输出根目录>/img/<项目简称>_<图名>`，同时得到 SVG 和 2 倍 PNG。
- 再拷一份到 `<输出根目录>/配图/<项目名>_<中文图名>.png`，SVG 一起拷。
- 每张图画完用 Read 看 PNG：字有没有溢出、重叠，编号有没有重复，标点有没有落单。

### 第 5 步：写 Markdown

把 `$SKILL/templates/guide-skeleton.md` 复制成 `<输出根目录>/md/<项目名>讲义.md`，按项目填，`{…}` 占位全部换掉。

- 每章怎么写：`references/structure.md`
- 「为什么」追问：`references/why-questions.md`
- 角色、讲稿、挖坑、雷区：`references/interview-prep.md`
- 锚点、目录块、引用块、加粗的写法：`references/output-and-checks.md`

写的时候：

- 讲概念先用生活例子，再讲定义，再贴代码，再放图。
- 贴代码只贴 10–30 行真实代码，逐行加中文注释，写明文件路径。
- 每个机制后面跟一个「为什么」引用块，标题括号写 W 编号，和追问章一一对应。
- 句子短。一段一件事。先结论后理由。不用套话。

### 第 6 步：生成 HTML 和 PDF

```bash
SKILL=~/.claude/skills/project-description; ROOT=<输出根目录>; NAME=<项目名>讲义
python3 "$SKILL/scripts/md2html_sidebar.py" "$ROOT/md/$NAME.md" "$ROOT/$NAME.html"
python3 "$SKILL/scripts/md2pdf.py" "$ROOT/md/$NAME.md" "$ROOT/PDF版/$NAME.pdf"
```

### 第 7 步：校验

```bash
SKILL=~/.claude/skills/project-description; ROOT=<输出根目录>; NAME=<项目名>讲义
python3 "$SKILL/scripts/check_guide.py" "$ROOT" "$NAME" --numbers
```

- 修到 0 个 ERROR。WARN 逐条看，能修就修。
- `--numbers` 列出正文里所有带数字的行。逐行对照 facts.md，找不到出处的改掉或删掉。
- 用 Read 看它截的四张图（开头、窄屏、中段、后段）：侧栏、图、表格、引用块有没有错位。
- 出了怪问题先看 `references/pitfalls.md`。

### 第 8 步：交付

告诉用户：

1. 文件在哪；先双击 `<项目名>讲义.html`。PDF 在 PDF版/，高清图在 配图/，原文在 md/。
2. 哪些说法代码里核不到（逐条列）。
3. 哪些事实要用户确认：角色、时间线、有没有上线、简历里的说法。
4. 建议先改的简历措辞（来自雷区表）。

## 质量清单

交付前逐条过：

- [ ] 每个数字都在 facts.md 里有出处
- [ ] 推断都标了「我的理解」，核不到的都标了「文档里有、代码里没找到」
- [ ] 第 1 章有规模与来历表，有讲细的底层概念小节
- [ ] 核心模型先讲生活例子，再贴真实代码（带逐行注释和出处）
- [ ] 每条链路：一张时序图 + 分步说明 + 「为什么」引用块（带 W 编号）
- [ ] W 追问每题：能直接说出口的回答 + 出处
- [ ] 讲稿 500–650 字，第一人称、自然段，讲判断和取舍
- [ ] 挖坑 6 组，每题有「面试官想考察」和「回答注意」
- [ ] 雷区表三列：原话 → 怀疑 → 代码里的证据与策略
- [ ] 角色一节只写事实，不清楚的列出来请用户确认
- [ ] 附录有代码索引
- [ ] `check_guide.py` 0 个 ERROR，截图看过
- [ ] 没有 Word 文件

## 参考文件

| 文件 | 什么时候看 |
|---|---|
| `references/structure.md` | 定大纲、写每一章 |
| `references/why-questions.md` | 写「为什么」引用块和追问章 |
| `references/interview-prep.md` | 写角色、讲稿、挖坑题、雷区表 |
| `references/diagrams.md` | 画图 |
| `references/output-and-checks.md` | 目录结构、Markdown 约定、生成和校验 |
| `references/pitfalls.md` | 出了怪问题 |
| `templates/guide-skeleton.md` | 讲义骨架 |
| `scripts/selftest.py` | 换了机器或改了脚本，先跑一遍 |

面试准备部分参考了开源 skill interview-experience-breakdown（MIT），出处见 `references/interview-prep.md`。

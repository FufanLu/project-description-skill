"""摸清一个仓库的全貌：目录、语言与行数、模块、入口、git 历史、测试、文档、部署痕迹、理由线索。

用法：python3 repo_facts.py <仓库路径>
只读：只跑 git log / ls-files 这类不写仓库的命令，不跑测试、不装依赖。
输出是文字清单，每个数字都写了怎么数的。写进讲义前，关键数字再到代码里核一遍。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "vendor", "third_party", "dist", "build", "target", ".venv", "venv", "env",
             "__pycache__", ".next", ".nuxt", "out", "coverage", ".mypy_cache", ".pytest_cache", ".tox",
             ".gradle", ".idea", ".vscode", "Pods", "DerivedData", ".turbo", ".cache", "site-packages"}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "poetry.lock", "go.sum",
              "Pipfile.lock", "composer.lock", "Gemfile.lock", "uv.lock", "bun.lockb"}
LANG = {
    ".py": "Python", ".pyi": "Python", ".ipynb": "Jupyter",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".vue": "Vue", ".svelte": "Svelte",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala", ".groovy": "Groovy",
    ".go": "Go", ".rs": "Rust", ".c": "C", ".h": "C/C++ 头文件", ".cc": "C++", ".cpp": "C++", ".cxx": "C++",
    ".hpp": "C++ 头文件", ".cs": "C#", ".swift": "Swift", ".m": "Objective-C", ".mm": "Objective-C",
    ".rb": "Ruby", ".php": "PHP", ".dart": "Dart", ".lua": "Lua", ".r": "R", ".jl": "Julia",
    ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang", ".hs": "Haskell", ".clj": "Clojure", ".zig": "Zig",
    ".sol": "Solidity", ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".ps1": "PowerShell",
    ".sql": "SQL", ".proto": "Protobuf", ".graphql": "GraphQL", ".gql": "GraphQL",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".less": "Less", ".tf": "Terraform",
    ".md": "Markdown", ".mdx": "Markdown", ".rst": "reStructuredText",
    ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".json": "JSON", ".xml": "XML", ".ini": "INI",
}
NAMES = {"Dockerfile": "Dockerfile", "Makefile": "Makefile", "Justfile": "Justfile", "CMakeLists.txt": "CMake"}
DOC_CONF = {"Markdown", "reStructuredText", "YAML", "TOML", "JSON", "XML", "INI"}
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|src/test)/|(^|/)test_[^/]*\.py$|_test\.(py|go|rb)$|"
                       r"\.(test|spec)\.[jt]sx?$|Tests?\.(java|kt|swift|cs)$|_spec\.rb$")
TEST_CASE = {
    "Python": re.compile(r"^\s*(async\s+)?def\s+test\w*\s*\(", re.M),
    "JavaScript": re.compile(r"\b(it|test)(\.each\([^)]*\))?\s*\(\s*['\"`]"),
    "TypeScript": re.compile(r"\b(it|test)(\.each\([^)]*\))?\s*\(\s*['\"`]"),
    "Rust": re.compile(r"#\[\s*(tokio::|async_std::|actix_rt::)?test\b|#\[\s*rstest\b"),
    "Go": re.compile(r"^func\s+Test\w*\s*\(\s*\w+\s+\*testing\.T\s*\)", re.M),
    "Java": re.compile(r"@(Test|ParameterizedTest)\b"),
    "Kotlin": re.compile(r"@(Test|ParameterizedTest)\b"),
    "C#": re.compile(r"\[\s*(Fact|Theory|Test|TestMethod|TestCase)\b"),
    "Ruby": re.compile(r"^\s*(it|specify)\s+['\"]|^\s*def\s+test_", re.M),
    "PHP": re.compile(r"function\s+test\w+\s*\(|@test\b"),
    "Swift": re.compile(r"func\s+test\w*\s*\("),
}
WHY = re.compile(r"\b(because|why|instead|otherwise|so that|in order to|trade-?off|invariant|NOTE|HACK|FIXME|XXX|SAFETY)\b|"
                 r"因为|否则|为了|避免|不然|取舍|代价|注意|踩坑|权衡", re.I)
COMMENT_LINE = re.compile(r"^\s*(#|//|/\*|\*|--|;|<!--)")
MANIFESTS = ("Cargo.toml", "package.json", "pyproject.toml", "setup.py", "setup.cfg", "go.mod", "pom.xml",
             "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "CMakeLists.txt",
             "composer.json", "Gemfile", "mix.exs", "pubspec.yaml", "Package.swift", "deno.json")
DEPLOY = re.compile(r"(^|/)(Dockerfile[^/]*|[^/]*\.dockerfile|docker-compose[^/]*\.ya?ml|compose\.ya?ml|Procfile|fly\.toml|"
                    r"vercel\.json|netlify\.toml|render\.yaml|app\.yaml|serverless\.ya?ml|Chart\.yaml|kustomization\.ya?ml|"
                    r"[^/]*\.tf|\.gitlab-ci\.yml|Jenkinsfile|azure-pipelines\.yml|\.env\.example|\.env\.sample|"
                    r"(k8s|kubernetes|helm|deploy|deployment|infra)/[^/]+)$", re.I)
CI = re.compile(r"^(\.github/workflows/[^/]+\.ya?ml|\.gitlab-ci\.yml|Jenkinsfile|\.circleci/config\.yml|azure-pipelines\.yml|"
                r"\.travis\.yml|bitbucket-pipelines\.yml|\.buildkite/[^/]+)$")
ENTRY = re.compile(r"(^|/)(main\.(py|go|rs|ts|js|kt|java|c|cpp|swift)|__main__\.py|app\.(py|ts|js)|manage\.py|"
                   r"server\.(py|ts|js|go)|index\.(ts|js)|cli\.(py|ts|js)|wsgi\.py|asgi\.py|[A-Z]\w*Application\.(java|kt)|"
                   r"cmd/[^/]+/main\.go|bin/[^/]+)$")


def git(repo, *args):
    try:
        out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=120)
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def list_files(repo):
    """git 仓库用 ls-files（含未提交、不含被 ignore 的）；不是 git 仓库就遍历目录。"""
    out = git(repo, "ls-files", "-z", "-co", "--exclude-standard")
    if out:
        files = [f for f in out.split("\0") if f]
        untracked = set(f for f in git(repo, "ls-files", "-z", "-o", "--exclude-standard").split("\0") if f)
    else:
        files, untracked = [], set()
        for root, dirs, names in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for n in names:
                files.append(os.path.relpath(os.path.join(root, n), repo))
    keep = []
    for f in files:
        parts = f.split("/")
        if any(p in SKIP_DIRS for p in parts[:-1]) or parts[-1] in SKIP_FILES or f.endswith((".min.js", ".min.css", ".map")):
            continue
        keep.append(f)
    return keep, untracked


def lang_of(f):
    name = f.rsplit("/", 1)[-1]
    if name in NAMES:
        return NAMES[name]
    if name.startswith("Dockerfile"):
        return "Dockerfile"
    return LANG.get(os.path.splitext(name)[1].lower())


def read(path, limit=2_000_000):
    try:
        if path.stat().st_size > limit:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:4096]:
        return None
    return data.decode("utf-8", errors="replace")


def mask(url):
    return re.sub(r"(https?://)[^/@\s]+@", r"\1***@", url)


def fmt_n(n):
    return f"{n:,}"


def section(title):
    print(f"\n## {title}\n")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    repo = Path(sys.argv[1]).expanduser().resolve()
    if not repo.is_dir():
        sys.exit(f"不是目录：{repo}")
    files, untracked = list_files(repo)
    is_git = bool(git(repo, "rev-parse", "--git-dir"))

    print(f"# 仓库全貌：{repo.name}\n")
    print(f"- 路径：{repo}")
    if is_git:
        head = git(repo, "log", "-1", "--format=%h %ad", "--date=short").strip()
        branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        remotes = sorted(set(mask(ln.split()[1]) for ln in git(repo, "remote", "-v").splitlines() if ln.split()))
        print(f"- 分支：{branch} · HEAD：{head or '（还没有提交）'}")
        print(f"- 远程：{'、'.join(remotes) if remotes else '没有'}")
    else:
        print("- 不是 git 仓库")
    how = f"git ls-files，含 {len(untracked)} 个未提交文件" if is_git else "遍历目录"
    print(f"- 统计范围：{fmt_n(len(files))} 个文件（{how}；跳过 node_modules、target、dist、lock 文件等）")

    # ------------------------------------------------------------ 语言与行数
    by_lang = defaultdict(lambda: [0, 0, 0, 0])  # 文件数、总行数、非空行、其中测试代码行
    top_dirs = defaultdict(lambda: [0, 0])
    why_hits, test_cases, test_files = Counter(), Counter(), Counter()
    manifests, deploy, ci, entries, docs, adrs = [], [], [], [], [], []
    for f in files:
        p = repo / f
        lang = lang_of(f)
        name = f.rsplit("/", 1)[-1]
        if name in MANIFESTS:
            manifests.append(f)
        if DEPLOY.search(f):
            deploy.append(f)
        if CI.match(f):
            ci.append(f)
        if ENTRY.search(f) and f.count("/") <= 3:
            entries.append(f)
        if lang in ("Markdown", "reStructuredText"):
            docs.append(f)
            if re.search(r"(^|/)(adr|adrs|decisions?|rfcs?)/", f, re.I) or re.match(r"(?i)adr[-_ ]?\d+", name):
                adrs.append(f)
        if lang is None:
            continue
        text = read(p)
        if text is None:
            continue
        lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        nonblank = sum(1 for ln in text.splitlines() if ln.strip())
        is_test = bool(TEST_PATH.search(f))
        st = by_lang[lang]
        st[0] += 1
        st[1] += lines
        st[2] += nonblank
        if is_test:
            st[3] += lines
        top = f.split("/", 1)[0] if "/" in f else "（根目录）"
        top_dirs[top][0] += 1
        top_dirs[top][1] += lines
        if lang not in DOC_CONF:
            rx = TEST_CASE.get(lang)
            if rx and (is_test or lang == "Rust"):
                n = len(rx.findall(text))
                if n:
                    test_cases[lang] += n
                    test_files[lang] += 1
            hits = sum(1 for ln in text.splitlines() if COMMENT_LINE.match(ln) and WHY.search(ln))
            if hits:
                why_hits[f] = hits

    section("语言与行数（行数含空行和注释）")
    code = sorted(((k, v) for k, v in by_lang.items() if k not in DOC_CONF), key=lambda kv: -kv[1][1])
    other = sorted(((k, v) for k, v in by_lang.items() if k in DOC_CONF), key=lambda kv: -kv[1][1])
    print("| 语言 | 文件 | 总行数 | 非空行 | 其中测试代码 |")
    print("|---|---|---|---|---|")
    for k, (nf, nl, nb, nt) in code:
        print(f"| {k} | {fmt_n(nf)} | {fmt_n(nl)} | {fmt_n(nb)} | {fmt_n(nt)} |")
    print(f"\n代码合计：{fmt_n(sum(v[0] for _, v in code))} 个文件，{fmt_n(sum(v[1] for _, v in code))} 行。")
    if other:
        print("文档与配置：" + "；".join(f"{k} {fmt_n(v[0])} 个文件 / {fmt_n(v[1])} 行" for k, v in other))
    if shutil.which("cloc"):
        print("本机装了 cloc，可以复核：cloc --vcs=git " + str(repo))

    section("顶层目录（文件数 · 行数）")
    for d, (nf, nl) in sorted(top_dirs.items(), key=lambda kv: -kv[1][1])[:20]:
        print(f"- {d}：{fmt_n(nf)} 个文件 · {fmt_n(nl)} 行")

    section("模块与构建文件")
    for m in sorted(manifests, key=lambda s: (s.count("/"), s))[:40]:
        text = read(repo / m) or ""
        info = ""
        if m.endswith("Cargo.toml"):
            mem = re.search(r"\[workspace\][^\[]*?members\s*=\s*\[(.*?)\]", text, re.S)
            name = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, re.M)
            members = re.findall(r'"([^"]+)"', mem.group(1)) if mem else []
            info = f"workspace，members：{', '.join(members)}" if mem else (name.group(1) if name else "")
        elif m.endswith("package.json"):
            try:
                pj = json.loads(text)
                info = pj.get("name", "")
                ws = pj.get("workspaces")
                if ws:
                    info += f" · workspaces：{ws if isinstance(ws, list) else ws.get('packages')}"
                scripts = list((pj.get("scripts") or {}).keys())[:8]
                if scripts:
                    info += f" · scripts：{', '.join(scripts)}"
            except ValueError:
                pass
        elif m.endswith("pyproject.toml"):
            name = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, re.M)
            info = name.group(1) if name else ""
        elif m.endswith("go.mod"):
            mod = re.search(r"^module\s+(\S+)", text, re.M)
            info = mod.group(1) if mod else ""
        elif m.endswith("pom.xml"):
            mods = re.findall(r"<module>([^<]+)</module>", text)
            info = f"modules：{', '.join(mods)}" if mods else ""
        elif "settings.gradle" in m:
            info = "include：" + ", ".join(re.findall(r"""include\s*\(?\s*['"]([^'"]+)""", text))
        print(f"- {m}" + (f"（{info}）" if info else ""))
    if not manifests:
        print("- 没找到常见的构建文件")

    section("入口候选（从这里开始读链路）")
    for e in sorted(entries)[:30]:
        print(f"- {e}")
    if not entries:
        print("- 没找到常见的入口文件名，从构建文件里的 scripts / bin / main 字段找")

    # ------------------------------------------------------------ git
    section("git 历史")
    if is_git and git(repo, "rev-parse", "--verify", "HEAD").strip():
        n = git(repo, "rev-list", "--count", "HEAD").strip()
        merges = git(repo, "rev-list", "--count", "--merges", "HEAD").strip()
        dates = git(repo, "log", "--format=%ad", "--date=short").split()
        authors = [f"{m.group(2)}（{m.group(1)} 个）" for m in re.finditer(r"^\s*(\d+)\t(.+)$", git(repo, "shortlog", "-sn", "HEAD"), re.M)]
        days = Counter(dates)
        print(f"- 提交：{n} 个（其中合并提交 {merges} 个）")
        print(f"- 时间跨度：{dates[-1]} 至 {dates[0]}，有提交的日子 {len(days)} 天")
        print(f"- 作者（git shortlog -sn）：{'；'.join(authors[:10])}")
        busiest = days.most_common(3)
        print(f"- 最忙的几天：{'、'.join(f'{d}（{c} 个）' for d, c in busiest)}")
        if dates and busiest and sum(c for _, c in busiest[:2]) > 0.5 * len(dates) and len(dates) >= 10:
            print("  注意：一半以上的提交集中在一两天，历史可能是导入或重放的，讲义里要如实写")
        bodies = git(repo, "log", "--format=%B%x00")
        co = Counter(m.strip() for m in re.findall(r"(?im)^co-authored-by:\s*([^<\n]+)", bodies))
        if co:
            print(f"- 提交说明里的 Co-Authored-By：{'；'.join(f'{k} {v} 次' for k, v in co.most_common(5))}")
        test_notes = [ln.strip() for ln in bodies.splitlines()
                      if re.search(r"(?i)\b\d[\d,]*\s+(tests?|specs?)\b.*\b(pass|passed|green|ok)\b|全部通过|测试通过", ln)]
        if test_notes:
            print("- 提交说明里记的测试结果（最近几条）：")
            for t in test_notes[:5]:
                print(f"  - {t[:120]}")
        print("- 最近 5 个提交：")
        for ln in git(repo, "log", "-5", "--format=%h %ad %s", "--date=short").splitlines():
            print(f"  - {ln[:120]}")
    else:
        print("- 没有 git 历史")

    # ------------------------------------------------------------ 测试
    section("测试（静态统计：参数化用例算 1 个，以测试框架自己的统计为准）")
    if test_cases:
        for lang, c in test_cases.most_common():
            print(f"- {lang}：{fmt_n(c)} 个用例，分布在 {test_files[lang]} 个文件里")
    else:
        print("- 没找到测试用例")
    evidence = []
    for root, dirs, names in os.walk(repo):
        rel = os.path.relpath(root, repo)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "venv", "site-packages"} and depth < 6]
        for n in names:
            p = Path(root) / n
            r = os.path.relpath(p, repo)
            try:
                when = time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime))
            except OSError:
                continue
            if n.endswith(".xml") and ("surefire-reports" in r or "test-results" in r or n.startswith("TEST-") or "junit" in n.lower()):
                txt = read(p) or ""
                nums = [sum(int(x) for x in re.findall(rf'<testsuite\b[^>]*\b{k}="(\d+)"', txt)) for k in ("tests", "failures", "errors", "skipped")]
                evidence.append((when, f"{r}：tests={nums[0]} failures={nums[1]} errors={nums[2]} skipped={nums[3]}"))
            elif r.endswith(os.path.join(".pytest_cache", "v", "cache", "lastfailed")):
                try:
                    evidence.append((when, f"{r}：上次失败 {len(json.loads(read(p) or '{}'))} 个"))
                except ValueError:
                    pass
            elif r.endswith(os.path.join(".pytest_cache", "v", "cache", "nodeids")):
                try:
                    evidence.append((when, f"{r}：pytest 收集过 {len(json.loads(read(p) or '[]'))} 个用例"))
                except ValueError:
                    pass
            elif n in (".coverage", "coverage.xml", "lcov.info", "coverage-final.json", "jacoco.xml"):
                evidence.append((when, f"{r}：覆盖率文件"))
    reports = [(w, r) for w, r in evidence if "surefire" in r or "test-results" in r or "TEST-" in r]
    shown = [e for e in evidence if e not in reports] + sorted(reports, reverse=True)[:5]
    if shown:
        print("- 跑过的痕迹（文件修改时间 · 内容）：")
        for when, r in sorted(shown, reverse=True):
            print(f"  - {when} · {r}")
        if len(reports) > 5:
            total = [0, 0, 0, 0]
            for _, r in reports:
                for i, k in enumerate(("tests", "failures", "errors", "skipped")):
                    m = re.search(rf"{k}=(\d+)", r)
                    total[i] += int(m.group(1)) if m else 0
            print(f"  - 另有 {len(reports) - 5} 份测试报告；全部报告合计 tests={total[0]} failures={total[1]} errors={total[2]} skipped={total[3]}")
    else:
        print("- 没找到跑过测试的痕迹（surefire / junit 报告、.pytest_cache、覆盖率文件）")
    print(f"- CI 配置：{'、'.join(ci) if ci else '没有'}")
    print("- 想要准确数字：pytest --collect-only -q | tail -1 · cargo test -- --list · go test ./... -list . · "
          "npx vitest list / npx jest --listTests · mvn test（会真跑，先问用户）")

    # ------------------------------------------------------------ 文档与部署
    section("文档")
    readmes = [d for d in docs if re.match(r"(?i)readme", d.rsplit("/", 1)[-1])]
    print(f"- Markdown / rst：{len(docs)} 份；README：{'、'.join(readmes[:5]) or '没有'}")
    if adrs:
        print(f"- ADR / 决策记录：{len(adrs)} 份（{os.path.dirname(adrs[0]) or '根目录'} 等）")
    special = [d for d in docs if re.search(r"(?i)(design|architecture|设计|架构|CLAUDE\.md|AGENTS\.md|HANDOVER|CHANGELOG)", d)]
    for d in special[:15]:
        print(f"- {d}")

    section("部署痕迹")
    for d in sorted(deploy)[:30]:
        print(f"- {d}")
    if not deploy:
        print("- 没找到 Dockerfile、compose、k8s、云平台配置")

    section("理由线索：注释里带「因为 / 否则 / 为了 / NOTE / invariant」的行最多的文件")
    for f, c in why_hits.most_common(12):
        print(f"- {f}：{c} 行")
    if not why_hits:
        print("- 注释里没找到理由线索，去 ADR、设计文档、提交说明里找")


if __name__ == "__main__":
    main()

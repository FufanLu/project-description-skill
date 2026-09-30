"""找 Chrome，跑一次无头 Chrome，跑完把进程清干净。

每次用一个临时 profile。等输出文件出现、大小不再变化就算完成，然后按 profile 路径 pkill：
无头 Chrome 偶尔写完文件也不退出，不清就会一直挂着。
macOS 没有 timeout 命令，超时靠这里的轮询。
"""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def find_chrome():
    cands = [os.environ.get("CHROME"), MAC_CHROME, "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        cands.append(shutil.which(name))
    for c in cands:
        if c and Path(c).exists():
            return c
    raise SystemExit("找不到 Chrome。请安装 Google Chrome，或设置环境变量 CHROME=<可执行文件路径>。")


def file_url(path):
    """本地文件转 file URL。中文和空格都做百分号编码：带中文路径又带 #锚点 的 URL 不编码会白屏。"""
    return Path(path).resolve().as_uri()


def run(args, out_file, timeout=90, poll=0.5):
    """跑无头 Chrome，直到 out_file 写完（非空且大小稳定）。成功返回 True。"""
    out_file = Path(out_file)
    if out_file.exists():
        out_file.unlink()
    profile = tempfile.mkdtemp(prefix="guide-chrome-")
    cmd = [find_chrome(), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--disable-extensions", f"--user-data-dir={profile}", *args]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok, last = False, -1
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            if out_file.exists():
                size = out_file.stat().st_size
                if size > 0 and size == last:
                    ok = True
                    break
                last = size
            elif proc.poll() is not None:
                break  # Chrome 退出了，却没写出文件
            time.sleep(poll)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        subprocess.run(["pkill", "-f", profile], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)
    return ok


def screenshot(url, png, width, height, scale=1, budget=3000, timeout=90):
    """整页截图（只截 width × height 这一屏）。"""
    return run(["--hide-scrollbars", f"--force-device-scale-factor={scale}", f"--virtual-time-budget={budget}",
                f"--window-size={int(width)},{int(height)}", f"--screenshot={Path(png).resolve()}", url], png, timeout)


def print_pdf(url, pdf, budget=6000, timeout=180):
    """打印成 PDF：不要页眉页脚，按标题层级生成书签。"""
    return run([f"--virtual-time-budget={budget}", "--no-pdf-header-footer", "--generate-pdf-document-outline",
                f"--print-to-pdf={Path(pdf).resolve()}", url], pdf, timeout)

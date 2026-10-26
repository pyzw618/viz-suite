# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""解析 viz-suite 包根路径 (<SKILL>)、任务工作区 (<WORKSPACE>) 与本机运行环境能力。

用法：
    uv run resolve_runtime.py --json
    uv run resolve_runtime.py --workspace ./my-task --json
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SKILL_ROOT = Path(__file__).resolve().parents[2]


def find_browser() -> str | None:
    env_p = os.environ.get("CHROME_PATH") or os.environ.get("BROWSER_PATH")
    if env_p and Path(env_p).is_file():
        return str(Path(env_p))
    for name in ("chrome", "google-chrome", "chromium", "msedge", "microsoft-edge"):
        hit = shutil.which(name)
        if hit:
            return hit
    win_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in win_candidates:
        if Path(c).is_file():
            return c
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="viz-suite 运行环境与路径锚点解析器")
    ap.add_argument("--workspace", default=".", help="当前任务工作区路径")
    ap.add_argument("--no-write", action="store_true", help="只输出 JSON，不写 .viz-suite/runtime.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()
    uv_bin = shutil.which("uv")
    browser_bin = find_browser()
    channels = [d.name for d in sorted(SKILL_ROOT.iterdir())
                if d.is_dir() and (d / "SKILL.md").is_file()]
    scenes = [p.stem for p in sorted((SKILL_ROOT / "shared" / "assets" / "scenes").glob("*.json"))]

    runtime = {
        "skill_root": str(SKILL_ROOT),
        "shared_dir": str(SKILL_ROOT / "shared"),
        "workspace": str(ws),
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "uv": uv_bin,
        "runner_prefix": "uv run" if uv_bin else f'"{sys.executable}"',
        "browser": browser_bin,
        "channels": channels,
        "scenes": scenes,
    }

    outputs = []
    warnings = []
    if not browser_bin:
        warnings.append("未检测到 Chrome/Edge，viz-interactive / viz-diagram 的无头截图将受限")
    if not args.no_write and ws.is_dir():
        cfg_dir = ws / ".viz-suite"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        rt_file = cfg_dir / "runtime.json"
        rt_file.write_text(json.dumps(runtime, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        outputs.append(str(rt_file))

    result = {
        "status": "success",
        "outputs": outputs,
        "rows_used": 0,
        "rows_dropped": 0,
        "verified": True,
        "warnings": warnings,
        "runtime": runtime,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

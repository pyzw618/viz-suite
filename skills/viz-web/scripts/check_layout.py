# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""用 CDP 检查 HTML 在指定视口下的横向溢出、越界元素与图表容器塌陷。

用法：
    uv run check_layout.py templates/echarts/*.html --json
    uv run check_layout.py templates/dashboard/sales_dashboard.html \
        --viewport desktop=1280x800 --viewport mobile=390x844 --json --out layout.json

判定：`documentElement.scrollWidth > innerWidth + 1`、`body.scrollWidth > innerWidth + 1`、
或任一可见元素 `right > innerWidth + 1` / `left < -1` 记为 issue。
"""
import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CAPTURE = Path(__file__).with_name("capture_html.py")
spec = importlib.util.spec_from_file_location("capture_html", CAPTURE)
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

DEFAULT_VIEWPORTS = [("desktop", 1280, 800), ("mobile", 390, 844)]

PROBE = r"""(() => {
  const iw = window.innerWidth;
  const ih = window.innerHeight;
  const de = document.documentElement;
  const body = document.body;
  const bad = [];
  for (const el of document.body.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    if (r.right > iw + 1 || r.left < -1) {
      bad.push({
        tag: el.tagName,
        id: el.id || '',
        cls: typeof el.className === 'string' ? el.className : '',
        left: Math.round(r.left),
        right: Math.round(r.right),
        width: Math.round(r.width)
      });
      if (bad.length >= 20) break;
    }
  }
  const charts = [...document.querySelectorAll('.chart, [id*="chart"], canvas, svg')]
    .map(el => {
      const r = el.getBoundingClientRect();
      return {tag: el.tagName, id: el.id || '', w: Math.round(r.width), h: Math.round(r.height)};
    })
    .filter(c => c.w > 0 || c.h > 0);
  return {
    innerWidth: iw,
    innerHeight: ih,
    docScrollWidth: de.scrollWidth,
    bodyScrollWidth: body ? body.scrollWidth : 0,
    overflowX: de.scrollWidth > iw + 1 || (body && body.scrollWidth > iw + 1),
    bad,
    charts
  };
})()"""


def parse_viewports(values):
    if not values:
        return list(DEFAULT_VIEWPORTS)
    out = []
    for raw in values:
        name, _, size = raw.partition("=")
        width, _, height = size.lower().partition("x")
        try:
            out.append((name or f"vp{len(out) + 1}", int(width), int(height)))
        except ValueError:
            raise SystemExit(f"非法视口：{raw}，应为 name=1280x800")
    return out


def wait_ready(ws, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.2)
        try:
            result = ws.command("Runtime.evaluate", {
                "expression": "document.readyState", "returnByValue": True})
            if result.get("result", {}).get("value") == "complete":
                return True
        except RuntimeError:
            pass
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="HTML 响应式溢出/越界检查（CDP）")
    ap.add_argument("files", nargs="+", help="本地 HTML 文件")
    ap.add_argument("--viewport", action="append", default=None,
                    help="name=WxH，可重复；默认 desktop=1280x800 与 mobile=390x844")
    ap.add_argument("--wait-ms", type=int, default=1400, help="页面加载后等待毫秒数")
    ap.add_argument("--browser", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    files = [Path(raw) for raw in args.files]
    viewports = parse_viewports(args.viewport)
    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [],
              "summary": {"files": len(files), "viewports": len(viewports),
                          "combinations": 0, "issues": 0, "missing": 0},
              "results": []}
    browser = cap.find_browser(args.browser)
    if browser is None:
        result["warnings"].append("未找到 Chrome/Edge；请安装或通过 --browser / CHROME_PATH 指定")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    profile = Path(tempfile.mkdtemp(prefix="vizaudit-"))
    process = None
    ws = None
    try:
        port = cap.free_port()
        process = cap.start_browser(browser, profile, port)
        cap.wait_for_cdp(port)
        target = cap.create_target(port)
        ws = cap.CDPWebSocket(target["webSocketDebuggerUrl"])
        ws.command("Page.enable")
        ws.command("Runtime.enable")
        for path in files:
            if not path.is_file():
                result["warnings"].append(f"文件不存在：{path}")
                result["summary"]["missing"] += 1
                continue
            url = path.resolve().as_uri()
            for name, width, height in viewports:
                record = {"file": str(path), "viewport": name, "width": width, "height": height}
                try:
                    ws.command("Emulation.setDeviceMetricsOverride", {
                        "width": width, "height": height, "deviceScaleFactor": 1,
                        "mobile": width < 600, "screenWidth": width, "screenHeight": height})
                    ws.command("Emulation.setScrollbarsHidden", {"hidden": True})
                    ws.command("Page.navigate", {"url": url})
                    wait_ready(ws)
                    time.sleep(max(args.wait_ms, 400) / 1000.0)
                    probe = ws.command("Runtime.evaluate", {
                        "expression": PROBE, "returnByValue": True})
                    value = probe.get("result", {}).get("value", {}) or {}
                    record.update(value)
                    record["ok"] = not (
                        value.get("overflowX")
                        or value.get("bad")
                        or value.get("docScrollWidth", 0) > width + 1
                        or value.get("bodyScrollWidth", 0) > width + 1
                    )
                    if value.get("innerWidth") != width:
                        record["ok"] = False
                        record["warning"] = (
                            f"布局视口 {value.get('innerWidth')} 与请求 {width} 不一致")
                except Exception as exc:  # noqa: BLE001
                    record["ok"] = False
                    record["error"] = f"{type(exc).__name__}: {exc}"
                result["results"].append(record)
                if not record["ok"]:
                    result["warnings"].append(
                        f"{path.name} [{name}]：{record.get('warning') or record.get('error') or '存在横向溢出/越界'}")
    finally:
        if ws:
            ws.close()
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:  # noqa: BLE001
                process.kill()
        shutil.rmtree(profile, ignore_errors=True)

    issues = [r for r in result["results"] if not r.get("ok")]
    result["summary"]["combinations"] = len(result["results"])
    result["summary"]["issues"] = len(issues)
    result["status"] = "success" if not issues and not result["summary"]["missing"] else "partial"
    result["verified"] = (not issues and not result["summary"]["missing"]
                          and bool(result["results"]))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        result["outputs"].append(str(args.out))
        payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json or not sys.stdout.isatty():
        print(payload)
    else:
        print(f"检查 {result['summary']['files']} 文件 × {result['summary']['viewports']} 视口："
              f"issues {result['summary']['issues']}")
        for item in issues:
            print("  ✗", item["file"], item["viewport"],
                  "scroll", item.get("docScrollWidth"), item.get("bodyScrollWidth"),
                  "bad", (item.get("bad") or [])[:3])
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

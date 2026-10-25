# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""离线自包含与结构检查：外链、容器高度、脚本语法、可访问性、响应式元信息。

用法：
    uv run lint_html.py templates/echarts/line.html --json
    uv run lint_html.py templates/dashboard/*.html --strict --json
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RESOURCE_TAGS = {"script", "link", "img", "iframe", "source", "video", "audio",
                 "track", "embed", "object", "use", "image"}
CONTAINER_HINTS = re.compile(r"(chart|map|graph|viz|dashboard|kpi|poster|infographic)", re.I)


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []
        self.scripts: list[str] = []
        self.styles: list[str] = []
        self._mode: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag.lower(), {k.lower(): (v or "") for k, v in attrs}))
        if tag.lower() in ("script", "style"):
            self._mode = tag.lower()
            self._buffer = []

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag.lower(), {k.lower(): (v or "") for k, v in attrs}))

    def handle_data(self, data):
        if self._mode:
            self._buffer.append(data)

    def handle_endtag(self, tag):
        if self._mode == "script" and tag.lower() == "script":
            self.scripts.append("".join(self._buffer))
            self._mode, self._buffer = None, []
        elif self._mode == "style" and tag.lower() == "style":
            self.styles.append("".join(self._buffer))
            self._mode, self._buffer = None, []


def add(checks, file, check, severity, passed, detail):
    checks.append({"file": file, "check": check, "severity": severity,
                   "passed": passed, "detail": detail})


def css_has_height(css: str, attrs: dict) -> bool:
    selectors = []
    if attrs.get("id"):
        selectors.append("#" + attrs["id"])
    for cls in (attrs.get("class") or "").split():
        selectors.append("." + cls)
    for selector in selectors:
        for match in re.finditer(re.escape(selector) + r"[^{]*\{([^}]*)\}", css):
            if re.search(r"height\s*:", match.group(1), re.I):
                return True
    return False


def node_check(scripts: list[str]) -> list[dict]:
    node = shutil.which("node")
    if not node:
        return [{"skipped": True}]
    results = []
    with tempfile.TemporaryDirectory(prefix="vizlint-") as tmp:
        for index, code in enumerate(scripts):
            if not code.strip():
                continue
            path = Path(tmp) / f"inline_{index}.js"
            path.write_text(code, encoding="utf-8")
            proc = subprocess.run([node, "--check", str(path)], capture_output=True, timeout=20)
            if proc.returncode != 0:
                message = (proc.stderr or b"").decode("utf-8", errors="replace").strip().splitlines()
                results.append({"index": index, "ok": False,
                                "detail": " | ".join(message[:3])})
            else:
                results.append({"index": index, "ok": True, "detail": ""})
    return results


def lint_file(path: Path) -> tuple[list, dict, list[str]]:
    checks: list = []
    warnings: list[str] = []
    metrics: dict = {"file": str(path)}
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
        warnings.append("文件不是合法 UTF-8，已按替换字符读取")
    collector = Collector()
    try:
        collector.feed(text)
        collector.close()
    except Exception as exc:  # noqa: BLE001
        add(checks, path.name, "parse", "blocking", False, f"HTML 解析失败：{exc}")
        return checks, metrics, warnings

    css = "\n".join(collector.styles)
    all_attrs = [attrs for _, attrs in collector.tags]
    metrics["tags"] = len(collector.tags)
    metrics["inline_scripts"] = len([s for s in collector.scripts if s.strip()])

    external = []
    for tag, attrs in collector.tags:
        for attr in ("src", "href", "poster", "data", "xlink:href"):
            value = attrs.get(attr, "").strip()
            if re.match(r"^(https?:)?//", value, re.I):
                if tag == "a":
                    warnings.append(f"外部链接（非资源依赖）：{value}")
                elif tag in RESOURCE_TAGS:
                    external.append(f"<{tag} {attr}={value}>")
    for match in re.findall(r"url\(\s*['\"]?((?:https?:)?//[^)]+)", css, re.I):
        external.append(f"CSS url({match})")
    for match in re.findall(r"@import\s+['\"]?((?:https?:)?//[^;'\"]+)", css, re.I):
        external.append(f"CSS @import({match})")
    if external:
        add(checks, path.name, "offline", "blocking", False,
            f"发现 {len(external)} 个外部资源：{external[:3]}")
    else:
        add(checks, path.name, "offline", "info", True, "无外部资源引用（离线自包含）")

    containers = []
    for tag, attrs in collector.tags:
        ident = f"{attrs.get('id', '')} {attrs.get('class', '')}"
        figure_poster = tag == "figure" and re.search(r"(poster|infographic)", ident, re.I)
        if (tag in ("div", "canvas", "svg") and CONTAINER_HINTS.search(ident)) or figure_poster:
            containers.append((tag, attrs))
    metrics["containers"] = len(containers)
    missing_height = []
    for tag, attrs in containers:
        inline = attrs.get("style", "")
        if not re.search(r"height\s*:", inline, re.I) and not css_has_height(css, attrs):
            missing_height.append(f"<{tag} id={attrs.get('id','')} class={attrs.get('class','')}>")
    if containers and missing_height:
        add(checks, path.name, "container_height", "warning", False,
            f"{len(missing_height)} 个图表容器未显式设置高度，可能塌陷：{missing_height[:3]}")
    elif containers:
        add(checks, path.name, "container_height", "info", True, "图表容器均有显式高度")
    else:
        add(checks, path.name, "container_height", "warning", False, "未识别到图表容器（id/class 需含 chart/map/graph/viz）")

    viewport = any(attrs.get("name", "").lower() == "viewport" for _, attrs in collector.tags)
    add(checks, path.name, "viewport_meta", "info" if viewport else "warning", viewport,
        "存在 viewport meta" if viewport else "缺少 <meta name=viewport>，移动端会按桌面宽度渲染")

    charset = any("charset" in attrs for tag, attrs in collector.tags if tag == "meta")
    add(checks, path.name, "charset", "info" if charset else "warning", charset,
        "存在 charset 声明" if charset else "缺少 <meta charset>")

    lang = next((attrs.get("lang", "") for tag, attrs in collector.tags if tag == "html"), "")
    add(checks, path.name, "lang", "info" if lang else "warning", bool(lang),
        f"html lang={lang}" if lang else "html 根元素缺少 lang 属性")

    has_figure = any(tag == "figure" for tag, _ in collector.tags)
    add(checks, path.name, "figure", "info" if has_figure else "warning", has_figure,
        "使用 <figure> 承载图表" if has_figure else "建议用 <figure>/<figcaption> 包裹图表与来源")

    aria = any(("aria-label" in attrs) or (attrs.get("role") == "img") for _, attrs in collector.tags)
    if not aria:
        aria = any("aria" in script for script in collector.scripts)
    add(checks, path.name, "aria", "info" if aria else "warning", aria,
        "存在 aria 描述" if aria else "缺少 aria-label / role=img / ECharts aria 配置")

    script_body = "\n".join(collector.scripts)
    if re.search(r"\.innerHTML\s*=", script_body):
        add(checks, path.name, "innerhtml", "warning", False,
            "内联脚本存在 innerHTML 赋值：动态文本请用 textContent 防注入")
    if "document.write" in script_body:
        add(checks, path.name, "document_write", "warning", False,
            "内联脚本使用 document.write，可能破坏解析")

    syntax = node_check(collector.scripts)
    if syntax and syntax[0].get("skipped"):
        add(checks, path.name, "js_syntax", "info", True, "未安装 node，跳过内联脚本语法检查")
    else:
        errors = [item for item in syntax if item and not item.get("ok")]
        if errors:
            add(checks, path.name, "js_syntax", "blocking", False,
                f"{len(errors)} 段内联脚本语法错误：{errors[0]['detail'][:180]}")
        else:
            add(checks, path.name, "js_syntax", "info", True,
                f"{len([s for s in syntax if s])} 段内联脚本语法通过 node --check")

    return checks, metrics, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="HTML 离线自包含与结构检查")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--strict", action="store_true", help="warning 也返回非零退出码")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    checks: list = []
    metrics: list = []
    warnings: list[str] = []
    for raw in args.files:
        path = Path(raw)
        if not path.is_file():
            add(checks, path.name, "exists", "blocking", False, f"文件不存在：{path}")
            continue
        file_checks, file_metrics, file_warnings = lint_file(path)
        checks.extend(file_checks)
        metrics.append(file_metrics)
        warnings.extend(file_warnings)

    blocking = [c for c in checks if c["severity"] == "blocking" and not c["passed"]]
    warned = [c for c in checks if c["severity"] == "warning" and not c["passed"]]
    result = {
        "status": "success" if not blocking else "partial",
        "outputs": [],
        "rows_used": 0,
        "rows_dropped": 0,
        "verified": not blocking,
        "warnings": warnings + [c["detail"] for c in blocking + warned],
        "summary": {"files": len(metrics), "blocking": len(blocking), "warning": len(warned),
                    "passed": sum(1 for c in checks if c["passed"]), "total_checks": len(checks)},
        "checks": checks,
        "metrics": metrics,
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        result["outputs"].append(str(args.out))
        payload = json.dumps(result, ensure_ascii=False, indent=2)

    if args.json or not sys.stdout.isatty():
        print(payload)
    else:
        print(f"检查 {len(metrics)} 个 HTML：blocking {len(blocking)} / warning {len(warned)}")
        for check in checks:
            if not check["passed"]:
                print(f"  [{check['severity']}] {check['file']} · {check['check']}: {check['detail']}")
    if blocking:
        return 1
    if args.strict and warned:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

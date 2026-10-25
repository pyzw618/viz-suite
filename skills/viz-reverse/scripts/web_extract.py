# /// script
# requires-python = ">=3.10"
# dependencies = ["defusedxml>=0.7"]
# ///
# -*- coding: utf-8 -*-
"""源码/DOM 逆向通道：静态提取 ECharts / Chart.js / Plotly 配置与 SVG 数据。

只解析本地文件，不执行未知页面脚本，不绕过登录/付费墙。
实时页面请用 --emit-browser 生成只读提取片段，再由 Browser 工具执行。
"""
import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from defusedxml import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts = []
        self.script_attrs = []
        self.texts = []
        self.tags = []
        self.title = ""
        self._script = None
        self._buffer = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): (v or "") for k, v in attrs}
        self.tags.append((tag.lower(), attrs))
        if tag.lower() == "script":
            self._script = attrs
            self._buffer = []
        elif tag.lower() == "title":
            self._in_title = True

    def handle_data(self, data):
        if self._script is not None:
            self._buffer.append(data)
        elif self._in_title:
            self.title += data
        else:
            stripped = data.strip()
            if stripped:
                self.texts.append(stripped)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._script is not None:
            self.scripts.append("".join(self._buffer))
            self.script_attrs.append(self._script)
            self._script = None
            self._buffer = []
        elif tag.lower() == "title":
            self._in_title = False


def json_after(text: str, marker: str):
    idx = text.find(marker)
    if idx < 0:
        return None
    candidates = [pos for pos in (text.find("{", idx), text.find("[", idx)) if pos >= 0]
    if not candidates:
        return None
    start = min(candidates)
    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
        return value
    except json.JSONDecodeError:
        return None


def embedded_json(collector: Collector):
    for attrs, body in zip(collector.script_attrs, collector.scripts):
        if attrs.get("type", "").lower() == "application/json" or attrs.get("id", "").lower().endswith("option"):
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                continue
    for body in collector.scripts:
        for marker in ("window.__ECHARTS_OPTION__", "window.__CHART_CONFIG__", "window.__PLOTLY_DATA__"):
            value = json_after(body, marker)
            if value is not None:
                return value
    return None


def get_colors(option) -> list[str]:
    colors = option.get("color") if isinstance(option, dict) else None
    if colors:
        return [c for c in colors if isinstance(c, str)]
    out = []
    for s in option.get("series", []) if isinstance(option, dict) else []:
        style = s.get("itemStyle") or {}
        color = style.get("color") or (s.get("lineStyle") or {}).get("color")
        if color:
            out.append(color)
    return out or ["#0072B2"]


def write_csv(path: Path, cols, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        f.write(",".join(cols) + "\n")
        for row in rows:
            f.write(",".join(str(row.get(c, "")) for c in cols) + "\n")


def echarts_data(option):
    series = option.get("series") or []
    first = series[0] if series else {}
    kind = str(first.get("type", "bar")).lower()
    x_axis = option.get("xAxis") or {}
    x_values = x_axis.get("data") if isinstance(x_axis, dict) else None
    title = (option.get("title") or {}).get("text", "") if isinstance(option.get("title"), dict) else ""
    colors = get_colors(option)
    if kind in ("pie", "doughnut"):
        rows = []
        for i, s in enumerate(series):
            for item in s.get("data", []):
                if isinstance(item, dict):
                    rows.append({"category": item.get("name", f"slice{i+1}"), "value": item.get("value", 0)})
                else:
                    rows.append({"category": f"slice{i+1}", "value": item})
        return "pie", rows, ["category", "value"], {"title": title, "colors": colors}
    if kind == "scatter":
        rows = []
        for s in series:
            for i, item in enumerate(s.get("data", [])):
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    rows.append({"x": item[0], "y": item[1], "series": s.get("name", "series")})
        return "scatter", rows, ["x", "y", "series"], {"title": title, "colors": colors}
    rows = []
    if kind in ("bar", "column") and len(series) == 1 and x_values:
        for i, item in enumerate(series[0].get("data", [])):
            value = item.get("value") if isinstance(item, dict) else item
            x = x_values[i] if i < len(x_values) else i
            rows.append({"category": x, "value": value})
        return "bar", rows, ["category", "value"], {"title": title, "colors": colors}
    for s in series:
        for i, item in enumerate(s.get("data", [])):
            value = item.get("value") if isinstance(item, dict) else item
            x = x_values[i] if x_values and i < len(x_values) else i
            rows.append({"x": x, "series": s.get("name", "series"), "value": value})
    return kind, rows, ["x", "series", "value"], {"title": title, "colors": colors}


def chartjs_data(config):
    data = config.get("data") or {}
    labels = data.get("labels") or []
    datasets = data.get("datasets") or []
    kind = str(config.get("type", "line")).lower()
    title = ((config.get("options") or {}).get("plugins") or {}).get("title", {}).get("text", "")
    colors = []
    rows = []
    for ds in datasets:
        color = ds.get("borderColor") or ds.get("backgroundColor") or "#0072B2"
        colors.append(color)
        for i, value in enumerate(ds.get("data", [])):
            rows.append({"x": labels[i] if i < len(labels) else i,
                         "series": ds.get("label", "series"), "value": value})
    if kind == "pie":
        rows = [{"category": labels[i] if i < len(labels) else i, "value": value}
                for i, value in enumerate(datasets[0].get("data", []))] if datasets else []
        return "pie", rows, ["category", "value"], {"title": title, "colors": colors}
    return kind, rows, ["x", "series", "value"], {"title": title, "colors": colors}


def plotly_data(data, layout):
    traces = data if isinstance(data, list) else [data]
    first = traces[0] if traces else {}
    kind = str(first.get("type", "scatter")).lower()
    title = ((layout or {}).get("title") or {}).get("text", "")
    colors = []
    rows = []
    for trace in traces:
        marker = trace.get("marker") or {}
        color = marker.get("color") or trace.get("line", {}).get("color") or "#0072B2"
        if isinstance(color, list):
            colors.extend(color)
        else:
            colors.append(color)
        if kind == "pie":
            for label, value in zip(trace.get("labels", []), trace.get("values", [])):
                rows.append({"category": label, "value": value})
        else:
            for x, y in zip(trace.get("x", []), trace.get("y", [])):
                rows.append({"x": x, "y": y, "series": trace.get("name", "series")})
    cols = ["category", "value"] if kind == "pie" else ["x", "y", "series"]
    return kind, rows, cols, {"title": title, "colors": colors}


def svg_data(path: Path):
    root = ET.parse(path).getroot()
    kind = root.attrib.get("data-chart-type", "").lower()
    title = root.attrib.get("data-title", "")
    if not title:
        node = root.find("{http://www.w3.org/2000/svg}title")
        title = (node.text or "") if node is not None else ""
    rows = []
    colors = []
    for el in root.iter():
        attrs = el.attrib
        if "data-value" in attrs:
            row = {"value": attrs["data-value"], "category": attrs.get("data-category", ""),
                   "series": attrs.get("data-series", ""), "x": attrs.get("data-x", ""),
                   "y": attrs.get("data-y", ""), "row": attrs.get("data-row", ""),
                   "col": attrs.get("data-col", "")}
            row = {k: v for k, v in row.items() if v != ""}
            rows.append(row)
            if attrs.get("fill"):
                colors.append(attrs["fill"])
    if not kind:
        if rows and "data-row" in rows[0]:
            kind = "heatmap"
        elif rows and "data-x" in rows[0]:
            kind = "scatter"
        elif rows:
            kind = "bar"
    if kind == "scatter":
        cols = ["x", "y", "series"]
    elif kind == "heatmap":
        cols = ["row", "col", "value"]
    else:
        cols = ["category", "value", "series"]
    return kind, rows, cols, {"title": title, "colors": colors or ["#0072B2"]}


def browser_snippet(kind: str) -> str:
    return f"""// viz-reverse · read-only browser extraction snippet
// Run only on pages you are authorized to inspect. It does not click, login, or bypass paywalls.
(async () => {{
  const out = {{source: 'browser', format: '{kind}'}};
  try {{
    if (window.echarts) {{
      const el = document.querySelector('[data-echarts], .echarts, #chart') || document.body;
      const inst = echarts.getInstanceByDom(el);
      if (inst) out.echarts = inst.getOption();
    }}
    if (window.Chart) {{
      const canvas = document.querySelector('canvas');
      if (canvas) out.chartjs = Chart.getChart(canvas)?.config;
    }}
    if (window.Plotly) {{
      const gd = document.querySelector('.plotly-graph-div, [data-plotly]');
      if (gd && gd.data) {{ out.plotlyData = gd.data; out.plotlyLayout = gd.layout; }}
    }}
  }} catch (e) {{ out.error = String(e); }}
  console.log(JSON.stringify(out));
}})();
"""


def skeleton(collector: Collector, path: Path, outdir: Path, warnings: list[str]):
    title = collector.title.strip() or (collector.texts[0] if collector.texts else "Untitled chart")
    css_colors = []
    for tag, attrs in collector.tags:
        css_colors += re.findall(r"#[0-9a-fA-F]{6}", attrs.get("style", ""))
    for body in collector.scripts:
        css_colors += re.findall(r"#[0-9a-fA-F]{6}", body)
    colors = list(dict.fromkeys(css_colors))[:8] or ["#0072B2"]
    skeleton_path = outdir / f"{path.stem}_skeleton.html"
    skeleton_path.write_text(
        f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{title}</title></head>
<body><h1>{title}</h1><p>TODO：该页面没有可静态读取的图表配置。请用 Browser 只读提取 getOption()/config，
或对清晰截图使用 inspect_image.py + calibrate_and_extract.py。</p>
<pre>{{"chart_type": "TODO", "colors": {json.dumps(colors)}, "source_text": {json.dumps(collector.texts[:8], ensure_ascii=False)}}}</pre>
</body></html>""", encoding="utf-8")
    warnings.append("未找到可静态读取的图表配置：已降级为 C 级结构骨架，数据为 TODO")
    return {"evidence_level": "GUESS", "chart_type": "unknown", "title": title,
            "colors": colors, "skeleton": str(skeleton_path)}


def main() -> int:
    ap = argparse.ArgumentParser(description="源码/DOM 静态逆向（ECharts/Chart.js/Plotly/SVG）")
    ap.add_argument("input", help="本地 HTML 或 SVG 文件")
    ap.add_argument("--outdir", default="web-reverse")
    ap.add_argument("--stem", default=None)
    ap.add_argument("--format", choices=["auto", "echarts", "chartjs", "plotly", "svg"], default="auto")
    ap.add_argument("--emit-browser", action="store_true", help="同时生成只读 Browser 提取片段")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "extraction": {}}
    warnings = result["warnings"]
    try:
        path = Path(args.input)
        if not path.is_file():
            raise ValueError(f"文件不存在：{path}")
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        stem = args.stem or path.stem
        extraction = {"evidence_level": "SOURCE", "format": args.format, "file": str(path)}

        if path.suffix.lower() == ".svg" or args.format == "svg":
            extraction["format"] = "svg"
            kind, rows, cols, style = svg_data(path)
            if not rows:
                collector = Collector()
                extraction = skeleton(collector, path, outdir, warnings)
                result.update({"status": "partial", "extraction": extraction,
                               "outputs": [extraction["skeleton"]]})
            else:
                data_path = outdir / f"{stem}_data.csv"
                write_csv(data_path, cols, rows)
                extraction.update({"chart_type": kind, "data": rows, "columns": cols,
                                   "title": style.get("title"), "colors": style.get("colors"),
                                   "data_csv": str(data_path), "exact_data": True})
                result.update({"status": "success", "verified": True,
                               "rows_used": len(rows), "outputs": [str(data_path)]})
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            collector = Collector()
            collector.feed(text)
            collector.close()
            option = embedded_json(collector)
            fmt = args.format
            if option is None and fmt == "auto":
                if "__PLOTLY_DATA__" in text:
                    fmt = "plotly"
                elif "__CHART_CONFIG__" in text:
                    fmt = "chartjs"
                elif "echarts" in text.lower():
                    fmt = "echarts"
            if fmt in ("echarts", "auto") and isinstance(option, dict) and "series" in option:
                kind, rows, cols, style = echarts_data(option)
                fmt = "echarts"
            elif fmt == "chartjs" or (isinstance(option, dict) and "datasets" in (option.get("data") or {})):
                kind, rows, cols, style = chartjs_data(option or {})
                fmt = "chartjs"
            elif fmt == "plotly" or (option is not None and isinstance(option, list)):
                layout = json_after(text, "window.__PLOTLY_LAYOUT__") or {}
                kind, rows, cols, style = plotly_data(option or [], layout)
                fmt = "plotly"
            elif option is None:
                extraction = skeleton(collector, path, outdir, warnings)
                result.update({"status": "partial", "extraction": extraction,
                               "outputs": [extraction["skeleton"]]})
                rows = []
            else:
                # 未知 JSON 配置：尽量按 ECharts 结构尝试
                try:
                    kind, rows, cols, style = echarts_data(option)
                    fmt = "echarts"
                except Exception:
                    kind, rows, cols, style = "unknown", [], [], {}
                    extraction = skeleton(collector, path, outdir, warnings)

            if rows:
                data_path = outdir / f"{stem}_data.csv"
                write_csv(data_path, cols, rows)
                spec_path = outdir / f"{stem}_reverse-spec.json"
                spec = {"chart_type": kind, "evidence_level": "SOURCE", "format": fmt,
                        "title": style.get("title") or collector.title, "colors": style.get("colors"),
                        "data_csv": str(data_path), "data": rows, "exact_data": True,
                        "source": str(path)}
                spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                code_path = outdir / f"{stem}_reproduction.js"
                code_path.write_text(
                    "// Exact source-level reproduction config extracted by viz-reverse\n"
                    f"const option = {json.dumps(option, ensure_ascii=False, indent=2)};\n"
                    "// Use it with the same chart library version; do not alter data values.\n",
                    encoding="utf-8")
                extraction.update({"chart_type": kind, "format": fmt, "data": rows,
                                   "columns": cols, "title": spec["title"], "colors": spec["colors"],
                                   "data_csv": str(data_path), "spec": str(spec_path),
                                   "code": str(code_path), "exact_data": True})
                result.update({"status": "success", "verified": True, "rows_used": len(rows),
                               "outputs": [str(data_path), str(spec_path), str(code_path)]})
            elif result["status"] != "partial":
                extraction = skeleton(collector, path, outdir, warnings)
                result.update({"status": "partial", "extraction": extraction,
                               "outputs": [extraction["skeleton"]]})

        if args.emit_browser:
            snippet_path = outdir / f"{stem}_browser-extract.js"
            snippet_path.write_text(browser_snippet(extraction.get("format", "auto")), encoding="utf-8")
            result["outputs"].append(str(snippet_path))
            extraction["browser_snippet"] = str(snippet_path)
        result["extraction"] = extraction
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{type(exc).__name__}: {exc}")

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        result["outputs"].append(str(args.out))
        payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    return 0 if result["status"] in ("success", "partial") else 2


if __name__ == "__main__":
    raise SystemExit(main())

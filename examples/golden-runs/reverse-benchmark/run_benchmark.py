# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=10"]
# ///
# -*- coding: utf-8 -*-
"""Gate 4 回归：跑 5 类清晰图 + 低清图 + 3D 饼图 + 4 个源码级夹具，汇总误差/SSIM/证据级别。

用法（需环境已安装 cv2/scikit-image/defusedxml/matplotlib）：
    python run_benchmark.py --python D:/Anaconda/envs/py4VLA/python.exe
"""
import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPTS = ROOT / "skills" / "viz-reverse" / "scripts"
OUT = HERE / "reverse-output"
CHARTS = ["bar", "line", "scatter", "pie", "heatmap"]


def run(python: str, script: str, args: list[str]) -> dict:
    proc = subprocess.run([python, str(SCRIPTS / script), *args, "--json"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode not in (0, 1, 2):
        raise RuntimeError(f"{script} exit {proc.returncode}: {proc.stderr[-500:]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{script} 输出不是 JSON：{exc}\n{proc.stdout[-500:]}\n{proc.stderr[-500:]}")


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def median_error(chart: str, gt_path: Path, rev_path: Path) -> float:
    gt, rv = read_csv(gt_path), read_csv(rev_path)
    values = []
    if chart == "line":
        index = {(str(r["x"]), r["series"]): float(r["value"]) for r in rv}
        for g in gt:
            key = (str(g["x"]), g["series"])
            if key in index:
                a, b = float(g["value"]), index[key]
                values.append(abs(a - b) / max(1e-9, abs(a)) * 100)
    elif chart == "scatter":
        for g in gt:
            x = float(g["x"])
            match = min(rv, key=lambda r: abs(float(r["x"]) - x))
            a, b = float(g["y"]), float(match["y"])
            values.append(abs(a - b) / max(1e-9, abs(a)) * 100)
    elif chart == "heatmap":
        index = {(r["row"], r["col"]): float(r["value"]) for r in rv}
        for g in gt:
            a = float(g["value"])
            b = index.get((g["row"], g["col"]))
            if b is None:
                continue
            if abs(a) < 1e-9:
                values.append(abs(a - b) * 100)  # 0–1 范围，绝对误差转百分点
            else:
                values.append(abs(a - b) / abs(a) * 100)
    else:
        for g in gt:
            match = next((r for r in rv if r.get("category") == g.get("category")), None)
            if match:
                a, b = float(g["value"]), float(match["value"])
                values.append(abs(a - b) / max(1e-9, abs(a)) * 100)
    return round(float(statistics.median(values)), 3) if values else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage 4 Gate 4 基准")
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()
    python = args.python
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"gate": {}, "clean": {}, "lowres": {}, "three_d": {}, "source_level": {}}

    for chart in CHARTS:
        base = OUT / chart
        base.mkdir(parents=True, exist_ok=True)
        inspect = run(python, "inspect_image.py", [
            str(HERE / "images" / f"{chart}.png"), "--chart-type", chart,
            "--outdir", str(base / "inspect")])
        calibrate = run(python, "calibrate_and_extract.py", [
            str(HERE / "images" / f"{chart}.png"),
            "--measurements", str(base / "inspect" / "measurements.json"),
            "--ticks", str(HERE / "ticks" / f"{chart}.json"),
            "--chart-type", chart, "--outdir", str(base), "--stem", chart, "--render"])
        compare = run(python, "compare_render.py", [
            str(HERE / "images" / f"{chart}.png"), str(base / "reproduction.png"),
            "--outdir", str(base / "compare"), "--out", str(base / "compare" / "compare.json")])
        err = median_error(chart, HERE / "ground-truth" / f"{chart}.csv", base / f"{chart}_data.csv")
        result["clean"][chart] = {
            "evidence": calibrate.get("reverse", {}).get("evidence_level"),
            "rows": calibrate.get("rows_used"),
            "median_error_pct": err,
            "ssim": compare.get("compare", {}).get("ssim"),
            "delta_e": compare.get("compare", {}).get("delta_e_mean"),
            "layout_iou": compare.get("compare", {}).get("layout_iou"),
            "status": calibrate.get("status"),
            "warnings": calibrate.get("warnings", []),
        }

    # 低清图
    low = OUT / "lowres"
    low.mkdir(parents=True, exist_ok=True)
    low_inspect = run(python, "inspect_image.py", [
        str(HERE / "images" / "bar_lowres.png"), "--chart-type", "bar",
        "--outdir", str(low / "inspect")])
    low_cal = run(python, "calibrate_and_extract.py", [
        str(HERE / "images" / "bar_lowres.png"),
        "--measurements", str(low / "inspect" / "measurements.json"),
        "--ticks", str(HERE / "ticks" / "bar_lowres.json"),
        "--chart-type", "bar", "--outdir", str(low), "--stem", "bar_lowres"])
    result["lowres"] = {
        "evidence": low_inspect.get("measurements", {}).get("evidence_hint"),
        "status": low_cal.get("status"),
        "precision_claimed": low_cal.get("reverse", {}).get("precision_claimed"),
        "warnings": low_cal.get("warnings", []),
        "correct_downgrade": low_inspect.get("measurements", {}).get("evidence_hint") == "C"
                             and low_cal.get("status") == "partial",
    }

    # 3D 饼图
    three = OUT / "pie_3d"
    three.mkdir(parents=True, exist_ok=True)
    three_inspect = run(python, "inspect_image.py", [
        str(HERE / "images" / "pie_3d.png"), "--chart-type", "pie",
        "--outdir", str(three / "inspect")])
    three_cal = run(python, "calibrate_and_extract.py", [
        str(HERE / "images" / "pie_3d.png"),
        "--measurements", str(three / "inspect" / "measurements.json"),
        "--ticks", str(HERE / "ticks" / "pie_3d.json"),
        "--chart-type", "pie", "--outdir", str(three), "--stem", "pie_3d"])
    result["three_d"] = {
        "evidence": three_inspect.get("measurements", {}).get("evidence_hint"),
        "refused": three_cal.get("reverse", {}).get("refused"),
        "status": three_cal.get("status"),
        "warnings": three_cal.get("warnings", []),
        "correct_refusal": three_inspect.get("measurements", {}).get("evidence_hint") == "X"
                           and bool(three_cal.get("reverse", {}).get("refused")),
    }

    # 源码级夹具
    web_expect = {
        "echarts_source.html": ("bar", "ground-truth/bar.csv"),
        "chartjs_source.html": ("line", "ground-truth/line.csv"),
        "plotly_source.html": ("pie", "ground-truth/pie.csv"),
        "bar_source.svg": ("bar", "ground-truth/bar.csv"),
        "generic_c.html": ("unknown", None),
    }
    for name, (kind, gt_rel) in web_expect.items():
        base = OUT / "web" / name
        base.mkdir(parents=True, exist_ok=True)
        ext = run(python, "web_extract.py", [
            str(HERE / "web" / name), "--outdir", str(base), "--emit-browser"])
        exact = None
        if gt_rel and ext.get("rows_used"):
            try:
                exact = median_error(kind, HERE / gt_rel, base / f"{Path(name).stem}_data.csv")
            except Exception:
                exact = None
        if isinstance(exact, float) and math.isnan(exact):
            exact = None
        result["source_level"][name] = {
            "evidence": ext.get("extraction", {}).get("evidence_level"),
            "format": ext.get("extraction", {}).get("format"),
            "rows": ext.get("rows_used"),
            "status": ext.get("status"),
            "exact_error_pct": exact,
            "browser_snippet": bool(ext.get("extraction", {}).get("browser_snippet")),
            "warnings": ext.get("warnings", []),
        }

    medians = [v["median_error_pct"] for v in result["clean"].values()]
    ssims = [v["ssim"] for v in result["clean"].values() if v["ssim"] is not None]
    result["gate"] = {
        "clean_median_error_pct": round(float(statistics.median(medians)), 3),
        "max_median_error_pct": max(medians),
        "min_ssim": min(ssims),
        "error_pass": max(medians) <= 5.0,
        "ssim_pass": min(ssims) >= 0.85,
        "lowres_pass": result["lowres"]["correct_downgrade"],
        "three_d_pass": result["three_d"]["correct_refusal"],
    }
    result["gate"]["pass"] = all(result["gate"][k] for k in
                                 ("error_pass", "ssim_pass", "lowres_pass", "three_d_pass"))
    (OUT / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8")

    # 接触表：原图 / 复现 / diff
    font = ImageFont.truetype(r"C:/Windows/Fonts/msyh.ttc", 16)
    rows = []
    for chart in CHARTS:
        base = OUT / chart
        rows.append((chart, base / "reproduction.png", base / "compare" / "diff.png"))
    width = 420
    cells = []
    for chart, repro, diff in rows:
        orig = Image.open(HERE / "images" / f"{chart}.png").convert("RGB")
        rep = Image.open(repro).convert("RGB")
        dif = Image.open(diff).convert("RGB")
        h = round(orig.height * width / orig.width)
        cells.append((chart, [im.resize((width, h), Image.LANCZOS) for im in (orig, rep, dif)], h))
    label_h = 26; gap = 10
    sheet = Image.new("RGB", (3 * width + 4 * gap, sum(h + label_h + gap for _, _, h in cells) + gap), "white")
    d = ImageDraw.Draw(sheet)
    y = gap
    for chart, ims, h in cells:
        d.text((gap, y), f"{chart} · 原图 / 复现 / diff", fill="black", font=font)
        y += label_h
        for i, im in enumerate(ims):
            sheet.paste(im, (gap + i * (width + gap), y))
        y += h + gap
    sheet.save(OUT / "contact.png")

    # 证据文件使用仓库相对路径，避免把本机绝对路径写进交付物
    root = str(ROOT.resolve())
    def portable(value):
        if isinstance(value, str):
            for prefix in (root + "\\", root + "/", root):
                if value.startswith(prefix):
                    return value[len(prefix):].lstrip("\/")
            return value
        if isinstance(value, list):
            return [portable(v) for v in value]
        if isinstance(value, dict):
            return {k: portable(v) for k, v in value.items()}
        return value
    for json_path in OUT.rglob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            json_path.write_text(json.dumps(portable(data), ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass
    print(json.dumps(result["gate"], ensure_ascii=False, indent=2))
    print(f"contact: {OUT / 'contact.png'}")
    return 0 if result["gate"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

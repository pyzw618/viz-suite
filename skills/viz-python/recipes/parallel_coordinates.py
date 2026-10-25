# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：多维平行坐标图（方向统一 + 组均值粗线 + 右侧直接标注）。

    uv run parallel_coordinates.py --json
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
CLASS_COL = "组别"
DIMENSIONS = ["准确率", "召回率", "F1", "推理时延", "内存占用", "稳定性"]
LOWER_IS_BETTER = ["推理时延", "内存占用"]
CLASS_ORDER = None
PALETTE = None
LAYOUT = "minimal_axis"
TITLE = "干预 B 在准确率与 F1 上领先，但推理时延与内存占用更高"
SUBTITLE = "每条线为样本，粗线为组均值｜时延/内存已反转方向"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.60
CITE_MM = None
OUTDIR = "outputs"
STEM = "parallel_coordinates"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    specs = {
        "对照组": [0.82, 0.78, 0.80, 45, 320, 0.90],
        "干预 A": [0.85, 0.80, 0.82, 52, 340, 0.88],
        "干预 B": [0.89, 0.84, 0.86, 68, 410, 0.86],
    }
    jitter = [0.015, 0.015, 0.012, 3.0, 18.0, 0.012]
    rows = []
    for name, centers in specs.items():
        for _ in range(20):
            row = {CLASS_COL: name}
            for dim, center, sd in zip(DIMENSIONS, centers, jitter):
                row[dim] = round(float(rng.normal(center, sd)), 4)
            rows.append(row)
    return pd.DataFrame(rows)


def read_table(path, sheet=None) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, sheet_name=sheet or 0)
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="latin-1")


def deoverlap(values: list[float], gap: float, low: float, high: float) -> list[float]:
    pairs = sorted(enumerate(values), key=lambda p: p[1])
    adjusted = []
    for _, value in pairs:
        if adjusted and value - adjusted[-1] < gap:
            value = adjusted[-1] + gap
        adjusted.append(value)
    shift = max(0.0, adjusted[-1] - high) if adjusted else 0.0
    if shift:
        adjusted = [v - shift for v in adjusted]
    if adjusted and adjusted[0] < low:
        delta = low - adjusted[0]
        adjusted = [v + delta for v in adjusted]
    out = [0.0] * len(values)
    for (idx, _), value in zip(pairs, adjusted):
        out[idx] = value
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="多维平行坐标图")
    ap.add_argument("--data", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--stem", default=None)
    ap.add_argument("--palette", default=None)
    ap.add_argument("--layout", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    global DATA_PATH, OUTDIR, STEM, PALETTE, LAYOUT
    if args.data:
        DATA_PATH = args.data
    if args.outdir:
        OUTDIR = args.outdir
    if args.stem:
        STEM = args.stem
    if args.palette:
        PALETTE = args.palette
    if args.layout:
        LAYOUT = args.layout

    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "figure": {"recipe": "parallel_coordinates"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        if CLASS_COL not in df.columns:
            raise ValueError(f"缺少组别列「{CLASS_COL}」；现有列：{list(df.columns)}")
        dims = [d for d in DIMENSIONS if d in df.columns]
        if len(dims) < 3:
            raise ValueError(f"至少需要 3 个数值维度；现有列：{list(df.columns)}")
        for dim in dims:
            df[dim] = pd.to_numeric(df[dim], errors="coerce")
        dropped = int(df[[CLASS_COL] + dims].isna().any(axis=1).sum())
        df = df.dropna(subset=[CLASS_COL] + dims)
        if df.empty:
            raise ValueError("清洗后数据为空")
        classes = CLASS_ORDER or list(dict.fromkeys(df[CLASS_COL].astype(str).tolist()))

        # 统一方向：数值越大越“好”；反向维度做 1 - 归一化
        normalized = df.copy()
        raw_stats = {}
        for dim in dims:
            values = df[dim].to_numpy(dtype=float)
            lo, hi = float(values.min()), float(values.max())
            raw_stats[dim] = (lo, hi)
            span = hi - lo if hi > lo else 1.0
            z = (values - lo) / span
            if dim in LOWER_IS_BETTER:
                z = 1.0 - z
            normalized[dim] = z

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        colors = vs.series_color_map([str(c) for c in classes], pal, theme)
        warnings.extend(size["notes"])

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(axis="both", length=0)
        xpos = np.arange(len(dims), dtype=float)

        for _, row in normalized.iterrows():
            cls = str(row[CLASS_COL])
            ax.plot(xpos, [row[d] for d in dims], color=colors[cls], alpha=0.26,
                    linewidth=0.8, zorder=2)

        means = []
        for cls in classes:
            sub = normalized[normalized[CLASS_COL].astype(str) == cls]
            mean_values = [float(sub[d].mean()) for d in dims]
            means.append((cls, mean_values))
            ax.plot(xpos, mean_values, color=colors[cls], linewidth=2.4, zorder=5,
                    solid_capstyle="round")

        for x, dim in zip(xpos, dims):
            ax.axvline(x, color=theme["colors"]["roles"]["grid"], linewidth=0.8, zorder=1)
            lo, hi = raw_stats[dim]
            if dim in LOWER_IS_BETTER:
                lo, hi = hi, lo
            fmt = "{:.3f}" if max(abs(lo), abs(hi)) < 10 else "{:.0f}"
            ax.text(x, 0.965, fmt.format(hi), ha="center", va="bottom",
                    fontsize=vs.font_size(theme, "source"),
                    color=theme["colors"]["roles"]["muted_text"], zorder=6)
            ax.text(x, 0.02, fmt.format(lo), ha="center", va="top",
                    fontsize=vs.font_size(theme, "source"),
                    color=theme["colors"]["roles"]["muted_text"], zorder=6)

        ax.set_xticks(xpos)
        ax.set_xticklabels(dims)
        ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, pad=12)
        ax.set_yticks([])
        ax.set_ylim(-0.02, 1.02)
        ax.set_xlim(-0.12, len(dims) - 1 + 1.15)

        label_x = len(dims) - 1 + 0.10
        ys = [mean_values[-1] for _, mean_values in means]
        adjusted = deoverlap(ys, 0.09, 0.03, 0.97) if ys else []
        for (cls, _), y in zip(means, adjusted):
            ax.text(label_x, y, cls, ha="left", va="center", fontsize=vs.font_size(theme, "annotation"),
                    color=colors[cls], fontweight="bold", clip_on=False)

        fig.text(0.015, 0.965, TITLE, ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"), color=theme["colors"]["roles"]["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"),
                 color=theme["colors"]["roles"]["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.055, right=0.86, top=0.735, bottom=0.12)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = df.copy()
        for dim in dims:
            export[f"{dim}_norm"] = normalized[dim].round(4)
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "parallel_coordinates", "dimensions": dims,
                       "inverted": [d for d in dims if d in LOWER_IS_BETTER],
                       "classes": classes, "palette": pal.id, "layout": LAYOUT,
                       "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "visual_verified": False,
                       "note": "脚本只验证文件生成；审美与可读性须由 viz-audit / ViewImage 复核"},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：消融阶梯瀑布 + 增益色带（基线 → 各模块 → 完整模型）。

    uv run waterfall_ablation.py --json
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
STEP_COL = "模块"
DELTA_COL = "增益"
BASELINE_VALUE = 61.0
BASELINE_LABEL = "基线模型"
FINAL_LABEL = "完整模型"
Y_LABEL = "综合得分（0–100）"
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "注意力模块贡献最大，四项改进累计提升 21.1 分"
SUBTITLE = "浮动块为各模块增益｜纵轴从 0 开始｜虚线为基线与最终水平"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.62
CITE_MM = None
OUTDIR = "outputs"
STEM = "waterfall_ablation"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [("注意力模块", 8.5), ("多尺度特征", 6.2), ("数据增强", 4.1), ("正则化", 2.3)]
    return pd.DataFrame(rows, columns=[STEP_COL, DELTA_COL])


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


def main() -> int:
    ap = argparse.ArgumentParser(description="消融阶梯瀑布")
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
              "verified": False, "warnings": [], "figure": {"recipe": "waterfall_ablation"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (STEP_COL, DELTA_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[DELTA_COL] = pd.to_numeric(df[DELTA_COL], errors="coerce")
        dropped = int(df[[STEP_COL, DELTA_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[STEP_COL, DELTA_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")

        steps = df[STEP_COL].astype(str).tolist()
        deltas = df[DELTA_COL].to_numpy(dtype=float)
        final_value = float(BASELINE_VALUE + deltas.sum())

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        n = len(steps)
        xpos = np.arange(n + 2, dtype=float)
        bar_w = 0.62

        # 基线柱
        ax.bar(0, BASELINE_VALUE, width=bar_w, color=roles["context"], edgecolor=roles["text"],
               linewidth=0.9, zorder=3)
        ax.text(0, BASELINE_VALUE + 0.8, f"{BASELINE_VALUE:.1f}", ha="center", va="bottom",
                fontsize=vs.font_size(theme, "annotation"), color=roles["text"])
        ax.plot([0.31, 0.69], [BASELINE_VALUE, BASELINE_VALUE], color=roles["muted_text"],
                linestyle=":", linewidth=0.8, zorder=4)

        cumulative = float(BASELINE_VALUE)
        for i, (step, delta) in enumerate(zip(steps, deltas), start=1):
            start = cumulative
            end = cumulative + float(delta)
            bottom = min(start, end)
            height = abs(float(delta))
            color = roles["positive"] if delta >= 0 else roles["negative"]
            ax.bar(i, height, bottom=bottom, width=bar_w,
                   **vs.bar_kwargs(color, theme=theme), zorder=3)
            label_y = max(start, end) + 0.9
            ax.text(i, label_y, f"{delta:+.1f}", ha="center", va="bottom",
                    fontsize=vs.font_size(theme, "annotation"), color=color)
            ax.plot([i + 0.31, i + 1 - 0.31], [end, end], color=roles["muted_text"],
                    linestyle=":", linewidth=0.8, zorder=4)
            cumulative = end

        # 完整模型柱
        ax.bar(n + 1, cumulative, width=bar_w, color=roles["focal"], edgecolor=roles["focal"],
               linewidth=0.9, zorder=3)
        ax.text(n + 1, cumulative + 0.8, f"{cumulative:.1f}", ha="center", va="bottom",
                fontsize=vs.font_size(theme, "annotation"), color=roles["text"])

        # 增益色带与基/终虚线
        ax.axhspan(BASELINE_VALUE, final_value, color=roles["positive"], alpha=0.055, zorder=0)
        ax.axhline(BASELINE_VALUE, color=roles["muted_text"], linestyle="--", linewidth=0.8, zorder=1)
        ax.axhline(final_value, color=roles["muted_text"], linestyle="--", linewidth=0.8, zorder=1)
        gain_total = final_value - BASELINE_VALUE
        ax.text(0.5, final_value + (final_value - BASELINE_VALUE) * 0.55,
                f"总增益 {gain_total:+.1f}", ha="left", va="center",
                fontsize=vs.font_size(theme, "annotation"), color=roles["positive"],
                bbox=dict(facecolor="#FFFFFF", edgecolor="none", alpha=0.85, pad=1.0))

        ax.set_xticks(xpos)
        ax.set_xticklabels([BASELINE_LABEL] + steps + [FINAL_LABEL])
        ax.set_ylabel(Y_LABEL)
        ax.set_xlim(-0.6, n + 1.6)
        ax.set_ylim(0, max(cumulative, BASELINE_VALUE) * 1.22)
        vs.ensure_zero_baseline(ax, "y")
        ax.yaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.35)
        ax.xaxis.grid(False)

        fig.text(0.015, 0.965, TITLE, ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"), color=roles["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"), color=roles["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.09, right=0.97, top=0.80, bottom=0.16)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = df.copy()
        export["cumulative"] = (BASELINE_VALUE + np.cumsum(deltas)).round(4)
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "waterfall_ablation", "baseline": BASELINE_VALUE,
                       "final": round(cumulative, 3), "gain_total": round(gain_total, 3),
                       "steps": steps, "layout": LAYOUT,
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

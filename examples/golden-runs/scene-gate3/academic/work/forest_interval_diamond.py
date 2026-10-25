# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：多指标点区间 + 汇总菱形森林图（对数刻度）。

    uv run forest_interval_diamond.py --json
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
from matplotlib.patches import Polygon

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = "../forest_data.csv"
SHEET = None
LABEL_COL = "研究"
EST_COL = "估计值"
LOW_COL = "下限"
HIGH_COL = "上限"
KIND_COL = "类型"
WEIGHT_COL = "权重"
NULL_VALUE = 0.0
LOG_SCALE = False
X_LABEL = "B − A 转化率差（百分点，95% CI）"
PALETTE = None
LAYOUT = "clean_open"
TITLE = ""
SUBTITLE = ""
SOURCE = "数据来源：经营实验数据（合成）｜n=28,812｜误差线=95% CI"
WIDTH_MM = 183
ASPECT = 0.58
CITE_MM = None
OUTDIR = "../outputs"
STEM = "fig-ab-conversion"
FORMATS = ("pdf", "svg", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        ("研究 A", 0.82, 0.65, 1.03, "study"),
        ("研究 B", 0.75, 0.58, 0.97, "study"),
        ("研究 C", 1.05, 0.80, 1.38, "study"),
        ("研究 D", 0.68, 0.52, 0.89, "study"),
        ("研究 E", 0.91, 0.70, 1.18, "study"),
        ("研究 F", 0.79, 0.60, 1.04, "study"),
        ("研究 G", 0.72, 0.55, 0.94, "study"),
        ("汇总", 0.79, 0.70, 0.89, "summary"),
    ]
    return pd.DataFrame(rows, columns=[LABEL_COL, EST_COL, LOW_COL, HIGH_COL, KIND_COL])


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
    ap = argparse.ArgumentParser(description="森林图 + 汇总菱形")
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
              "verified": False, "warnings": [], "figure": {"recipe": "forest_interval_diamond"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (LABEL_COL, EST_COL, LOW_COL, HIGH_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        for col in (EST_COL, LOW_COL, HIGH_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[LABEL_COL, EST_COL, LOW_COL, HIGH_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[LABEL_COL, EST_COL, LOW_COL, HIGH_COL])
        invalid = df[(df[LOW_COL] > df[EST_COL]) | (df[EST_COL] > df[HIGH_COL])]
        if len(invalid):
            warnings.append(f"{len(invalid)} 行区间不含估计值，已剔除：{invalid[LABEL_COL].tolist()}")
            dropped += len(invalid)
            df = df.drop(invalid.index)
        if LOG_SCALE:
            bad = df[(df[LOW_COL] <= 0) | (df[EST_COL] <= 0) | (df[HIGH_COL] <= 0)]
            if len(bad):
                warnings.append(f"{len(bad)} 行含非正值，无法用于对数刻度，已剔除")
                dropped += len(bad)
                df = df.drop(bad.index)
        if df.empty:
            raise ValueError("清洗后没有可用行")

        kind = (df[KIND_COL].astype(str).str.lower() if KIND_COL in df.columns
                else pd.Series(["study"] * len(df), index=df.index))
        is_summary = kind.isin(["summary", "汇总", "合并", "pooled"]) | df[LABEL_COL].astype(str).str.contains("汇总|合并")
        studies = df[~is_summary].reset_index(drop=True)
        summary = df[is_summary].head(1)
        if summary.empty:
            warnings.append("未找到汇总行（类型=summary/汇总）；只绘制单项研究")
        if len(df[is_summary]) > 1:
            warnings.append("存在多个汇总行，仅使用第一个")

        if WEIGHT_COL in studies.columns:
            weights = pd.to_numeric(studies[WEIGHT_COL], errors="coerce").to_numpy(dtype=float)
            if len(weights) != len(studies) or np.isnan(weights).any():
                weights = None
        else:
            weights = None
        if weights is None:
            se = (np.log(studies[HIGH_COL]) - np.log(studies[LOW_COL])) / 3.92 if LOG_SCALE else \
                 (studies[HIGH_COL] - studies[LOW_COL]) / 3.92
            weights = 1.0 / np.maximum(se.to_numpy(dtype=float) ** 2, 1e-12)
        sizes = 28 + 92 * (weights / max(weights.max(), 1e-9))

        theme = vs.resolve_theme()
        # 学术场景：单栏 89 mm 下压缩到 6–8 pt，并关闭背景网格
        theme.setdefault("typography", {}).setdefault("size_pt", {}).update({
            "title": 8.0, "subtitle": 7.5, "axis_label": 7.0, "tick": 6.5,
            "legend": 6.5, "annotation": 6.0, "source": 6.0, "panel_label": 9.0,
        })
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.yaxis.grid(False)
        ax.xaxis.grid(False)
        n = len(studies)
        summary_y = n + 0.9
        for i in range(n):
            if i % 2 == 0:
                ax.axhspan(i - 0.5, i + 0.5, color=roles["grid"], alpha=0.20, zorder=0)

        for i, row in studies.iterrows():
            ax.plot([row[LOW_COL], row[HIGH_COL]], [i, i], color=roles["text"], linewidth=1.1,
                    solid_capstyle="butt", zorder=3)
            ax.plot([row[LOW_COL], row[LOW_COL]], [i - 0.09, i + 0.09], color=roles["text"],
                    linewidth=1.0, zorder=3)
            ax.plot([row[HIGH_COL], row[HIGH_COL]], [i - 0.09, i + 0.09], color=roles["text"],
                    linewidth=1.0, zorder=3)
            ax.scatter([row[EST_COL]], [i], s=float(sizes[i]), marker="s", color=roles["focal"],
                       edgecolor="#FFFFFF", linewidth=0.6, zorder=4)
            ax.text(1.02, i, f"{row[EST_COL]:.2f} [{row[LOW_COL]:.2f}, {row[HIGH_COL]:.2f}]",
                    transform=ax.get_yaxis_transform(), ha="left", va="center",
                    fontsize=vs.font_size(theme, "annotation"), color=roles["muted_text"])

        summary_stats = {}
        if not summary.empty:
            row = summary.iloc[0]
            low, est, high = float(row[LOW_COL]), float(row[EST_COL]), float(row[HIGH_COL])
            summary_stats = {"summary_est": est, "summary_low": low, "summary_high": high}
            diamond = Polygon([[low, summary_y], [est, summary_y + 0.28],
                               [high, summary_y], [est, summary_y - 0.28]],
                              closed=True, facecolor=roles["focal"], edgecolor=roles["focal"],
                              alpha=0.28, linewidth=1.0, zorder=4)
            ax.add_patch(diamond)
            ax.text(1.02, summary_y, f"{est:.2f} [{low:.2f}, {high:.2f}]",
                    transform=ax.get_yaxis_transform(), ha="left", va="center",
                    fontsize=vs.font_size(theme, "annotation"), color=roles["focal"],
                    fontweight="bold")

        ax.axvline(NULL_VALUE, color=roles["muted_text"], linestyle="--", linewidth=0.9, zorder=2)
        ax.text(NULL_VALUE, -0.62, f"无效线 = {NULL_VALUE:g}", ha="center", va="bottom",
                fontsize=vs.font_size(theme, "source"), color=roles["muted_text"])
        ticks = [0.5, 0.75, 1.0, 1.5, 2.0] if LOG_SCALE else None
        if LOG_SCALE:
            ax.set_xscale("log")
            valid_ticks = [t for t in ticks if 0 < t]
            lo = min(float(df[LOW_COL].min()), NULL_VALUE) * 0.85
            hi = max(float(df[HIGH_COL].max()), NULL_VALUE) * 1.25
            ax.set_xlim(lo, hi)
            ax.set_xticks(valid_ticks)
            ax.set_xticklabels([f"{t:g}" for t in valid_ticks])
            ax.xaxis.set_minor_formatter(plt.NullFormatter())
        ax.set_yticks(list(range(n)) + ([summary_y] if not summary.empty else []))
        ax.set_yticklabels(studies[LABEL_COL].astype(str).tolist()
                           + ([str(summary.iloc[0][LABEL_COL])] if not summary.empty else []))
        ax.set_ylim(-0.8, summary_y + 0.8)
        ax.invert_yaxis()
        if not summary.empty:
            tick_labels = ax.get_yticklabels()
            if tick_labels:
                tick_labels[-1].set_fontweight("bold")
        ax.set_xlabel(X_LABEL)

        if TITLE:
            title = vs.fill_title(TITLE, **summary_stats) if summary_stats else "多指标效应量与 95% 置信区间"
            fig.text(0.015, 0.965, title, ha="left", va="top", fontweight="bold",
                     fontsize=vs.font_size(theme, "title"), color=roles["text"])
        if SUBTITLE:
            fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                     fontsize=vs.font_size(theme, "subtitle"), color=roles["muted_text"])
        vs.panel_label(ax, "a", theme=theme, x=-0.34, y=1.04)
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.245, right=0.735, top=0.94, bottom=0.18)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        df.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(studies)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "forest_interval_diamond", "studies": n,
                       "summary": summary_stats, "null": NULL_VALUE,
                       "palette": pal.id, "layout": LAYOUT,
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

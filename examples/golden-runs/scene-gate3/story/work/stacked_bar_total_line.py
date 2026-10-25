# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：堆叠柱 + 总量折线（构成与总量同轴融合）。

    uv run stacked_bar_total_line.py --json
    uv run stacked_bar_total_line.py --data data.csv --json
"""
import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = "../data/channel_month_long.csv"
SHEET = None
X_COL = "月份"
SERIES_COL = "渠道"
VALUE_COL = "收入"
X_LABEL = "月份"
VALUE_LABEL = "收入（万元）"
SERIES_ORDER = ["电商", "门店", "私域", "直播"]
SORT_X = True
PALETTE = None
LAYOUT = None
TITLE = "直播从 12% 升至 33%，贡献了上半年新增收入的三分之二"
SUBTITLE = "堆叠柱为各渠道收入｜灰色=非焦点渠道｜单位：万元"
SOURCE = "数据来源：经营分析部 2025 年 1–6 月月报（合成）｜假设：确认收入；增量=6 月−1 月"
WIDTH_MM = 254
ASPECT = 0.5625
CITE_MM = None
SHOW_TOTAL = True
ANNOTATE_TOTAL = True
OUTDIR = "../outputs"
STEM = "story-revenue-shift"
FORMATS = ("svg", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def natural_key(value):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(value))]


def demo_frame() -> pd.DataFrame:
    months = ["1月", "2月", "3月", "4月", "5月", "6月"]
    series = {
        "产品线 A": [42, 45, 48, 52, 55, 58],
        "产品线 B": [28, 30, 29, 33, 35, 37],
        "产品线 C": [15, 18, 20, 21, 24, 26],
    }
    rows = []
    for month in months:
        for name, values in series.items():
            rows.append({X_COL: month, SERIES_COL: name, VALUE_COL: values[months.index(month)]})
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


def main() -> int:
    ap = argparse.ArgumentParser(description="堆叠柱 + 总量折线")
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
              "verified": False, "warnings": [], "figure": {"recipe": "stacked_bar_total_line"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (X_COL, SERIES_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[X_COL, SERIES_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[X_COL, SERIES_COL, VALUE_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")
        if dropped:
            warnings.append(f"{dropped} 行因缺失被剔除")

        x_values = list(dict.fromkeys(df[X_COL].tolist()))
        if SORT_X:
            try:
                x_values = sorted(x_values, key=natural_key)
            except TypeError:
                pass
        series = SERIES_ORDER or list(dict.fromkeys(df[SERIES_COL].tolist()))
        pivot = (df.pivot_table(index=X_COL, columns=SERIES_COL, values=VALUE_COL, aggfunc="sum")
                   .reindex(index=x_values, columns=series).fillna(0.0))

        theme = vs.resolve_theme()
        # 汇报叙事：投影安全字号；标题约为正文 1.5×
        theme.setdefault("typography", {}).setdefault("size_pt", {}).update({
            "title": 17.0, "subtitle": 13.0, "axis_label": 11.5, "tick": 10.5,
            "legend": 10.5, "annotation": 10.5, "source": 10.5,
        })
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        if len(series) > pal.safe_k:
            warnings.append(f"系列数 {len(series)} 超过色板 {pal.id} 的 safe_k={pal.safe_k}，建议合并小类")
        colors = vs.series_color_map([str(s) for s in series], pal, theme)
        warnings.extend(size["notes"])

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        xpos = np.arange(len(x_values), dtype=float)
        bottom = np.zeros(len(x_values))
        bar_w = 0.62
        for name in series:
            values = pivot[name].to_numpy(dtype=float)
            ax.bar(xpos, values, bottom=bottom, width=bar_w,
                   zorder=3, **vs.bar_kwargs(colors[str(name)], theme=theme))
            bottom += values

        if SHOW_TOTAL:
            total = pivot.sum(axis=1).to_numpy(dtype=float)
            ax.plot(xpos, total, color=theme["colors"]["roles"]["text"], linewidth=1.5,
                    marker="o", markersize=4.2, markerfacecolor="#FFFFFF",
                    markeredgecolor=theme["colors"]["roles"]["text"],
                    markeredgewidth=1.0, zorder=5)
            if ANNOTATE_TOTAL:
                for x, value in zip(xpos, total):
                    ax.annotate(f"{value:,.0f}", (x, value), xytext=(0, 6),
                                textcoords="offset points", ha="center", va="bottom",
                                fontsize=vs.font_size(theme, "annotation"),
                                color=theme["colors"]["roles"]["muted_text"])

        ax.set_xticks(xpos)
        ax.set_xticklabels([str(v) for v in x_values])
        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(VALUE_LABEL)
        ymax = float(bottom.max()) if len(bottom) else 1.0
        ax.set_ylim(0, ymax * 1.20)
        vs.ensure_zero_baseline(ax, "y")
        ax.set_xlim(-0.6, len(x_values) - 0.4)

        handles = [Patch(facecolor=vs.blend(colors[str(s)], theme["colors"]["backgrounds"]["white"],
                                            theme["marks"]["fill_alpha"]),
                         edgecolor=colors[str(s)], linewidth=theme["marks"]["edge_width"])
                   for s in series]
        if SHOW_TOTAL:
            handles.append(plt.Line2D([0], [0], color=theme["colors"]["roles"]["text"],
                                      marker="o", markersize=4, markerfacecolor="white",
                                      markeredgecolor=theme["colors"]["roles"]["text"],
                                      linewidth=1.5, label="总量"))
        labels = [str(s) for s in series] + (["总量"] if SHOW_TOTAL else [])
        leg = ax.legend(handles, labels, loc="lower right", bbox_to_anchor=(1.0, 1.005),
                        ncol=len(labels), frameon=False, handlelength=1.1,
                        columnspacing=1.2, handletextpad=0.5,
                        fontsize=vs.font_size(theme, "legend"))
        vs.style_legend(leg, theme)

        fig.text(0.015, 0.965, TITLE, ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"), color=theme["colors"]["roles"]["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"),
                 color=theme["colors"]["roles"]["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.09, right=0.975, top=0.80, bottom=0.15)
        if "直播" in pivot.columns:
            live = pivot["直播"].to_numpy(dtype=float)
            base = bottom - live
            idx = len(x_values) - 1
            ax.text(0.012, 0.965,
                    f"6 月直播 {live[idx]:,.0f} 万元（占比 {live[idx] / bottom[idx]:.1%}）",
                    transform=ax.transAxes, ha="left", va="top",
                    fontsize=vs.font_size(theme, "annotation"), fontweight="bold",
                    color=theme["colors"]["roles"]["focal"])

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = pivot.copy()
        export["total"] = pivot.sum(axis=1)
        export.to_csv(data_path, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "stacked_bar_total_line", "x": [str(v) for v in x_values],
                       "series": [str(s) for s in series], "palette": pal.id, "layout": LAYOUT,
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

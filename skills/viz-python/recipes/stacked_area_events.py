# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：堆叠面积 + 事件竖线。

    uv run stacked_area_events.py --json
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
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
X_COL = "月份"
SERIES_COL = "渠道"
VALUE_COL = "访问量"
SERIES_ORDER = None
EVENTS = [
    {"x": "2024-04", "label": "直播改版"},
    {"x": "2024-11", "label": "双十一"},
    {"x": "2025-03", "label": "投放提效"},
    {"x": "2025-06", "label": "618 大促"},
]
X_LABEL = "月份"
VALUE_LABEL = "访问量（万次）"
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "直播改版与大促叠加，总量在 11 月与 6 月形成双峰"
SUBTITLE = "堆叠面积为三类渠道访问量｜虚线标注关键事件"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.60
CITE_MM = None
OUTDIR = "outputs"
STEM = "stacked_area_events"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    months = [f"2024-{m:02d}" for m in range(1, 13)] + [f"2025-{m:02d}" for m in range(1, 13)]
    n = len(months)
    rng = np.random.default_rng(DEMO_SEED)
    base = {"自然流量": 42, "付费投放": 24, "直播": 6}
    slope = {"自然流量": 0.25, "付费投放": 0.55, "直播": 1.05}
    rows = []
    for i, month in enumerate(months):
        spike = 0.0
        if month in ("2024-11", "2025-06"):
            spike = 18.0
        elif month in ("2024-06", "2024-12"):
            spike = 6.0
        for name, start in base.items():
            value = start + slope[name] * i + (spike if name != "自然流量" else spike * 0.35)
            value += rng.normal(0, 1.6)
            rows.append({X_COL: month, SERIES_COL: name, VALUE_COL: max(1.0, round(float(value), 2))})
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
    ap = argparse.ArgumentParser(description="堆叠面积 + 事件竖线")
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
              "verified": False, "warnings": [], "figure": {"recipe": "stacked_area_events"}}
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

        x_values = list(dict.fromkeys(df[X_COL].tolist()))
        series = SERIES_ORDER or list(dict.fromkeys(df[SERIES_COL].tolist()))
        pivot = (df.pivot_table(index=X_COL, columns=SERIES_COL, values=VALUE_COL, aggfunc="sum")
                   .reindex(index=x_values, columns=series).fillna(0.0))

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        colors = vs.series_color_map([str(s) for s in series], pal, theme)
        warnings.extend(size["notes"])

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        xpos = np.arange(len(x_values), dtype=float)
        cumulative = np.zeros(len(x_values))
        for name in series:
            values = pivot[name].to_numpy(dtype=float)
            color = colors[str(name)]
            ax.fill_between(xpos, cumulative, cumulative + values, color=color, alpha=0.20,
                            linewidth=0, zorder=2)
            ax.plot(xpos, cumulative + values, color=color, linewidth=0.9, zorder=3)
            cumulative += values

        total_max = float(cumulative.max()) if len(cumulative) else 1.0
        ax.set_ylim(0, total_max * 1.28)
        vs.ensure_zero_baseline(ax, "y")
        ax.set_xlim(-0.4, len(x_values) - 0.6)

        event_y = [0.965, 0.885]
        for i, event in enumerate(EVENTS):
            if event["x"] not in x_values:
                warnings.append(f"事件「{event['label']}」的 x={event['x']} 不在数据中，已跳过")
                continue
            x = float(x_values.index(event["x"]))
            ax.axvline(x, color=theme["colors"]["roles"]["muted_text"], linestyle=":",
                       linewidth=0.9, zorder=1)
            ax.text(x, event_y[i % len(event_y)], event["label"], transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=vs.font_size(theme, "annotation"),
                    color=theme["colors"]["roles"]["text"],
                    bbox=dict(facecolor="#FFFFFF", edgecolor=theme["colors"]["roles"]["grid"],
                              linewidth=0.5, boxstyle="round,pad=0.25"))

        step = max(1, len(x_values) // 8)
        ticks = list(range(0, len(x_values), step))
        ax.set_xticks([xpos[i] for i in ticks])
        ax.set_xticklabels([str(x_values[i]) for i in ticks])
        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(VALUE_LABEL)

        handles = [Patch(facecolor=vs.blend(colors[str(s)], "#FFFFFF", 0.20),
                         edgecolor=colors[str(s)], linewidth=0.8) for s in series]
        leg = ax.legend(handles, [str(s) for s in series], loc="lower right",
                        bbox_to_anchor=(1.0, 1.005), ncol=len(series), frameon=False,
                        handlelength=1.1, columnspacing=1.2, handletextpad=0.5,
                        fontsize=vs.font_size(theme, "legend"))
        vs.style_legend(leg, theme)

        fig.text(0.015, 0.965, TITLE, ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"), color=theme["colors"]["roles"]["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"),
                 color=theme["colors"]["roles"]["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.09, right=0.975, top=0.80, bottom=0.15)

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
            "figure": {"recipe": "stacked_area_events", "series": [str(s) for s in series],
                       "events": EVENTS, "palette": pal.id, "layout": LAYOUT,
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

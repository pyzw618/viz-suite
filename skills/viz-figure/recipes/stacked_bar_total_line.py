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
DATA_PATH = None
SHEET = None
X_COL = "月份"
SERIES_COL = "产品线"
VALUE_COL = "收入"
X_LABEL = "月份"
VALUE_LABEL = "收入（万元）"
SERIES_ORDER = None
SORT_X = True
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "产品线 A 贡献最大，总量在 6 月达到峰值"
SUBTITLE = "堆叠柱为各产品线收入，折线为当月总量"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.60
CITE_MM = None
SHOW_TOTAL = True
ANNOTATE_TOTAL = True
OUTDIR = "outputs"
STEM = "stacked_bar_total_line"
FORMATS = ("pdf", "png")
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
    ap.add_argument("--scene", default=None, choices=["academic", "bi", "story", "geo"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    global DATA_PATH, OUTDIR, STEM, PALETTE, LAYOUT, SCENE, WIDTH_MM, ASPECT
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
    if args.scene:
        SCENE = args.scene

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
        series = SERIES_ORDER or list(dict.fromkeys(df[SERIES_COL].tolist()))
        pivot = (df.pivot_table(index=X_COL, columns=SERIES_COL, values=VALUE_COL, aggfunc="sum")
                   .reindex(index=x_values, columns=series).fillna(0.0))
        if SORT_X == "total_desc":
            x_values = list(pivot.sum(axis=1).sort_values(ascending=False).index)
            pivot = pivot.reindex(index=x_values)
        elif SORT_X == "total_asc":
            x_values = list(pivot.sum(axis=1).sort_values(ascending=True).index)
            pivot = pivot.reindex(index=x_values)
        elif SORT_X:
            try:
                x_values = sorted(x_values, key=natural_key)
                pivot = pivot.reindex(index=x_values)
            except TypeError:
                pass

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme.get("scene_preset", {}).get("double_column_mm", 183) if (False and theme.get("scene") == "academic") else theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("economist_civic", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        if len(series) > pal.safe_k:
            warnings.append(f"系列数 {len(series)} 超过色板 {pal.id} 的 safe_k={pal.safe_k}，建议合并小类")
        colors = vs.series_color_map([str(s) for s in series], pal, theme)
        warnings.extend(size["notes"])

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        xpos = np.arange(len(x_values), dtype=float)
        bottom = np.zeros(len(x_values))
        total_vec = pivot.sum(axis=1).to_numpy(dtype=float)
        ymax_raw = float(total_vec.max()) if len(total_vec) else 1.0
        bar_w = 0.60
        for name in series:
            values = pivot[name].to_numpy(dtype=float)
            c_hex = colors[str(name)]
            bkw = vs.bar_kwargs(c_hex, theme=theme)
            ax.bar(xpos, values, bottom=bottom, width=bar_w, zorder=3, **bkw)
            # 在足够高的色段内部嵌入构成占比%，提升图表信息密度
            txt_col = vs.contrast_text(vs.mix("#FFFFFF", c_hex, 0.84), alpha=0.90)
            for idx_x, (val, btm, tot) in enumerate(zip(values, bottom, total_vec)):
                if tot > 0 and val >= 0.16 * ymax_raw and len(x_values) <= 10:
                    share = 100.0 * val / tot
                    ax.text(xpos[idx_x], btm + 0.5 * val, f"{share:.0f}%",
                            ha="center", va="center", fontsize=vs.font_size(theme, "source"),
                            fontweight="bold", color=txt_col, zorder=4)
            bottom += values

        if SHOW_TOTAL:
            total = total_vec
            ax.plot(xpos, total, color=theme["colors"]["roles"]["text"], linewidth=1.6,
                    marker="o", markersize=4.6, markerfacecolor="#FFFFFF",
                    markeredgecolor=theme["colors"]["roles"]["text"],
                    markeredgewidth=1.1, zorder=5)
            peak_i = int(np.argmax(total)) if len(total) else -1
            if ANNOTATE_TOTAL:
                for idx_x, (x, value) in enumerate(zip(xpos, total)):
                    if idx_x == peak_i and len(total) >= 2 and total[0] > 0:
                        growth = 100.0 * (value - total[0]) / abs(total[0])
                        vs.annotate_champion(ax, float(x), float(value),
                                             f"{value:,.0f} ({growth:+.0f}%)",
                                             color=colors[str(series[0])],
                                             offset_xy=(0, 10), theme=theme)
                    else:
                        ax.annotate(f"{value:,.0f}", (x, value), xytext=(0, 6),
                                    textcoords="offset points", ha="center", va="bottom",
                                    fontsize=vs.font_size(theme, "annotation"),
                                    color=theme["colors"]["roles"]["muted_text"])

        ax.set_xticks(xpos)
        ax.set_xticklabels([str(v) for v in x_values])
        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(VALUE_LABEL)
        ymax = float(bottom.max()) if len(bottom) else 1.0
        ax.set_ylim(0, ymax * 1.26)
        vs.ensure_zero_baseline(ax, "y")
        ax.set_xlim(-0.6, len(x_values) - 0.4)

        handles = []
        for s in series:
            bkw = vs.bar_kwargs(colors[str(s)], theme=theme)
            handles.append(Patch(facecolor=bkw["color"], edgecolor=bkw["edgecolor"], linewidth=bkw["linewidth"]))
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

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.09, right=0.975, top=0.80, bottom=0.15, theme=theme)

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
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit(), "visual_verified": False,
                       "note": "脚本已验证文件与文本包围盒；审美与可读性仍须经 audit_export 与宿主读图工具复核"},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

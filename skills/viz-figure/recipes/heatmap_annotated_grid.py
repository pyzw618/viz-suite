# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：双分类业务热力矩阵 + 顶/右均值边际条复合图（自动黑白对比文字 + 峰值高亮框）。

    uv run heatmap_annotated_grid.py --json
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
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
ROW_COL = "获客批次"
COL_COL = "留存周期"
VALUE_COL = "留存率"
TITLE = "{best_row} 在 {best_col} 保持最高活跃度（{best_val:.1f}%），近期批次首月留存稳步抬升"
SUBTITLE = "主矩阵展示精细数值与白边网格｜顶部与右侧边际条同步汇总各列/各行均值"
SOURCE = "数据来源：演示队列同期群 Cohort 留存分析表（合成）"
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
WIDTH_MM = 168
ASPECT = 0.66
CITE_MM = None
OUTDIR = "outputs"
STEM = "heatmap_annotated_grid"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    cohorts = ["2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]
    months = ["M+1", "M+2", "M+3", "M+4", "M+5", "M+6"]
    mat = [
        [68.2, 54.0, 46.5, 42.1, 39.4, 37.8],
        [71.5, 57.8, 49.2, 45.0, 42.6, 40.5],
        [74.0, 61.2, 53.6, 48.9, 46.1, 44.2],
        [76.8, 64.5, 56.8, 52.4, 49.5, 47.6],
        [79.4, 67.2, 59.5, 55.1, 52.0, 50.1],
        [82.6, 70.8, 63.4, 58.6, 55.4, 53.2],
    ]
    rows = []
    for r_i, ch in enumerate(cohorts):
        for c_i, m in enumerate(months):
            rows.append({ROW_COL: ch, COL_COL: m, VALUE_COL: mat[r_i][c_i]})
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
    ap = argparse.ArgumentParser(description="双分类业务热力矩阵 + 边际均值条")
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
              "verified": False, "warnings": [], "figure": {"recipe": "heatmap_annotated_grid"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (ROW_COL, COL_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df = df.copy()
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[ROW_COL, COL_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[ROW_COL, COL_COL, VALUE_COL])
        r_order = list(dict.fromkeys(df[ROW_COL].astype(str).tolist()))[:12]
        c_order = list(dict.fromkeys(df[COL_COL].astype(str).tolist()))[:12]
        piv = (df.assign(**{ROW_COL: df[ROW_COL].astype(str), COL_COL: df[COL_COL].astype(str)})
                 .pivot_table(index=ROW_COL, columns=COL_COL, values=VALUE_COL, aggfunc="mean")
                 .reindex(index=r_order, columns=c_order))
        mat = piv.to_numpy(dtype=float)

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene") and not args.layout:
            LAYOUT = theme.get("layout_family", LAYOUT)
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("met_hokusai2", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]
        base_col = pal.colors[-1] if pal.id.startswith("met_hokusai") else pal.colors[0]
        accent_col = "#D97706"

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(2, 2, height_ratios=[0.95, 3.8], width_ratios=[3.8, 1.15],
                              hspace=0.08, wspace=0.08)
        ax_top = fig.add_subplot(gs[0, 0])
        ax_corner = fig.add_subplot(gs[0, 1])
        ax = fig.add_subplot(gs[1, 0])
        ax_right = fig.add_subplot(gs[1, 1])

        vmin, vmax = float(np.nanmin(mat)), float(np.nanmax(mat))
        span = max(vmax - vmin, 1e-6)
        cmap = vs.sequential_cmap(base_col, light="#F8FAFC", light_mix=0.94)
        ax.imshow(mat, cmap=cmap, vmin=vmin - 0.05 * span, vmax=vmax, aspect="auto")

        nr, nc = mat.shape
        best_pos = np.unravel_index(int(np.nanargmax(mat)), mat.shape)
        for r in range(nr):
            for c in range(nc):
                val = mat[r, c]
                if np.isnan(val):
                    ax.text(c, r, "—", ha="center", va="center", color=roles["muted_text"])
                    continue
                norm_v = float(np.clip((val - (vmin - 0.05 * span)) / (1.05 * span), 0, 1))
                fill_hex = matplotlib.colors.to_hex(cmap(norm_v))
                txt_col = vs.contrast_text(fill_hex, alpha=1.0)
                ax.text(c, r, f"{val:.1f}", ha="center", va="center",
                        fontsize=vs.font_size(theme, "annotation"),
                        fontweight="bold" if (r, c) == best_pos else "normal", color=txt_col)

        ax.set_xticks(np.arange(nc + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(nr + 1) - 0.5, minor=True)
        ax.grid(which="minor", color="#FFFFFF", linestyle="-", linewidth=1.8)
        ax.tick_params(which="minor", bottom=False, left=False)
        ax.add_patch(Rectangle((best_pos[1] - 0.48, best_pos[0] - 0.48), 0.96, 0.96,
                               fill=False, edgecolor=accent_col, linewidth=2.0, zorder=5))
        ax.set_xticks(np.arange(nc))
        ax.set_xticklabels(c_order)
        ax.set_yticks(np.arange(nr))
        ax.set_yticklabels(r_order)
        ax.set_xlabel(COL_COL)
        ax.set_ylabel(ROW_COL)
        for sp in ax.spines.values():
            sp.set_visible(False)

        col_means = np.nanmean(mat, axis=0)
        row_means = np.nanmean(mat, axis=1)
        grand_mean = float(np.nanmean(mat))

        vs.apply_style(ax_top, "clean_open", theme=theme)
        ax_top.spines["left"].set_visible(False)
        ax_top.tick_params(axis="x", bottom=False, labelbottom=False)
        ax_top.tick_params(axis="y", left=False, labelleft=False)
        ax_top.bar(np.arange(nc), col_means, width=0.56, **vs.bar_kwargs(base_col, theme=theme))
        for i, v in enumerate(col_means):
            ax_top.text(i, v + vmax * 0.03, f"{v:.1f}", ha="center", va="bottom",
                        fontsize=vs.font_size(theme, "source"), color=roles["text"])
        ax_top.set_xlim(-0.5, nc - 0.5)
        ax_top.set_ylim(0, float(np.nanmax(col_means)) * 1.28)
        ax_top.set_title("列均值", loc="left", fontsize=vs.font_size(theme, "source"), color=roles["muted_text"], pad=2)

        vs.apply_style(ax_right, "clean_open", theme=theme)
        ax_right.spines["bottom"].set_visible(False)
        ax_right.tick_params(axis="x", bottom=False, labelbottom=False)
        ax_right.tick_params(axis="y", left=False, labelleft=False)
        ax_right.barh(np.arange(nr), row_means, height=0.56, **vs.bar_kwargs(base_col, theme=theme))
        for i, v in enumerate(row_means):
            ax_right.text(v + vmax * 0.03, i, f"{v:.1f}", va="center", ha="left",
                          fontsize=vs.font_size(theme, "source"), color=roles["text"])
        ax_right.set_ylim(nr - 0.5, -0.5)
        ax_right.set_xlim(0, float(np.nanmax(row_means)) * 1.35)
        ax_right.set_title("行均值", loc="left", fontsize=vs.font_size(theme, "source"), color=roles["muted_text"], pad=2)

        ax_corner.set_facecolor(vs.mix("#FFFFFF", base_col, 0.08))
        for sp in ax_corner.spines.values():
            sp.set_visible(True)
            sp.set_color(vs.mix("#FFFFFF", base_col, 0.40))
            sp.set_linewidth(0.75)
        ax_corner.set_xticks([])
        ax_corner.set_yticks([])
        ax_corner.text(0.5, 0.65, f"{grand_mean:.1f}", transform=ax_corner.transAxes,
                       ha="center", va="center", fontsize=vs.font_size(theme, "title"),
                       fontweight="bold", color=base_col)
        ax_corner.text(0.5, 0.25, "全表总均值", transform=ax_corner.transAxes,
                       ha="center", va="center", fontsize=vs.font_size(theme, "source"), color=roles["muted_text"])

        title = vs.fill_title(TITLE, best_row=r_order[best_pos[0]], best_col=c_order[best_pos[1]],
                              best_val=float(mat[best_pos]))
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        max_u = max(vs.display_units(r) for r in r_order)
        left = min(0.24, 0.075 + max_u * 0.011)
        vs.adjust_layout(fig, left=left, right=0.965, top=0.79, bottom=0.12, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        piv.to_csv(Path(OUTDIR) / f"{STEM}_matrix.csv", encoding="utf-8-sig")
        outputs.append(str(Path(OUTDIR) / f"{STEM}_matrix.csv"))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "heatmap_annotated_grid", "rows": r_order, "cols": c_order,
                       "grand_mean": round(grand_mean, 3), "palette": pal.id, "layout": LAYOUT,
                       "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit()},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

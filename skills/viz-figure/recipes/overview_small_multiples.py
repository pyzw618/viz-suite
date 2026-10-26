# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：全局总览 + 局部机理分面小多图（Overview + Small Multiples 旗舰双联图）。

    uv run overview_small_multiples.py --json
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
CATEGORY_COL = "行业大类"
TIME_COL = "季度"
VALUE_COL = "净利润率_pct"
TITLE = "{top1} 净利率达 {top1_val:.1f}% 居首，Top 4 赛道近三年走势分化加剧"
SUBTITLE = "(a) 全行业最新利润率横向总览与均值线｜(b) 头部四大核心赛道历史演化机理（小多图背景灰线为行业全景）"
X_LABEL_MAIN = "净利润率（%）"
SOURCE = "数据来源：演示行业横向与纵向复合成长数据库（合成）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
WIDTH_MM = 180
ASPECT = 0.54
CITE_MM = None
OUTDIR = "outputs"
STEM = "overview_small_multiples"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    periods = ["23Q1", "23Q2", "23Q3", "23Q4", "24Q1", "24Q2", "24Q3", "24Q4", "25Q1", "25Q2"]
    data = {
        "高端半导体": [24.5, 25.2, 26.8, 28.5, 29.4, 31.0, 32.5, 33.8, 34.2, 35.6],
        "生命科学仪器": [21.0, 21.8, 22.4, 23.0, 24.2, 24.8, 25.6, 26.5, 27.0, 27.8],
        "新能源智能车": [16.5, 17.2, 18.0, 19.5, 20.8, 21.4, 22.5, 23.4, 24.1, 25.2],
        "基础工业软件": [18.2, 18.0, 17.5, 18.4, 19.0, 19.8, 20.2, 21.0, 21.8, 22.5],
        "智慧电网储能": [15.2, 15.6, 16.0, 16.5, 17.0, 17.4, 18.0, 18.2, 18.5, 18.9],
        "精密激光加工": [13.4, 13.8, 14.1, 14.5, 14.8, 15.2, 15.5, 15.8, 16.0, 16.4],
        "工业机器人": [11.8, 12.0, 12.5, 12.8, 13.0, 13.4, 13.8, 14.0, 14.2, 14.5],
        "通用消费电子": [9.5, 9.2, 8.8, 8.5, 8.4, 8.2, 8.0, 7.8, 7.5, 7.2],
    }
    rows = []
    for cat, series in data.items():
        for t_idx, t in enumerate(periods):
            rows.append({CATEGORY_COL: cat, TIME_COL: t, VALUE_COL: series[t_idx]})
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
    ap = argparse.ArgumentParser(description="全局总览 + 局部机理分面小多图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "overview_small_multiples"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (CATEGORY_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df = df.copy()
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[CATEGORY_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[CATEGORY_COL, VALUE_COL])
        has_time = TIME_COL in df.columns
        if not has_time:
            df[TIME_COL] = "当前"

        times = list(dict.fromkeys(df[TIME_COL].astype(str).tolist()))
        last_t = times[-1]
        latest_df = df[df[TIME_COL].astype(str) == last_t].groupby(CATEGORY_COL, as_index=False)[VALUE_COL].mean()
        latest_df = latest_df.sort_values(VALUE_COL, ascending=False).reset_index(drop=True)
        categories = latest_df[CATEGORY_COL].astype(str).tolist()
        top4 = categories[:4]

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene") and not args.layout:
            LAYOUT = theme.get("layout_family", LAYOUT)
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("tol_bright", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]
        top_colors = vs.series_color_map(top4, pal, theme)

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.45], wspace=0.24)
        ax_main = fig.add_subplot(gs[0, 0])
        sub_gs = gs[0, 1].subgridspec(2, 2, hspace=0.28, wspace=0.20)
        axes_facet = [fig.add_subplot(sub_gs[r, c]) for r in (0, 1) for c in (0, 1)]

        # (a) 左侧全局总览横向条形
        vs.apply_style(ax_main, LAYOUT, theme=theme)
        ax_main.yaxis.grid(False)
        ax_main.xaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.35)
        n_c = len(categories)
        v_latest = latest_df[VALUE_COL].to_numpy(dtype=float)
        mean_v = float(v_latest.mean())
        ramp = vs.group_lightness_ramp(pal.colors[0], n_c, (0.45, 0.95), reverse=True)

        for i in range(n_c):
            cat_name = categories[i]
            col = top_colors[cat_name] if cat_name in top4 else ramp[i]
            ax_main.barh(i, v_latest[i], height=0.62, **vs.bar_kwargs(col, theme=theme), zorder=3)
            ax_main.text(v_latest[i] + float(v_latest.max()) * 0.02, i, f"{v_latest[i]:.1f}%",
                         va="center", ha="left", fontsize=vs.font_size(theme, "source"),
                         fontweight="bold" if i < 4 else "normal", color=roles["text"])

        ax_main.axvline(mean_v, color=roles["muted_text"], linestyle="--", linewidth=0.9, zorder=2.5)
        ax_main.text(mean_v, n_c - 0.45, f"均值 {mean_v:.1f}%", ha="left", va="bottom",
                     fontsize=vs.font_size(theme, "source"), color=roles["muted_text"])
        ax_main.set_yticks(list(range(n_c)))
        ax_main.set_yticklabels(categories)
        ax_main.set_ylim(-0.7, n_c - 0.3)
        ax_main.invert_yaxis()
        ax_main.set_xlim(0, float(v_latest.max()) * 1.25)
        ax_main.set_xlabel(X_LABEL_MAIN)
        ax_main.set_title("(a) 全行业利润率总览", loc="left",
                          fontsize=vs.font_size(theme, "axis_label"), fontweight="bold", pad=6)

        # (b) 右侧 2×2 分面小多图（突出核心，灰显全景）
        piv_all = (df.assign(**{CATEGORY_COL: df[CATEGORY_COL].astype(str), TIME_COL: df[TIME_COL].astype(str)})
                     .pivot_table(index=TIME_COL, columns=CATEGORY_COL, values=VALUE_COL, aggfunc="mean")
                     .reindex(index=times, columns=categories))
        t_xpos = np.arange(len(times))
        y_all_min = float(np.nanmin(piv_all.to_numpy())) * 0.90
        y_all_max = float(np.nanmax(piv_all.to_numpy())) * 1.10

        for f_idx, cat in enumerate(top4):
            fax = axes_facet[f_idx]
            vs.apply_style(fax, "clean_open", theme=theme)
            fax.xaxis.grid(False)
            fax.yaxis.grid(True, linestyle="--", linewidth=0.5, color=roles["grid"], alpha=0.3)
            # 背景灰线全景
            for c_other in categories:
                fax.plot(t_xpos, piv_all[c_other], color="#E2E8F0", linewidth=0.85, zorder=1.5)
            # 焦点序列加粗彩色
            f_col = top_colors[cat]
            f_vals = piv_all[cat].to_numpy(dtype=float)
            fax.plot(t_xpos, f_vals, color=f_col, linewidth=2.1, zorder=3.5)
            fax.scatter([t_xpos[-1]], [f_vals[-1]], s=24, color=f_col, edgecolor="#FFFFFF",
                        linewidth=0.8, zorder=4.0)
            fax.text(0.04, 0.90, f"{cat}\n{f_vals[-1]:.1f}%", transform=fax.transAxes,
                     ha="left", va="top", fontsize=vs.font_size(theme, "source"),
                     fontweight="bold", color=f_col)
            fax.set_ylim(y_all_min, y_all_max)
            fax.set_xlim(-0.3, len(times) - 0.7)
            if f_idx in (2, 3):
                step = max(1, len(times) // 3)
                fax.set_xticks(t_xpos[::step])
                fax.set_xticklabels([times[k] for k in range(0, len(times), step)],
                                    fontsize=vs.font_size(theme, "source") * 0.9)
            else:
                fax.tick_params(axis="x", labelbottom=False)
            if f_idx not in (0, 2):
                fax.tick_params(axis="y", labelleft=False)

        title = vs.fill_title(TITLE, top1=categories[0], top1_val=float(v_latest[0]))
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        max_u = max(vs.display_units(c) for c in categories)
        left = min(0.24, 0.075 + max_u * 0.011)
        vs.adjust_layout(fig, left=left, right=0.965, top=0.78, bottom=0.12, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        piv_all.to_csv(Path(OUTDIR) / f"{STEM}_data.csv", encoding="utf-8-sig")
        outputs.append(str(Path(OUTDIR) / f"{STEM}_data.csv"))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "overview_small_multiples", "top4": top4,
                       "palette": pal.id, "layout": LAYOUT,
                       "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit()},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

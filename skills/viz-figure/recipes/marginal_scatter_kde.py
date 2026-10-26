# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：散点回归 + 二维密度等高线 + 双边际核密度（共享轴多面板）。

    uv run marginal_scatter_kde.py --json
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
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
X_COL = "投入时长"
Y_COL = "产出评分"
GROUP_COL = "组别"
X_LABEL = "投入时长（小时）"
Y_LABEL = "产出评分（0–100）"
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
TITLE = "投入时长与产出正相关（R² = {r2:.2f}），高密度区沿对角线分布"
SUBTITLE = "主图：散点 + 二维密度等高线 + 线性拟合｜边际：核密度"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.72
CITE_MM = None
OUTDIR = "outputs"
STEM = "marginal_scatter_kde"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    rows = []
    for group, n, shift in (("组 A", 80, 0.0), ("组 B", 80, 4.0)):
        x = rng.normal(28, 8, n)
        y = 30 + 1.15 * x + shift + rng.normal(0, 5, n)
        for xi, yi in zip(x, y):
            rows.append({X_COL: round(float(xi), 2), Y_COL: round(float(np.clip(yi, 0, 100)), 2),
                         GROUP_COL: group})
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


def smooth2d(matrix: np.ndarray, sigma: float = 1.2) -> np.ndarray:
    radius = max(1, int(3 * sigma))
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    out = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), 0, matrix)
    out = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), 1, out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="散点回归 + 边际密度")
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
              "verified": False, "warnings": [], "figure": {"recipe": "marginal_scatter_kde"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (X_COL, Y_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        for col in (X_COL, Y_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        required = [X_COL, Y_COL] + ([GROUP_COL] if GROUP_COL in df.columns else [])
        dropped = int(df[required].isna().any(axis=1).sum())
        df = df.dropna(subset=required)
        if len(df) < 5:
            raise ValueError("有效样本少于 5 行")
        group_col = GROUP_COL if GROUP_COL in df.columns else None
        groups = ([str(g) for g in df[group_col].astype(str)] if group_col
                  else ["样本"] * len(df))
        df["__group"] = groups

        x = df[X_COL].to_numpy(dtype=float)
        y = df[Y_COL].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        pred = slope * x + intercept
        ss_res = float(((y - pred) ** 2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        stats = {"r2": r2, "slope": slope, "n": len(df), "intercept": intercept}

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme.get("scene_preset", {}).get("double_column_mm", 183) if (True and theme.get("scene") == "academic") else theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        unique_groups = list(dict.fromkeys(groups))
        colors = vs.series_color_map(unique_groups, pal, theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(2, 2, width_ratios=[4.2, 1.08], height_ratios=[1.08, 4.2],
                              wspace=0.06, hspace=0.06)
        ax = fig.add_subplot(gs[1, 0])
        ax_top = fig.add_subplot(gs[0, 0], sharex=ax)
        ax_right = fig.add_subplot(gs[1, 1], sharey=ax)
        ax_leg = fig.add_subplot(gs[0, 1])
        vs.apply_style(ax, LAYOUT, theme=theme)

        for name in unique_groups:
            mask = np.array([g == name for g in groups])
            ax.scatter(x[mask], y[mask], s=22, color=colors[name], alpha=0.62,
                       edgecolors="white", linewidths=0.3, zorder=3, label=name)

        # 二维密度等高线
        xpad = (x.max() - x.min()) * 0.04
        ypad = (y.max() - y.min()) * 0.04
        xmin, xmax = x.min() - xpad, x.max() + xpad
        ymin, ymax = y.min() - ypad, y.max() + ypad
        hist, xe, ye = np.histogram2d(x, y, bins=(52, 52), range=[[xmin, xmax], [ymin, ymax]])
        dens = smooth2d(hist, 1.5)
        positive = dens[dens > 0]
        if positive.size:
            levels = np.unique(np.quantile(positive, [0.50, 0.70, 0.85, 0.95]))
            if len(levels) >= 2:
                cmap = vs.sequential_cmap("#94A3B8", n=64)
                ax.contourf(xe[:-1] + np.diff(xe) / 2, ye[:-1] + np.diff(ye) / 2, dens.T,
                            levels=levels, cmap=cmap, alpha=0.28, zorder=1)

        line_x = np.linspace(float(x.min()), float(x.max()), 100)
        ax.plot(line_x, slope * line_x + intercept, color=roles["text"], linewidth=1.6, zorder=5)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(Y_LABEL)
        ax.text(0.015, 0.975, f"n = {len(df)}\n斜率 = {slope:.2f}\nR² = {r2:.2f}",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=vs.font_size(theme, "annotation"), color=roles["text"], linespacing=1.35,
                bbox=dict(facecolor="#FFFFFF", edgecolor=roles["grid"], linewidth=0.5,
                          boxstyle="round,pad=0.3", alpha=0.9), zorder=6)

        # 顶部边际密度
        top_max = 0.0
        for name in unique_groups:
            mask = np.array([g == name for g in groups])
            gx, gd = vs.kde_1d(x[mask], cut=0.0, n=200)
            top_max = max(top_max, float(gd.max()) if len(gd) else 0.0)
            ax_top.fill_between(gx, 0, gd, color=colors[name], alpha=0.20, linewidth=0)
            ax_top.plot(gx, gd, color=colors[name], linewidth=0.9)
        ax_top.set_xlim(xmin, xmax)
        ax_top.set_ylim(0, top_max * 1.12 if top_max > 0 else 1.0)
        ax_top.set_axis_off()

        # 右侧边际密度
        right_max = 0.0
        for name in unique_groups:
            mask = np.array([g == name for g in groups])
            gy, gd = vs.kde_1d(y[mask], cut=0.0, n=200)
            right_max = max(right_max, float(gd.max()) if len(gd) else 0.0)
            ax_right.fill_betweenx(gy, 0, gd, color=colors[name], alpha=0.20, linewidth=0)
            ax_right.plot(gd, gy, color=colors[name], linewidth=0.9)
        ax_right.set_ylim(ymin, ymax)
        ax_right.set_xlim(0, right_max * 1.12 if right_max > 0 else 1.0)
        ax_right.set_axis_off()

        ax_leg.set_axis_off()
        handles = [Line2D([0], [0], marker="o", linestyle="none", markersize=5,
                          markerfacecolor=colors[g], markeredgecolor="white", label=str(g))
                   for g in unique_groups]
        handles.append(Line2D([0], [0], color=roles["text"], linewidth=1.6, label="线性拟合"))
        handles.append(Patch(facecolor="#94A3B8", alpha=0.28, edgecolor="none", label="二维密度"))
        leg = ax_leg.legend(handles=handles, loc="center left", frameon=False,
                            fontsize=vs.font_size(theme, "legend"), handletextpad=0.6,
                            borderaxespad=0.0)
        vs.style_legend(leg, theme)

        vs.add_header(fig, vs.fill_title(TITLE, **stats), SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.09, right=0.975, top=0.80, bottom=0.13, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        df.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "marginal_scatter_kde", "n": len(df), "slope": round(float(slope), 4),
                       "r2": round(float(r2), 4), "groups": unique_groups,
                       "palette": pal.id, "layout": LAYOUT,
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

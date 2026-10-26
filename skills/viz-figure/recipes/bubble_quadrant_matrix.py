# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：战略气泡四象限矩阵（双均值十字基准 + 核心象限底色 + 面积比例气泡 + 引线防叠标签）。

    uv run bubble_quadrant_matrix.py --json
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
NAME_COL = "产品矩阵"
X_COL = "市场渗透率"
Y_COL = "毛利率"
SIZE_COL = "营收体量"
GROUP_COL = "战略分层"
QUAD_LABELS = ("高潜攻坚区\n(低渗透·高毛利)", "明星领航区\n(高渗透·高毛利)",
               "收缩观察区\n(低渗透·低毛利)", "规模现金牛\n(高渗透·低毛利)")
TITLE = "{star_name} 稳居高渗透·高毛利明星象限，贡献体量达 {star_size:.0f}M"
SUBTITLE = "虚线十字为全局均值分界｜气泡面积正比于营收体量（右上战略焦点象限浅底高亮）"
X_LABEL = "市场渗透率（%）"
Y_LABEL = "综合毛利率（%）"
SOURCE = "数据来源：演示商业组合评估矩阵（合成）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
WIDTH_MM = 165
ASPECT = 0.66
CITE_MM = None
OUTDIR = "outputs"
STEM = "bubble_quadrant_matrix"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        ("企业智算一体机", 26.8, 68.5, 420, "核心增长极"),
        ("云原生数据库", 22.4, 62.0, 340, "核心增长极"),
        ("多模态客服 Agent", 11.5, 71.2, 185, "高潜孵化"),
        ("数据合规审计引擎", 8.8, 64.5, 130, "高潜孵化"),
        ("标准 CDN 分发", 31.2, 34.0, 390, "规模基座"),
        ("基础对象存储", 28.5, 41.5, 310, "规模基座"),
        ("私有化定制外包", 9.6, 31.8, 115, "存量优化"),
        ("传统短信网关", 14.2, 26.5, 145, "存量优化"),
        ("零信任安全网关", 19.8, 56.4, 240, "核心增长极"),
    ]
    return pd.DataFrame(rows, columns=[NAME_COL, X_COL, Y_COL, SIZE_COL, GROUP_COL])


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
    ap = argparse.ArgumentParser(description="战略气泡四象限矩阵")
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
              "verified": False, "warnings": [], "figure": {"recipe": "bubble_quadrant_matrix"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (NAME_COL, X_COL, Y_COL, SIZE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df = df.copy()
        for col in (X_COL, Y_COL, SIZE_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[NAME_COL, X_COL, Y_COL, SIZE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[NAME_COL, X_COL, Y_COL, SIZE_COL]).reset_index(drop=True)
        if df.empty:
            raise ValueError("清洗后无可用散点数据")

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("tol_bright", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme, grid="both")

        xv = df[X_COL].to_numpy(dtype=float)
        yv = df[Y_COL].to_numpy(dtype=float)
        sv = np.maximum(df[SIZE_COL].to_numpy(dtype=float), 1e-6)
        xm, ym = float(xv.mean()), float(yv.mean())
        xspan, yspan = max(float(xv.max() - xv.min()), 1.0), max(float(yv.max() - yv.min()), 1.0)
        xlo, xhi = float(xv.min()) - 0.18 * xspan, float(xv.max()) + 0.24 * xspan
        ylo, yhi = float(yv.min()) - 0.18 * yspan, float(yv.max()) + 0.22 * yspan
        ax.set_xlim(xlo, xhi)
        ax.set_ylim(ylo, yhi)

        # 右上明星象限柔和高亮底色 + 四角语义水印
        ax.axvspan(xm, xhi, ymin=(ym - ylo) / (yhi - ylo), ymax=1.0,
                   color=vs.mix("#FFFFFF", pal.colors[0], 0.08), zorder=0.5)
        ax.axvline(xm, color=roles["muted_text"], linestyle="--", linewidth=0.95, zorder=1.8)
        ax.axhline(ym, color=roles["muted_text"], linestyle="--", linewidth=0.95, zorder=1.8)

        q_style = dict(fontsize=vs.font_size(theme, "source"), color=roles["muted_text"], alpha=0.82)
        ax.text(0.02, 0.97, QUAD_LABELS[0], transform=ax.transAxes, ha="left", va="top", **q_style)
        ax.text(0.98, 0.97, QUAD_LABELS[1], transform=ax.transAxes, ha="right", va="top",
                fontsize=vs.font_size(theme, "source"), fontweight="bold",
                color=vs.mix("#0F172A", pal.colors[0], 0.65))
        ax.text(0.02, 0.03, QUAD_LABELS[2], transform=ax.transAxes, ha="left", va="bottom", **q_style)
        ax.text(0.98, 0.03, QUAD_LABELS[3], transform=ax.transAxes, ha="right", va="bottom", **q_style)

        has_grp = GROUP_COL in df.columns
        groups = list(dict.fromkeys(df[GROUP_COL].astype(str).tolist())) if has_grp else ["样本"]
        cmap_dict = vs.series_color_map(groups, pal, theme)

        # 面积编码（严禁按半径平方放大失真）
        areas = 95.0 + 460.0 * (sv / float(sv.max()))
        for g in groups:
            sub = df[df[GROUP_COL].astype(str) == g] if has_grp else df
            idx = sub.index.to_numpy()
            col = cmap_dict[g]
            ax.scatter(xv[idx], yv[idx], s=areas[idx], color=vs.mix("#FFFFFF", col, 0.84),
                       alpha=0.88, edgecolors=vs.mix("#0F172A", col, 0.68), linewidths=1.15,
                       label=g, zorder=3.5)

        # 为气泡标注交替偏移方向，避免遮挡圆心与边界裁切
        order_idx = np.argsort(-sv)[:min(10, len(df))]
        for rank_k, idx in enumerate(order_idx):
            name = str(df.loc[idx, NAME_COL])
            xi, yi = float(xv[idx]), float(yv[idx])
            rad_pt = float(np.sqrt(areas[idx] / np.pi)) * 0.55
            dx = -6 - rad_pt if xi > xlo + 0.72 * (xhi - xlo) else 6 + rad_pt
            dy = -9 if (yi > ylo + 0.80 * (yhi - ylo) or rank_k % 2 == 1) else 8
            ha = "right" if dx < 0 else "left"
            ax.annotate(f"{name} ({sv[idx]:.0f})", xy=(xi, yi), xytext=(dx, dy),
                        textcoords="offset points", ha=ha, va="center",
                        fontsize=vs.font_size(theme, "source"),
                        fontweight="bold" if rank_k < 2 else "normal",
                        color=roles["text"],
                        arrowprops={"arrowstyle": "-", "color": "#94A3B8", "linewidth": 0.65},
                        zorder=4.5)

        if has_grp and len(groups) > 1:
            leg = ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.005), ncol=len(groups),
                            frameon=False, markerscale=0.65, handletextpad=0.4, columnspacing=1.1,
                            fontsize=vs.font_size(theme, "legend"))
            vs.style_legend(leg, theme)

        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(Y_LABEL)

        star_idx = int(np.argmax((xv - xm) / xspan + (yv - ym) / yspan))
        title = vs.fill_title(TITLE, star_name=str(df.loc[star_idx, NAME_COL]),
                              star_size=float(sv[star_idx]))
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.10, right=0.96, top=0.79, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        df.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "bubble_quadrant_matrix", "groups": groups,
                       "x_mean": round(xm, 3), "y_mean": round(ym, 3),
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

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：真三维响应曲面空间场 + 右侧等高线最优点投影双联图（严格限连续双因子场 z=f(x,y)）。

    uv run response_surface_3d_contour.py --json
    uv run response_surface_3d_contour.py --data examples/fixtures/半导体蚀刻_双因子响应面实验.csv --json
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
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
X_COL = "腔体温度_C"
Y_COL = "射频功率_W"
Z_COL = "晶圆良率_pct"
TITLE = "工艺窗口在 {opt_x:.0f}°C × {opt_y:.0f}W 达到全局最高良率 {opt_z:.1f}%"
SUBTITLE = "(a) 双因子连续三维响应曲面场｜(b) 等高线平面投影与全局最优工作点 ★（严禁伪 3D 柱/饼图）"
X_LABEL = "腔体温度 (°C)"
Y_LABEL = "射频功率 (W)"
Z_LABEL = "晶圆良率 (%)"
SOURCE = "数据来源：演示半导体反应离子蚀刻 DOE 响应面实验（合成）"
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
WIDTH_MM = 178
ASPECT = 0.52
CITE_MM = None
OUTDIR = "outputs"
STEM = "response_surface_3d_contour"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    temps = np.linspace(140, 260, 17)
    powers = np.linspace(300, 700, 17)
    rows = []
    for t in temps:
        for p in powers:
            dt = (t - 206.0) / 38.0
            dp = (p - 515.0) / 125.0
            z = 94.8 - 6.8 * dt ** 2 - 5.9 * dp ** 2 + 2.1 * dt * dp
            rows.append({X_COL: round(float(t), 1), Y_COL: round(float(p), 1), Z_COL: round(float(z), 2)})
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


def fit_quadratic_grid(x: np.ndarray, y: np.ndarray, z: np.ndarray, n: int = 50):
    """若输入为散乱 DOE 点而非规则网格，用二次多项式响应面最小二乘重构平滑场。"""
    design = np.column_stack([np.ones_like(x), x, y, x * x, y * y, x * y])
    coef, *_ = np.linalg.lstsq(design, z, rcond=None)
    gx = np.linspace(float(x.min()), float(x.max()), n)
    gy = np.linspace(float(y.min()), float(y.max()), n)
    XX, YY = np.meshgrid(gx, gy)
    ZZ = (coef[0] + coef[1] * XX + coef[2] * YY
          + coef[3] * XX * XX + coef[4] * YY * YY + coef[5] * XX * YY)
    return XX, YY, ZZ


def main() -> int:
    ap = argparse.ArgumentParser(description="真三维响应曲面 + 等高线投影双联图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "response_surface_3d_contour"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        cols = list(df.columns)
        xc = X_COL if X_COL in cols else cols[0]
        yc = Y_COL if Y_COL in cols else cols[1]
        zc = Z_COL if Z_COL in cols else cols[2]
        df = df.copy()
        for col in (xc, yc, zc):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[xc, yc, zc]].isna().any(axis=1).sum())
        df = df.dropna(subset=[xc, yc, zc])

        ux = np.sort(df[xc].unique())
        uy = np.sort(df[yc].unique())
        if len(ux) * len(uy) == len(df) and len(ux) >= 4 and len(uy) >= 4:
            piv = df.pivot_table(index=yc, columns=xc, values=zc, aggfunc="mean").reindex(index=uy, columns=ux)
            XX, YY = np.meshgrid(ux, uy)
            ZZ = piv.to_numpy(dtype=float)
        else:
            XX, YY, ZZ = fit_quadratic_grid(df[xc].to_numpy(dtype=float),
                                            df[yc].to_numpy(dtype=float),
                                            df[zc].to_numpy(dtype=float))

        opt_idx = np.unravel_index(int(np.nanargmax(ZZ)), ZZ.shape)
        opt_x, opt_y, opt_z = float(XX[opt_idx]), float(YY[opt_idx]), float(ZZ[opt_idx])

        theme = vs.resolve_theme(scene=SCENE)
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("met_hiroshige", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]

        cmap = LinearSegmentedColormap.from_list(
            "rsm_hiroshige",
            ["#1E3D59", "#376795", "#72BCD5", "#FFE6B7", "#F7AA58", "#E76254"],
            N=256,
        )

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(1, 2, width_ratios=[1.22, 1.0], wspace=0.24)

        ax3d = fig.add_subplot(gs[0, 0], projection="3d")
        ax2d = fig.add_subplot(gs[0, 1])

        ax3d.set_facecolor("#FFFFFF")
        for axis_obj in (ax3d.xaxis, ax3d.yaxis, ax3d.zaxis):
            axis_obj.pane.fill = True
            axis_obj.pane.set_facecolor((0.97, 0.98, 0.99, 0.85))
            axis_obj.pane.set_edgecolor("#E2E8F0")
            axis_obj._axinfo["grid"]["color"] = "#E2E8F0"
            axis_obj._axinfo["grid"]["linewidth"] = 0.55

        ax3d.plot_surface(XX, YY, ZZ, cmap=cmap, edgecolor="#0F172A", linewidth=0.14,
                          alpha=0.92, antialiased=True)
        z_floor = float(np.nanmin(ZZ)) - 0.12 * max(float(np.nanmax(ZZ) - np.nanmin(ZZ)), 1.0)
        ax3d.contourf(XX, YY, ZZ, zdir="z", offset=z_floor, cmap=cmap, levels=10, alpha=0.42)
        ax3d.scatter([opt_x], [opt_y], [opt_z], s=48, color="#B91C1C", edgecolor="#FFFFFF",
                     linewidth=1.1, zorder=10)
        ax3d.set_zlim(z_floor, float(np.nanmax(ZZ)) + 0.05 * max(float(np.nanmax(ZZ) - z_floor), 1.0))
        ax3d.view_init(elev=27, azim=-128)
        ax3d.set_xlabel(X_LABEL, labelpad=4, fontsize=vs.font_size(theme, "source"))
        ax3d.set_ylabel(Y_LABEL, labelpad=4, fontsize=vs.font_size(theme, "source"))
        ax3d.set_zlabel(Z_LABEL, labelpad=3, fontsize=vs.font_size(theme, "source"))
        ax3d.tick_params(labelsize=vs.font_size(theme, "source") * 0.92, pad=1)
        ax3d.set_title("(a) 三维连续响应曲面", loc="left",
                       fontsize=vs.font_size(theme, "axis_label"), fontweight="bold", pad=4)

        # (b) 二维等高线投影 + 最优靶心十字线
        vs.apply_style(ax2d, "clean_open", theme=theme)
        cf = ax2d.contourf(XX, YY, ZZ, levels=12, cmap=cmap, alpha=0.90)
        cs = ax2d.contour(XX, YY, ZZ, levels=4, colors="#1E293B", linewidths=0.65, alpha=0.68)
        ax2d.axvline(opt_x, color="#FFFFFF", linestyle="--", linewidth=0.95, zorder=4)
        ax2d.axhline(opt_y, color="#FFFFFF", linestyle="--", linewidth=0.95, zorder=4)
        ax2d.scatter([opt_x], [opt_y], s=65, marker="*", color="#B91C1C",
                     edgecolor="#FFFFFF", linewidth=0.9, zorder=6)
        vs.annotate_champion(ax2d, opt_x, opt_y,
                             f"最优点 {opt_z:.1f}%\n({opt_x:.0f}°C, {opt_y:.0f}W)",
                             color="#B91C1C",
                             offset_xy=(-14 if opt_x > float(XX.mean()) else 14, -22),
                             ha="right" if opt_x > float(XX.mean()) else "left",
                             va="top", theme=theme)
        ax2d.set_xlabel(X_LABEL)
        ax2d.set_ylabel(Y_LABEL)
        ax2d.set_title("(b) 等高线投影与最优窗口", loc="left",
                       fontsize=vs.font_size(theme, "axis_label"), fontweight="bold", pad=6)
        cb = fig.colorbar(cf, ax=ax2d, fraction=0.046, pad=0.03)
        cb.outline.set_linewidth(0.5)
        cb.ax.tick_params(labelsize=vs.font_size(theme, "source"))

        title = vs.fill_title(TITLE, opt_x=opt_x, opt_y=opt_y, opt_z=opt_z)
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.05, right=0.95, top=0.77, bottom=0.14, theme=theme)

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
            "figure": {"recipe": "response_surface_3d_contour",
                       "optimum": {"x": round(opt_x, 2), "y": round(opt_y, 2), "z": round(opt_z, 2)},
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

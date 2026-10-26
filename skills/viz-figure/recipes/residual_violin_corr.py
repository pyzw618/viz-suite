# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：残差分布小提琴 + 模型变量相关矩阵复合面板。

    uv run residual_violin_corr.py --json
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
from matplotlib.colors import to_hex

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
GROUP_COL = "组别"
RESIDUAL_COL = "残差"
FEATURES = ["特征1", "特征2", "特征3", "特征4", "特征5"]
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "三组残差均值接近 0，但组 C 方差更大"
SUBTITLE = "左：残差分布（小提琴 + 箱线 + 散点）｜右：模型变量相关矩阵（下三角）"
Y_LABEL = "残差"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.66
CITE_MM = None
OUTDIR = "outputs"
STEM = "residual_violin_corr"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    specs = {"组 A": (0.05, 1.0), "组 B": (-0.10, 1.45), "组 C": (0.15, 2.2)}
    rows = []
    for group, (mu, sigma) in specs.items():
        for _ in range(90):
            f1 = rng.normal(0, 1)
            f2 = 0.7 * f1 + rng.normal(0, 0.7)
            f3 = -0.4 * f1 + 0.5 * f2 + rng.normal(0, 0.7)
            row = {GROUP_COL: group, RESIDUAL_COL: round(float(rng.normal(mu, sigma)), 3),
                   "特征1": round(float(f1), 3), "特征2": round(float(f2), 3),
                   "特征3": round(float(f3), 3),
                   "特征4": round(float(rng.normal(0, 1)), 3),
                   "特征5": round(float(0.6 * f1 + rng.normal(0, 0.8)), 3)}
            rows.append(row)
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
    ap = argparse.ArgumentParser(description="残差小提琴 + 相关矩阵")
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
              "verified": False, "warnings": [], "figure": {"recipe": "residual_violin_corr"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (GROUP_COL, RESIDUAL_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[RESIDUAL_COL] = pd.to_numeric(df[RESIDUAL_COL], errors="coerce")
        features = [f for f in FEATURES if f in df.columns]
        if len(features) < 2:
            features = [c for c in df.columns
                        if c not in (GROUP_COL, RESIDUAL_COL) and pd.api.types.is_numeric_dtype(df[c])][:8]
        if len(features) < 2:
            raise ValueError("至少需要 2 个数值特征列")
        for name in features:
            df[name] = pd.to_numeric(df[name], errors="coerce")
        required = [GROUP_COL, RESIDUAL_COL] + features
        dropped = int(df[required].isna().any(axis=1).sum())
        df = df.dropna(subset=required)
        if len(df) < 6:
            raise ValueError("有效样本少于 6 行")
        groups = list(dict.fromkeys(df[GROUP_COL].astype(str).tolist()))
        corr = df[features].corr().fillna(0.0).to_numpy(dtype=float)
        stats = {"n": len(df), "k_groups": len(groups), "k_features": len(features)}

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
        colors = vs.series_color_map(groups, pal, theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(1, 2, width_ratios=[1.18, 1.0], wspace=0.18)
        ax = fig.add_subplot(gs[0, 0])
        ax_corr = fig.add_subplot(gs[0, 1])
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.axhline(0, color=roles["muted_text"], linestyle=":", linewidth=0.9, zorder=1)

        rng = np.random.default_rng(DEMO_SEED)
        xpos = np.arange(len(groups), dtype=float)
        all_resid = df[RESIDUAL_COL].to_numpy(dtype=float)
        span = max(float(all_resid.max() - all_resid.min()), 1e-6)
        ax.set_ylim(float(all_resid.min()) - 0.08 * span, float(all_resid.max()) + 0.08 * span)
        ax.set_xlim(-0.6, len(groups) - 0.4)
        tick_labels = []
        for i, group in enumerate(groups):
            values = df[df[GROUP_COL].astype(str) == group][RESIDUAL_COL].to_numpy(dtype=float)
            color = colors[group]
            grid, dens = vs.kde_1d(values, cut=0.0, n=200)
            width = dens / dens.max() * 0.32 if dens.max() > 0 else dens
            ax.fill_betweenx(grid, i - width, i + width, color=color, alpha=0.22, linewidth=0)
            ax.plot(i - width, grid, color=color, linewidth=0.8, zorder=2)
            ax.plot(i + width, grid, color=color, linewidth=0.8, zorder=2)
            bp = ax.boxplot([values], positions=[i], widths=0.10, patch_artist=True,
                            showfliers=False, manage_ticks=False, zorder=4,
                            boxprops=dict(facecolor=color, alpha=0.28, edgecolor=color, linewidth=0.9),
                            whiskerprops=dict(color=color, linewidth=0.9),
                            capprops=dict(color=color, linewidth=0.9),
                            medianprops=dict(color="#FFFFFF", linewidth=1.3))
            for patch in bp["boxes"]:
                patch.set_zorder(4)
            jitter = rng.uniform(-0.09, 0.09, len(values))
            ax.scatter(i + 0.23 + jitter, values, s=8, color=color, alpha=0.45,
                       edgecolors="white", linewidths=0.25, zorder=3)
            ax.scatter([i], [float(values.mean())], marker="D", s=22, color=color,
                       edgecolors="white", linewidths=0.7, zorder=6)
            tick_labels.append(f"{group}\n(n={len(values)})")
            if len(values) < 20:
                warnings.append(f"{group} n={len(values)}<20，核密度与四分位估计不稳定")

        ax.set_xticks(xpos)
        ax.set_xticklabels(tick_labels)
        ax.set_ylabel(Y_LABEL)
        ax.set_xlabel("")
        ax.yaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.35)
        ax.xaxis.grid(False)

        cmap = vs.diverging_cmap("#0072B2", other="#D55E00", midpoint="#FFFFFF", n=257)
        masked = np.ma.array(corr, mask=np.triu(np.ones_like(corr, dtype=bool), k=1))
        im = ax_corr.imshow(masked, cmap=cmap, vmin=-1, vmax=1, origin="upper",
                            aspect="auto", interpolation="nearest")
        n = len(features)
        ax_corr.set_xticks(np.arange(n))
        ax_corr.set_yticks(np.arange(n))
        ax_corr.set_xticklabels(features, rotation=0, fontsize=vs.font_size(theme, "source"))
        ax_corr.set_yticklabels(features, fontsize=vs.font_size(theme, "source"))
        ax_corr.tick_params(length=0)
        for spine in ax_corr.spines.values():
            spine.set_visible(False)
        for i in range(n):
            for j in range(i + 1):
                value = float(corr[i, j])
                cell = to_hex(cmap((value + 1) / 2))
                ax_corr.text(j, i, f"{value:.2f}", ha="center", va="center",
                             fontsize=vs.font_size(theme, "source"),
                             color=vs.contrast_text(cell, background="#FFFFFF", alpha=1.0))
        ax_corr.set_title("变量相关矩阵", fontsize=vs.font_size(theme, "annotation"),
                          color=roles["muted_text"], pad=6)

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.09, right=0.97, top=0.80, bottom=0.18, theme=theme)
        cb = fig.colorbar(im, ax=ax_corr, orientation="horizontal", fraction=0.05, pad=0.10,
                          ticks=[-1, 0, 1])
        cb.ax.set_title("Pearson r", fontsize=vs.font_size(theme, "source"),
                        color=roles["muted_text"], pad=3)
        cb.ax.tick_params(labelsize=vs.font_size(theme, "source"), length=2)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        df.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))
        corr_path = Path(OUTDIR) / f"{STEM}_corr.csv"
        pd.DataFrame(corr, index=features, columns=features).to_csv(corr_path, encoding="utf-8-sig")
        outputs.append(str(corr_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "residual_violin_corr", "groups": groups, "features": features,
                       "n": len(df), "palette": pal.id, "layout": LAYOUT,
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

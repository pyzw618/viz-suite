# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0", "scipy>=1.10"]
# ///
# -*- coding: utf-8 -*-
"""配方：下三角相关矩阵 + 双侧层次聚类树状图。

    uv run clustered_corr_dendro.py --json
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
from scipy.cluster.hierarchy import dendrogram, leaves_list, linkage
from scipy.spatial.distance import squareform

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
FEATURES = ["特征1", "特征2", "特征3", "特征4", "特征5",
            "特征6", "特征7", "特征8", "特征9", "特征10"]
LINKAGE_METHOD = "average"
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
TITLE = "相关矩阵聚成 3 个特征簇，下三角标注 Pearson r"
SUBTITLE = "颜色为相关系数（−1 蓝 ← 0 白 → +1 橙红）｜行列按平均连接聚类排序"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.82
CITE_MM = None
ANNOTATE_MAX = 12
OUTDIR = "outputs"
STEM = "clustered_corr_dendro"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    n = 220
    f1, f2, f3 = rng.normal(size=(3, n))
    data = {
        "特征1": f1 + rng.normal(0, 0.25, n),
        "特征2": 0.82 * f1 + rng.normal(0, 0.35, n),
        "特征3": 0.62 * f1 - 0.28 * f2 + rng.normal(0, 0.45, n),
        "特征4": f2 + rng.normal(0, 0.25, n),
        "特征5": 0.88 * f2 + rng.normal(0, 0.32, n),
        "特征6": 0.70 * f2 + 0.40 * f3 + rng.normal(0, 0.40, n),
        "特征7": f3 + rng.normal(0, 0.25, n),
        "特征8": 0.80 * f3 + rng.normal(0, 0.34, n),
        "特征9": 0.48 * f1 - 0.52 * f3 + rng.normal(0, 0.48, n),
        "特征10": rng.normal(0, 1.0, n),
    }
    return pd.DataFrame({k: np.round(v, 4) for k, v in data.items()})


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
    ap = argparse.ArgumentParser(description="下三角相关矩阵 + 聚类树")
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
              "verified": False, "warnings": [], "figure": {"recipe": "clustered_corr_dendro"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        features = [f for f in FEATURES if f in df.columns]
        if len(features) < 3:
            features = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if len(features) < 3:
            raise ValueError("至少需要 3 个数值特征")
        for name in features:
            df[name] = pd.to_numeric(df[name], errors="coerce")
        dropped = int(df[features].isna().any(axis=1).sum())
        df = df.dropna(subset=features)
        if len(df) < 3:
            raise ValueError("有效样本少于 3 行")
        corr = df[features].corr(method="pearson").fillna(0.0).to_numpy(dtype=float)

        dist = 1.0 - corr
        np.fill_diagonal(dist, 0.0)
        dist = np.clip((dist + dist.T) / 2.0, 0.0, 2.0)
        Z = linkage(squareform(dist, checks=False), method=LINKAGE_METHOD)
        order = leaves_list(Z)
        ordered = corr[np.ix_(order, order)]
        labels = [features[i] for i in order]

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
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]
        n = len(labels)
        extent = 10 * n

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(2, 2, width_ratios=[1.15, 4.5], height_ratios=[1.15, 4.5],
                              wspace=0.0, hspace=0.0)
        ax_row = fig.add_subplot(gs[1, 0])
        ax_col = fig.add_subplot(gs[0, 1])
        ax_heat = fig.add_subplot(gs[1, 1])
        ax_blank = fig.add_subplot(gs[0, 0])

        dendrogram(Z, orientation="left", no_labels=True, color_threshold=0,
                   above_threshold_color=roles["muted_text"], ax=ax_row)
        ax_row.set_ylim(0, extent)
        ax_row.set_xticks([])
        ax_row.set_yticks(np.arange(5, extent, 10))
        ax_row.set_yticklabels(labels)
        ax_row.tick_params(axis="y", length=0, labelsize=vs.font_size(theme, "annotation"))
        ax_row.invert_yaxis()  # 让 order[0] 位于顶部，与 origin='upper' 的热图对齐
        for spine in ax_row.spines.values():
            spine.set_visible(False)

        dendrogram(Z, orientation="top", no_labels=True, color_threshold=0,
                   above_threshold_color=roles["muted_text"], ax=ax_col)
        ax_col.set_xlim(0, extent)
        ax_col.set_xticks([])
        ax_col.set_yticks([])
        for spine in ax_col.spines.values():
            spine.set_visible(False)

        cmap = vs.diverging_cmap("#0072B2", other="#D55E00", midpoint="#FFFFFF", n=257)
        masked = np.ma.array(ordered, mask=np.triu(np.ones_like(ordered, dtype=bool), k=1))
        im = ax_heat.imshow(masked, cmap=cmap, vmin=-1, vmax=1, origin="upper",
                            extent=(0, extent, 0, extent), aspect="auto", interpolation="nearest")
        ax_heat.set_xlim(0, extent)
        ax_heat.set_ylim(0, extent)
        ax_heat.set_xticks(np.arange(5, extent, 10))
        ax_heat.set_xticklabels(labels, rotation=0, ha="center",
                                fontsize=vs.font_size(theme, "annotation"))
        ax_heat.set_yticks([])
        for spine in ax_heat.spines.values():
            spine.set_visible(False)

        if n <= ANNOTATE_MAX:
            for i in range(n):
                for j in range(i + 1):
                    value = float(ordered[i, j])
                    cell = to_hex(cmap((value + 1) / 2))
                    ax_heat.text(j * 10 + 5, (n - 1 - i) * 10 + 5, f"{value:.2f}", ha="center", va="center",
                                 fontsize=vs.font_size(theme, "source"),
                                 color=vs.contrast_text(cell, background="#FFFFFF", alpha=1.0))
        else:
            warnings.append(f"特征数 {n} > {ANNOTATE_MAX}，已关闭单元格数值标注")

        ax_blank.axis("off")
        cax = ax_blank.inset_axes([0.18, 0.36, 0.64, 0.16])
        cb = fig.colorbar(im, cax=cax, orientation="horizontal", ticks=[-1, 0, 1])
        cb.ax.set_title("Pearson r", fontsize=vs.font_size(theme, "source"),
                        color=roles["muted_text"], pad=4)
        cb.ax.tick_params(labelsize=vs.font_size(theme, "source"), length=2)
        ax_blank.text(0.5, 0.82, f"{n} 个特征", ha="center", va="center",
                      fontsize=vs.font_size(theme, "source"), color=roles["muted_text"],
                      transform=ax_blank.transAxes)

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.17, right=0.96, top=0.80, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_corr.csv"
        pd.DataFrame(ordered, index=labels, columns=labels).to_csv(data_path, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "clustered_corr_dendro", "features": labels,
                       "n": len(df), "method": LINKAGE_METHOD, "layout": LAYOUT,
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

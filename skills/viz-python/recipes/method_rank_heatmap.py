# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0", "scipy>=1.10"]
# ///
# -*- coding: utf-8 -*-
"""配方：多指标方法排名聚类热力图（行/列双侧树状图）。

    uv run method_rank_heatmap.py --json
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
from scipy.spatial.distance import pdist

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
METHOD_COL = "方法"
INDICATORS = ["准确率", "召回率", "F1", "推理速度", "稳定性", "可解释性"]
LOWER_IS_BETTER = []          # 例如 ["推理时延", "内存占用"]；未列出的指标均视为越高越好
LINKAGE_METHOD = "average"
PALETTE = None
LAYOUT = "clean_open"
TITLE = "方法 E 质量领先但速度与可解释性靠后，方法 H 相反"
SUBTITLE = "颜色越深名次越靠前（1=最好）｜行列按名次轮廓聚类｜含缺失指标的方法整行剔除"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.76
CITE_MM = None
OUTDIR = "outputs"
STEM = "method_rank_heatmap"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    abilities = {"方法 A": 0.72, "方法 B": 0.80, "方法 C": 0.65, "方法 D": 0.85,
                 "方法 E": 0.92, "方法 F": 0.60, "方法 G": 0.75, "方法 H": 0.50}
    rows = []
    for method, a in abilities.items():
        rows.append({
            METHOD_COL: method,
            "准确率": round(60 + 35 * a + rng.normal(0, 2.0), 2),
            "召回率": round(55 + 38 * a + rng.normal(0, 2.2), 2),
            "F1": round(58 + 36 * a + rng.normal(0, 1.8), 2),
            "推理速度": round(90 - 45 * a + rng.normal(0, 2.5), 2),
            "稳定性": round(65 + 28 * a + rng.normal(0, 2.0), 2),
            "可解释性": round(88 - 42 * a + rng.normal(0, 3.0), 2),
        })
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
    ap = argparse.ArgumentParser(description="方法排名聚类热力图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "method_rank_heatmap"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        if METHOD_COL not in df.columns:
            raise ValueError(f"缺少列「{METHOD_COL}」；现有列：{list(df.columns)}")
        indicators = [c for c in INDICATORS if c in df.columns]
        if not indicators:
            indicators = [c for c in df.columns if c != METHOD_COL
                          and pd.api.types.is_numeric_dtype(df[c])]
        if len(indicators) < 2:
            raise ValueError("至少需要 2 个数值指标")
        methods = df[METHOD_COL].astype(str).tolist()
        raw = df[indicators].apply(pd.to_numeric, errors="coerce")
        dropped = int(raw.isna().any(axis=1).sum())
        keep = ~raw.isna().any(axis=1)
        methods = [m for m, k in zip(methods, keep) if k]
        raw = raw.loc[keep].reset_index(drop=True)
        if len(methods) < 2:
            raise ValueError("有效方法少于 2 个")

        ranks = pd.DataFrame(index=raw.index)
        for name in indicators:
            higher_better = name not in LOWER_IS_BETTER
            ranks[name] = raw[name].rank(ascending=not higher_better, method="min")
        rank_mat = ranks.to_numpy(dtype=float)

        Z_row = linkage(pdist(rank_mat, metric="euclidean"), method=LINKAGE_METHOD)
        Z_col = linkage(pdist(rank_mat.T, metric="euclidean"), method=LINKAGE_METHOD)
        row_order = leaves_list(Z_row)
        col_order = leaves_list(Z_col)
        ordered = rank_mat[np.ix_(row_order, col_order)]
        row_labels = [methods[i] for i in row_order]
        col_labels = [indicators[i] for i in col_order]
        n_rows, n_cols = ordered.shape

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(2, 2, width_ratios=[1.05, 4.5], height_ratios=[1.05, 4.5],
                              wspace=0.0, hspace=0.0)
        ax_row = fig.add_subplot(gs[1, 0])
        ax_col = fig.add_subplot(gs[0, 1])
        ax_heat = fig.add_subplot(gs[1, 1])
        ax_blank = fig.add_subplot(gs[0, 0])

        dendrogram(Z_row, orientation="left", no_labels=True, color_threshold=0,
                   above_threshold_color=roles["muted_text"], ax=ax_row)
        ax_row.set_ylim(0, 10 * n_rows)
        ax_row.set_xticks([])
        ax_row.set_yticks(np.arange(5, 10 * n_rows, 10))
        ax_row.set_yticklabels(row_labels)
        ax_row.tick_params(axis="y", length=0, labelsize=vs.font_size(theme, "annotation"))
        for spine in ax_row.spines.values():
            spine.set_visible(False)

        dendrogram(Z_col, orientation="top", no_labels=True, color_threshold=0,
                   above_threshold_color=roles["muted_text"], ax=ax_col)
        ax_col.set_xlim(0, 10 * n_cols)
        ax_col.set_xticks([])
        ax_col.set_yticks([])
        for spine in ax_col.spines.values():
            spine.set_visible(False)

        cmap = vs.sequential_cmap(roles["focal"], n=256).reversed()
        im = ax_heat.imshow(ordered, cmap=cmap, vmin=1, vmax=max(n_rows, 2), origin="lower",
                            extent=(0, 10 * n_cols, 0, 10 * n_rows), aspect="auto",
                            interpolation="nearest")
        ax_heat.set_xlim(0, 10 * n_cols)
        ax_heat.set_ylim(0, 10 * n_rows)
        ax_heat.set_xticks(np.arange(5, 10 * n_cols, 10))
        ax_heat.set_xticklabels(col_labels, rotation=0, ha="center",
                                fontsize=vs.font_size(theme, "annotation"))
        ax_heat.set_yticks([])
        for spine in ax_heat.spines.values():
            spine.set_visible(False)

        for i in range(n_rows):
            for j in range(n_cols):
                value = float(ordered[i, j])
                norm = (value - 1) / max(n_rows - 1, 1)
                cell = to_hex(cmap(norm))
                ax_heat.text(j * 10 + 5, i * 10 + 5, f"{int(round(value))}",
                             ha="center", va="center",
                             fontsize=vs.font_size(theme, "annotation"),
                             color=vs.contrast_text(cell, background="#FFFFFF", alpha=1.0))

        ax_blank.axis("off")
        cax = ax_blank.inset_axes([0.18, 0.36, 0.64, 0.16])
        cb = fig.colorbar(im, cax=cax, orientation="horizontal", ticks=[1, max(n_rows, 2)])
        cb.ax.set_title("名次（1=最好）", fontsize=vs.font_size(theme, "source"),
                        color=roles["muted_text"], pad=4)
        cb.ax.tick_params(labelsize=vs.font_size(theme, "source"), length=2)

        fig.text(0.015, 0.965, TITLE, ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"), color=roles["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"), color=roles["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.16, right=0.96, top=0.80, bottom=0.14)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_ranks.csv"
        pd.DataFrame(ordered, index=row_labels, columns=col_labels).to_csv(
            data_path, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(methods)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "method_rank_heatmap", "methods": row_labels,
                       "indicators": col_labels, "direction": {
                           "higher_is_better": [i for i in indicators if i not in LOWER_IS_BETTER],
                           "lower_is_better": LOWER_IS_BETTER},
                       "palette": pal.id, "layout": LAYOUT,
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

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：差异倍数火山图（背景密度 + 阈值带 + 防碰撞引线标注）。

    uv run volcano_fusion.py --json
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

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
GENE_COL = "基因"
FC_COL = "log2FC"
P_COL = "p值"
FC_THRESHOLD = 1.0
P_THRESHOLD = 0.05
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
TITLE = "上调 {n_up} 个、下调 {n_down} 个基因（|log2FC|>{fc_thr:g} 且 p<{p_thr:g}）"
SUBTITLE = "灰点为不显著基因｜背景为点密度｜虚线为 |log2FC|=1 与 p=0.05｜引线标注效应量最大的基因"
X_LABEL = "log2 倍数变化"
Y_LABEL = "−log10(p)"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.64
CITE_MM = None
LABEL_TOP_N = 6
OUTDIR = "outputs"
STEM = "volcano_fusion"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    genes, fcs, ps = [], [], []
    for i in range(420):
        fc = rng.normal(0, 0.34)
        p = np.clip(np.exp(-abs(fc) * 1.2) * rng.uniform(0.02, 1.0), 1e-4, 1.0)
        genes.append(f"基因{i:03d}")
        fcs.append(fc)
        ps.append(p)
    for i in range(26):
        fc = rng.uniform(1.4, 3.0)
        genes.append(f"上调基因{i:02d}")
        fcs.append(fc)
        ps.append(10 ** rng.uniform(-8, -1.5))
    for i in range(22):
        fc = -rng.uniform(1.4, 3.0)
        genes.append(f"下调基因{i:02d}")
        fcs.append(fc)
        ps.append(10 ** rng.uniform(-8, -1.5))
    df = pd.DataFrame({GENE_COL: genes, FC_COL: np.round(fcs, 4), P_COL: ps})
    return df.sample(frac=1.0, random_state=DEMO_SEED).reset_index(drop=True)


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


def smooth2d(matrix: np.ndarray, sigma: float = 1.3) -> np.ndarray:
    radius = max(1, int(3 * sigma))
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    out = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), 0, matrix)
    out = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="same"), 1, out)
    return out


def place_labels(ax, rows, x_span, y_span, theme):
    roles = theme["colors"]["roles"]
    placed: list[tuple[float, float]] = []
    bx, by = 0.28 * x_span, 0.088 * y_span
    for _, row in rows.iterrows():
        x, y = float(row[FC_COL]), float(row["__y"])
        # 标签一律朝图内放置，避免贴边被裁切；白底框保证压在点云上仍可读
        if x < 0:
            tx, ha = x + 0.09 * x_span, "left"
        else:
            tx, ha = x - 0.09 * x_span, "right"
        ty = y + 0.03 * y_span
        base_ty = ty
        for attempt in range(1, 22):
            if not any(abs(tx - px) < bx and abs(ty - py) < by for px, py in placed):
                break
            step = ((attempt + 1) // 2) * 0.085 * y_span
            cand = base_ty + (step if attempt % 2 == 1 else -step)
            ty = max(0.06 * y_span, min(y_span * 1.04, cand))
        placed.append((tx, ty))
        ax.annotate(str(row[GENE_COL]), xy=(x, y), xytext=(tx, ty),
                    ha=ha, va="center",
                    fontsize=vs.font_size(theme, "source"), color=roles["text"],
                    bbox=dict(facecolor="#FFFFFF", edgecolor="none", alpha=0.82, pad=0.7),
                    arrowprops=dict(arrowstyle="-", color=roles["muted_text"], linewidth=0.6,
                                    shrinkA=0, shrinkB=2))


def main() -> int:
    ap = argparse.ArgumentParser(description="差异倍数火山图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "volcano_fusion"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (GENE_COL, FC_COL, P_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        for col in (FC_COL, P_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[GENE_COL, FC_COL, P_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[GENE_COL, FC_COL, P_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")
        zero_p = int((df[P_COL] <= 0).sum())
        if zero_p:
            df.loc[df[P_COL] <= 0, P_COL] = 1e-300
            warnings.append(f"{zero_p} 个 p 值 ≤0，已按 1e-300 截断")
        df = df[df[P_COL] <= 1.0]
        df["__y"] = -np.log10(df[P_COL].astype(float))
        df["__sig"] = ((df[FC_COL].abs() >= FC_THRESHOLD) & (df[P_COL] <= P_THRESHOLD))
        up = df[(df["__sig"]) & (df[FC_COL] > 0)]
        down = df[(df["__sig"]) & (df[FC_COL] < 0)]
        ns = df[~df["__sig"]]
        stats = {"n_up": len(up), "n_down": len(down), "n_ns": len(ns), "k": len(df),
                 "fc_thr": FC_THRESHOLD, "p_thr": P_THRESHOLD}

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
        pal = vs.palette(theme=theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]
        up_color, down_color = roles["positive"], roles["negative"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)

        x_span = max(float(df[FC_COL].max() - df[FC_COL].min()), 1.0)
        y_span = max(float(df["__y"].max()), 1.0)
        xmin, xmax = float(df[FC_COL].min()) - 0.05 * x_span, float(df[FC_COL].max()) + 0.05 * x_span
        ymin, ymax = 0.0, y_span * 1.10
        hist, xe, ye = np.histogram2d(df[FC_COL], df["__y"], bins=(64, 64),
                                      range=[[xmin, xmax], [ymin, ymax]])
        density = smooth2d(hist, sigma=1.25)
        cmap = vs.sequential_cmap("#94A3B8", n=128)
        ax.pcolormesh(xe, ye, density.T, cmap=cmap, shading="auto", alpha=0.42, zorder=0)

        ax.scatter(ns[FC_COL], ns["__y"], s=10, color=roles["context"], alpha=0.38,
                   edgecolors="none", zorder=2)
        ax.scatter(up[FC_COL], up["__y"], s=19, color=up_color, alpha=0.78,
                   edgecolors="white", linewidths=0.3, zorder=3)
        ax.scatter(down[FC_COL], down["__y"], s=19, color=down_color, alpha=0.78,
                   edgecolors="white", linewidths=0.3, zorder=3)

        ax.axvline(FC_THRESHOLD, color=roles["muted_text"], linestyle="--", linewidth=0.8, zorder=1)
        ax.axvline(-FC_THRESHOLD, color=roles["muted_text"], linestyle="--", linewidth=0.8, zorder=1)
        ax.axhline(-np.log10(P_THRESHOLD), color=roles["muted_text"], linestyle="--",
                   linewidth=0.8, zorder=1)
        ax.text(xmin + 0.01 * x_span, -np.log10(P_THRESHOLD) + 0.012 * y_span,
                f"p = {P_THRESHOLD:g}", ha="left", va="bottom",
                fontsize=vs.font_size(theme, "source"), color=roles["muted_text"],
                bbox=dict(facecolor="#FFFFFF", edgecolor="none", alpha=0.82, pad=0.6))

        if LABEL_TOP_N and len(up) + len(down) > 0:
            labelled = df[df["__sig"]].copy()
            labelled["__score"] = labelled[FC_COL].abs() * labelled["__y"]
            labelled = labelled.sort_values("__score", ascending=False).head(LABEL_TOP_N)
            place_labels(ax, labelled, x_span, y_span, theme)

        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(Y_LABEL)
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
        ax.set_xscale("linear")

        handles = [
            Line2D([0], [0], marker="o", linestyle="none", markersize=5,
                   markerfacecolor=up_color, markeredgecolor="white", label=f"上调 {len(up)}"),
            Line2D([0], [0], marker="o", linestyle="none", markersize=5,
                   markerfacecolor=down_color, markeredgecolor="white", label=f"下调 {len(down)}"),
            Line2D([0], [0], marker="o", linestyle="none", markersize=4,
                   markerfacecolor=roles["context"], markeredgecolor="none", label=f"不显著 {len(ns)}"),
        ]
        leg = ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 1.005),
                        ncol=3, frameon=False, fontsize=vs.font_size(theme, "legend"),
                        handletextpad=0.5, columnspacing=1.2)
        vs.style_legend(leg, theme)

        vs.add_header(fig, vs.fill_title(TITLE, **stats), SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.10, right=0.975, top=0.79, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = df.copy()
        export["neg_log10_p"] = export["__y"].round(4)
        export["significant"] = export["__sig"]
        export = export.drop(columns=["__y", "__sig"])
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "volcano_fusion", "n_up": len(up), "n_down": len(down),
                       "n_ns": len(ns), "thresholds": [FC_THRESHOLD, P_THRESHOLD],
                       "palette": pal.id, "layout": LAYOUT,
                       "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit(), "visual_verified": False,
                       "note": "脚本只验证文件生成；审美与可读性须由 viz-audit / ViewImage 复核"},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

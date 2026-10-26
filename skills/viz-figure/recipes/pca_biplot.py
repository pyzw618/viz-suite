# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：PCA 样本得分与载荷双标图（含 95% 置信椭圆）。

    uv run pca_biplot.py --json
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
from matplotlib.patches import Ellipse

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
GROUP_COL = "组别"
FEATURES = ["特征1", "特征2", "特征3", "特征4", "特征5", "特征6"]
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "PC1 解释 {pc1:.1f}% 方差，主要区分组 A 与组 B；PC2 拉开组 C"
SUBTITLE = "点为样本得分｜箭头为变量载荷｜椭圆为 95% 置信区域"
X_LABEL = "PC1（{pc1:.1f}%）"
Y_LABEL = "PC2（{pc2:.1f}%）"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.70
CITE_MM = None
OUTDIR = "outputs"
STEM = "pca_biplot"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    specs = {
        "组 A": [-1.6, 0.9, 0.6, -0.4, 0.3, -0.5],
        "组 B": [1.5, -0.8, 0.4, 0.7, -0.4, 0.5],
        "组 C": [0.0, 0.2, -1.4, 0.1, 1.0, 0.2],
    }
    rows = []
    for group, center in specs.items():
        for _ in range(24):
            row = {GROUP_COL: group}
            for name, mu in zip(FEATURES, center):
                row[name] = round(float(rng.normal(mu, 0.9)), 4)
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


def add_ellipse(ax, x, y, color, theme):
    if len(x) < 3:
        return
    cov = np.cov(x, y)
    vals, vecs = np.linalg.eigh(cov)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]
    theta = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
    width, height = 2 * np.sqrt(np.maximum(vals, 0) * 5.991)
    ax.add_patch(Ellipse((float(np.mean(x)), float(np.mean(y))), width, height, angle=theta,
                         facecolor=color, edgecolor=color, alpha=0.06, linewidth=0.8,
                         linestyle="--", zorder=1))


def main() -> int:
    ap = argparse.ArgumentParser(description="PCA 双标图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "pca_biplot"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        features = [f for f in FEATURES if f in df.columns]
        if len(features) < 2:
            raise ValueError(f"至少需要 2 个数值特征；现有列：{list(df.columns)}")
        for name in features:
            df[name] = pd.to_numeric(df[name], errors="coerce")
        required = ([GROUP_COL] if GROUP_COL in df.columns else []) + features
        dropped = int(df[required].isna().any(axis=1).sum())
        df = df.dropna(subset=required)
        if len(df) < 3:
            raise ValueError("有效样本少于 3 行")

        X = df[features].to_numpy(dtype=float)
        X = (X - X.mean(axis=0)) / np.where(X.std(axis=0, ddof=1) > 0, X.std(axis=0, ddof=1), 1.0)
        U, S, Vt = np.linalg.svd(X, full_matrices=False)
        scores = U * S
        explained = S ** 2 / np.sum(S ** 2)
        for k in range(min(2, len(Vt))):
            if np.abs(Vt[k]).max() > 0 and Vt[k][np.argmax(np.abs(Vt[k]))] < 0:
                Vt[k] *= -1
                scores[:, k] *= -1
        loadings = Vt[:2, :].T
        stats = {"pc1": explained[0] * 100, "pc2": explained[1] * 100 if len(explained) > 1 else 0.0,
                 "n": len(df), "p": len(features)}

        groups = ([str(g) for g in df[GROUP_COL].astype(str)] if GROUP_COL in df.columns
                  else ["样本"] * len(df))
        df["__group"] = groups

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
        unique_groups = list(dict.fromkeys(groups))
        colors = vs.series_color_map(unique_groups, pal, theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.axhline(0, color=roles["muted_text"], linestyle=":", linewidth=0.8, zorder=1)
        ax.axvline(0, color=roles["muted_text"], linestyle=":", linewidth=0.8, zorder=1)

        for group in unique_groups:
            mask = np.array([g == group for g in groups])
            ax.scatter(scores[mask, 0], scores[mask, 1], s=26, color=colors[group], alpha=0.72,
                       edgecolors="white", linewidths=0.45, zorder=3, label=group)
            add_ellipse(ax, scores[mask, 0], scores[mask, 1], colors[group], theme)

        score_max = float(np.abs(scores[:, :2]).max()) if scores.size else 1.0
        loading_max = float(np.abs(loadings).max()) if loadings.size else 1.0
        scale = 0.62 * score_max / max(loading_max, 1e-9)
        for (lx, ly), name in zip(loadings * scale, features):
            ax.annotate("", xy=(lx, ly), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color=roles["text"], linewidth=0.9,
                                        mutation_scale=8, shrinkA=0, shrinkB=0), zorder=5)
            ax.text(lx * 1.05, ly * 1.05, name, ha="center", va="center",
                    fontsize=vs.font_size(theme, "source"), color=roles["text"],
                    bbox=dict(facecolor="#FFFFFF", edgecolor="none", alpha=0.82, pad=0.7),
                    zorder=6)

        ax.set_xlabel(vs.fill_title(X_LABEL, **stats))
        ax.set_ylabel(vs.fill_title(Y_LABEL, **stats))
        pad_x = score_max * 1.35
        pad_y = float(np.abs(scores[:, 1]).max()) * 1.35 if scores.shape[1] > 1 else pad_x
        ax.set_xlim(-pad_x, pad_x)
        ax.set_ylim(-pad_y, pad_y)

        leg = ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.005), ncol=len(unique_groups),
                        frameon=False, fontsize=vs.font_size(theme, "legend"),
                        handletextpad=0.5, columnspacing=1.2)
        vs.style_legend(leg, theme)

        vs.add_header(fig, vs.fill_title(TITLE, **stats), SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.10, right=0.975, top=0.80, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = df.copy()
        export["PC1"] = scores[:, 0].round(4)
        export["PC2"] = scores[:, 1].round(4) if scores.shape[1] > 1 else 0.0
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        load_path = Path(OUTDIR) / f"{STEM}_loadings.csv"
        pd.DataFrame({"feature": features, "PC1": loadings[:, 0].round(4),
                      "PC2": loadings[:, 1].round(4) if loadings.shape[1] > 1 else 0.0}).to_csv(
            load_path, index=False, encoding="utf-8-sig")
        outputs.extend([str(data_path), str(load_path)])

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "pca_biplot", "explained_pct": [round(float(e * 100), 2) for e in explained[:2]],
                       "n": len(df), "p": len(features), "groups": unique_groups,
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

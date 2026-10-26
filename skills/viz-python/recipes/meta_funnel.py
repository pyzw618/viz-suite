# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：Meta 分析三层置信漏斗图（90/95/99% 伪置信区间 + 加权散点）。

    uv run meta_funnel.py --json
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
STUDY_COL = "研究"
EFFECT_COL = "效应量"
SE_COL = "标准误"
X_LABEL = "效应量（Hedges' g）"
Y_LABEL = "标准误（SE，0 在顶部）"
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
TITLE = "合并效应量 {pooled:+.2f}（95% CI {ci_low:+.2f} 至 {ci_high:+.2f}），共 {k} 项研究"
SUBTITLE = "漏斗为 90/95/99% 伪置信区间｜点大小 ∝ 权重(1/SE²)｜不是显著性检验"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.64
CITE_MM = None
LABEL_OUTLIERS = True
OUTDIR = "outputs"
STEM = "meta_funnel"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    effects = np.concatenate([
        rng.normal(0.36, 0.12, 12), rng.normal(0.42, 0.10, 5),
        rng.normal(0.24, 0.14, 3),
    ])
    ses = np.concatenate([rng.uniform(0.05, 0.16, 12), rng.uniform(0.18, 0.30, 5),
                          rng.uniform(0.10, 0.22, 3)])
    return pd.DataFrame({
        STUDY_COL: [f"研究 {i:02d}" for i in range(1, len(effects) + 1)],
        EFFECT_COL: np.round(effects, 3), SE_COL: np.round(ses, 3),
    })


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
    ap = argparse.ArgumentParser(description="Meta 分析置信漏斗图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "meta_funnel"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (STUDY_COL, EFFECT_COL, SE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        for col in (EFFECT_COL, SE_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[STUDY_COL, EFFECT_COL, SE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[STUDY_COL, EFFECT_COL, SE_COL])
        df = df[df[SE_COL] > 0]
        if len(df) < 3:
            raise ValueError("有效研究少于 3 项，无法绘制漏斗")

        effects = df[EFFECT_COL].to_numpy(dtype=float)
        ses = df[SE_COL].to_numpy(dtype=float)
        weights = 1.0 / ses ** 2
        pooled = float(np.sum(weights * effects) / np.sum(weights))
        pooled_se = float(np.sqrt(1.0 / np.sum(weights)))
        ci_low, ci_high = pooled - 1.96 * pooled_se, pooled + 1.96 * pooled_se
        stats = {"pooled": pooled, "ci_low": ci_low, "ci_high": ci_high,
                 "k": len(df), "pooled_se": pooled_se}

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
        focal = roles["focal"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        se_grid = np.linspace(0, float(ses.max()) * 1.06, 200)
        for z, alpha in ((2.576, 0.055), (1.96, 0.07), (1.645, 0.09)):
            ax.fill_betweenx(se_grid, pooled - z * se_grid, pooled + z * se_grid,
                             color=focal, alpha=alpha, linewidth=0)
            ax.plot(pooled - z * se_grid, se_grid, color=focal, linewidth=0.7, alpha=0.45)
            ax.plot(pooled + z * se_grid, se_grid, color=focal, linewidth=0.7, alpha=0.45)
            label = {2.576: "99%", 1.96: "95%", 1.645: "90%"}[z]
            ax.text(pooled + z * se_grid[-1] * 0.985, se_grid[-1] * 0.985, label,
                    ha="left", va="center", fontsize=vs.font_size(theme, "source"),
                    color=focal, alpha=0.65)

        sizes = 18 + 110 * (weights / weights.max())
        ax.scatter(effects, ses, s=sizes, color=focal, alpha=0.62,
                   edgecolors="white", linewidths=0.45, zorder=4)
        ax.axvline(pooled, color=roles["text"], linewidth=1.2, zorder=3)
        ax.text(pooled, -0.015 * float(ses.max()), f"合并效应 {pooled:+.2f}",
                ha="center", va="bottom", fontsize=vs.font_size(theme, "annotation"),
                color=roles["text"], fontweight="bold")

        if LABEL_OUTLIERS and len(df) >= 5:
            residual = np.abs(effects - pooled) / ses
            for idx in np.argsort(-residual)[:3]:
                if residual[idx] < 2:
                    continue
                x, y = float(effects[idx]), float(ses[idx])
                right = x >= pooled
                ax.annotate(str(df.iloc[idx][STUDY_COL]), xy=(x, y),
                            xytext=(10 if right else -10, -2), textcoords="offset points",
                            ha="left" if right else "right", va="center",
                            fontsize=vs.font_size(theme, "source"),
                            color=roles["muted_text"],
                            arrowprops=dict(arrowstyle="-", color=roles["muted_text"],
                                            linewidth=0.6, shrinkA=0, shrinkB=2))

        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(Y_LABEL)
        ax.set_ylim(float(ses.max()) * 1.12, 0)
        x_span = max(float(effects.max() - effects.min()), 0.2)
        ax.set_xlim(min(float(effects.min()), pooled - 2.6 * float(ses.max())) - 0.06 * x_span,
                    max(float(effects.max()), pooled + 2.6 * float(ses.max())) + 0.06 * x_span)

        ax.text(0.015, 0.97, f"k = {len(df)}\n合并效应 = {pooled:+.2f}\n"
                             f"95% CI = {ci_low:+.2f} ~ {ci_high:+.2f}",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=vs.font_size(theme, "annotation"), color=roles["text"],
                linespacing=1.35,
                bbox=dict(facecolor="#FFFFFF", edgecolor=roles["grid"], linewidth=0.5,
                          boxstyle="round,pad=0.35", alpha=0.92))

        vs.add_header(fig, vs.fill_title(TITLE, **stats), SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.10, right=0.975, top=0.80, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = df.copy()
        export["weight"] = (weights / weights.sum()).round(5)
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "meta_funnel", "k": len(df), "pooled": round(pooled, 3),
                       "ci": [round(ci_low, 3), round(ci_high, 3)],
                       "pooled_se": round(pooled_se, 3), "palette": pal.id, "layout": LAYOUT,
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

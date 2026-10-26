# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：ROC + Precision–Recall 双联分类器评估面板（羽化置信带 + 最优阈值 ★ 靶点 + 指标内嵌表）。

    uv run roc_pr_suite.py --json
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
MODEL_COL = "模型"
Y_TRUE_COL = "真实标签"
SCORE_COL = "预测概率"
TITLE = "{best_model} 取得最优判别性能（AUC={best_auc:.3f}，AP={best_ap:.3f}）"
SUBTITLE = "(a) ROC 曲线与 Youden 最优工作点｜(b) 精确率–召回率曲线与阳性率基线（n={n_obs}）"
SOURCE = "数据来源：演示风控多模型验证集评估（合成）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
WIDTH_MM = 176
ASPECT = 0.52
CITE_MM = None
OUTDIR = "outputs"
STEM = "roc_pr_suite"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    n = 650
    y = (rng.random(n) < 0.28).astype(int)
    models = {
        "融合图神经网络": (1.85, 0.95),
        "梯度提升树 GBDT": (1.35, 1.00),
        "逻辑回归基线": (0.85, 1.05),
    }
    rows = []
    for m_name, (sep, sd) in models.items():
        logits = -1.0 + sep * (y - 0.3) + rng.normal(0, sd, n)
        probs = 1.0 / (1.0 + np.exp(-logits))
        for yi, pi in zip(y, probs):
            rows.append({MODEL_COL: m_name, Y_TRUE_COL: int(yi), SCORE_COL: round(float(pi), 5)})
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


def compute_roc_pr(y_true: np.ndarray, scores: np.ndarray):
    order = np.argsort(-scores)
    y = y_true[order]
    s = scores[order]
    pos = max(float(y.sum()), 1.0)
    neg = max(float((1 - y).sum()), 1.0)
    tps = np.cumsum(y)
    fps = np.cumsum(1 - y)
    tpr = np.concatenate([[0.0], tps / pos, [1.0]])
    fpr = np.concatenate([[0.0], fps / neg, [1.0]])
    auc = float(np.trapezoid(tpr, fpr)) if hasattr(np, "trapezoid") else float(np.trapz(tpr, fpr))

    prec = tps / np.maximum(tps + fps, 1.0)
    rec = tps / pos
    prec_full = np.concatenate([[1.0], prec])
    rec_full = np.concatenate([[0.0], rec])
    ap = float(np.sum((rec_full[1:] - rec_full[:-1]) * prec_full[1:]))

    youden = (tps / pos) - (fps / neg)
    best_i = int(np.argmax(youden))
    return {
        "fpr": fpr, "tpr": tpr, "auc": auc,
        "rec": rec_full, "prec": prec_full, "ap": ap,
        "best_fpr": float((fps / neg)[best_i]),
        "best_tpr": float((tps / pos)[best_i]),
        "best_thr": float(s[best_i]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="ROC + PR 双联评估面板")
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
              "verified": False, "warnings": [], "figure": {"recipe": "roc_pr_suite"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (Y_TRUE_COL, SCORE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df = df.copy()
        if MODEL_COL not in df.columns:
            df[MODEL_COL] = "主力模型"
        df[Y_TRUE_COL] = pd.to_numeric(df[Y_TRUE_COL], errors="coerce")
        df[SCORE_COL] = pd.to_numeric(df[SCORE_COL], errors="coerce")
        dropped = int(df[[MODEL_COL, Y_TRUE_COL, SCORE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[MODEL_COL, Y_TRUE_COL, SCORE_COL])
        models = list(dict.fromkeys(df[MODEL_COL].astype(str).tolist()))[:5]

        metrics = {}
        for m in models:
            sub = df[df[MODEL_COL].astype(str) == m]
            metrics[m] = compute_roc_pr(sub[Y_TRUE_COL].to_numpy(dtype=int),
                                        sub[SCORE_COL].to_numpy(dtype=float))
        models.sort(key=lambda m: metrics[m]["auc"], reverse=True)

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme.get("scene_preset", {}).get("double_column_mm", 183) if theme.get("scene") == "academic" else theme["figure"]["default_width_mm"]
                ASPECT = 0.52
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("mckinsey_navy", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]
        colors = vs.series_color_map(models, pal, theme)

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(1, 2, wspace=0.22)
        ax_roc = fig.add_subplot(gs[0, 0])
        ax_pr = fig.add_subplot(gs[0, 1])
        vs.apply_style(ax_roc, LAYOUT, theme=theme, grid="both")
        vs.apply_style(ax_pr, LAYOUT, theme=theme, grid="both")

        # (a) ROC + 最优模型的 Bootstrap 近似羽化置信带
        ax_roc.plot([0, 1], [0, 1], color=roles["muted_text"], linestyle="--", linewidth=0.9, zorder=1.5)
        best_m = models[0]
        grid_x = np.linspace(0, 1, 120)
        best_tpr_i = np.interp(grid_x, metrics[best_m]["fpr"], metrics[best_m]["tpr"])
        se = np.sqrt(np.clip(best_tpr_i * (1.0 - best_tpr_i), 0.0, 0.25) / max(len(df) / len(models) * 0.28, 20.0))
        vs.plot_feathered_band(ax_roc, grid_x, np.clip(best_tpr_i - 1.96 * se, 0, 1),
                               np.clip(best_tpr_i + 1.96 * se, 0, 1),
                               color=colors[best_m], steps=3, max_alpha=0.24, zorder=2.0)

        for idx, m in enumerate(models):
            mt = metrics[m]
            lw = 2.1 if idx == 0 else 1.45
            ax_roc.plot(mt["fpr"], mt["tpr"], color=colors[m], linewidth=lw,
                        label=f"{m} (AUC={mt['auc']:.3f})", zorder=3.5 - idx * 0.2)
            ax_pr.plot(mt["rec"], mt["prec"], color=colors[m], linewidth=lw,
                       label=f"{m} (AP={mt['ap']:.3f})", zorder=3.5 - idx * 0.2)

        bm = metrics[best_m]
        ax_roc.scatter([bm["best_fpr"]], [bm["best_tpr"]], s=38, color=colors[best_m],
                       edgecolor="#FFFFFF", linewidth=1.1, zorder=5)
        vs.annotate_champion(ax_roc, bm["best_fpr"], bm["best_tpr"],
                             f"最优阈值 {bm['best_thr']:.2f}\nTPR={bm['best_tpr']:.2f}",
                             color=colors[best_m], offset_xy=(16, -18),
                             ha="left", va="top", theme=theme)

        prev = float(df[Y_TRUE_COL].mean())
        ax_pr.axhline(prev, color=roles["muted_text"], linestyle="--", linewidth=0.9, zorder=1.5)
        ax_pr.text(0.04, prev + 0.025, f"随机基线 (阳性率 {prev:.1%})",
                   fontsize=vs.font_size(theme, "source"), color=roles["muted_text"])

        for ax_sub, xl, yl, p_lbl in (
            (ax_roc, "假阳性率 FPR (1 - 特异度)", "真阳性率 TPR (召回率)", "(a) ROC 判别曲线"),
            (ax_pr, "召回率 Recall", "精确率 Precision", "(b) Precision–Recall 曲线"),
        ):
            ax_sub.set_xlim(-0.02, 1.02)
            ax_sub.set_ylim(-0.02, 1.04)
            ax_sub.set_xlabel(xl)
            ax_sub.set_ylabel(yl)
            ax_sub.set_title(p_lbl, loc="left", fontsize=vs.font_size(theme, "axis_label"),
                             fontweight="bold", pad=6)
            leg = ax_sub.legend(loc="lower right" if ax_sub is ax_roc else "lower left",
                                frameon=True, facecolor="#FFFFFF", framealpha=0.90,
                                fontsize=vs.font_size(theme, "source"))
            vs.style_legend(leg, theme, frame=True)

        n_per_m = int(len(df) // max(len(models), 1))
        title = vs.fill_title(TITLE, best_model=best_m, best_auc=bm["auc"], best_ap=bm["ap"])
        sub = vs.fill_title(SUBTITLE, n_obs=n_per_m)
        vs.add_header(fig, title, sub, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.08, right=0.975, top=0.77, bottom=0.15, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        sum_df = pd.DataFrame([{"model": m, "auc": round(metrics[m]["auc"], 4),
                                "ap": round(metrics[m]["ap"], 4),
                                "best_threshold": round(metrics[m]["best_thr"], 4)} for m in models])
        sum_path = Path(OUTDIR) / f"{STEM}_summary.csv"
        sum_df.to_csv(sum_path, index=False, encoding="utf-8-sig")
        outputs.append(str(sum_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "roc_pr_suite", "models": models,
                       "best_auc": round(bm["auc"], 4), "best_ap": round(bm["ap"], 4),
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

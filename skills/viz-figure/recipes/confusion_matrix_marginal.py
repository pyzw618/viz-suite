# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：混淆矩阵 + 精确率/召回率双边际条复合图（计数与行占比%双标 + 右上角综合准确率徽章）。

    uv run confusion_matrix_marginal.py --json
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
TRUE_COL = "真实类别"
PRED_COL = "预测类别"
COUNT_COL = "样本数"                  # 若输入长表无 COUNT_COL，则按行计数
TITLE = "多分类整体准确率 {acc:.1%}（Macro-F1={macro_f1:.3f}），仅相似语义对存在少量混淆"
SUBTITLE = "主矩阵标注「样本数 + 行召回占比%」｜上方边际柱为精确率 Precision，右侧边际柱为召回率 Recall"
SOURCE = "数据来源：演示意图识别测试集混淆评估（合成，N={total_n}）"
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
WIDTH_MM = 165
ASPECT = 0.72
CITE_MM = None
OUTDIR = "outputs"
STEM = "confusion_matrix_marginal"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    classes = ["账单查询", "退订挽留", "套餐升级", "故障报修", "人工转接"]
    mat = np.array([
        [168,  9,  6,  4,  3],
        [  8, 142, 14,  5, 11],
        [  5, 12, 154,  4,  5],
        [  3,  4,  3, 172,  8],
        [  4,  9,  5,  7, 145],
    ])
    rows = []
    for i, tc in enumerate(classes):
        for j, pc in enumerate(classes):
            rows.append({TRUE_COL: tc, PRED_COL: pc, COUNT_COL: int(mat[i, j])})
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
    ap = argparse.ArgumentParser(description="混淆矩阵 + 精确率/召回率双边际条")
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
              "verified": False, "warnings": [], "figure": {"recipe": "confusion_matrix_marginal"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (TRUE_COL, PRED_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df = df.copy()
        if COUNT_COL in df.columns:
            df[COUNT_COL] = pd.to_numeric(df[COUNT_COL], errors="coerce").fillna(0)
            piv = df.pivot_table(index=TRUE_COL, columns=PRED_COL, values=COUNT_COL, aggfunc="sum", fill_value=0)
        else:
            piv = pd.crosstab(df[TRUE_COL], df[PRED_COL])
        classes = list(dict.fromkeys(list(piv.index.astype(str)) + list(piv.columns.astype(str))))[:10]
        piv = piv.reindex(index=classes, columns=classes, fill_value=0)
        mat = piv.to_numpy(dtype=float)
        total_n = int(mat.sum())
        if total_n <= 0:
            raise ValueError("混淆矩阵总样本数为 0")

        row_sums = np.maximum(mat.sum(axis=1), 1.0)
        col_sums = np.maximum(mat.sum(axis=0), 1.0)
        row_pct = mat / row_sums[:, None] * 100.0
        recall = np.diag(mat) / row_sums * 100.0
        precision = np.diag(mat) / col_sums * 100.0
        f1 = 2 * (precision * recall) / np.maximum(precision + recall, 1e-9) / 100.0
        acc = float(np.diag(mat).sum() / total_n)
        macro_f1 = float(np.mean(f1))

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("economist_civic", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]
        base_col = pal.colors[0]
        err_col = pal.colors[1] if len(pal) > 1 else "#D97706"

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 3.8], width_ratios=[3.8, 1.15],
                              hspace=0.08, wspace=0.08)
        ax_top = fig.add_subplot(gs[0, 0])
        ax_kpi = fig.add_subplot(gs[0, 1])
        ax = fig.add_subplot(gs[1, 0])
        ax_right = fig.add_subplot(gs[1, 1])

        cmap = vs.sequential_cmap(base_col, light="#F8FAFC", light_mix=0.96)
        k = len(classes)
        ax.imshow(row_pct, cmap=cmap, vmin=0.0, vmax=100.0, aspect="auto")

        for r in range(k):
            for c in range(k):
                pct = float(row_pct[r, c])
                cnt = int(mat[r, c])
                fill_hex = matplotlib.colors.to_hex(cmap(pct / 100.0))
                txt_col = vs.contrast_text(fill_hex, alpha=1.0)
                if r != c and pct >= 5.0:
                    txt_col = vs.mix("#0F172A", err_col, 0.65) if pct < 45 else "#FFFFFF"
                ax.text(c, r, f"{cnt}\n({pct:.1f}%)", ha="center", va="center",
                        fontsize=vs.font_size(theme, "source"),
                        fontweight="bold" if r == c else "normal", color=txt_col)

        # 白色细格线防糊团
        ax.set_xticks(np.arange(k + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(k + 1) - 0.5, minor=True)
        ax.grid(which="minor", color="#FFFFFF", linestyle="-", linewidth=1.6)
        ax.tick_params(which="minor", bottom=False, left=False)
        ax.set_xticks(np.arange(k))
        ax.set_xticklabels(classes)
        ax.set_yticks(np.arange(k))
        ax.set_yticklabels(classes)
        ax.set_xlabel("模型预测类别")
        ax.set_ylabel("真实标注类别")
        for sp in ax.spines.values():
            sp.set_visible(False)

        # 顶部精确率柱状边际条
        vs.apply_style(ax_top, "clean_open", theme=theme)
        ax_top.spines["bottom"].set_visible(True)
        ax_top.spines["left"].set_visible(False)
        ax_top.tick_params(axis="x", bottom=False, labelbottom=False)
        ax_top.tick_params(axis="y", left=False, labelleft=False)
        ax_top.bar(np.arange(k), precision, width=0.58, **vs.bar_kwargs(base_col, theme=theme))
        for i, p_val in enumerate(precision):
            ax_top.text(i, p_val + 3.0, f"{p_val:.1f}%", ha="center", va="bottom",
                        fontsize=vs.font_size(theme, "source"), fontweight="bold", color=roles["text"])
        ax_top.set_xlim(-0.5, k - 0.5)
        ax_top.set_ylim(0, 122)
        ax_top.set_title("列精确率 Precision", loc="left",
                         fontsize=vs.font_size(theme, "source"), color=roles["muted_text"], pad=2)

        # 右侧召回率横向边际条
        vs.apply_style(ax_right, "clean_open", theme=theme)
        ax_right.spines["bottom"].set_visible(False)
        ax_right.tick_params(axis="x", bottom=False, labelbottom=False)
        ax_right.tick_params(axis="y", left=False, labelleft=False)
        ax_right.barh(np.arange(k), recall, height=0.58, **vs.bar_kwargs(pal.colors[2] if len(pal) > 2 else base_col, theme=theme))
        for i, r_val in enumerate(recall):
            ax_right.text(r_val + 3.0, i, f"{r_val:.1f}%", va="center", ha="left",
                          fontsize=vs.font_size(theme, "source"), fontweight="bold", color=roles["text"])
        ax_right.set_ylim(k - 0.5, -0.5)
        ax_right.set_xlim(0, 138)
        ax_right.set_title("行召回率", loc="left",
                           fontsize=vs.font_size(theme, "source"), color=roles["muted_text"], pad=2)

        # 右上角 KPI 摘要徽章卡
        ax_kpi.set_facecolor(vs.mix("#FFFFFF", base_col, 0.08))
        for sp in ax_kpi.spines.values():
            sp.set_visible(True)
            sp.set_color(vs.mix("#FFFFFF", base_col, 0.45))
            sp.set_linewidth(0.8)
        ax_kpi.set_xticks([])
        ax_kpi.set_yticks([])
        ax_kpi.text(0.5, 0.68, f"{acc:.1%}", transform=ax_kpi.transAxes, ha="center", va="center",
                    fontsize=vs.font_size(theme, "title"), fontweight="bold", color=base_col)
        ax_kpi.text(0.5, 0.26, f"总体准确率\nF1={macro_f1:.3f}", transform=ax_kpi.transAxes,
                    ha="center", va="center", fontsize=vs.font_size(theme, "source"), color=roles["muted_text"])

        title = vs.fill_title(TITLE, acc=acc, macro_f1=macro_f1)
        src = vs.fill_title(SOURCE, total_n=total_n)
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, src, theme=theme)
        max_u = max(vs.display_units(c) for c in classes)
        left = min(0.24, 0.075 + max_u * 0.011)
        vs.adjust_layout(fig, left=left, right=0.965, top=0.79, bottom=0.12, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        piv.to_csv(Path(OUTDIR) / f"{STEM}_matrix.csv", encoding="utf-8-sig")
        outputs.append(str(Path(OUTDIR) / f"{STEM}_matrix.csv"))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": total_n,
            "rows_dropped": 0,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "confusion_matrix_marginal", "classes": classes,
                       "accuracy": round(acc, 4), "macro_f1": round(macro_f1, 4),
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

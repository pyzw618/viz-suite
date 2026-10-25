# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：排名徽章棒棒糖图（横向排序 + 前三名徽章）。

    uv run lollipop_rank_badges.py --json
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
CATEGORY_COL = "方法"
VALUE_COL = "综合得分"
VALUE_LABEL = "综合得分（0–100）"
PALETTE = None
LAYOUT = None
TITLE = "深度集成模型综合得分最高，前两名相差 6 分"
SUBTITLE = "按得分降序｜前三名以徽章高亮｜长度编码数值"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = None
ASPECT = 0.64
CITE_MM = None
SHOW_VALUE = True
TOP_N = 3
OUTDIR = "outputs"
STEM = "lollipop_rank_badges"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        ("深度集成模型", 92), ("梯度提升树", 86), ("随机森林", 80), ("支持向量机", 74),
        ("逻辑回归", 68), ("朴素贝叶斯", 61), ("K 近邻", 55), ("决策树", 49),
    ]
    return pd.DataFrame(rows, columns=[CATEGORY_COL, VALUE_COL])


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
    ap = argparse.ArgumentParser(description="排名徽章棒棒糖图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "lollipop_rank_badges"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (CATEGORY_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[CATEGORY_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[CATEGORY_COL, VALUE_COL]).sort_values(VALUE_COL, ascending=False)
        if df.empty:
            raise ValueError("清洗后数据为空")
        if (df[VALUE_COL] < 0).any():
            warnings.append("存在负值：零基线会保留，负值向左延伸，请确认是否适合棒棒糖图")

        labels = df[CATEGORY_COL].astype(str).tolist()
        values = df[VALUE_COL].to_numpy(dtype=float)
        n = len(df)

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        warnings.extend(size["notes"])
        focal = theme["colors"]["roles"]["focal"]
        context = theme["colors"]["roles"]["context"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        ypos = np.arange(n, dtype=float)[::-1]
        max_value = float(values.max()) if n else 1.0
        pad = max_value * 0.035

        for i, (label, value, y) in enumerate(zip(labels, values, ypos)):
            ax.hlines(y, 0, value, color=context, linewidth=1.3, zorder=2)
            ax.scatter([value], [y], s=62, color=focal, edgecolor="#FFFFFF",
                       linewidth=0.8, zorder=4)
            if SHOW_VALUE:
                ax.text(value + pad, y, f"{value:,.0f}", ha="left", va="center",
                        fontsize=vs.font_size(theme, "annotation"),
                        color=theme["colors"]["roles"]["text"])
            rank = i + 1
            if rank <= TOP_N:
                badge_color = [theme["colors"]["roles"]["focal"],
                               theme["colors"]["roles"]["positive"],
                               theme["colors"]["roles"]["alert"]][rank - 1]
                text_color = vs.contrast_text(badge_color)
            else:
                badge_color = theme["colors"]["backgrounds"]["white"]
                text_color = theme["colors"]["roles"]["muted_text"]
            ax.scatter([0], [y], s=118, color=badge_color, edgecolor=context,
                       linewidth=0.8, zorder=6, clip_on=False)
            ax.text(0, y, str(rank), ha="center", va="center", fontsize=vs.font_size(theme, "source"),
                    color=text_color, fontweight="bold", zorder=7, clip_on=False)

        ax.set_yticks(ypos)
        ax.set_yticklabels(labels)
        ax.set_ylim(-0.7, n - 0.3)
        ax.set_xlim(-0.02 * max_value, max_value * 1.22)
        vs.ensure_zero_baseline(ax, "x")
        ax.set_xlabel(VALUE_LABEL)
        ax.xaxis.grid(True, linestyle="--", linewidth=0.6,
                      color=theme["colors"]["roles"]["grid"], alpha=0.35)
        ax.yaxis.grid(False)

        fig.text(0.015, 0.965, TITLE, ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"), color=theme["colors"]["roles"]["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"),
                 color=theme["colors"]["roles"]["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        longest = max(vs.display_units(x) for x in labels)
        left = min(0.40, 0.06 + longest * 0.011)
        fig.subplots_adjust(left=left, right=0.965, top=0.80, bottom=0.14)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = df.copy()
        export["rank"] = np.arange(1, n + 1)
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "lollipop_rank_badges", "ranked": labels,
                       "top_n": TOP_N, "layout": LAYOUT,
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

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：对称小提琴 + 窄箱线 + 组间差值括号（不计算 p 值）。

    uv run split_violin_box_sig.py --json
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
from matplotlib.colors import to_rgba

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
CATEGORY_COL = "方法"
GROUP_COL = "组别"
VALUE_COL = "评分"
GROUP_ORDER = None
CATEGORY_ORDER = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "改进组在方法 A 与方法 D 上提升最明显"
SUBTITLE = "左右半小提琴为两组分布｜箱体为 IQR｜括号内为组均值差（非显著性检验）"
VALUE_LABEL = "评分"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.62
CITE_MM = None
SHOW_DIFF = True
DIFF_LABELS = None                 # 形如 {"方法 A": "*"}；提供则替换差值标签，并视为上游检验结论
SIG_LABELS_NOTE = "括号标签为组均值差；如需显著性，必须由上游统计给出 p 值/星号"
HALF_WIDTH = 0.38
OUTDIR = "outputs"
STEM = "split_violin_box_sig"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    specs = {
        "方法 A": (62, 68), "方法 B": (58, 59), "方法 C": (65, 67),
        "方法 D": (60, 64), "方法 E": (55, 56),
    }
    rows = []
    for cat, (base, improved) in specs.items():
        for group, mu in (("基线", base), ("改进", improved)):
            for value in rng.normal(mu, 7.0, 60):
                rows.append({CATEGORY_COL: cat, GROUP_COL: group, VALUE_COL: round(float(np.clip(value, 0, 100)), 2)})
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
    ap = argparse.ArgumentParser(description="对称小提琴 + 箱线 + 差值括号")
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
              "verified": False, "warnings": [], "figure": {"recipe": "split_violin_box_sig"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (CATEGORY_COL, GROUP_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[CATEGORY_COL, GROUP_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[CATEGORY_COL, GROUP_COL, VALUE_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")
        groups = GROUP_ORDER or list(dict.fromkeys(df[GROUP_COL].astype(str).tolist()))
        if len(groups) != 2:
            raise ValueError(f"对称小提琴要求恰好 2 个组别，当前为 {groups}")
        categories = CATEGORY_ORDER or list(dict.fromkeys(df[CATEGORY_COL].astype(str).tolist()))

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        color_map = vs.series_color_map([str(g) for g in groups], pal, theme)
        warnings.extend(size["notes"])
        if DIFF_LABELS:
            warnings.append("显著性标签由调用方提供；请在图注写明检验方法与 p 值定义")

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        xpos = np.arange(len(categories), dtype=float)
        all_values = df[VALUE_COL].to_numpy(dtype=float)
        y_min, y_max = float(all_values.min()), float(all_values.max())
        span = max(y_max - y_min, 1.0)
        ax.set_ylim(y_min - 0.05 * span, y_max + 0.16 * span)
        ax.set_xlim(-0.6, len(categories) - 0.4)

        diffs = []
        for i, category in enumerate(categories):
            x0 = xpos[i]
            means = []
            for side, group in (("left", groups[0]), ("right", groups[1])):
                values = df[(df[CATEGORY_COL].astype(str) == category)
                            & (df[GROUP_COL].astype(str) == group)][VALUE_COL].to_numpy(dtype=float)
                if len(values) < 2:
                    warnings.append(f"{category}/{group} 只有 {len(values)} 个观测，跳过小提琴")
                    continue
                color = color_map[str(group)]
                grid, dens = vs.kde_1d(values, cut=0.0, n=220)
                width = dens / dens.max() * HALF_WIDTH if dens.max() > 0 else dens
                if side == "left":
                    ax.fill_betweenx(grid, x0 - width, x0, color=to_rgba(color, 0.22),
                                     linewidth=0, zorder=2)
                    ax.plot(x0 - width, grid, color=color, linewidth=0.9, zorder=3)
                    box_x = x0 - 0.09
                else:
                    ax.fill_betweenx(grid, x0, x0 + width, color=to_rgba(color, 0.22),
                                     linewidth=0, zorder=2)
                    ax.plot(x0 + width, grid, color=color, linewidth=0.9, zorder=3)
                    box_x = x0 + 0.09
                bp = ax.boxplot([values], positions=[box_x], widths=0.075, patch_artist=True,
                                showfliers=False, manage_ticks=False, zorder=4,
                                boxprops=dict(facecolor=to_rgba(color, 0.30),
                                              edgecolor=color, linewidth=0.8),
                                whiskerprops=dict(color=color, linewidth=0.8),
                                capprops=dict(color=color, linewidth=0.8),
                                medianprops=dict(color="#FFFFFF", linewidth=1.2))
                for patch in bp["boxes"]:
                    patch.set_zorder(4)
                ax.scatter([box_x], [float(values.mean())], marker="D", s=22, c=color,
                           edgecolors="white", linewidths=0.7, zorder=6)
                means.append((group, float(values.mean()), len(values)))
            if len(means) == 2:
                diff = means[1][1] - means[0][1]
                diffs.append((category, diff, means[0][2], means[1][2]))
                if SHOW_DIFF:
                    label = (DIFF_LABELS or {}).get(category)
                    if label is None:
                        label = f"Δ={diff:+.1f}"
                    diff_color = (theme["colors"]["roles"]["positive"] if diff > 0
                                  else theme["colors"]["roles"]["negative"] if diff < 0
                                  else theme["colors"]["roles"]["muted_text"])
                    vs.sig_bracket(ax, x0 - 0.09, x0 + 0.09, y_max + 0.06 * span, label,
                                   h_frac=0.012, color=diff_color, theme=theme)

        ax.set_xticks(xpos)
        if diffs:
            tick_labels = [f"{c}\n(n={d[2]}/{d[3]})" for c, d in zip(categories, diffs)]
        else:
            tick_labels = categories
        ax.set_xticklabels(tick_labels)
        ax.set_ylabel(VALUE_LABEL)
        ax.set_xlabel("")

        handles = [plt.Line2D([0], [0], marker="o", linestyle="none", markersize=5,
                              markerfacecolor=color_map[str(g)], markeredgecolor="white",
                              label=str(g)) for g in groups]
        leg = ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 1.005),
                        ncol=2, frameon=False, fontsize=vs.font_size(theme, "legend"),
                        handletextpad=0.5, columnspacing=1.2)
        vs.style_legend(leg, theme)

        fig.text(0.015, 0.965, TITLE, ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"), color=theme["colors"]["roles"]["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"),
                 color=theme["colors"]["roles"]["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.085, right=0.975, top=0.79, bottom=0.16)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_summary.csv"
        summary = []
        for category in categories:
            for group in groups:
                values = df[(df[CATEGORY_COL].astype(str) == category)
                            & (df[GROUP_COL].astype(str) == group)][VALUE_COL].to_numpy(dtype=float)
                if len(values):
                    summary.append({CATEGORY_COL: category, GROUP_COL: group, "n": len(values),
                                    "mean": round(float(values.mean()), 3),
                                    "median": round(float(np.median(values)), 3),
                                    "sd": round(float(values.std(ddof=1)), 3) if len(values) > 1 else 0.0})
        pd.DataFrame(summary).to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings + [SIG_LABELS_NOTE] if DIFF_LABELS else warnings,
            "figure": {"recipe": "split_violin_box_sig", "groups": groups,
                       "categories": categories,
                       "mean_diffs": {c: round(d, 3) for c, d, _, _ in diffs},
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

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：分组误差棒柱图（浅填深边 + 总体均值线）。

黄金底稿 —— 适配时只改 PARAMS 块，不要删改下方绘制逻辑中的
浅填深边、误差帽、零基线、n 标注与直接标注分支。

    uv run grouped_errorbar_bar.py --json
    uv run grouped_errorbar_bar.py --data ../../examples/fixtures/xxx.csv --json
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
from matplotlib.patches import Patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None                      # CSV/XLSX；None → 内置合成演示数据
SHEET = None
DROP_DUPLICATES = False               # True 时剔除完全重复行（会在 warnings 中报告行数）
GROUP_COL = "渠道"                    # 分类轴
SERIES_COL = "季度"                   # 分组系列；None → 单系列
VALUE_COL = "满意度"                  # 原始观测值列
ERROR_COL = None                      # 已聚合数据的误差列（与 VALUE_COL 同时给出时直接使用）
AGG = "mean_ci"                       # mean_ci | mean_sd | mean_sem | mean | count
ORIENTATION = "auto"                  # auto | horizontal | vertical
PALETTE = None
LAYOUT = None
GROUP_ORDER = None                    # 显式分类顺序；None → 按总体均值升序（横排时高者在上）
SERIES_ORDER = None
SORT_GROUPS = True
TITLE = "各渠道满意度对比：深度访谈最高、社媒舆情最低"
SUBTITLE = "按季度分组｜误差棒为 95% 置信区间（正态近似）"
VALUE_LABEL = "满意度（1–5 分）"
SOURCE = "数据来源：演示调研数据（合成）"
WIDTH_MM = None
ASPECT = 0.62
CITE_MM = None                        # 若最终会被缩放到此宽度，自动放大字号
SHOW_MEAN_LINE = True
ANNOTATE_N = True
DIRECT_LABELS = "auto"                # auto（单系列开启）| always | never
OUTDIR = "outputs"
STEM = "grouped_errorbar"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    channels = {
        "传统问卷回访": 3.55, "门店拦截访谈": 3.72, "线上行为埋点": 3.38,
        "客服工单挖掘": 3.48, "社媒舆情抓取": 3.18, "深度用户访谈": 3.85,
    }
    quarters = {"2024Q4": -0.06, "2025Q1": 0.04, "2025Q2": 0.10}
    rows = []
    for channel, base in channels.items():
        for quarter, delta in quarters.items():
            values = np.clip(rng.normal(base + delta, 0.85, 40), 1, 5)
            for value in values:
                rows.append({GROUP_COL: channel, SERIES_COL: quarter, VALUE_COL: round(float(value), 2)})
    df = pd.DataFrame(rows)
    mask = rng.random(len(df)) < 0.02
    df.loc[mask, VALUE_COL] = np.nan
    return df


def read_table(path: str | Path, sheet=None) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, sheet_name=sheet or 0)
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="latin-1")


def load_data() -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
    if SERIES_COL and SERIES_COL not in df.columns:
        raise ValueError(f"缺少系列列「{SERIES_COL}」；现有列：{list(df.columns)}")
    if GROUP_COL not in df.columns:
        raise ValueError(f"缺少分类列「{GROUP_COL}」；现有列：{list(df.columns)}")
    if VALUE_COL not in df.columns:
        raise ValueError(f"缺少数值列「{VALUE_COL}」；现有列：{list(df.columns)}")
    return df, warnings


def aggregate(df: pd.DataFrame) -> tuple[pd.DataFrame, int, list[str]]:
    warnings: list[str] = []
    work = df.copy()
    work[VALUE_COL] = pd.to_numeric(work[VALUE_COL], errors="coerce")
    if ERROR_COL and ERROR_COL in work.columns:
        work[ERROR_COL] = pd.to_numeric(work[ERROR_COL], errors="coerce")
    dropped = int(work[VALUE_COL].isna().sum())
    work = work.loc[work[VALUE_COL].notna()]
    keys = [GROUP_COL] + ([SERIES_COL] if SERIES_COL else [])
    missing_keys = int(work[keys].isna().any(axis=1).sum())
    if missing_keys:
        work = work.loc[~work[keys].isna().any(axis=1)]
        dropped += missing_keys
    if work.empty:
        raise ValueError("数值列清洗后为空，无法绘图")
    if dropped:
        warnings.append(f"{dropped} 行因缺失/空键被剔除；图注中的 n 为实际有效样本")

    rows = []
    low_n: list[str] = []
    for key, g in work.groupby(keys, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        record = {GROUP_COL: key[0]}
        if SERIES_COL:
            record[SERIES_COL] = key[1]
        values = g[VALUE_COL].to_numpy(dtype=float)
        n = len(values)
        mean = float(values.mean())
        sd = float(values.std(ddof=1)) if n > 1 else 0.0
        if ERROR_COL and ERROR_COL in g.columns and g[ERROR_COL].notna().any():
            err = float(g[ERROR_COL].mean())
            stat = "provided"
        elif AGG == "mean_ci":
            err = 1.96 * sd / np.sqrt(n) if n > 1 else 0.0
            stat = "mean_ci_normal"
        elif AGG == "mean_sd":
            err = sd
            stat = "mean_sd"
        elif AGG == "mean_sem":
            err = sd / np.sqrt(n) if n > 1 else 0.0
            stat = "mean_sem"
        elif AGG == "count":
            err, mean, stat = 0.0, float(n), "count"
        else:
            err, stat = 0.0, "mean"
        if n < 30:
            suffix = f"/{record[SERIES_COL]}" if SERIES_COL else ""
            low_n.append(f"{record[GROUP_COL]}{suffix} (n={n})")
        record.update({"mean": mean, "error": err, "n": n, "stat": stat})
        rows.append(record)

    if low_n:
        preview = "、".join(low_n[:6]) + (f" 等 {len(low_n)} 个组合" if len(low_n) > 6 else "")
        warnings.append(f"{len(low_n)} 个分组×系列组合 n<30（{preview}），正态近似 CI 仅供参考")

    agg = pd.DataFrame(rows)
    group_order = GROUP_ORDER
    if group_order is None and SORT_GROUPS:
        totals = agg.groupby(GROUP_COL)["mean"].mean().sort_values()
        group_order = list(totals.index)
    agg["__group_rank"] = agg[GROUP_COL].map({g: i for i, g in enumerate(group_order or sorted(agg[GROUP_COL].unique()))})
    if SERIES_ORDER:
        series_order = SERIES_ORDER
    else:
        series_order = list(dict.fromkeys(agg[SERIES_COL].tolist())) if SERIES_COL else [None]
    agg["__series_rank"] = agg[SERIES_COL].map({s: i for i, s in enumerate(series_order)}) if SERIES_COL else 0
    agg = agg.sort_values(["__group_rank", "__series_rank"]).reset_index(drop=True)
    agg.attrs["group_order"] = group_order or sorted(agg[GROUP_COL].unique())
    agg.attrs["series_order"] = series_order
    return agg, dropped, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="分组误差棒柱图（viz-python 黄金配方）")
    ap.add_argument("--data", default=None, help="覆盖 PARAMS.DATA_PATH")
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
              "verified": False, "warnings": [], "figure": {"recipe": "grouped_errorbar_bar"}}
    warnings: list[str] = []
    try:
        df, read_warn = load_data()
        warnings.extend(read_warn)
        blank = int(df.isna().all(axis=1).sum())
        if blank:
            df = df.loc[~df.isna().all(axis=1)].reset_index(drop=True)
            warnings.append(f"已剔除 {blank} 行全空行")
        duplicate_rows = 0
        if DROP_DUPLICATES:
            duplicate_rows = int(df.duplicated().sum())
            if duplicate_rows:
                df = df.drop_duplicates().reset_index(drop=True)
                warnings.append(f"已剔除 {duplicate_rows} 行完全重复记录（DROP_DUPLICATES=True）")
        agg, dropped, agg_warnings = aggregate(df)
        warnings.extend(dict.fromkeys(agg_warnings))

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        groups = list(agg.attrs["group_order"])
        series = [s for s in agg.attrs["series_order"] if s is not None]
        if not series:
            series = ["数值"]
        if len(series) > pal.__len__():
            raise ValueError(f"系列数 {len(series)} 超过色板 {pal.id} 的 {len(pal)} 色上限")
        colors = vs.series_color_map([str(s) for s in series], pal, theme)

        labels = [str(g) for g in groups]
        orientation = ORIENTATION
        if orientation == "auto":
            orientation = vs.pick_orientation(labels, theme=theme)
        horizontal = orientation == "horizontal"

        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        warnings.extend(size["notes"])
        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)

        k = len(series)
        bar_h = 0.78 / max(k, 1)
        offsets = (np.arange(k) - (k - 1) / 2) * bar_h
        ypos = np.arange(len(groups), dtype=float)
        label_size = vs.font_size(theme, "tick")

        group_n = agg.groupby(GROUP_COL)["n"].sum().to_dict()
        for i, s in enumerate(series):
            subset = agg[agg[SERIES_COL] == s] if SERIES_COL else agg
            subset = subset.set_index(GROUP_COL).reindex(groups)
            means = subset["mean"].to_numpy(dtype=float)
            errs = subset["error"].to_numpy(dtype=float)
            color = colors[str(s)]
            kwargs = vs.bar_kwargs(color, theme=theme)
            if horizontal:
                ax.barh(ypos + offsets[i], means, height=bar_h * 0.92, zorder=3, **kwargs)
                ax.errorbar(means, ypos + offsets[i], xerr=errs, fmt="none",
                            ecolor=color, elinewidth=1.0, capsize=2.4, capthick=1.0, zorder=4)
            else:
                ax.bar(ypos + offsets[i], means, width=bar_h * 0.92, zorder=3, **kwargs)
                ax.errorbar(ypos + offsets[i], means, yerr=errs, fmt="none",
                            ecolor=color, elinewidth=1.0, capsize=2.4, capthick=1.0, zorder=4)

        tick_labels = []
        for g in groups:
            n = int(group_n.get(g, 0))
            tick_labels.append(f"{g}\n(n={n})" if ANNOTATE_N else str(g))
        if horizontal:
            ax.set_yticks(ypos)
            ax.set_yticklabels(tick_labels, fontsize=label_size)
            ax.set_xlabel(VALUE_LABEL)
            vs.ensure_zero_baseline(ax, "x")
            hi = float(np.nanmax(agg["mean"] + agg["error"]))
            ax.set_xlim(0, hi * 1.16)
            ax.set_ylim(-0.6, len(groups) - 0.4)
            ax.xaxis.grid(True, linestyle="--", linewidth=0.6,
                          color=theme["colors"]["roles"]["grid"], alpha=0.35)
            ax.yaxis.grid(False)
        else:
            ax.set_xticks(ypos)
            ax.set_xticklabels(tick_labels, fontsize=label_size)
            ax.set_ylabel(VALUE_LABEL)
            vs.ensure_zero_baseline(ax, "y")
            hi = float(np.nanmax(agg["mean"] + agg["error"]))
            ax.set_ylim(0, hi * 1.16)
            ax.set_xlim(-0.6, len(groups) - 0.4)

        if SHOW_MEAN_LINE:
            overall = float(np.average(agg["mean"], weights=agg["n"]))
            line = theme["marks"]["mean_line"]
            if horizontal:
                ax.axvline(overall, color=line["color"], linestyle=line["linestyle"],
                           linewidth=line["linewidth"], zorder=2)
                ax.annotate(f"总体均值 {overall:.2f}", xy=(overall, 1.0),
                            xycoords=("data", "axes fraction"), xytext=(4, -2),
                            textcoords="offset points", ha="left", va="top",
                            fontsize=vs.font_size(theme, "annotation"),
                            color=theme["colors"]["roles"]["muted_text"])
            else:
                ax.axhline(overall, color=line["color"], linestyle=line["linestyle"],
                           linewidth=line["linewidth"], zorder=2)
                ax.annotate(f"总体均值 {overall:.2f}", xy=(0.0, overall),
                            xycoords=("axes fraction", "data"), xytext=(2, 4),
                            textcoords="offset points", ha="left", va="bottom",
                            fontsize=vs.font_size(theme, "annotation"),
                            color=theme["colors"]["roles"]["muted_text"])

        if k > 1:
            handles = [Patch(facecolor=vs.blend(colors[str(s)], theme["colors"]["backgrounds"]["white"],
                                                theme["marks"]["fill_alpha"]),
                             edgecolor=colors[str(s)], linewidth=theme["marks"]["edge_width"])
                       for s in series]
            leg = ax.legend(handles, [str(s) for s in series], loc="lower right",
                            bbox_to_anchor=(1.0, 1.005), ncol=k, frameon=False,
                            handlelength=1.1, columnspacing=1.2, handletextpad=0.5,
                            fontsize=vs.font_size(theme, "legend"))
            vs.style_legend(leg, theme)
        elif DIRECT_LABELS == "always" or (DIRECT_LABELS == "auto" and k == 1):
            for i, g in enumerate(groups):
                row = agg[agg[GROUP_COL] == g].iloc[0]
                if horizontal:
                    ax.text(row["mean"] + row["error"] + hi * 0.012, i, f"{row['mean']:.2f}",
                            va="center", ha="left", fontsize=label_size,
                            color=theme["colors"]["roles"]["text"])
                else:
                    ax.text(i, row["mean"] + row["error"] + hi * 0.02, f"{row['mean']:.2f}",
                            va="bottom", ha="center", fontsize=label_size,
                            color=theme["colors"]["roles"]["text"])

        fig.text(0.015, 0.965, TITLE, ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"),
                 color=theme["colors"]["roles"]["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"),
                 color=theme["colors"]["roles"]["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)

        if horizontal:
            longest = max(max(vs.display_units(part) for part in t.split("\n")) for t in tick_labels)
            left = min(0.42, 0.055 + longest * 0.011)
        else:
            left = 0.09
        fig.subplots_adjust(left=left, right=0.975, top=0.80, bottom=0.16)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)

        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export_cols = [GROUP_COL] + ([SERIES_COL] if SERIES_COL else []) + ["mean", "error", "n", "stat"]
        agg[export_cols].to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(agg["n"].sum()),
            "rows_dropped": dropped + duplicate_rows + blank,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {
                "recipe": "grouped_errorbar_bar",
                "orientation": orientation,
                "groups": [str(g) for g in groups],
                "series": [str(s) for s in series],
                "palette": pal.id,
                "layout": LAYOUT,
                "width_mm": size["width_mm"],
                "height_mm": size["height_mm"],
                "stat": str(agg["stat"].iloc[0]),
                "visual_verified": False,
                "note": "脚本只验证文件生成；审美与可读性须由 viz-audit / ViewImage 复核",
            },
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

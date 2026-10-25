# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：竖向雨云图（半小提琴 + 窄箱体 + 白边散点 + 均值菱形）。

黄金底稿 —— 适配时只改 PARAMS 块。禁止删掉多层透明度、白边散点或箱体，
它们共同承担“分布形状 / 集中趋势 / 原始观测”三层信息。

    uv run raincloud_fusion.py --json
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
from matplotlib.patches import Patch
from matplotlib.colors import to_rgba

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None                      # CSV/XLSX；None → 内置合成演示数据
SHEET = None
DROP_DUPLICATES = False               # True 时剔除完全重复行（会在 warnings 中报告行数）
GROUP_COL = "行业"
VALUE_COL = "30日留存率"
GROUP_ORDER = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "金融行业留存分布最集中，医疗行业离散度最大"
SUBTITLE = "每点为一个用户群｜半小提琴为高斯核密度｜箱体为四分位距"
VALUE_LABEL = "30 日留存率（%）"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.60
CITE_MM = None
SHOW_MEAN = True
SHOW_LEGEND = True
CLOUD_WIDTH = 0.40
POINT_OFFSET = 0.30
JITTER_WIDTH = 0.11
SIG_PAIRS = []                        # [{"a": "教育行业", "b": "金融行业", "label": "*"}]
                                      # 星号/p 值必须由上游统计给出，本脚本绝不算 p 值
OUTDIR = "outputs"
STEM = "raincloud_fusion"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    specs = {
        "教育行业": ("normal", 64, 11),
        "金融行业": ("normal", 58, 8),
        "医疗健康": ("skew", 70, 14),
        "先进制造": ("bimodal", 55, 6),
    }
    rows = []
    for group, (kind, mu, sigma) in specs.items():
        if kind == "normal":
            values = rng.normal(mu, sigma, 90)
        elif kind == "skew":
            values = rng.lognormal(np.log(mu) - 0.05, 0.22, 90)
        else:
            values = np.concatenate([
                rng.normal(mu - 7, sigma, 45),
                rng.normal(mu + 7, sigma, 45),
            ])
        values = np.clip(values, 5, 98)
        for value in values:
            rows.append({GROUP_COL: group, VALUE_COL: round(float(value), 2)})
    return pd.DataFrame(rows)


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


def kde(values: np.ndarray, grid: np.ndarray, bw: float | None = None) -> np.ndarray:
    """一维高斯核密度，带宽用 Silverman 规则；纯 numpy，避免引入 scipy。"""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < 2:
        return np.zeros_like(grid)
    sd = float(values.std(ddof=1))
    q1, q3 = np.percentile(values, [25, 75])
    iqr = float(q3 - q1)
    sigma = min(sd, iqr / 1.34) if iqr > 0 else sd
    if sigma <= 0:
        sigma = sd if sd > 0 else 1.0
    if bw is None:
        bw = 0.9 * sigma * n ** (-1 / 5)
    bw = max(bw, 1e-6)
    diff = (grid[:, None] - values[None, :]) / bw
    return np.exp(-0.5 * diff ** 2).sum(axis=1) / (n * bw * np.sqrt(2 * np.pi))


def main() -> int:
    ap = argparse.ArgumentParser(description="雨云图（viz-python 黄金配方）")
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
              "verified": False, "warnings": [], "figure": {"recipe": "raincloud_fusion"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
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
        for col in (GROUP_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[VALUE_COL].isna().sum())
        df = df.loc[df[VALUE_COL].notna()]
        missing_group = int(df[GROUP_COL].isna().sum())
        if missing_group:
            df = df.loc[df[GROUP_COL].notna()]
            dropped += missing_group
        if df.empty:
            raise ValueError("数值列清洗后为空")
        if dropped:
            warnings.append(f"{dropped} 行因缺失值/空分组被剔除")

        groups = GROUP_ORDER or list(dict.fromkeys(df[GROUP_COL].astype(str)))
        groups = [g for g in groups if g in set(df[GROUP_COL].astype(str))]
        if len(groups) < 1:
            raise ValueError("没有可用的分组")
        data = {g: df.loc[df[GROUP_COL].astype(str) == g, VALUE_COL].to_numpy(dtype=float) for g in groups}

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        if len(groups) > len(pal):
            raise ValueError(f"分组数 {len(groups)} 超过色板 {pal.id} 的 {len(pal)} 色上限")
        colors = vs.series_color_map(groups, pal, theme)

        warnings.extend(size["notes"])
        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)

        positions = np.arange(len(groups), dtype=float)
        rng = np.random.default_rng(DEMO_SEED)
        all_values = np.concatenate(list(data.values()))
        lo, hi = float(all_values.min()), float(all_values.max())
        span = max(hi - lo, 1e-6)
        y_low, y_high = lo - 0.07 * span, hi + 0.07 * span
        bracket_room = 0.10 * span * (len(SIG_PAIRS) + 1) if SIG_PAIRS else 0.0
        ax.set_ylim(y_low, y_high + bracket_room)

        summaries = []
        tick_pt = vs.font_size(theme, "tick")
        for i, group in enumerate(groups):
            values = data[group]
            color = colors[group]
            x0 = positions[i]
            cloud_center = x0 - 0.11
            # cut=0：半小提琴严格落在实测范围内，避免长尾被坐标轴裁成平口
            grid = np.linspace(values.min(), values.max(), 300)
            dens = kde(values, grid)
            width = dens / dens.max() * CLOUD_WIDTH if dens.max() > 0 else dens
            ax.fill_betweenx(grid, cloud_center - width, cloud_center,
                             facecolor=to_rgba(color, theme["marks"]["violin_alpha"]),
                             edgecolor="none", zorder=2)
            ax.plot(cloud_center - width, grid, color=color, linewidth=0.9, zorder=3)

            bp = ax.boxplot([values], positions=[x0], widths=0.10, patch_artist=True,
                            showfliers=False, manage_ticks=False, zorder=4,
                            boxprops=dict(facecolor=to_rgba(color, theme["marks"]["box_alpha"]),
                                          edgecolor=color, linewidth=0.9),
                            whiskerprops=dict(color=color, linewidth=0.9),
                            capprops=dict(color=color, linewidth=0.9),
                            medianprops=dict(color="#FFFFFF", linewidth=1.4))
            for patch in bp["boxes"]:
                patch.set_zorder(4)

            jitter = rng.uniform(-JITTER_WIDTH, JITTER_WIDTH, len(values))
            ax.scatter(x0 + POINT_OFFSET + jitter, values, s=8,
                       c=[to_rgba(color, 0.55)], edgecolors="white", linewidths=0.3, zorder=3)

            mean = float(values.mean())
            if SHOW_MEAN:
                ax.scatter([x0], [mean], marker="D", s=26, c=color,
                           edgecolors="white", linewidths=0.8, zorder=6)

            q1, median, q3 = np.percentile(values, [25, 50, 75])
            sd = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            summaries.append({
                GROUP_COL: group, "n": len(values), "mean": round(mean, 3),
                "median": round(float(median), 3), "sd": round(sd, 3),
                "q1": round(float(q1), 3), "q3": round(float(q3), 3),
                "min": round(float(values.min()), 3), "max": round(float(values.max()), 3),
            })
            if len(values) < 20:
                warnings.append(f"「{group}」n={len(values)}<20，核密度与四分位估计不稳定")

        ax.set_xticks(positions)
        ax.set_xticklabels([f"{g}\n(n={len(data[g])})" for g in groups], fontsize=tick_pt)
        ax.set_xlim(-0.6, len(groups) - 0.4)
        ax.set_ylabel(VALUE_LABEL)
        ax.set_xlabel("")

        if SIG_PAIRS:
            base_y = y_high
            step = 0.10 * span
            for idx, pair in enumerate(SIG_PAIRS):
                if pair.get("a") not in groups or pair.get("b") not in groups:
                    warnings.append(f"显著性括号引用了不存在的分组：{pair}")
                    continue
                x1, x2 = positions[groups.index(pair["a"])], positions[groups.index(pair["b"])]
                vs.sig_bracket(ax, x1, x2, base_y + idx * step, pair.get("label", "n.s."),
                               h_frac=0.012, theme=theme)
            warnings.append("显著性标记来自调用方输入；请在图注写明检验方法与 p 值来源")

        if SHOW_LEGEND:
            legend_color = theme["colors"]["roles"]["muted_text"]
            handles = [
                Patch(facecolor=to_rgba(legend_color, theme["marks"]["violin_alpha"]),
                      edgecolor=legend_color, linewidth=0.8, label="半小提琴（密度）"),
                Patch(facecolor=to_rgba(legend_color, theme["marks"]["box_alpha"]),
                      edgecolor=legend_color, linewidth=0.8, label="箱体（IQR）"),
                Line2D([0], [0], marker="o", linestyle="none", markersize=4,
                       markerfacecolor=to_rgba(legend_color, 0.55),
                       markeredgecolor="white", label="观测点"),
                Line2D([0], [0], marker="D", linestyle="none", markersize=4.5,
                       markerfacecolor=legend_color, markeredgecolor="white", label="均值"),
            ]
            leg = ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.20),
                            frameon=False, ncol=4,
                            fontsize=vs.font_size(theme, "legend"),
                            handlelength=1.0, columnspacing=1.2, handletextpad=0.5)
            vs.style_legend(leg, theme)

        fig.text(0.015, 0.965, TITLE, ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"),
                 color=theme["colors"]["roles"]["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"),
                 color=theme["colors"]["roles"]["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.095, right=0.975, top=0.80, bottom=0.225)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_summary.csv"
        pd.DataFrame(summaries).to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped + duplicate_rows + blank,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {
                "recipe": "raincloud_fusion",
                "groups": groups,
                "palette": pal.id,
                "layout": LAYOUT,
                "width_mm": size["width_mm"],
                "height_mm": size["height_mm"],
                "kde": "gaussian_silverman",
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

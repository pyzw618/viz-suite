# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：Kaplan–Meier 生存阶梯曲线 + 下方在险人数表（共享 X 轴）。

    uv run km_survival_risk_table.py --json
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
TIME_COL = "随访月"
EVENT_COL = "事件"
GROUP_COL = "组别"
GROUP_ORDER = None
RISK_TIMES = [0, 6, 12, 18, 24, 30, 36]
X_LABEL = "随访时间（月）"
Y_LABEL = "生存率"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "联合组生存率最高，对照组中位生存期约 17 个月"
SUBTITLE = "阶梯曲线为 Kaplan–Meier 估计｜竖线为删失｜下方为各时点在险人数｜未做显著性检验"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.70
CITE_MM = None
OUTDIR = "outputs"
STEM = "km_survival_risk_table"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    specs = {"对照组": 24.0, "单药组": 31.0, "联合组": 38.0}
    rows = []
    for group, scale in specs.items():
        for _ in range(120):
            t = float(rng.exponential(scale))
            censor = min(float(rng.uniform(8, 100)), 36.0)
            if censor < t:
                rows.append({GROUP_COL: group, TIME_COL: round(censor, 1), EVENT_COL: 0})
            elif t <= 36:
                rows.append({GROUP_COL: group, TIME_COL: round(t, 1), EVENT_COL: 1})
            else:
                rows.append({GROUP_COL: group, TIME_COL: 36.0, EVENT_COL: 0})
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


def km_curve(times: np.ndarray, events: np.ndarray):
    order = np.argsort(times)
    times, events = times[order], events[order]
    unique_times = np.unique(times)
    at_risk = len(times)
    survival = 1.0
    xs, ys = [0.0], [1.0]
    censors: list[tuple[float, float]] = []
    for t in unique_times:
        n = int(np.sum(times >= t))
        d = int(np.sum((times == t) & (events == 1)))
        if d > 0:
            survival *= (1 - d / max(n, 1))
            xs.append(float(t))
            ys.append(survival)
        for _ in range(int(np.sum((times == t) & (events == 0)))):
            censors.append((float(t), survival))
    return np.asarray(xs), np.asarray(ys), censors


def step_value(xs: np.ndarray, ys: np.ndarray, t: float) -> float:
    idx = np.searchsorted(xs, t, side="right") - 1
    return float(ys[max(idx, 0)])


def main() -> int:
    ap = argparse.ArgumentParser(description="KM 生存曲线 + 在险人数表")
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
              "verified": False, "warnings": [], "figure": {"recipe": "km_survival_risk_table"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (TIME_COL, EVENT_COL, GROUP_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[TIME_COL] = pd.to_numeric(df[TIME_COL], errors="coerce")
        df[EVENT_COL] = pd.to_numeric(df[EVENT_COL], errors="coerce")
        dropped = int(df[[TIME_COL, EVENT_COL, GROUP_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[TIME_COL, EVENT_COL, GROUP_COL])
        df = df[df[TIME_COL] >= 0]
        if df.empty:
            raise ValueError("清洗后数据为空")
        groups = GROUP_ORDER or list(dict.fromkeys(df[GROUP_COL].astype(str).tolist()))

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme.get("scene_preset", {}).get("double_column_mm", 183) if (True and theme.get("scene") == "academic") else theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        colors = vs.series_color_map([str(g) for g in groups], pal, theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(2, 1, height_ratios=[4.0, 1.18], hspace=0.08)
        ax = fig.add_subplot(gs[0, 0])
        ax_risk = fig.add_subplot(gs[1, 0], sharex=ax)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.set_ylabel(Y_LABEL)
        ax.set_ylim(0, 1.03)
        ax.set_xlim(-1.8, max(RISK_TIMES[-1], float(df[TIME_COL].max())) + 0.8)
        ax.axhline(0.5, color=roles["muted_text"], linestyle=":", linewidth=0.9, zorder=1)

        medians = {}
        for group in groups:
            sub = df[df[GROUP_COL].astype(str) == group]
            xs, ys, censors = km_curve(sub[TIME_COL].to_numpy(dtype=float),
                                       sub[EVENT_COL].to_numpy(dtype=float))
            ax.step(xs, ys, where="post", color=colors[str(group)], linewidth=1.9,
                    zorder=3, label=str(group))
            if censors:
                cx = [c[0] for c in censors]
                cy = [c[1] for c in censors]
                ax.plot(cx, cy, linestyle="none", marker="|", markersize=4,
                        color=colors[str(group)], alpha=0.8, zorder=4)
            if ys.min() <= 0.5:
                below = np.where(ys <= 0.5)[0]
                medians[str(group)] = float(xs[below[0]]) if len(below) else None
            else:
                medians[str(group)] = None

        ax.set_xticklabels([])
        legend_labels = []
        for group in groups:
            median = medians.get(str(group))
            legend_labels.append(f"{group}（中位 {median:.0f} 月）" if median is not None else str(group))
        leg = ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.005), ncol=len(groups),
                        frameon=False, fontsize=vs.font_size(theme, "legend"),
                        handlelength=1.6, columnspacing=1.2)
        for text, label in zip(leg.get_texts(), legend_labels):
            text.set_text(label)
        vs.style_legend(leg, theme)

        ax_risk.set_ylim(-0.6, len(groups) - 0.4)
        ax_risk.set_yticks(np.arange(len(groups)))
        ax_risk.set_yticklabels([str(g) for g in groups])
        ax_risk.set_xlabel(X_LABEL)
        ax_risk.set_ylabel("在险人数")
        ax_risk.tick_params(axis="x", labelsize=vs.font_size(theme, "annotation"))
        ax_risk.set_xticks(RISK_TIMES)
        ax_risk.set_xticklabels([str(t) for t in RISK_TIMES])
        ax.tick_params(axis="x", labelbottom=False)
        for spine in ("top", "right", "left"):
            ax_risk.spines[spine].set_visible(False)
        ax_risk.grid(False)

        for row_idx, group in enumerate(groups):
            sub = df[df[GROUP_COL].astype(str) == group]
            if row_idx % 2 == 0:
                ax_risk.axhspan(row_idx - 0.5, row_idx + 0.5, color=roles["grid"],
                                alpha=0.20, zorder=0)
            for t in RISK_TIMES:
                count = int((sub[TIME_COL] >= t).sum())
                ax_risk.text(t, row_idx, str(count), ha="center", va="center",
                             fontsize=vs.font_size(theme, "annotation"),
                             color=roles["text"])

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.14, right=0.975, top=0.79, bottom=0.13, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        df.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "km_survival_risk_table", "groups": groups, "medians": medians,
                       "risk_times": RISK_TIMES, "palette": pal.id, "layout": LAYOUT,
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

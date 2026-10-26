# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：事件研究 / 双重差分（DID）动态处理效应图（事前平行趋势安慰剂区 + 冲击分界 + 羽化置信带）。

    uv run event_study_did.py --json
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
REL_TIME_COL = "相对期数"
EST_COL = "效应估计"
LOW_COL = "下限95"
HIGH_COL = "上限95"
SHOCK_X = -0.5                        # 政策/事件发生分割线（基期 t=-1 归零）
PRE_TREND_P = 0.64                    # 上游回归提供的事前平行趋势联合 F 检验 p 值（若无则设为 None）
TITLE = "政策实施后动态处理效应持续显著放大（事后平均 ATT={att:+.2f}，第 {peak_t} 期达峰值）"
SUBTITLE = "左区灰底为事前平行趋势安慰剂检验（基期 t=-1 标准化为 0）｜阴影为 95% 聚类稳健置信带"
X_LABEL = "距政策冲击相对期数（期）"
Y_LABEL = "动态处理效应估计值（百分点）"
SOURCE = "数据来源：演示面板双向固定效应 TWFE / Sun-Abraham 事件研究估计（合成）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
WIDTH_MM = 166
ASPECT = 0.58
CITE_MM = None
OUTDIR = "outputs"
STEM = "event_study_did"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        (-5, -0.25, -1.35, 0.85),
        (-4,  0.18, -0.88, 1.24),
        (-3, -0.12, -1.10, 0.86),
        (-2,  0.22, -0.74, 1.18),
        (-1,  0.00,  0.00, 0.00),
        ( 0,  1.65,  0.62, 2.68),
        ( 1,  2.95,  1.84, 4.06),
        ( 2,  4.10,  2.92, 5.28),
        ( 3,  4.85,  3.58, 6.12),
        ( 4,  4.62,  3.25, 5.99),
        ( 5,  4.48,  3.04, 5.92),
    ]
    return pd.DataFrame(rows, columns=[REL_TIME_COL, EST_COL, LOW_COL, HIGH_COL])


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
    ap = argparse.ArgumentParser(description="事件研究 / DID 动态处理效应图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "event_study_did"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (REL_TIME_COL, EST_COL, LOW_COL, HIGH_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df = df.copy()
        for col in (REL_TIME_COL, EST_COL, LOW_COL, HIGH_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[REL_TIME_COL, EST_COL, LOW_COL, HIGH_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[REL_TIME_COL, EST_COL, LOW_COL, HIGH_COL]).sort_values(REL_TIME_COL).reset_index(drop=True)
        if df.empty:
            raise ValueError("清洗后无可用期数")

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("mckinsey_navy", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]
        post_col = pal.colors[0]
        pre_col = "#64748B"

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)

        t = df[REL_TIME_COL].to_numpy(dtype=float)
        est = df[EST_COL].to_numpy(dtype=float)
        lo = df[LOW_COL].to_numpy(dtype=float)
        hi = df[HIGH_COL].to_numpy(dtype=float)

        x_min, x_max = float(t.min()) - 0.55, float(t.max()) + 0.55
        y_min, y_max = float(min(lo.min(), -0.5)), float(max(hi.max(), 0.5))
        yspan = max(y_max - y_min, 1.0)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min - 0.16 * yspan, y_max + 0.24 * yspan)

        # 事前安慰剂检验底色区 + 零效应水平线 + 政策冲击竖线
        ax.axvspan(x_min, SHOCK_X, color="#F1F5F9", alpha=0.82, zorder=0.4)
        ax.axhline(0.0, color=roles["text"], linewidth=0.95, linestyle="-", alpha=0.65, zorder=1.5)
        ax.axvline(SHOCK_X, color=pal.colors[1] if len(pal) > 1 else "#DA1E28",
                   linestyle="--", linewidth=1.25, zorder=2.2)
        ax.text(SHOCK_X + 0.14, y_max + 0.12 * yspan, "政策冲击介入 (t=0)",
                ha="left", va="top", fontsize=vs.font_size(theme, "annotation"),
                fontweight="bold", color=pal.colors[1] if len(pal) > 1 else "#DA1E28")

        pre_mask = t <= SHOCK_X
        post_mask = t >= -1.0  # 从基期 -1 无缝衔接到事后
        if post_mask.sum() >= 2:
            vs.plot_feathered_band(ax, t[post_mask], lo[post_mask], hi[post_mask],
                                   color=post_col, steps=4, max_alpha=0.25, zorder=1.8)
            ax.plot(t[post_mask], est[post_mask], color=post_col, linewidth=1.9, zorder=3.5)

        if pre_mask.sum() >= 2:
            ax.plot(t[pre_mask], est[pre_mask], color=pre_col, linewidth=1.25, linestyle="--", zorder=3.0)

        for ti, ei, li, hi_v in zip(t, est, lo, hi):
            is_post = ti > SHOCK_X
            c = post_col if is_post else pre_col
            if hi_v > li + 1e-6:
                ax.plot([ti, ti], [li, hi_v], color=c, linewidth=1.15, zorder=3.6)
                ax.plot([ti - 0.10, ti + 0.10], [li, li], color=c, linewidth=1.0, zorder=3.6)
                ax.plot([ti - 0.10, ti + 0.10], [hi_v, hi_v], color=c, linewidth=1.0, zorder=3.6)
            mk = "D" if abs(ti - (-1.0)) < 1e-6 else "o"
            ax.scatter([ti], [ei], s=34, marker=mk,
                       color="#FFFFFF" if mk == "D" else c,
                       edgecolor=c if mk == "D" else "#FFFFFF",
                       linewidth=1.3 if mk == "D" else 0.9, zorder=4.5)

        post_only = df[df[REL_TIME_COL] > SHOCK_X]
        att = float(post_only[EST_COL].mean()) if not post_only.empty else 0.0
        peak_row = post_only.loc[post_only[EST_COL].idxmax()] if not post_only.empty else df.iloc[-1]
        vs.annotate_champion(ax, float(peak_row[REL_TIME_COL]), float(peak_row[HIGH_COL]),
                             f"峰值 {peak_row[EST_COL]:+.2f}pp",
                             color=post_col, offset_xy=(0, 8), theme=theme)

        pre_note = f"事前平行趋势检验 p = {PRE_TREND_P:.2f}" if (PRE_TREND_P is not None and DATA_PATH is None) else "事前安慰剂期 (t < 0)"
        ax.text(0.025, 0.94, f"{pre_note}\n事后平均 ATT = {att:+.2f}pp",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=vs.font_size(theme, "source"), color=roles["text"],
                bbox={"boxstyle": "round,pad=0.30,rounding_size=0.35",
                      "facecolor": "#FFFFFF", "edgecolor": "#CBD5E1", "linewidth": 0.8})

        ax.set_xticks([int(v) if float(v).is_integer() else v for v in t])
        ax.set_xticklabels([f"t={int(v):+d}" if int(v) != 0 else "t=0" for v in t])
        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(Y_LABEL)

        title = vs.fill_title(TITLE, att=att, peak_t=int(peak_row[REL_TIME_COL]))
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.10, right=0.97, top=0.80, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        df.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "event_study_did", "att_post": round(att, 4),
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

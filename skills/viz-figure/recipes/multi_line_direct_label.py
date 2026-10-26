# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：多序列焦点折线 + 尾端直接标注 + 分位参考带（消除图例来回比对与单薄裸线）。

    uv run multi_line_direct_label.py --json
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
X_COL = "季度"
SERIES_COL = "业务线"
VALUE_COL = "净留存率"
FOCAL_SERIES = None                   # None → 自动选末期最高与次高双焦点，其余归为低饱和背景参考
SHOW_REF_BAND = True                  # 绘制跨序列 P25–P75 分位参考带
TITLE = "{top_series} 净留存率持续领跑并于末期达 {top_last:.1f}%，较行业中枢高出 {spread:+.1f}pp"
SUBTITLE = "焦点序列加粗实线配尾端直接标注｜浅色羽化带为同期跨业务线 P25–P75 分位区间"
X_LABEL = "统计周期"
Y_LABEL = "净收入留存率 NRR（%）"
SOURCE = "数据来源：演示经营监控数据（合成）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
WIDTH_MM = 168
ASPECT = 0.58
CITE_MM = None
OUTDIR = "outputs"
STEM = "multi_line_direct_label"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    periods = ["23Q1", "23Q2", "23Q3", "23Q4", "24Q1", "24Q2", "24Q3", "24Q4", "25Q1", "25Q2"]
    trajectories = {
        "AI 数据平台": [108.0, 111.5, 114.2, 118.0, 121.4, 125.8, 127.2, 130.5, 132.8, 135.4],
        "云原生安全": [106.2, 107.8, 109.5, 111.0, 113.6, 115.2, 117.8, 119.4, 121.0, 122.6],
        "企业协同套件": [104.5, 105.0, 104.2, 103.8, 104.6, 105.5, 106.1, 106.8, 107.2, 107.9],
        "全渠道营销云": [102.0, 101.2, 99.8, 98.5, 99.2, 100.4, 101.1, 101.8, 102.0, 102.4],
        "传统本地部署": [99.5, 98.4, 97.2, 96.0, 95.1, 94.3, 93.8, 93.0, 92.4, 91.8],
    }
    rows = []
    for p_i, p in enumerate(periods):
        for name, vals in trajectories.items():
            rows.append({X_COL: p, SERIES_COL: name, VALUE_COL: vals[p_i]})
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


def repel_positions(targets: list[float], min_gap: float, lo: float, hi: float) -> list[float]:
    if not targets:
        return []
    order = np.argsort(targets)
    ys = [float(targets[i]) for i in order]
    for _ in range(40):
        for i in range(1, len(ys)):
            if ys[i] - ys[i - 1] < min_gap:
                mid = 0.5 * (ys[i] + ys[i - 1])
                ys[i - 1] = mid - 0.5 * min_gap
                ys[i] = mid + 0.5 * min_gap
        if ys[0] < lo:
            ys[0] = lo
        if ys[-1] > hi:
            ys[-1] = hi
    out = [0.0] * len(targets)
    for rank_idx, orig_idx in enumerate(order):
        out[orig_idx] = ys[rank_idx]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="多序列焦点折线 + 尾端直接标注")
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
              "verified": False, "warnings": [], "figure": {"recipe": "multi_line_direct_label"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (X_COL, SERIES_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[X_COL, SERIES_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[X_COL, SERIES_COL, VALUE_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")

        x_vals = list(dict.fromkeys(df[X_COL].astype(str).tolist()))
        series_all = list(dict.fromkeys(df[SERIES_COL].astype(str).tolist()))
        pivot = (df.assign(**{X_COL: df[X_COL].astype(str), SERIES_COL: df[SERIES_COL].astype(str)})
                   .pivot_table(index=X_COL, columns=SERIES_COL, values=VALUE_COL, aggfunc="mean")
                   .reindex(index=x_vals, columns=series_all))
        last_scores = pivot.iloc[-1].sort_values(ascending=False)
        series_sorted = list(last_scores.index)
        pivot = pivot[series_sorted]

        focals = list(FOCAL_SERIES) if FOCAL_SERIES else series_sorted[:min(2, len(series_sorted))]

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

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        xpos = np.arange(len(x_vals), dtype=float)

        if SHOW_REF_BAND and len(series_sorted) >= 3:
            q25 = np.nanpercentile(pivot.to_numpy(dtype=float), 25, axis=1)
            q75 = np.nanpercentile(pivot.to_numpy(dtype=float), 75, axis=1)
            vs.plot_feathered_band(ax, xpos, q25, q75, color="#94A3B8", steps=3,
                                   max_alpha=0.22, zorder=1.2)
            ax.text(xpos[1], float(q75[1]) + 0.6, "行业 P25–P75 分位带",
                    fontsize=vs.font_size(theme, "source"), color=roles["muted_text"], zorder=2)

        if float(np.nanmin(pivot.to_numpy())) <= 100.0 <= float(np.nanmax(pivot.to_numpy())):
            ax.axhline(100.0, color=roles["muted_text"], linestyle=":", linewidth=0.85, zorder=1.8)

        focal_colors = vs.series_color_map(focals, pal, theme)
        end_ys = []
        end_meta = []
        for s in series_sorted:
            y = pivot[s].to_numpy(dtype=float)
            is_foc = s in focals
            col = focal_colors[s] if is_foc else vs.mix("#CBD5E1", "#64748B", 0.45)
            lw = 2.2 if s == focals[0] else (1.75 if is_foc else 1.05)
            z = 4.5 if is_foc else 2.4
            ax.plot(xpos, y, color=col, linewidth=lw, zorder=z, solid_capstyle="round")
            if is_foc:
                ax.scatter([xpos[-1]], [y[-1]], s=28, color=col, edgecolor="#FFFFFF",
                           linewidth=0.9, zorder=z + 0.3)
            delta = float(y[-1] - y[0])
            end_ys.append(float(y[-1]))
            end_meta.append((s, col, is_foc, float(y[-1]), delta))

        ylo = float(np.nanmin(pivot.to_numpy(dtype=float)))
        yhi = float(np.nanmax(pivot.to_numpy(dtype=float)))
        span = max(yhi - ylo, 1.0)
        ax.set_ylim(ylo - 0.12 * span, yhi + 0.20 * span)
        ax.set_xlim(-0.25, len(x_vals) - 1 + 0.25)

        placed_ys = repel_positions(end_ys, min_gap=span * 0.085,
                                    lo=ylo - 0.05 * span, hi=yhi + 0.12 * span)
        for (s, col, is_foc, raw_y, delta), py in zip(end_meta, placed_ys):
            ax.plot([xpos[-1] + 0.06, xpos[-1] + 0.22], [raw_y, py],
                    color=col, linewidth=0.75, alpha=0.75, clip_on=False)
            sign = "+" if delta >= 0 else ""
            txt = f"{s}  {raw_y:.1f} ({sign}{delta:.1f})"
            ax.text(xpos[-1] + 0.26, py, txt, va="center", ha="left",
                    fontsize=vs.font_size(theme, "annotation" if is_foc else "source"),
                    fontweight="bold" if is_foc else "normal",
                    color=col if is_foc else roles["muted_text"], clip_on=False)

        # 峰值语义胶囊锚点
        top_s = focals[0]
        top_vec = pivot[top_s].to_numpy(dtype=float)
        pk_i = int(np.nanargmax(top_vec))
        med_last = float(np.nanmedian(pivot.iloc[-1].to_numpy(dtype=float)))
        spread = float(top_vec[-1] - med_last)
        vs.annotate_champion(ax, float(xpos[pk_i]), float(top_vec[pk_i]),
                             f"峰值 {top_vec[pk_i]:.1f}%",
                             color=focal_colors[top_s],
                             offset_xy=(-18 if pk_i >= len(xpos) - 2 else 0, 12),
                             ha="right" if pk_i >= len(xpos) - 2 else "center",
                             theme=theme)

        step = max(1, int(np.ceil(len(x_vals) / 10)))
        ax.set_xticks(xpos[::step])
        ax.set_xticklabels([x_vals[i] for i in range(0, len(x_vals), step)])
        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(Y_LABEL)

        title = vs.fill_title(TITLE, top_series=top_s, top_last=float(top_vec[-1]), spread=spread)
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        max_lbl_u = max(vs.display_units(f"{m[0]}  {m[3]:.1f} (+00.0)") for m in end_meta)
        right = max(0.64, 0.96 - max_lbl_u * 0.0115)
        vs.adjust_layout(fig, left=0.10, right=right, top=0.80, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        pivot.to_csv(data_path, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "multi_line_direct_label", "series": series_sorted,
                       "focal": focals, "palette": pal.id, "layout": LAYOUT,
                       "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit()},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

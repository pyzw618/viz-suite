# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：趋势 + 环比/同比涨跌拆分双面板旗舰复合图（主图实测与 LOWESS 平滑 + 副图同轴 Δ% 正负脉冲柱）。

    uv run trend_yoy_decomposed.py --json
    uv run trend_yoy_decomposed.py --data examples/fixtures/电商大促_全渠道36天事件冲击_脏数据.csv --json
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
X_COL = "日期"
VALUE_COL = "GMV_万元"
DELTA_COL = None                      # None → 自动由相邻期计算环比涨跌%
EVENT_COL = "事件标记"
TITLE = "峰值达 {peak_val:,.1f}（{peak_x}），平滑中枢较期初抬升 {net_gain:+.1f}%"
SUBTITLE = "(a) 实测序列、LOWESS 平滑趋势与事件窗口｜(b) 同轴逐期涨跌脉冲 Δ%（消除双轴刻度误导）"
Y_LABEL_TOP = "规模指标"
Y_LABEL_BOT = "逐期 Δ%"
X_LABEL = "时间序列"
SOURCE = "数据来源：演示经营高频追踪台账（合成）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
WIDTH_MM = 172
ASPECT = 0.64
CITE_MM = None
OUTDIR = "outputs"
STEM = "trend_yoy_decomposed"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    dates = pd.date_range("2026-05-01", periods=28, freq="D")
    vals = []
    events = []
    for i, d in enumerate(dates):
        base = 420.0 + i * 7.2 + 28.0 * np.sin(i / 2.6)
        ev = ""
        if i == 11:
            base += 115.0
            ev = "预售开启"
        elif i == 19:
            base += 210.0
            ev = "大促爆发"
        vals.append(round(float(base + rng.normal(0, 14)), 1))
        events.append(ev)
    return pd.DataFrame({X_COL: dates.strftime("%m-%d"), VALUE_COL: vals, EVENT_COL: events})


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


def clean_num(s: pd.Series) -> pd.Series:
    cleaned = (s.astype(str)
                .str.replace(r"[¥$€£,，%％\s]", "", regex=True)
                .replace({"—": np.nan, "-": np.nan, "N/A": np.nan, "nan": np.nan, "": np.nan}))
    return pd.to_numeric(cleaned, errors="coerce")


def main() -> int:
    ap = argparse.ArgumentParser(description="趋势 + YoY/MoM 涨跌拆分双面板图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "trend_yoy_decomposed"}}
    warnings: list[str] = []
    try:
        raw_df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        raw_df = raw_df.dropna(how="all").drop_duplicates().copy()
        xc = X_COL if X_COL in raw_df.columns else raw_df.columns[0]
        vc = VALUE_COL if VALUE_COL in raw_df.columns else next(
            (c for c in raw_df.columns[1:] if clean_num(raw_df[c]).notna().sum() >= 3), raw_df.columns[1]
        )
        raw_df[vc] = clean_num(raw_df[vc])
        dropped = int(raw_df[vc].isna().sum())
        raw_df = raw_df.dropna(subset=[xc, vc]).copy()
        ev_map = {}
        if EVENT_COL in raw_df.columns:
            for k_val, ev in zip(raw_df[xc].astype(str), raw_df[EVENT_COL].fillna("").astype(str)):
                if ev.strip() and ev.strip().lower() != "nan":
                    ev_map[k_val] = ev.strip()
        agg = raw_df.groupby(xc, sort=False, as_index=False)[vc].sum()
        if len(agg) < 3:
            raise ValueError("时间点数少于 3，无法分解趋势与涨跌")

        x_labels = agg[xc].astype(str).tolist()
        y_vals = agg[vc].to_numpy(dtype=float)
        if DELTA_COL and DELTA_COL in raw_df.columns:
            deltas = raw_df.groupby(xc, sort=False)[DELTA_COL].mean().to_numpy(dtype=float)
        else:
            prev = np.roll(y_vals, 1)
            prev[0] = y_vals[0]
            deltas = np.where(np.abs(prev) > 1e-9, 100.0 * (y_vals - prev) / np.abs(prev), 0.0)
            deltas[0] = 0.0

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene") and not args.layout:
            LAYOUT = theme.get("layout_family", LAYOUT)
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("mckinsey_navy", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]
        main_col = pal.colors[0]
        trend_col = pal.colors[1] if len(pal) > 1 else "#D97706"

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(2, 1, height_ratios=[2.75, 1.15], hspace=0.12)
        ax_top = fig.add_subplot(gs[0, 0])
        ax_bot = fig.add_subplot(gs[1, 0], sharex=ax_top)
        vs.apply_style(ax_top, LAYOUT, theme=theme)
        vs.apply_style(ax_bot, LAYOUT, theme=theme)
        ax_top.tick_params(axis="x", labelbottom=False)

        xpos = np.arange(len(x_labels), dtype=float)
        xg, yg = vs.smooth_trend(xpos, y_vals, frac=0.36, n_grid=180)
        ax_top.fill_between(xpos, float(y_vals.min()) * 0.90, y_vals,
                            color=vs.mix("#FFFFFF", main_col, 0.22), alpha=0.55, zorder=1.5)
        ax_top.plot(xpos, y_vals, color=main_col, linewidth=1.35, marker="o", markersize=3.4,
                    markerfacecolor="#FFFFFF", markeredgecolor=main_col, markeredgewidth=0.9,
                    label="实测值", zorder=3.0)
        ax_top.plot(xg, yg, color=trend_col, linewidth=2.15, linestyle="-",
                    label="LOWESS 平滑中枢", zorder=4.0)

        for idx_e, lbl_x in enumerate(x_labels):
            if lbl_x in ev_map:
                ax_top.axvline(idx_e, color=roles["muted_text"], linestyle=":", linewidth=0.9, zorder=2.0)
                ax_bot.axvline(idx_e, color=roles["muted_text"], linestyle=":", linewidth=0.9, zorder=2.0)

        pk_i = int(np.argmax(y_vals))
        ylo, yhi = float(y_vals.min()) * 0.90, float(y_vals.max()) * 1.20
        ax_top.set_ylim(ylo, yhi)
        near_r = pk_i >= len(xpos) - 4
        ev_tag = f"·{ev_map[x_labels[pk_i]]}" if x_labels[pk_i] in ev_map else ""
        vs.annotate_champion(ax_top, float(xpos[pk_i]), float(y_vals[pk_i]),
                             f"{y_vals[pk_i]:,.1f} ({x_labels[pk_i]}{ev_tag})",
                             color=main_col, offset_xy=(-10 if near_r else 0, 10),
                             ha="right" if near_r else "center", theme=theme)
        leg = ax_top.legend(loc="upper left", frameon=False, ncol=2, fontsize=vs.font_size(theme, "legend"))
        vs.style_legend(leg, theme)
        ax_top.set_ylabel(vc if Y_LABEL_TOP == "规模指标" else Y_LABEL_TOP)

        # 下方正负涨跌脉冲条
        pos_c = roles.get("positive", "#198038")
        neg_c = roles.get("negative", "#DA1E28")
        ax_bot.axhline(0.0, color=roles["text"], linewidth=0.85, zorder=2.0)
        for xi, dv in zip(xpos, deltas):
            c_bar = pos_c if dv >= 0 else neg_c
            ax_bot.bar(xi, dv, width=0.64, **vs.bar_kwargs(c_bar, theme=theme), zorder=3.0)
        d_abs = max(float(np.max(np.abs(deltas))), 5.0)
        ax_bot.set_ylim(-d_abs * 1.25, d_abs * 1.28)
        ax_bot.set_ylabel(Y_LABEL_BOT)
        ax_bot.set_xlabel(X_LABEL)

        step = max(1, int(np.ceil(len(x_labels) / 9)))
        ax_bot.set_xticks(xpos[::step])
        ax_bot.set_xticklabels([x_labels[i][-5:] if len(x_labels[i]) >= 10 else x_labels[i]
                                for i in range(0, len(x_labels), step)])
        ax_top.set_xlim(-0.6, len(x_labels) - 0.4)

        net_gain = 100.0 * (float(yg[-1]) - float(yg[0])) / max(abs(float(yg[0])), 1e-9)
        title = vs.fill_title(TITLE, peak_val=float(y_vals[pk_i]), peak_x=x_labels[pk_i], net_gain=net_gain)
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.10, right=0.97, top=0.79, bottom=0.13, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        agg["delta_pct"] = np.round(deltas, 2)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        agg.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(agg)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "trend_yoy_decomposed", "n_points": int(len(agg)),
                       "peak": round(float(y_vals[pk_i]), 2), "palette": pal.id, "layout": LAYOUT,
                       "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit()},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

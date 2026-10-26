# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：多序列嵌套置信带折线图（50% / 80% / 95% 区间）。

    uv run nested_ci_bands_line.py --json
"""
import argparse
import json
import re
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
X_COL = "月份"
SERIES_COL = "模型"
MEAN_COL = "均值"
BAND_COLS = [("low_95", "high_95"), ("low_80", "high_80"), ("low_50", "high_50")]
BAND_ALPHAS = [0.07, 0.11, 0.16]
SERIES_ORDER = None
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "模型 B 准确率持续领先，三组区间随样本增加收窄"
SUBTITLE = "阴影由浅到深依次为 95%、80%、50% 区间"
X_LABEL = "月份"
VALUE_LABEL = "准确率（%）"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.60
CITE_MM = None
DIRECT_LABELS = True
OUTDIR = "outputs"
STEM = "nested_ci_bands_line"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def natural_key(value):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(value))]


def demo_frame() -> pd.DataFrame:
    months = [f"{i}月" for i in range(1, 13)]
    specs = {"模型 A": (72, 0.55), "模型 B": (75, 0.70), "模型 C": (70, 0.45)}
    rows = []
    for name, (base, slope) in specs.items():
        for i, month in enumerate(months):
            mean = base + slope * i
            shrink = 1.0 - 0.035 * i
            rows.append({
                X_COL: month, SERIES_COL: name, MEAN_COL: round(mean, 2),
                "low_95": round(mean - 3.2 * shrink, 2), "high_95": round(mean + 3.2 * shrink, 2),
                "low_80": round(mean - 2.1 * shrink, 2), "high_80": round(mean + 2.1 * shrink, 2),
                "low_50": round(mean - 1.2 * shrink, 2), "high_50": round(mean + 1.2 * shrink, 2),
            })
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
    ap = argparse.ArgumentParser(description="嵌套置信带折线图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "nested_ci_bands_line"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (X_COL, SERIES_COL, MEAN_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        numeric_cols = [MEAN_COL] + [c for pair in BAND_COLS for c in pair if c in df.columns]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[X_COL, SERIES_COL, MEAN_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[X_COL, SERIES_COL, MEAN_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")

        x_values = list(dict.fromkeys(df[X_COL].tolist()))
        try:
            x_values = sorted(x_values, key=natural_key)
        except TypeError:
            pass
        series = SERIES_ORDER or list(dict.fromkeys(df[SERIES_COL].tolist()))

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme.get("scene_preset", {}).get("double_column_mm", 183) if (False and theme.get("scene") == "academic") else theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        colors = vs.series_color_map([str(s) for s in series], pal, theme)
        warnings.extend(size["notes"])

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        xpos = np.arange(len(x_values), dtype=float)

        # 由宽到窄绘制：先铺所有系列的 95% 带，再叠 80%、50%，避免跨系列串色
        available_bands = [(lo, hi) for lo, hi in BAND_COLS if lo in df.columns and hi in df.columns]
        for (lo, hi), alpha in zip(available_bands, BAND_ALPHAS):
            for name in series:
                sub = df[df[SERIES_COL] == name].set_index(X_COL).reindex(x_values)
                lower = sub[lo].to_numpy(dtype=float)
                upper = sub[hi].to_numpy(dtype=float)
                if np.isnan(lower).all() or np.isnan(upper).all():
                    continue
                ax.fill_between(xpos, lower, upper, color=colors[str(name)], alpha=alpha,
                                linewidth=0, zorder=2)
        for name in series:
            sub = df[df[SERIES_COL] == name].set_index(X_COL).reindex(x_values)
            means = sub[MEAN_COL].to_numpy(dtype=float)
            ax.plot(xpos, means, color=colors[str(name)], linewidth=1.8,
                    marker="o", markersize=3.4, markerfacecolor="#FFFFFF",
                    markeredgecolor=colors[str(name)], markeredgewidth=0.9, zorder=4)

        ax.set_xticks(xpos)
        ax.set_xticklabels([str(v) for v in x_values])
        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(VALUE_LABEL)
        ax.set_xlim(-0.5, len(x_values) - 0.5 + (2.0 if DIRECT_LABELS else 0.0))
        finite = df[MEAN_COL].to_numpy(dtype=float)
        band_values = []
        for lo, hi in available_bands:
            band_values.extend(df[lo].dropna().to_numpy(dtype=float))
            band_values.extend(df[hi].dropna().to_numpy(dtype=float))
        if band_values:
            finite = np.concatenate([finite, np.asarray(band_values, dtype=float)])
        span = max(float(finite.max() - finite.min()), 1.0)
        ax.set_ylim(float(finite.min()) - 0.06 * span, float(finite.max()) + 0.06 * span)

        if DIRECT_LABELS and len(series) <= 5:
            label_x = len(x_values) - 0.35
            points = []
            for name in series:
                sub = df[df[SERIES_COL] == name].set_index(X_COL).reindex(x_values)
                y = float(sub[MEAN_COL].iloc[-1])
                points.append([name, y])
            points.sort(key=lambda p: p[1])
            gap = 0.045 * span
            for i in range(1, len(points)):
                if points[i][1] - points[i - 1][1] < gap:
                    points[i][1] = points[i - 1][1] + gap
            for name, y in points:
                ax.text(label_x, y, str(name), ha="left", va="center",
                        fontsize=vs.font_size(theme, "annotation"),
                        color=colors[str(name)], fontweight="bold")
        else:
            handles = [plt.Line2D([0], [0], color=colors[str(s)], linewidth=1.8,
                                  marker="o", markersize=3.4, markerfacecolor="white",
                                  markeredgecolor=colors[str(s)]) for s in series]
            leg = ax.legend(handles, [str(s) for s in series], loc="lower right",
                            bbox_to_anchor=(1.0, 1.005), ncol=min(len(series), 4),
                            frameon=False, fontsize=vs.font_size(theme, "legend"))
            vs.style_legend(leg, theme)

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.09, right=0.975, top=0.80, bottom=0.15, theme=theme)

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
            "figure": {"recipe": "nested_ci_bands_line", "series": [str(s) for s in series],
                       "bands": [list(b) for b in available_bands], "palette": pal.id,
                       "layout": LAYOUT, "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit(), "visual_verified": False,
                       "note": "脚本已验证文件与文本包围盒；审美与可读性仍须经 audit_export 与宿主读图工具复核"},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

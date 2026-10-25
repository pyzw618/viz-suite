# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：Bland–Altman 一致性偏差带图（平均偏差 + 95% 一致性界限）。

    uv run bland_altman.py --json
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
A_COL = "方法A"
B_COL = "方法B"
A_LABEL = "方法 A"
B_LABEL = "方法 B"
X_LABEL = "两种方法均值"
Y_LABEL = "差值（方法 A − 方法 B）"
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "平均偏差 {bias:+.2f}，95% 一致性界限 {loa_low:+.2f} 至 {loa_high:+.2f}"
SUBTITLE = "蓝点为界限内，红点为界限外｜虚线为 ±1.96 SD 一致性界限｜阴影为一致区间"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.62
CITE_MM = None
OUTDIR = "outputs"
STEM = "bland_altman"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    a = rng.normal(70, 12, 120)
    b = a - (2.5 + 0.04 * (a - 70) + rng.normal(0, 1.6, 120))
    return pd.DataFrame({A_COL: np.round(a, 2), B_COL: np.round(b, 2)})


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
    ap = argparse.ArgumentParser(description="Bland–Altman 一致性偏差图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "bland_altman"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (A_COL, B_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        for col in (A_COL, B_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[A_COL, B_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[A_COL, B_COL])
        if len(df) < 3:
            raise ValueError("有效配对少于 3 对，无法估计一致性界限")

        a = df[A_COL].to_numpy(dtype=float)
        b = df[B_COL].to_numpy(dtype=float)
        means = (a + b) / 2
        diffs = a - b
        bias = float(diffs.mean())
        sd = float(diffs.std(ddof=1))
        loa_low, loa_high = bias - 1.96 * sd, bias + 1.96 * sd
        outside = (diffs < loa_low) | (diffs > loa_high)
        if len(df) < 30:
            warnings.append(f"配对 n={len(df)}<30，一致性界限估计不稳定")
        stats = {"bias": bias, "loa_low": loa_low, "loa_high": loa_high, "sd": sd, "n": len(df)}

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.axhspan(loa_low, loa_high, color=roles["focal"], alpha=0.05, zorder=0)
        ax.axhline(0, color=roles["muted_text"], linestyle=":", linewidth=0.9, zorder=1)
        ax.axhline(bias, color=roles["focal"], linestyle="-", linewidth=1.3, zorder=2)
        for y, label in ((loa_low, f"下限 {loa_low:+.2f}"), (loa_high, f"上限 {loa_high:+.2f}")):
            ax.axhline(y, color=roles["muted_text"], linestyle="--", linewidth=1.0, zorder=2)
            ax.text(0.995, y, label, transform=ax.get_yaxis_transform(), ha="right", va="bottom",
                    fontsize=vs.font_size(theme, "annotation"), color=roles["muted_text"])
        ax.text(0.995, bias, f"平均偏差 {bias:+.2f}", transform=ax.get_yaxis_transform(),
                ha="right", va="bottom", fontsize=vs.font_size(theme, "annotation"),
                color=roles["focal"], fontweight="bold")

        inside_color = roles["focal"]
        outside_color = roles["negative"]
        ax.scatter(means[~outside], diffs[~outside], s=18, color=inside_color, alpha=0.52,
                   edgecolors="white", linewidths=0.35, zorder=4)
        if outside.any():
            ax.scatter(means[outside], diffs[outside], s=26, color=outside_color, alpha=0.70,
                       edgecolors="white", linewidths=0.4, zorder=5)

        info = (f"n = {len(df)}\n偏差 = {bias:+.2f} ｜ SD = {sd:.2f}\n"
                f"界限内 {int((~outside).sum())} ｜ 界限外 {int(outside.sum())}")
        ax.text(0.015, 0.97, info, transform=ax.transAxes, ha="left", va="top",
                fontsize=vs.font_size(theme, "annotation"), color=roles["text"],
                linespacing=1.35,
                bbox=dict(facecolor="#FFFFFF", edgecolor=roles["grid"], linewidth=0.5,
                          boxstyle="round,pad=0.35", alpha=0.92))

        ax.set_xlabel(X_LABEL)
        ax.set_ylabel(Y_LABEL)
        x_pad = (means.max() - means.min()) * 0.04 if means.max() > means.min() else 1.0
        y_pad = max((diffs.max() - diffs.min()) * 0.10, 0.3)
        ax.set_xlim(means.min() - x_pad, means.max() + x_pad)
        ax.set_ylim(min(diffs.min(), loa_low) - y_pad, max(diffs.max(), loa_high) + y_pad)

        fig.text(0.015, 0.965, vs.fill_title(TITLE, **stats), ha="left", va="top", fontweight="bold",
                 fontsize=vs.font_size(theme, "title"), color=roles["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"), color=roles["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.10, right=0.975, top=0.80, bottom=0.14)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = df.copy()
        export["mean"] = means.round(4)
        export["diff"] = diffs.round(4)
        export["outside_loa"] = outside
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "bland_altman", "n": len(df), "bias": round(bias, 3),
                       "sd": round(sd, 3), "loa": [round(loa_low, 3), round(loa_high, 3)],
                       "outside": int(outside.sum()), "palette": pal.id, "layout": LAYOUT,
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

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：前后对比哑铃图（零基线 + Δ 直接标注 + 方向双编码）。

    uv run dumbbell_before_after.py --json
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
CATEGORY_COL = "城市"
BEFORE_COL = "2024"
AFTER_COL = "2025"
BEFORE_LABEL = "2024"
AFTER_LABEL = "2025"
VALUE_LABEL = "满意度得分（0–100）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "杭州与成都提升最快，北京与西安小幅回落"
SUBTITLE = "灰点=2024，蓝点=2025｜绿线=提升，红线=下降｜X 轴保留 0 基线"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.64
CITE_MM = None
OUTDIR = "outputs"
STEM = "dumbbell_before_after"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        ("杭州", 71, 80), ("成都", 69, 76), ("武汉", 66, 71), ("深圳", 74, 78),
        ("上海", 82, 85), ("广州", 70, 72), ("北京", 86, 85), ("西安", 68, 66),
    ]
    return pd.DataFrame(rows, columns=[CATEGORY_COL, BEFORE_COL, AFTER_COL])


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
    ap = argparse.ArgumentParser(description="前后对比哑铃图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "dumbbell_before_after"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (CATEGORY_COL, BEFORE_COL, AFTER_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        for col in (BEFORE_COL, AFTER_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[CATEGORY_COL, BEFORE_COL, AFTER_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[CATEGORY_COL, BEFORE_COL, AFTER_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")
        df["__delta"] = df[AFTER_COL] - df[BEFORE_COL]
        df = df.sort_values(AFTER_COL, ascending=True).reset_index(drop=True)

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
        warnings.extend(size["notes"])

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        roles = theme["colors"]["roles"]
        ypos = np.arange(len(df), dtype=float)
        before = df[BEFORE_COL].to_numpy(dtype=float)
        after = df[AFTER_COL].to_numpy(dtype=float)
        deltas = df["__delta"].to_numpy(dtype=float)

        for y, b, a, d in zip(ypos, before, after, deltas):
            color = roles["positive"] if d > 0 else roles["negative"] if d < 0 else roles["muted_text"]
            ax.plot([b, a], [y, y], color=color, linewidth=2.0, alpha=0.65, zorder=2,
                    solid_capstyle="round")
            ax.scatter([b], [y], s=46, color=roles["muted_text"], edgecolor="#FFFFFF",
                       linewidth=0.7, zorder=4)
            ax.scatter([a], [y], s=62, color=roles["focal"], edgecolor="#FFFFFF",
                       linewidth=0.9, zorder=5)
            arrow = "▲" if d > 0 else "▼" if d < 0 else "■"
            ax.text(max(a, b) + 1.6, y, f"{arrow} {d:+.0f}", ha="left", va="center",
                    fontsize=vs.font_size(theme, "annotation"), color=color)

        ax.set_yticks(ypos)
        ax.set_yticklabels(df[CATEGORY_COL].astype(str).tolist())
        ax.set_xlabel(VALUE_LABEL)
        ax.set_xlim(0, max(float(after.max()), float(before.max())) * 1.16)
        ax.set_ylim(-0.7, len(df) - 0.3)
        vs.ensure_zero_baseline(ax, "x")
        ax.xaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.35)
        ax.yaxis.grid(False)

        handles = [
            plt.Line2D([0], [0], marker="o", linestyle="none", markersize=5.5,
                       markerfacecolor=roles["muted_text"], markeredgecolor="white", label=BEFORE_LABEL),
            plt.Line2D([0], [0], marker="o", linestyle="none", markersize=6.5,
                       markerfacecolor=roles["focal"], markeredgecolor="white", label=AFTER_LABEL),
        ]
        leg = ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 1.005),
                        ncol=2, frameon=False, fontsize=vs.font_size(theme, "legend"),
                        handletextpad=0.5, columnspacing=1.2)
        vs.style_legend(leg, theme)

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.11, right=0.965, top=0.80, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        df.rename(columns={"__delta": "delta"}).to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "dumbbell_before_after", "categories": df[CATEGORY_COL].astype(str).tolist(),
                       "deltas": [round(float(v), 2) for v in deltas],
                       "layout": LAYOUT, "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit(), "visual_verified": False,
                       "note": "脚本只验证文件生成；审美与可读性须由 viz-audit / ViewImage 复核"},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

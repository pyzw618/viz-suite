# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：两阶段排名斜率图（名次上升/下降双编码）。

    uv run slope_rank_change.py --json
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
NAME_COL = "产品"
BEFORE_COL = "2024排名"
AFTER_COL = "2025排名"
BEFORE_LABEL = "2024"
AFTER_LABEL = "2025"
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
TITLE = "产品 C 从第 5 升至第 2，产品 B 稳居第一"
SUBTITLE = "绿色=排名上升，红色=下降，灰色=持平｜粗线为最大变动｜# 后为名次"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 150
ASPECT = 0.68
CITE_MM = None
OUTDIR = "outputs"
STEM = "slope_rank_change"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        ("产品 A", 2, 4), ("产品 B", 1, 1), ("产品 C", 5, 2),
        ("产品 D", 3, 6), ("产品 E", 6, 3), ("产品 F", 4, 5),
    ]
    return pd.DataFrame(rows, columns=[NAME_COL, BEFORE_COL, AFTER_COL])


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
    ap = argparse.ArgumentParser(description="两阶段排名斜率图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "slope_rank_change"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (NAME_COL, BEFORE_COL, AFTER_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        for col in (BEFORE_COL, AFTER_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[NAME_COL, BEFORE_COL, AFTER_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[NAME_COL, BEFORE_COL, AFTER_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")
        for col in (BEFORE_COL, AFTER_COL):
            if df[col].duplicated().any():
                warnings.append(f"「{col}」存在重复名次：斜率图通常要求每阶段名次唯一")
        n = len(df)
        df["__delta"] = df[BEFORE_COL] - df[AFTER_COL]  # 正数 = 名次上升

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
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.axis("off")
        ax.set_xlim(-0.32, 1.32)
        ax.set_ylim(n + 0.6, 0.4)

        for rank in range(1, n + 1):
            ax.hlines(rank, 0, 1, color=roles["grid"], linewidth=0.6,
                      linestyle=":", zorder=1, alpha=0.6)

        for _, row in df.iterrows():
            before, after = float(row[BEFORE_COL]), float(row[AFTER_COL])
            delta = after - before
            color = roles["positive"] if delta < 0 else roles["negative"] if delta > 0 else roles["muted_text"]
            lw = 2.6 if abs(delta) == df["__delta"].abs().max() and delta != 0 else 1.5
            ax.plot([0, 1], [before, after], color=color, linewidth=lw, alpha=0.9, zorder=3,
                    solid_capstyle="round")
            ax.scatter([0, 1], [before, after], s=42, color=color, edgecolor="#FFFFFF",
                       linewidth=0.8, zorder=4)
            name = str(row[NAME_COL])
            ax.text(-0.045, before, f"{name}  #{int(before)}", ha="right", va="center",
                    fontsize=vs.font_size(theme, "annotation"), color=roles["text"])
            ax.text(1.045, after, f"#{int(after)}  {name}", ha="left", va="center",
                    fontsize=vs.font_size(theme, "annotation"), color=roles["text"])

        for x, label in ((0, BEFORE_LABEL), (1, AFTER_LABEL)):
            ax.text(x, 0.55, label, ha="center", va="bottom", fontweight="bold",
                    fontsize=vs.font_size(theme, "title"), color=roles["text"])

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.20, right=0.80, top=0.80, bottom=0.10, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        df.rename(columns={"__delta": "rank_change"}).to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "slope_rank_change", "n": n,
                       "biggest_mover": df.loc[df["__delta"].abs().idxmax(), NAME_COL],
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

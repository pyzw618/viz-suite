# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：多阶段名次凹凸轨迹图（Bump Chart）。

    uv run bump_rank_trajectory.py --json
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
PERIOD_COL = "季度"
NAME_COL = "产品"
RANK_COL = "名次"
PERIOD_ORDER = None
NAME_ORDER = None
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "产品 B 连续六个季度第一，产品 C 升至第二，产品 A 跌至末位"
SUBTITLE = "纵轴为名次（1 在顶部）｜颜色区分产品｜右侧直接标注"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.62
CITE_MM = None
OUTDIR = "outputs"
STEM = "bump_rank_trajectory"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    data = {
        "产品 A": [2, 3, 4, 5, 6, 6],
        "产品 B": [1, 1, 1, 1, 1, 1],
        "产品 C": [5, 4, 3, 2, 2, 2],
        "产品 D": [3, 2, 2, 3, 4, 5],
        "产品 E": [6, 6, 5, 4, 3, 3],
        "产品 F": [4, 5, 6, 6, 5, 4],
    }
    periods = ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1", "2025Q2"]
    rows = []
    for name, ranks in data.items():
        for period, rank in zip(periods, ranks):
            rows.append({PERIOD_COL: period, NAME_COL: name, RANK_COL: rank})
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


def deoverlap(values: list[float], gap: float, low: float, high: float) -> list[float]:
    pairs = sorted(enumerate(values), key=lambda p: p[1])
    adjusted = []
    for _, value in pairs:
        if adjusted and value - adjusted[-1] < gap:
            value = adjusted[-1] + gap
        adjusted.append(value)
    shift = max(0.0, adjusted[-1] - high) if adjusted else 0.0
    if shift:
        adjusted = [v - shift for v in adjusted]
    if adjusted and adjusted[0] < low:
        delta = low - adjusted[0]
        adjusted = [v + delta for v in adjusted]
    out = [0.0] * len(values)
    for (idx, _), value in zip(pairs, adjusted):
        out[idx] = value
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="多阶段名次凹凸轨迹图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "bump_rank_trajectory"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (PERIOD_COL, NAME_COL, RANK_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[RANK_COL] = pd.to_numeric(df[RANK_COL], errors="coerce")
        dropped = int(df[[PERIOD_COL, NAME_COL, RANK_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[PERIOD_COL, NAME_COL, RANK_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")
        df[RANK_COL] = df[RANK_COL].round().astype(int)
        periods = PERIOD_ORDER or list(dict.fromkeys(df[PERIOD_COL].astype(str).tolist()))
        names = NAME_ORDER or list(dict.fromkeys(df[NAME_COL].astype(str).tolist()))
        for period in periods:
            ranks = df[df[PERIOD_COL].astype(str) == period][RANK_COL].tolist()
            if len(ranks) != len(set(ranks)):
                warnings.append(f"{period} 存在重复名次：请确认排名口径")
        n = max(len(names), int(df[RANK_COL].max()))

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
        color_map = vs.series_color_map([str(nm) for nm in names], pal, theme)
        warnings.extend(size["notes"])

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        xpos = {p: float(i) for i, p in enumerate(periods)}
        for name in names:
            sub = df[df[NAME_COL].astype(str) == name].copy()
            sub["__x"] = sub[PERIOD_COL].astype(str).map(xpos)
            sub = sub.dropna(subset=["__x"]).sort_values("__x")
            if sub.empty:
                continue
            ax.plot(sub["__x"], sub[RANK_COL], color=color_map[str(name)], linewidth=1.8,
                    marker="o", markersize=4.6, markerfacecolor="#FFFFFF",
                    markeredgecolor=color_map[str(name)], markeredgewidth=1.1,
                    zorder=3, solid_capstyle="round")
            last = sub.iloc[-1]
            ax.text(float(last["__x"]) + 0.10, float(last[RANK_COL]), str(name),
                    ha="left", va="center", fontsize=vs.font_size(theme, "annotation"),
                    color=color_map[str(name)], fontweight="bold")

        ax.set_xticks([xpos[p] for p in periods])
        ax.set_xticklabels([str(p) for p in periods])
        ax.set_yticks(range(1, n + 1))
        ax.set_yticklabels([f"第 {i}" for i in range(1, n + 1)])
        ax.invert_yaxis()
        ax.set_ylim(n + 0.6, 0.4)
        ax.set_xlim(-0.35, len(periods) - 0.35)
        ax.set_xlabel("")
        ax.set_ylabel("名次")
        ax.yaxis.grid(True, linestyle="--", linewidth=0.6,
                      color=theme["colors"]["roles"]["grid"], alpha=0.35)
        ax.xaxis.grid(False)

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.09, right=0.85, top=0.80, bottom=0.13, theme=theme)

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
            "figure": {"recipe": "bump_rank_trajectory", "periods": periods, "names": names,
                       "palette": pal.id, "layout": LAYOUT,
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

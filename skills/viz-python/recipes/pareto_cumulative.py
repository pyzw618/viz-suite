# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：帕累托降序柱 + 右轴累计占比曲线（80% 关键少数）。

    uv run pareto_cumulative.py --json
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
CATEGORY_COL = "缺陷类型"
VALUE_COL = "问题量"
VALUE_LABEL = "问题量（件）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "前 {cutoff} 类缺陷贡献约 {cut_pct:.0f}% 的问题量"
SUBTITLE = "柱为问题量（左轴，零基线），折线为累计占比（右轴）｜右轴仅用于累计占比"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.62
CITE_MM = None
THRESHOLD = 80.0
OUTDIR = "outputs"
STEM = "pareto_cumulative"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        ("外观划痕", 420), ("屏幕亮点", 310), ("电池鼓包", 240), ("接口松动", 180),
        ("异响", 120), ("按键失灵", 90), ("充电异常", 70), ("发热", 45),
        ("包装破损", 30), ("其他", 20),
    ]
    return pd.DataFrame(rows, columns=[CATEGORY_COL, VALUE_COL])


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
    ap = argparse.ArgumentParser(description="帕累托图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "pareto_cumulative"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (CATEGORY_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[CATEGORY_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[CATEGORY_COL, VALUE_COL])
        df = df[df[VALUE_COL] >= 0].sort_values(VALUE_COL, ascending=False).reset_index(drop=True)
        if df.empty or df[VALUE_COL].sum() <= 0:
            raise ValueError("没有可用的正数值")
        total = float(df[VALUE_COL].sum())
        cum = df[VALUE_COL].cumsum() / total * 100.0
        cutoff = int(np.searchsorted(cum.to_numpy(dtype=float), THRESHOLD) + 1)
        cutoff = min(max(cutoff, 1), len(df))
        cut_pct = float(cum.iloc[cutoff - 1])
        stats = {"cutoff": cutoff, "cut_pct": cut_pct, "n": len(df)}

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
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax2 = ax.twinx()
        x = np.arange(len(df), dtype=float)
        colors = [roles["focal"] if i < cutoff else roles["context"] for i in range(len(df))]
        for i, value in enumerate(df[VALUE_COL].to_numpy(dtype=float)):
            ax.bar(i, value, width=0.62, **vs.bar_kwargs(colors[i], theme=theme), zorder=3)

        ax2.plot(x, cum.to_numpy(dtype=float), color=roles["text"], linewidth=1.4,
                 marker="o", markersize=4.2, markerfacecolor="#FFFFFF",
                 markeredgecolor=roles["text"], markeredgewidth=0.9, zorder=5)
        ax2.axhline(THRESHOLD, color=roles["alert"], linestyle="--", linewidth=0.9, zorder=2)
        ax2.text(len(df) - 0.5, THRESHOLD + 2.0, f"{THRESHOLD:g}% 阈值", ha="right", va="bottom",
                 fontsize=vs.font_size(theme, "annotation"), color=roles["alert"])
        ax.axvline(cutoff - 0.5, color=roles["muted_text"], linestyle=":", linewidth=1.0, zorder=2)

        ax.set_xticks(x)
        ax.set_xticklabels(df[CATEGORY_COL].astype(str).tolist(),
                           fontsize=vs.font_size(theme, "annotation"))
        ax.set_ylabel(VALUE_LABEL)
        ax.set_xlabel("")
        ax.set_xlim(-0.6, len(df) - 0.4)
        ax.set_ylim(0, float(df[VALUE_COL].max()) * 1.18)
        vs.ensure_zero_baseline(ax, "y")
        ax.yaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.35)
        ax.xaxis.grid(False)

        ax2.set_ylim(0, 105)
        ax2.set_yticks([0, 20, 40, 60, 80, 100])
        ax2.set_ylabel("累计占比（%）")
        ax2.tick_params(axis="y", labelsize=vs.font_size(theme, "annotation"),
                        colors=roles["muted_text"], length=2)
        ax2.spines["right"].set_color(roles["muted_text"])
        ax2.spines["right"].set_linewidth(0.8)
        for spine in ("top", "left", "bottom"):
            ax2.spines[spine].set_visible(False)
        ax2.grid(False)

        # 图例已由副标题与左右轴标题承担，避免遮挡累计占比曲线

        vs.add_header(fig, vs.fill_title(TITLE, **stats), SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.10, right=0.91, top=0.80, bottom=0.16, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = df.copy()
        export["cumulative_pct"] = cum.round(2)
        export["vital_few"] = np.arange(len(df)) < cutoff
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "pareto_cumulative", "cutoff": cutoff, "cut_pct": round(cut_pct, 2),
                       "threshold": THRESHOLD, "palette": pal.id, "layout": LAYOUT,
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

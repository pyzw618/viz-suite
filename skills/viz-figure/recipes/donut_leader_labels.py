# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：外置引线圆环图（≤6 类，直接标注）。

    uv run donut_leader_labels.py --json
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
CATEGORY_COL = "渠道"
VALUE_COL = "订单量"
VALUE_UNIT = "单"
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
TITLE = "门店与企业微信贡献近六成订单"
SUBTITLE = "按订单量排序｜外置引线直接标注，不使用图例"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 150
ASPECT = 0.70
CITE_MM = None
MAX_CATEGORIES = 6
OUTDIR = "outputs"
STEM = "donut_leader_labels"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        ("企业微信专属客户经理", 1284), ("线下门店导购", 986), ("400 电话热线", 742),
        ("电商平台旗舰店", 531), ("微信小程序", 318), ("社交平台私信", 142),
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
    ap = argparse.ArgumentParser(description="外置引线圆环图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "donut_leader_labels"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (CATEGORY_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[CATEGORY_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[CATEGORY_COL, VALUE_COL])
        grouped = df.groupby(CATEGORY_COL, as_index=False)[VALUE_COL].sum()
        grouped = grouped[grouped[VALUE_COL] > 0].sort_values(VALUE_COL, ascending=False)
        if grouped.empty:
            raise ValueError("没有可用的正数值")
        if len(grouped) > MAX_CATEGORIES:
            raise ValueError(f"分类数 {len(grouped)} 超过圆环图上限 {MAX_CATEGORIES}；请合并小类或改用排序条形图")

        labels = grouped[CATEGORY_COL].astype(str).tolist()
        values = grouped[VALUE_COL].to_numpy(dtype=float)
        total = float(values.sum())
        shares = values / total * 100.0

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
        colors = pal.pick(len(labels))
        warnings.extend(size["notes"])

        fig, ax = vs.figure(size["figsize"], theme=theme)
        ax.set_aspect("equal")
        wedges, _ = ax.pie(
            values, colors=colors, startangle=90, counterclock=False,
            wedgeprops=dict(width=0.36, edgecolor="#FFFFFF", linewidth=1.8),
            radius=1.0,
        )
        ax.set_xlim(-1.75, 1.75)
        ax.set_ylim(-1.35, 1.35)
        ax.axis("off")

        gap = 0.135
        right_idx = [i for i, w in enumerate(wedges) if np.cos((w.theta1 + w.theta2) / 2) >= 0]
        left_idx = [i for i, w in enumerate(wedges) if i not in right_idx]
        for side, indices in (("right", right_idx), ("left", left_idx)):
            angles = [(wedges[i].theta1 + wedges[i].theta2) / 2 for i in indices]
            ys = [np.sin(np.deg2rad(a)) * 1.18 for a in angles]
            adjusted = deoverlap(ys, gap, -1.05, 1.05) if ys else []
            for i, y in zip(indices, adjusted):
                angle = np.deg2rad((wedges[i].theta1 + wedges[i].theta2) / 2)
                x_anchor = np.cos(angle) * 1.01
                y_anchor = np.sin(angle) * 1.01
                text_x = 1.38 if side == "right" else -1.38
                ha = "left" if side == "right" else "right"
                ax.annotate(
                    f"{labels[i]}\n{shares[i]:.1f}%  ({values[i]:,.0f} {VALUE_UNIT})",
                    xy=(x_anchor, y_anchor), xytext=(text_x, y),
                    ha=ha, va="center",
                    fontsize=vs.font_size(theme, "annotation"),
                    color=theme["colors"]["roles"]["text"], linespacing=1.35,
                    arrowprops=dict(arrowstyle="-", color=theme["colors"]["roles"]["muted_text"],
                                    linewidth=0.8, shrinkA=0, shrinkB=0,
                                    connectionstyle="arc3,rad=0"),
                )

        ax.text(0, 0.10, "总计", ha="center", va="center",
                fontsize=vs.font_size(theme, "annotation"),
                color=theme["colors"]["roles"]["muted_text"])
        ax.text(0, -0.10, f"{total:,.0f}", ha="center", va="center", fontweight="bold",
                fontsize=vs.font_size(theme, "panel_label") * 1.3,
                color=theme["colors"]["roles"]["text"])
        ax.text(0, -0.29, f"（{VALUE_UNIT}）", ha="center", va="center",
                fontsize=vs.font_size(theme, "source"),
                color=theme["colors"]["roles"]["muted_text"])

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.03, right=0.97, top=0.80, bottom=0.08, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = grouped.copy()
        export["share_pct"] = (export[VALUE_COL] / total * 100).round(2)
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "donut_leader_labels", "categories": labels,
                       "shares_pct": [round(float(s), 2) for s in shares],
                       "palette": pal.id, "layout": LAYOUT,
                       "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit(), "visual_verified": False,
                       "note": "脚本已验证文件与文本包围盒；审美与可读性仍须经 audit_export 与宿主读图工具复核"},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

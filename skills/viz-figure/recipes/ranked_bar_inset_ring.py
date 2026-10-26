# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：长尾降序条形 + 负空间内嵌构成双层环图（Dead-Space Inset 消除右下空白）。

    uv run ranked_bar_inset_ring.py --json
    uv run ranked_bar_inset_ring.py --data examples/fixtures/SaaS企业客户_9大细分行业续费归因_脏数据.csv --json
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
ITEM_COL = "细分行业"
VALUE_COL = "ARR_万元"
MACRO_GROUP_COL = "客户层级"           # 可选宏观大类，用于内嵌环图；若无则自动按 Top3 / 其余 聚合
TITLE = "{top1} 以 {top1_val:,.1f}{unit} 领跑（占 {top1_share:.1f}%），长尾头部集中度显著"
SUBTITLE = "主图为长尾降序明度阶梯条形｜右下负空间内嵌宏观层级构成环图（Dead-Space Inset 消除空洞）"
X_LABEL = "年度经常性收入 ARR（万元）"
UNIT = "万"
SOURCE = "数据来源：演示客户大盘经常性收入台账（合成）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
WIDTH_MM = 170
ASPECT = 0.62
CITE_MM = None
OUTDIR = "outputs"
STEM = "ranked_bar_inset_ring"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        ("高端制造装备", 1680.0, "头部标杆"),
        ("新能源产业链", 1420.0, "头部标杆"),
        ("企业金融科技", 1150.0, "核心中坚"),
        ("生命科学医药", 980.0, "核心中坚"),
        ("跨境国际物流", 820.0, "核心中坚"),
        ("政企数字政务", 680.0, "长尾基石"),
        ("零售电商平台", 540.0, "长尾基石"),
        ("教育协同办公", 420.0, "长尾基石"),
        ("现代农业物联", 310.0, "长尾基石"),
    ]
    return pd.DataFrame(rows, columns=[ITEM_COL, VALUE_COL, MACRO_GROUP_COL])


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
    ap = argparse.ArgumentParser(description="长尾降序条形 + 负空间内嵌构成双层环图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "ranked_bar_inset_ring"}}
    warnings: list[str] = []
    try:
        raw_df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        cols = list(raw_df.columns)
        ic = ITEM_COL if ITEM_COL in cols else cols[1] if len(cols) > 1 else cols[0]
        vc = VALUE_COL if VALUE_COL in cols else next(
            (c for c in cols if clean_num(raw_df[c]).notna().sum() >= 3), cols[-1]
        )
        raw_df[vc] = clean_num(raw_df[vc])
        dropped = int(raw_df[vc].isna().sum())
        raw_df = raw_df.dropna(subset=[ic, vc]).copy()
        mg_c = MACRO_GROUP_COL if MACRO_GROUP_COL in raw_df.columns else None

        agg = raw_df.groupby(ic, as_index=False)[vc].sum().sort_values(vc, ascending=False).reset_index(drop=True)
        agg = agg.head(11)
        items = agg[ic].astype(str).tolist()
        vals = agg[vc].to_numpy(dtype=float)
        total_v = max(float(vals.sum()), 1e-9)
        n = len(items)

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene") and not args.layout:
            LAYOUT = theme.get("layout_family", LAYOUT)
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("editorial_sage_rust", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]
        base_col = pal.colors[0]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.yaxis.grid(False)
        ax.xaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.35)

        ramp = vs.group_lightness_ramp(base_col, n, (0.45, 0.95), reverse=True)
        vmax = float(vals.max())
        for i in range(n):
            ax.barh(i, vals[i], height=0.62, **vs.bar_kwargs(ramp[i], theme=theme), zorder=3)
            share_p = 100.0 * vals[i] / total_v
            ax.text(vals[i] + vmax * 0.02, i, f"{vals[i]:,.0f}{UNIT} ({share_p:.1f}%)",
                    va="center", ha="left", fontsize=vs.font_size(theme, "source"),
                    fontweight="bold" if i == 0 else "normal", color=roles["text"])

        mean_v = float(vals.mean())
        ax.axvline(mean_v, color=roles["muted_text"], linestyle="--", linewidth=0.9, zorder=2.5)
        ax.text(mean_v, n - 0.45, f"均值 {mean_v:,.0f}{UNIT}", ha="left", va="bottom",
                fontsize=vs.font_size(theme, "source"), color=roles["muted_text"])

        ax.set_yticks(list(range(n)))
        ax.set_yticklabels(items)
        ax.set_ylim(-0.75, n - 0.3)
        ax.invert_yaxis()
        ax.set_xlim(0, vmax * 1.52)
        ax.set_xlabel(X_LABEL)

        # 负空间内嵌构成环图（Dead-Space Inset: 右下角 [0.56, 0.08, 0.38, 0.46]）
        ax_inset = vs.add_dead_space_inset(ax, (0.55, 0.06, 0.40, 0.48), theme=theme,
                                           title="大盘层级构成占比", facecolor="#F8FAFC", border=True)
        if mg_c and mg_c in raw_df.columns:
            ring_df = raw_df.groupby(mg_c, as_index=False)[vc].sum().sort_values(vc, ascending=False)
        else:
            top3_sum = float(vals[:3].sum())
            other_sum = float(vals[3:].sum())
            ring_df = pd.DataFrame([{"tier": "Top 3 头部", "val": top3_sum},
                                    {"tier": "其余长尾", "val": other_sum}])
            ring_df.columns = ["tier", "val"]

        ring_labels = ring_df.iloc[:, 0].astype(str).tolist()
        ring_vals = ring_df.iloc[:, 1].to_numpy(dtype=float)
        ring_cols = pal.pick(len(ring_labels))

        wedges, _ = ax_inset.pie(
            ring_vals,
            colors=ring_cols,
            radius=1.0,
            wedgeprops=dict(width=0.38, edgecolor="#FFFFFF", linewidth=1.5),
            startangle=90,
        )
        ax_inset.text(0, 0, f"{total_v:,.0f}\n{UNIT}", ha="center", va="center",
                     fontsize=vs.font_size(theme, "annotation"), fontweight="bold",
                     color=roles["text"])
        # 紧凑图例放在环图右侧或下方
        inset_leg = [f"{lbl} ({100.0 * v / sum(ring_vals):.0f}%)" for lbl, v in zip(ring_labels, ring_vals)]
        leg = ax_inset.legend(wedges, inset_leg, loc="center left", bbox_to_anchor=(0.88, 0.5),
                              frameon=False, fontsize=vs.font_size(theme, "source") * 0.90)
        vs.style_legend(leg, theme)

        title = vs.fill_title(TITLE, top1=items[0], top1_val=float(vals[0]), unit=UNIT,
                              top1_share=100.0 * vals[0] / total_v)
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        max_u = max(vs.display_units(x) for x in items)
        left = min(0.25, 0.075 + max_u * 0.011)
        vs.adjust_layout(fig, left=left, right=0.965, top=0.79, bottom=0.12, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        agg.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(raw_df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "ranked_bar_inset_ring", "items_count": n,
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

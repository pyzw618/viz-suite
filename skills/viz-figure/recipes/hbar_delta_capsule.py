# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：横向对比条形 + 右侧占比与涨跌 Δ% 胶囊微表融合（Table-Plot Fusion）。

    uv run hbar_delta_capsule.py --json
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
CATEGORY_COL = "细分行业"
VALUE_COL = "ARR营收"
DELTA_COL = "同比增速"               # 百分比涨跌列（如 +28.4 或 28.4）
UNIT = "M"
TITLE = "{top1} ARR 达 {top1_val:.1f}{unit} 居首（占 {top1_share:.1f}%），高增赛道全面领跑"
SUBTITLE = "左栏同色系明度阶梯条形展示体量与均值基准｜右栏对齐融合构成占比%与同比涨跌 Δ% 胶囊"
X_LABEL = "年度经常性收入 ARR（百万元）"
SOURCE = "数据来源：演示商业智能经营台账（合成）"
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
WIDTH_MM = 168
ASPECT = 0.62
CITE_MM = None
OUTDIR = "outputs"
STEM = "hbar_delta_capsule"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rows = [
        ("智能制造装备", 148.5, 34.2),
        ("新能源动力电池", 132.0, 28.6),
        ("金融科技核心云", 114.2, 15.4),
        ("生物医药研发", 96.8, 21.8),
        ("跨境供应链物流", 84.5, 11.2),
        ("智慧医疗影像", 71.0, 18.9),
        ("政企数字治理", 63.4, -4.8),
        ("传统商超零售", 49.2, -11.5),
    ]
    return pd.DataFrame(rows, columns=[CATEGORY_COL, VALUE_COL, DELTA_COL])


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
    ap = argparse.ArgumentParser(description="横向条形 + 右侧占比与涨跌胶囊微表融合")
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
              "verified": False, "warnings": [], "figure": {"recipe": "hbar_delta_capsule"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (CATEGORY_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df = df.copy()
        df[VALUE_COL] = clean_num(df[VALUE_COL])
        has_delta = DELTA_COL in df.columns
        if has_delta:
            df[DELTA_COL] = clean_num(df[DELTA_COL])
        else:
            df[DELTA_COL] = 0.0
        dropped = int(df[[CATEGORY_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[CATEGORY_COL, VALUE_COL])
        agg = (df.groupby(CATEGORY_COL, as_index=False)
                 .agg({VALUE_COL: "sum", DELTA_COL: "mean"})
                 .sort_values(VALUE_COL, ascending=False)
                 .head(12)
                 .reset_index(drop=True))
        if agg.empty:
            raise ValueError("清洗后无可用分类数据")

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("economist_civic", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.yaxis.grid(False)
        ax.xaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.38)

        n = len(agg)
        vals = agg[VALUE_COL].to_numpy(dtype=float)
        deltas = agg[DELTA_COL].fillna(0.0).to_numpy(dtype=float)
        total = max(float(vals.sum()), 1e-9)
        mean_val = float(vals.mean())
        vmax = float(vals.max())

        ramp = vs.group_lightness_ramp(pal.colors[0], n, light_range=(0.45, 0.95), reverse=True)
        for i in range(n):
            if i % 2 == 0:
                ax.axhspan(i - 0.48, i + 0.48, color=roles["grid"], alpha=0.16, zorder=0)
            ax.barh(i, vals[i], height=0.62, **vs.bar_kwargs(ramp[i], theme=theme), zorder=3)
            ax.text(vals[i] + vmax * 0.02, i, f"{vals[i]:,.1f}{UNIT}",
                    va="center", ha="left", fontsize=vs.font_size(theme, "annotation"),
                    fontweight="bold" if i == 0 else "normal", color=roles["text"])

        ax.axvline(mean_val, color=roles["muted_text"], linestyle="--", linewidth=0.95, zorder=2.5)
        ax.text(mean_val, n - 0.42, f"均值 {mean_val:,.1f}{UNIT}", ha="left", va="bottom",
                fontsize=vs.font_size(theme, "source"), color=roles["muted_text"],
                bbox={"boxstyle": "round,pad=0.16", "facecolor": "#FFFFFF", "edgecolor": "none", "alpha": 0.88})

        # 右栏微表表头与胶囊徽章（Table-Plot Fusion）
        hdr_y = -0.88
        ax.axhline(-0.52, color=roles["text"], linewidth=0.85, zorder=3)
        ax.text(1.03, hdr_y, "占比", transform=ax.get_yaxis_transform(), ha="center", va="center",
                fontsize=vs.font_size(theme, "annotation"), fontweight="bold", color=roles["text"])
        ax.text(1.19, hdr_y, "同比 Δ%", transform=ax.get_yaxis_transform(), ha="center", va="center",
                fontsize=vs.font_size(theme, "annotation"), fontweight="bold", color=roles["text"])

        pos_col = roles.get("positive", "#198038")
        neg_col = roles.get("negative", "#DA1E28")
        for i in range(n):
            share = 100.0 * vals[i] / total
            ax.text(1.03, i, f"{share:4.1f}%", transform=ax.get_yaxis_transform(),
                    ha="center", va="center", fontsize=vs.font_size(theme, "annotation"),
                    color=roles["muted_text"])
            d_val = float(deltas[i])
            c_base = pos_col if d_val >= 0 else neg_col
            sign = "+" if d_val >= 0 else ""
            ax.text(1.19, i, f"{sign}{d_val:.1f}%", transform=ax.get_yaxis_transform(),
                    ha="center", va="center", fontsize=vs.font_size(theme, "source"),
                    fontweight="bold", color=vs.mix("#0F172A", c_base, 0.72),
                    bbox={"boxstyle": "round,pad=0.24,rounding_size=0.45",
                          "facecolor": vs.mix("#FFFFFF", c_base, 0.16),
                          "edgecolor": vs.mix("#FFFFFF", c_base, 0.58), "linewidth": 0.75})

        ax.set_yticks(list(range(n)))
        ax.set_yticklabels(agg[CATEGORY_COL].astype(str).tolist())
        ax.set_xlim(0, vmax * 1.24)
        ax.set_ylim(-1.25, n - 0.35)
        ax.invert_yaxis()
        ax.set_xlabel(X_LABEL)

        top1_share = 100.0 * vals[0] / total
        title = vs.fill_title(TITLE, top1=str(agg.loc[0, CATEGORY_COL]),
                              top1_val=float(vals[0]), unit=UNIT, top1_share=top1_share)
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        max_u = max(vs.display_units(str(x)) for x in agg[CATEGORY_COL])
        left = min(0.32, 0.065 + max_u * 0.011)
        vs.adjust_layout(fig, left=left, right=0.74, top=0.80, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        agg.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "hbar_delta_capsule", "categories": agg[CATEGORY_COL].astype(str).tolist(),
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

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：全球 177 国 Robinson 伪圆柱投影分级设色地图 + Top/Bottom 排名副图。

    uv run world_choropleth_robinson.py --json
    uv run world_choropleth_robinson.py --data examples/fixtures/全球重点市场_营收增速与渗透_ISO3.csv --json
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
from matplotlib.patches import Polygon

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
ISO_COL = "ISO3"
VALUE_COL = "移动端渗透率_pct"
TITLE = "{top_country} 渗透率达 {top_val:.1f}% 领跑全球，发达市场与拉美快速爬坡"
SUBTITLE = "(a) 全球 177 国 Robinson 伪圆柱投影（Natural Earth CC0）｜(b) 重点国家渗透率排名（未覆盖区域浅灰显示）"
VALUE_LABEL = "移动端渗透率（%）"
SOURCE = "数据来源：演示全球区域数字经济渗透监测（合成，ISO-3166-1 alpha-3 对齐）"
SCENE = "geo"
PALETTE = None
LAYOUT = "clean_open"
WIDTH_MM = 182
ASPECT = 0.52
CITE_MM = None
OUTDIR = "outputs"
STEM = "world_choropleth_robinson"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================

# Arthur H. Robinson (1974) 官方投影表：每 5 度的 (lat, Plen, Pdist)
ROBINSON_TABLE = [
    (0,  1.0000, 0.0000), (5,  0.9986, 0.0620), (10, 0.9954, 0.1240),
    (15, 0.9900, 0.1860), (20, 0.9822, 0.2480), (25, 0.9730, 0.3100),
    (30, 0.9600, 0.3720), (35, 0.9427, 0.4340), (40, 0.9216, 0.4958),
    (45, 0.8962, 0.5571), (50, 0.8679, 0.6176), (55, 0.8350, 0.6769),
    (60, 0.7986, 0.7346), (65, 0.7597, 0.7903), (70, 0.7186, 0.8435),
    (75, 0.6732, 0.8936), (80, 0.6213, 0.9394), (85, 0.5722, 0.9761),
    (90, 0.5322, 1.0000),
]
_ROB_LATS = np.array([r[0] for r in ROBINSON_TABLE], dtype=float)
_ROB_PLEN = np.array([r[1] for r in ROBINSON_TABLE], dtype=float)
_ROB_PDIST = np.array([r[2] for r in ROBINSON_TABLE], dtype=float)


def project_robinson(lons: np.ndarray, lats: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """官方 Arthur Robinson 1974 伪圆柱投影表线性插值（纯 NumPy 实现，零 GDAL 依赖）。"""
    abslat = np.abs(lats)
    signlat = np.sign(lats)
    plen = np.interp(abslat, _ROB_LATS, _ROB_PLEN)
    pdist = np.interp(abslat, _ROB_LATS, _ROB_PDIST)
    x = 0.8487 * (lons * np.pi / 180.0) * plen
    y = 1.3523 * signlat * pdist
    return x, y


def demo_frame() -> pd.DataFrame:
    sample_iso = {
        "USA": 88.5, "GBR": 86.2, "KOR": 92.4, "JPN": 85.0, "DEU": 83.4,
        "FRA": 81.8, "AUS": 84.6, "CAN": 82.0, "BRA": 76.5, "IND": 72.0,
        "IDN": 74.2, "MEX": 71.8, "VNM": 75.6, "NGA": 58.4, "ZAF": 66.2,
        "SAU": 89.0, "ARE": 94.2, "SGP": 93.8, "ARG": 73.5, "EGY": 61.0,
        "TUR": 77.4, "ESP": 82.5, "ITA": 79.8, "POL": 78.0, "SWE": 91.0,
        "NOR": 92.5, "CHN": 89.6, "THA": 78.4, "MYS": 83.0, "CHL": 81.2,
    }
    rows = [{ISO_COL: iso, VALUE_COL: val} for iso, val in sample_iso.items()]
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


def clean_num(s: pd.Series) -> pd.Series:
    cleaned = (s.astype(str)
                .str.replace(r"[¥$€£,，%％\s]", "", regex=True)
                .replace({"—": np.nan, "-": np.nan, "N/A": np.nan, "nan": np.nan, "": np.nan}))
    return pd.to_numeric(cleaned, errors="coerce")


def main() -> int:
    ap = argparse.ArgumentParser(description="全球 177 国 Robinson 投影分级设色地图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "world_choropleth_robinson"}}
    warnings: list[str] = []
    try:
        geo = vs.load_geo_asset("ne_110m_countries.geojson")
        features = geo.get("features", [])

        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        cols = list(df.columns)
        ic = ISO_COL if ISO_COL in cols else next((c for c in cols if "iso" in c.lower()), cols[0])
        vc = VALUE_COL if VALUE_COL in cols else next(
            (c for c in cols if clean_num(df[c]).notna().sum() >= 5), cols[-1]
        )
        df[vc] = clean_num(df[vc])
        df = df.dropna(subset=[ic, vc]).copy()
        val_map = {str(row[ic]).strip().upper(): float(row[vc]) for _, row in df.iterrows()}

        theme = vs.resolve_theme(scene=SCENE)
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("met_hokusai2", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]
        base_col = pal.colors[-1] if pal.id.startswith("met_hokusai") else pal.colors[0]

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(1, 2, width_ratios=[2.0, 1.0], wspace=0.18)
        ax_map = fig.add_subplot(gs[0, 0])
        ax_bar = fig.add_subplot(gs[0, 1])

        vs.apply_style(ax_map, "clean_open", theme=theme)
        ax_map.set_xticks([])
        ax_map.set_yticks([])
        for sp in ax_map.spines.values():
            sp.set_visible(False)

        valid_vals = [v for v in val_map.values() if np.isfinite(v)]
        vmin = float(min(valid_vals)) if valid_vals else 0.0
        vmax = float(max(valid_vals)) if valid_vals else 100.0
        cmap = vs.sequential_cmap(base_col, light="#F1F5F9", light_mix=0.92)

        # 绘制 Robinson 外轮廓椭圆框
        edge_lats = np.linspace(-90, 90, 80)
        ex_r, ey_r = project_robinson(np.full_like(edge_lats, 180.0), edge_lats)
        ex_l, ey_l = project_robinson(np.full_like(edge_lats, -180.0), edge_lats)
        ax_map.plot(np.concatenate([ex_r, ex_l[::-1]]), np.concatenate([ey_r, ey_l[::-1]]),
                    color=roles["grid"], linewidth=0.85, zorder=1)

        # 解析并投影 MultiPolygon
        matched_names: dict[str, str] = {}
        for feat in features:
            props = feat.get("properties", {})
            iso = str(props.get("iso_a3", "")).strip().upper()
            c_name = str(props.get("name", iso))
            val = val_map.get(iso)
            if val is not None:
                matched_names[iso] = c_name
                norm_v = float(np.clip((val - vmin) / max(vmax - vmin, 1e-6), 0.0, 1.0))
                fc = cmap(norm_v)
                ec = vs.mix("#0F172A", matplotlib.colors.to_hex(fc), 0.70)
            else:
                fc = "#E2E8F0"
                ec = "#CBD5E1"

            geom = feat.get("geometry", {})
            g_type = geom.get("type")
            polys = []
            if g_type == "Polygon":
                polys = [geom.get("coordinates", [])]
            elif g_type == "MultiPolygon":
                polys = geom.get("coordinates", [])

            for poly in polys:
                if not poly or not poly[0]:
                    continue
                coords = np.array(poly[0], dtype=float)
                px, py = project_robinson(coords[:, 0], coords[:, 1])
                patch = Polygon(np.column_stack([px, py]), closed=True,
                                facecolor=fc, edgecolor=ec, linewidth=0.35, zorder=2)
                ax_map.add_patch(patch)

        ax_map.set_xlim(-2.8, 2.8)
        ax_map.set_ylim(-1.5, 1.5)
        ax_map.set_title("(a) 全球 Robinson 伪圆柱分级设色", loc="left",
                         fontsize=vs.font_size(theme, "axis_label"), fontweight="bold", pad=6)

        # 地图左下微型色条
        cbar_ax = ax_map.inset_axes([0.04, 0.04, 0.38, 0.038])
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        cb = fig.colorbar(sm, cax=cbar_ax, orientation="horizontal")
        cb.outline.set_linewidth(0.5)
        cb.ax.tick_params(labelsize=vs.font_size(theme, "source") * 0.88, pad=1)

        # (b) 右侧重点国家 Top/Bottom 排行榜
        vs.apply_style(ax_bar, "soft_grid", theme=theme)
        ax_bar.yaxis.grid(False)
        ax_bar.xaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.35)

        ranked_items = sorted(val_map.items(), key=lambda kv: kv[1], reverse=True)
        top8 = ranked_items[:8]
        bot3 = ranked_items[-3:] if len(ranked_items) > 11 else []
        bar_items = top8 + ([("...", np.nan)] if bot3 else []) + bot3

        b_labels = [matched_names.get(k, k) if k != "..." else "..." for k, _ in bar_items]
        b_vals = [v for _, v in bar_items]
        nb = len(bar_items)
        ramp = vs.group_lightness_ramp(base_col, len(top8), (0.45, 0.95), reverse=True)

        for i, ((iso, val), lbl) in enumerate(zip(bar_items, b_labels)):
            if iso == "...":
                continue
            c_bar = ramp[i] if i < len(top8) else "#94A3B8"
            ax_bar.barh(i, val, height=0.62, **vs.bar_kwargs(c_bar, theme=theme), zorder=3)
            ax_bar.text(val + vmax * 0.02, i, f"{val:.1f}%", va="center", ha="left",
                        fontsize=vs.font_size(theme, "source"),
                        fontweight="bold" if i == 0 else "normal", color=roles["text"])

        ax_bar.set_yticks(list(range(nb)))
        ax_bar.set_yticklabels(b_labels)
        ax_bar.set_ylim(-0.7, nb - 0.3)
        ax_bar.invert_yaxis()
        ax_bar.set_xlim(0, vmax * 1.25)
        ax_bar.set_xlabel(VALUE_LABEL)
        ax_bar.set_title("(b) 标杆国家排名", loc="left",
                         fontsize=vs.font_size(theme, "axis_label"), fontweight="bold", pad=6)

        top_iso = ranked_items[0][0] if ranked_items else "ARE"
        top_name = matched_names.get(top_iso, top_iso)
        top_v = ranked_items[0][1] if ranked_items else 94.2
        title = vs.fill_title(TITLE, top_country=top_name, top_val=top_v)
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        max_u = max(vs.display_units(x) for x in b_labels if x != "...")
        left = min(0.18, 0.05 + max_u * 0.010)
        vs.adjust_layout(fig, left=0.03, right=0.965, top=0.79, bottom=0.12, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        export_df = pd.DataFrame([{"iso": k, "name": matched_names.get(k, k), "value": v}
                                  for k, v in ranked_items])
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export_df.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": len(ranked_items),
            "rows_dropped": len(features) - len(ranked_items),
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "world_choropleth_robinson", "top_country": top_name,
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

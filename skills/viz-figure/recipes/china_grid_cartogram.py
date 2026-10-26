# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：中国 34 省级行政区拓扑方块网格示意地图 + 七大区均值副图（免审图风险合规地图）。

    uv run china_grid_cartogram.py --json
    uv run china_grid_cartogram.py --data examples/fixtures/新能源汽车_34省渗透率与交付_脏数据.csv --json
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
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
PROV_COL = "省份"
VALUE_COL = "渗透率_pct"
TITLE = "{top_prov} 渗透率达 {top_val:.1f}% 居全国首位，东南沿海与华南整体领跑"
SUBTITLE = "(a) 34 省级行政区拓扑方块网格（含港澳台）｜(b) 七大经济地理区均值柱（注：示意方块非真实行政边界）"
VALUE_LABEL = "新能源车渗透率（%）"
SOURCE = "数据来源：演示区域汽车消费与补能台账（合成）；注：本图为拓扑方块示意图，免审图风险"
SCENE = "geo"
PALETTE = None
LAYOUT = "clean_open"
WIDTH_MM = 175
ASPECT = 0.58
CITE_MM = None
OUTDIR = "outputs"
STEM = "china_grid_cartogram"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    grid = vs.load_geo_asset("china_prov_tile_grid.json")
    rows = []
    base_by_region = {"华东": 48.0, "华南": 52.0, "华中": 41.0, "华北": 38.0, "西南": 43.0, "西北": 29.0, "东北": 24.0}
    rng = np.random.default_rng(DEMO_SEED)
    for t in grid["tiles"]:
        pname = t["name"]
        reg = t["region"]
        base = base_by_region.get(reg, 35.0)
        v = base + rng.normal(0, 4.5)
        if pname == "海南":
            v = 58.2
        elif pname == "上海":
            v = 55.4
        rows.append({PROV_COL: pname, VALUE_COL: round(float(np.clip(v, 12.0, 65.0)), 1)})
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


def match_prov(raw: str, tile_names: set[str], tile_abbrs: dict[str, str], tile_full: dict[str, str]) -> str | None:
    s = str(raw).strip()
    if s in tile_names:
        return s
    for name, full in tile_full.items():
        if s == full or s.startswith(name) or name.startswith(s):
            return name
    if s in tile_abbrs:
        return tile_abbrs[s]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="中国 34 省拓扑方块网格图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "china_grid_cartogram"}}
    warnings: list[str] = []
    try:
        grid_data = vs.load_geo_asset("china_prov_tile_grid.json")
        tiles = grid_data["tiles"]
        t_names = {t["name"] for t in tiles}
        t_abbrs = {t["abbr"]: t["name"] for t in tiles}
        t_full = {t["name"]: t["full_name"] for t in tiles}
        t_region = {t["name"]: t["region"] for t in tiles}

        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        cols = list(df.columns)
        pc = PROV_COL if PROV_COL in cols else cols[0]
        vc = VALUE_COL if VALUE_COL in cols else next(
            (c for c in cols if clean_num(df[c]).notna().sum() >= 5), cols[-1]
        )
        df[vc] = clean_num(df[vc])
        df = df.dropna(subset=[pc, vc]).copy()

        val_map: dict[str, float] = {}
        for raw_p, val in zip(df[pc], df[vc]):
            m = match_prov(raw_p, t_names, t_abbrs, t_full)
            if m:
                val_map[m] = float(val)

        missing = t_names - set(val_map.keys())
        if missing:
            warnings.append(f"以下 {len(missing)} 个省级单位在输入数据中缺失，已显示斜纹占位：{sorted(missing)}")

        theme = vs.resolve_theme(scene=SCENE)
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("met_hiroshige", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(1, 2, width_ratios=[1.75, 1.0], wspace=0.18)
        ax_map = fig.add_subplot(gs[0, 0])
        ax_bar = fig.add_subplot(gs[0, 1])

        # (a) 左侧 9×8 拓扑方块地图
        vs.apply_style(ax_map, "clean_open", theme=theme)
        ax_map.set_xticks([])
        ax_map.set_yticks([])
        for sp in ax_map.spines.values():
            sp.set_visible(False)

        valid_vals = list(val_map.values())
        vmin = float(min(valid_vals)) if valid_vals else 0.0
        vmax = float(max(valid_vals)) if valid_vals else 100.0
        cmap = vs.sequential_cmap(pal.colors[0], light="#F8FAFC", light_mix=0.92)

        top_p = max(val_map, key=lambda k: val_map[k]) if val_map else "海南"
        top_v = val_map.get(top_p, 0.0)

        for t in tiles:
            pname = t["name"]
            col, row = t["col"], t["row"]
            # y 轴翻转，使 (0, 0) 位于左上角
            x, y = float(col), float(grid_data["rows"] - 1 - row)
            val = val_map.get(pname)
            if val is not None and np.isfinite(val):
                norm_v = float(np.clip((val - vmin) / max(vmax - vmin, 1e-6), 0.0, 1.0))
                fill_c = cmap(norm_v)
                rect = Rectangle((x + 0.05, y + 0.05), 0.90, 0.90,
                                 facecolor=fill_c, edgecolor="#FFFFFF", linewidth=1.4, zorder=2)
                ax_map.add_patch(rect)
                fill_hex = matplotlib.colors.to_hex(fill_c)
                txt_c = vs.contrast_text(fill_hex, alpha=1.0)
                star = "★" if pname == top_p else ""
                ax_map.text(x + 0.50, y + 0.48, f"{star}{pname}\n{val:.1f}%", ha="center", va="center",
                            fontsize=vs.font_size(theme, "source"), fontweight="bold" if pname == top_p else "normal",
                            color=txt_c, zorder=3)
            else:
                rect = Rectangle((x + 0.05, y + 0.05), 0.90, 0.90,
                                 facecolor="#F1F5F9", edgecolor="#CBD5E1", linewidth=0.8,
                                 hatch="//", zorder=1)
                ax_map.add_patch(rect)
                ax_map.text(x + 0.50, y + 0.48, f"{pname}\n暂缺", ha="center", va="center",
                            fontsize=vs.font_size(theme, "source") * 0.92, color="#94A3B8", zorder=3)

        ax_map.set_xlim(-0.2, grid_data["cols"] + 0.2)
        ax_map.set_ylim(-0.2, grid_data["rows"] + 0.2)
        ax_map.set_title("(a) 34 省级行政区拓扑方块", loc="left",
                         fontsize=vs.font_size(theme, "axis_label"), fontweight="bold", pad=6)

        # 底部紧凑水平颜色条
        cbar_ax = ax_map.inset_axes([0.05, -0.06, 0.42, 0.035])
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        cb = fig.colorbar(sm, cax=cbar_ax, orientation="horizontal")
        cb.outline.set_linewidth(0.5)
        cb.ax.tick_params(labelsize=vs.font_size(theme, "source") * 0.88, pad=1)

        # (b) 右侧大区均值横向柱图
        vs.apply_style(ax_bar, "soft_grid", theme=theme)
        ax_bar.yaxis.grid(False)
        ax_bar.xaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.35)

        region_records = []
        for pname, val in val_map.items():
            region_records.append({"region": t_region.get(pname, "其他"), "val": val})
        reg_df = pd.DataFrame(region_records).groupby("region", as_index=False)["val"].mean()
        reg_df = reg_df.sort_values("val", ascending=False).reset_index(drop=True)
        reg_names = reg_df["region"].tolist()
        reg_vals = reg_df["val"].to_numpy(dtype=float)

        ramp = vs.group_lightness_ramp(pal.colors[0], len(reg_names), (0.45, 0.95), reverse=True)
        for i, (rn, rv) in enumerate(zip(reg_names, reg_vals)):
            ax_bar.barh(i, rv, height=0.60, **vs.bar_kwargs(ramp[i], theme=theme), zorder=3)
            ax_bar.text(rv + vmax * 0.02, i, f"{rv:.1f}%", va="center", ha="left",
                        fontsize=vs.font_size(theme, "source"),
                        fontweight="bold" if i == 0 else "normal", color=roles["text"])

        nat_mean = float(np.mean(valid_vals)) if valid_vals else 0.0
        ax_bar.axvline(nat_mean, color=roles["muted_text"], linestyle="--", linewidth=0.9, zorder=2.5)
        ax_bar.text(nat_mean, len(reg_names) - 0.45, f"全国均值 {nat_mean:.1f}%", ha="left", va="bottom",
                    fontsize=vs.font_size(theme, "source"), color=roles["muted_text"])

        ax_bar.set_yticks(list(range(len(reg_names))))
        ax_bar.set_yticklabels(reg_names)
        ax_bar.set_ylim(-0.7, len(reg_names) - 0.3)
        ax_bar.invert_yaxis()
        ax_bar.set_xlim(0, max(reg_vals.max() * 1.28, vmax * 1.22))
        ax_bar.set_xlabel(VALUE_LABEL)
        ax_bar.set_title("(b) 七大区均值", loc="left",
                         fontsize=vs.font_size(theme, "axis_label"), fontweight="bold", pad=6)

        title = vs.fill_title(TITLE, top_prov=top_p, top_val=top_v)
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.04, right=0.97, top=0.79, bottom=0.12, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        export_df = pd.DataFrame([{"province": t["name"], "region": t["region"],
                                  "value": val_map.get(t["name"])} for t in tiles])
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export_df.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": len(val_map),
            "rows_dropped": len(missing),
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "china_grid_cartogram", "provinces_covered": len(val_map),
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

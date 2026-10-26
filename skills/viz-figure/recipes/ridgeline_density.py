# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：多组山脊核密度分布图（羽化渐变填充 + IQR 核心区 + 中位数锚点）。

    uv run ridgeline_density.py --json
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
GROUP_COL = "端到端链路"
VALUE_COL = "响应耗时_ms"
OVERLAP = 0.58                        # 山脊纵向交叠系数（0.35–0.75）
TITLE = "{fastest} 中位响应最低（{fast_med:.0f}ms），{slowest} 长尾离散度最宽"
SUBTITLE = "山脊轮廓为高斯核密度（cut=0）｜深色核区为 P25–P75 四分位带，白边圆点为中位数"
X_LABEL = "响应延迟（ms）"
SOURCE = "数据来源：演示分布式网关压测追踪（合成，每组 n=180）"
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
WIDTH_MM = 165
ASPECT = 0.64
CITE_MM = None
OUTDIR = "outputs"
STEM = "ridgeline_density"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261026
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    specs = [
        ("内存缓存命中", 24.0, 5.5, 4.0),
        ("边缘节点路由", 38.0, 7.8, 6.5),
        ("向量索引检索", 56.0, 10.5, 11.0),
        ("跨区事务写入", 74.0, 13.0, 16.0),
        ("多跳模型推理", 98.0, 16.5, 22.0),
        ("冷启动批处理", 122.0, 21.0, 28.0),
    ]
    rows = []
    for name, loc, sd, exp_scale in specs:
        vals = rng.normal(loc, sd, 180) + rng.exponential(exp_scale, 180)
        vals = np.clip(vals, 8.0, 240.0)
        for v in vals:
            rows.append({GROUP_COL: name, VALUE_COL: round(float(v), 2)})
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


def main() -> int:
    ap = argparse.ArgumentParser(description="多组山脊核密度分布图")
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
              "verified": False, "warnings": [], "figure": {"recipe": "ridgeline_density"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (GROUP_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df = df.copy()
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[GROUP_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[GROUP_COL, VALUE_COL])
        if df.empty:
            raise ValueError("清洗后无可用观测")

        meds = df.groupby(GROUP_COL)[VALUE_COL].median().sort_values(ascending=True)
        groups = list(meds.index)[:10]
        df = df[df[GROUP_COL].isin(groups)].copy()

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.select_palette("met_hiroshige", theme=theme, cli_palette=PALETTE)
        theme["palette_id"] = pal.id
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.xaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.35)

        n_g = len(groups)
        colors = pal.pick(n_g) if n_g <= len(pal) else vs.group_lightness_ramp(pal.colors[0], n_g, (0.45, 0.95))
        all_v = df[VALUE_COL].to_numpy(dtype=float)
        x_lo, x_hi = float(np.percentile(all_v, 0.5)), float(np.percentile(all_v, 99.5))
        span = max(x_hi - x_lo, 1e-6)

        summary_rows = []
        # 从底部组到顶部组逆序绘制以产生自然层叠遮挡感
        for i in range(n_g - 1, -1, -1):
            g_name = groups[i]
            vals = df.loc[df[GROUP_COL] == g_name, VALUE_COL].to_numpy(dtype=float)
            base_y = float(n_g - 1 - i)
            col = colors[i]
            grid, dens = vs.kde_1d(vals, n=220, cut=0.0)
            if dens.max() > 0:
                dens_scaled = dens / dens.max() * (1.0 + OVERLAP)
            else:
                dens_scaled = dens
            z = 2.0 + (n_g - i) * 0.4
            ax.axhline(base_y, color=roles["grid"], linewidth=0.65, zorder=z - 0.1)
            # 白底遮罩消除下层网格穿透，再叠加羽化彩色山脊与 IQR 核区
            ax.fill_between(grid, base_y, base_y + dens_scaled, color="#FFFFFF", alpha=0.92, zorder=z)
            ax.fill_between(grid, base_y, base_y + dens_scaled,
                            color=vs.mix("#FFFFFF", col, 0.62), alpha=0.78, zorder=z + 0.05)
            q1, med, q3 = np.percentile(vals, [25, 50, 75])
            iqr_mask = (grid >= q1) & (grid <= q3)
            if iqr_mask.any():
                ax.fill_between(grid[iqr_mask], base_y, base_y + dens_scaled[iqr_mask],
                                color=vs.mix("#FFFFFF", col, 0.90), alpha=0.90, zorder=z + 0.1)
            ax.plot(grid, base_y + dens_scaled, color=vs.mix("#0F172A", col, 0.72),
                    linewidth=1.25, zorder=z + 0.15)
            med_h = float(np.interp(med, grid, dens_scaled))
            ax.plot([med, med], [base_y, base_y + med_h], color="#FFFFFF", linewidth=1.2, zorder=z + 0.2)
            ax.scatter([med], [base_y + 0.22], s=26, color=vs.mix("#0F172A", col, 0.65),
                       edgecolor="#FFFFFF", linewidth=0.9, zorder=z + 0.25)
            ax.text(1.015, base_y + 0.18, f"M={med:.0f} (IQR {q3 - q1:.0f})",
                    transform=ax.get_yaxis_transform(), ha="left", va="center",
                    fontsize=vs.font_size(theme, "source"), color=roles["muted_text"])
            summary_rows.append({GROUP_COL: g_name, "n": len(vals), "median": round(float(med), 2),
                                 "q1": round(float(q1), 2), "q3": round(float(q3), 2)})

        ax.set_yticks([float(n_g - 1 - i) + 0.15 for i in range(n_g)])
        ax.set_yticklabels(groups)
        ax.set_xlim(x_lo - 0.04 * span, x_hi + 0.05 * span)
        ax.set_ylim(-0.15, float(n_g - 1) + 1.0 + OVERLAP + 0.18)
        ax.set_xlabel(X_LABEL)

        title = vs.fill_title(TITLE, fastest=groups[0], fast_med=float(meds.iloc[0]), slowest=groups[-1])
        vs.add_header(fig, title, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        max_u = max(vs.display_units(str(g)) for g in groups)
        left = min(0.28, 0.065 + max_u * 0.011)
        vs.adjust_layout(fig, left=left, right=0.77, top=0.80, bottom=0.14, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        sum_path = Path(OUTDIR) / f"{STEM}_summary.csv"
        pd.DataFrame(summary_rows).to_csv(sum_path, index=False, encoding="utf-8-sig")
        outputs.append(str(sum_path))

        result.update({
            "status": "success",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "ridgeline_density", "groups": groups,
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

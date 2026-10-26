# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：SHAP 蜂群散点 + 右侧平均贡献条组合图。

    uv run shap_beeswarm_bars.py --json
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
from matplotlib.colors import Normalize

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
SAMPLE_COL = "样本"
FEATURE_COL = "特征"
SHAP_COL = "SHAP"
VALUE_COL = "特征值"
TOP_N = 10
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
TITLE = "平均 |SHAP| 最高的特征为 {top1}，其次为 {top2}"
SUBTITLE = "蜂群图为样本级 SHAP 值，颜色为特征值｜右侧为平均绝对贡献"
X_LABEL = "SHAP 值"
RIGHT_LABEL = "平均 |SHAP|"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.66
CITE_MM = None
OUTDIR = "outputs"
STEM = "shap_beeswarm_bars"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    features = [f"特征{i}" for i in range(1, 9)]
    coefficients = [1.15, 0.92, 0.70, 0.52, 0.35, -0.42, -0.24, 0.14]
    rows = []
    for s in range(180):
        for name, coef in zip(features, coefficients):
            value = float(rng.normal(0, 1))
            shap = coef * value + float(rng.normal(0, 0.22 + 0.10 * abs(coef)))
            rows.append({SAMPLE_COL: f"S{s:03d}", FEATURE_COL: name,
                         SHAP_COL: round(shap, 4), VALUE_COL: round(value, 4)})
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
    ap = argparse.ArgumentParser(description="SHAP 蜂群 + 贡献条")
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
              "verified": False, "warnings": [], "figure": {"recipe": "shap_beeswarm_bars"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (SAMPLE_COL, FEATURE_COL, SHAP_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        for col in (SHAP_COL, VALUE_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[FEATURE_COL, SHAP_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[FEATURE_COL, SHAP_COL, VALUE_COL])
        if df.empty:
            raise ValueError("清洗后数据为空")
        importance = df.groupby(FEATURE_COL)[SHAP_COL].apply(lambda s: float(np.abs(s).mean()))
        importance = importance.sort_values(ascending=False)
        features = importance.index.tolist()[:TOP_N]
        if len(importance) > TOP_N:
            warnings.append(f"共 {len(importance)} 个特征，仅展示平均 |SHAP| 前 {TOP_N} 个")
        df = df[df[FEATURE_COL].isin(features)].copy()
        features = [f for f in features if f in set(df[FEATURE_COL])]
        stats = {"top1": features[0] if features else "-", "top2": features[1] if len(features) > 1 else "-"}

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme.get("scene_preset", {}).get("double_column_mm", 183) if (True and theme.get("scene") == "academic") else theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig = plt.figure(figsize=size["figsize"])
        fig.set_facecolor(theme["colors"]["backgrounds"]["white"])
        gs = fig.add_gridspec(1, 2, width_ratios=[3.8, 1.18], wspace=0.13)
        ax = fig.add_subplot(gs[0, 0])
        ax_bar = fig.add_subplot(gs[0, 1], sharey=ax)
        vs.apply_style(ax, LAYOUT, theme=theme)
        vs.apply_style(ax_bar, LAYOUT, theme=theme)
        ax_bar.tick_params(axis="y", left=False, labelleft=False)
        ax.yaxis.grid(False)
        ax.xaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.3)
        ax_bar.yaxis.grid(False)
        ax_bar.xaxis.grid(True, linestyle="--", linewidth=0.6, color=roles["grid"], alpha=0.3)

        values_all = df[VALUE_COL].to_numpy(dtype=float)
        vmin, vmax = np.percentile(values_all, [2, 98])
        if vmax <= vmin:
            vmin, vmax = float(values_all.min()), float(values_all.max()) + 1e-6
        norm = Normalize(vmin=float(vmin), vmax=float(vmax))
        cmap = vs.diverging_cmap("#0072B2", other="#D55E00", midpoint="#F3F4F6", n=257)
        ypos = {f: i for i, f in enumerate(features)}
        rng = np.random.default_rng(DEMO_SEED)
        for feature in features:
            sub = df[df[FEATURE_COL] == feature].sort_values(SHAP_COL)
            shap_values = sub[SHAP_COL].to_numpy(dtype=float)
            if len(sub) > 1 and shap_values.max() > shap_values.min():
                bins = np.linspace(shap_values.min(), shap_values.max(), 26)
                bin_idx = np.clip(np.digitize(shap_values, bins) - 1, 0, 24)
            else:
                bin_idx = np.zeros(len(sub), dtype=int)
            offsets = np.zeros(len(sub), dtype=float)
            for b in np.unique(bin_idx):
                members = np.where(bin_idx == b)[0]
                m = len(members)
                local = (np.arange(m) - (m - 1) / 2) * 0.035
                rng.shuffle(local)
                offsets[members] = local
            offsets = np.clip(offsets, -0.34, 0.34)
            y = ypos[feature] + offsets
            sc = ax.scatter(sub[SHAP_COL], y, c=sub[VALUE_COL], cmap=cmap, norm=norm,
                            s=10, alpha=0.72, edgecolors="none", zorder=3)
        ax.axvline(0, color=roles["muted_text"], linestyle="--", linewidth=0.9, zorder=2)

        means = [float(np.abs(df.loc[df[FEATURE_COL] == f, SHAP_COL]).mean()) for f in features]
        ax_bar.barh(np.arange(len(features)), means, height=0.62,
                    **vs.bar_kwargs(roles["focal"], theme=theme), zorder=3)
        max_mean = max(means) if means else 1.0
        for i, value in enumerate(means):
            ax_bar.text(value + max_mean * 0.03, i, f"{value:.2f}", va="center", ha="left",
                        fontsize=vs.font_size(theme, "source"), color=roles["text"])

        ax.set_yticks(list(range(len(features))))
        ax.set_yticklabels(features)
        ax.set_ylim(len(features) - 0.5, -0.5)
        ax.set_xlabel(X_LABEL)
        ax.set_ylabel("")
        ax_bar.set_xlabel(RIGHT_LABEL)
        ax_bar.set_xlim(0, max_mean * 1.28)
        ax_bar.set_ylim(len(features) - 0.5, -0.5)

        # 底部横向色条（放在布局调整之后，避免位置漂移）
        vs.add_header(fig, vs.fill_title(TITLE, **stats), SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.16, right=0.97, top=0.80, bottom=0.26, theme=theme)

        pos = ax.get_position()
        cax = fig.add_axes([pos.x0 + 0.22 * pos.width, 0.055, 0.45 * pos.width, 0.014])
        cb = fig.colorbar(sc, cax=cax, orientation="horizontal", ticks=[])
        cb.ax.set_title("特征值：低 → 高", fontsize=vs.font_size(theme, "source"),
                        color=roles["muted_text"], pad=3)

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
            "figure": {"recipe": "shap_beeswarm_bars", "features": features,
                       "mean_abs_shap": dict(zip(features, [round(m, 4) for m in means])),
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

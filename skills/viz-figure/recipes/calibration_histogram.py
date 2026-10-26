# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：概率校准曲线 + 下方预测分布直方图。

    uv run calibration_histogram.py --json
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
P_COL = "预测概率"
Y_COL = "实际结果"
BINS = 10
SCENE = None
PALETTE = None
LAYOUT = "soft_grid"
TITLE = "校准曲线整体贴近对角线（Brier = {brier:.3f}，ECE = {ece:.3f}）"
SUBTITLE = "点为分箱实际发生率，误差棒为 95% Wilson 区间｜下方为预测概率分布｜未做显著性检验"
X_LABEL = "预测概率"
Y_LABEL = "实际发生率"
HIST_LABEL = "样本数"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.70
CITE_MM = None
OUTDIR = "outputs"
STEM = "calibration_histogram"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_frame() -> pd.DataFrame:
    rng = np.random.default_rng(DEMO_SEED)
    p = np.clip(rng.beta(2.2, 2.2, 600), 0.02, 0.98)
    true_p = np.clip(0.10 + 0.80 * p, 0, 1)
    y = rng.binomial(1, true_p, size=len(p))
    return pd.DataFrame({P_COL: np.round(p, 4), Y_COL: y})


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


def wilson(obs: float, n: int, z: float = 1.96):
    if n <= 0:
        return 0.0, 1.0
    denom = 1 + z ** 2 / n
    center = (obs + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(obs * (1 - obs) / n + z ** 2 / (4 * n ** 2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def main() -> int:
    ap = argparse.ArgumentParser(description="校准曲线 + 预测分布")
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
              "verified": False, "warnings": [], "figure": {"recipe": "calibration_histogram"}}
    warnings: list[str] = []
    try:
        df = demo_frame() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (P_COL, Y_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        for col in (P_COL, Y_COL):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df[[P_COL, Y_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[P_COL, Y_COL])
        out_of_range = df[(df[P_COL] < 0) | (df[P_COL] > 1)]
        if len(out_of_range):
            warnings.append(f"{len(out_of_range)} 行预测概率不在 [0,1]，已剔除")
            dropped += len(out_of_range)
            df = df.drop(out_of_range.index)
        if df.empty:
            raise ValueError("清洗后数据为空")
        df[Y_COL] = (df[Y_COL] > 0.5).astype(int)

        bins = np.linspace(0, 1, BINS + 1)
        df["__bin"] = pd.cut(df[P_COL], bins=bins, include_lowest=True, right=True)
        rows = []
        for interval, group in df.groupby("__bin", observed=True):
            n = len(group)
            if n == 0:
                continue
            p_mean = float(group[P_COL].mean())
            obs = float(group[Y_COL].mean())
            low, high = wilson(obs, n)
            rows.append({"bin_low": float(interval.left), "bin_high": float(interval.right),
                         "n": n, "p_mean": p_mean, "obs": obs, "low": low, "high": high})
        cal = pd.DataFrame(rows)
        if len(cal) < 2:
            raise ValueError("有效分箱少于 2 个，无法绘制校准曲线")
        empty_bins = BINS - len(cal)
        if empty_bins:
            warnings.append(f"{empty_bins} 个概率区间没有样本，已在曲线上跳过")

        brier = float(np.mean((df[P_COL].to_numpy(dtype=float) - df[Y_COL].to_numpy(dtype=float)) ** 2))
        ece = float(np.sum(cal["n"] / len(df) * np.abs(cal["obs"] - cal["p_mean"])))
        stats = {"brier": brier, "ece": ece, "n": len(df)}

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
        gs = fig.add_gridspec(2, 1, height_ratios=[3.4, 1.2], hspace=0.06)
        ax = fig.add_subplot(gs[0, 0])
        ax_hist = fig.add_subplot(gs[1, 0], sharex=ax)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.plot([0, 1], [0, 1], color=roles["muted_text"], linestyle="--", linewidth=0.9,
                label="完美校准", zorder=1)
        ax.errorbar(cal["p_mean"], cal["obs"],
                    yerr=[cal["obs"] - cal["low"], cal["high"] - cal["obs"]],
                    fmt="o", color=roles["focal"], ecolor=roles["muted_text"],
                    elinewidth=1.0, capsize=2.5, capthick=1.0, markersize=5.0, zorder=3,
                    label="分箱观测")
        ax.plot(cal["p_mean"], cal["obs"], color=roles["focal"], linewidth=1.3, zorder=2)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.set_ylabel(Y_LABEL)
        ax.tick_params(axis="x", labelbottom=False)
        ax.text(0.015, 0.975, f"n = {len(df)}\nBrier = {brier:.3f}\nECE = {ece:.3f}",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=vs.font_size(theme, "annotation"), color=roles["text"], linespacing=1.35,
                bbox=dict(facecolor="#FFFFFF", edgecolor=roles["grid"], linewidth=0.5,
                          boxstyle="round,pad=0.3", alpha=0.92), zorder=5)
        leg = ax.legend(loc="lower right", frameon=False,
                        fontsize=vs.font_size(theme, "legend"), handletextpad=0.5,
                        columnspacing=1.2)
        vs.style_legend(leg, theme)

        centers = (cal["bin_low"] + cal["bin_high"]) / 2
        ax_hist.bar(centers, cal["n"], width=0.095, color=roles["context"], edgecolor="#FFFFFF",
                    linewidth=0.8, zorder=2)
        ax_hist.set_xlim(0, 1)
        ax_hist.set_xticks(np.linspace(0, 1, 6))
        ax_hist.set_xlabel(X_LABEL)
        ax_hist.set_ylabel(HIST_LABEL)
        ax_hist.set_ylim(0, float(cal["n"].max()) * 1.22)
        ax_hist.grid(False)
        for spine in ("top", "right"):
            ax_hist.spines[spine].set_visible(False)

        vs.add_header(fig, vs.fill_title(TITLE, **stats), SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.10, right=0.975, top=0.80, bottom=0.12, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = cal.copy()
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "calibration_histogram", "n": len(df), "bins": len(cal),
                       "brier": round(brier, 4), "ece": round(ece, 4),
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

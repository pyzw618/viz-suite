# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""E2E 01：科研多面板组图（academic scene）——均值 95% CI、趋势带、配对变化分布。"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "skills" / "viz-python" / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "input" / "experiment.csv"
OUT = HERE.parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

GROUPS = ["Control", "Treatment A", "Treatment B"]
CONDS = ["Baseline", "Week 4", "Week 8"]
COLORS = ["#0072B2", "#E69F00", "#009E73"]
MARKERS = ["o", "s", "^"]
LINESTYLES = ["-", "--", ":"]


def ci95(series):
    values = np.asarray(series, dtype=float)
    return 1.96 * values.std(ddof=1) / np.sqrt(len(values))


def main() -> int:
    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "figure": {}}
    warnings = result["warnings"]
    try:
        df = pd.read_csv(DATA)
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
        dropped = int(df["score"].isna().sum())
        df = df.dropna(subset=["score"])
        stats = df.groupby(["group", "condition"])["score"].agg(["mean", "std", "count"]).reset_index()
        stats["ci"] = stats.apply(lambda r: 1.96 * r["std"] / np.sqrt(r["count"]), axis=1)
        week8 = stats[stats["condition"] == "Week 8"].set_index("group").reindex(GROUPS)

        theme = vs.resolve_theme()
        theme.setdefault("typography", {}).setdefault("size_pt", {}).update({
            "title": 8.0, "subtitle": 7.0, "axis_label": 7.0, "tick": 6.5,
            "legend": 6.5, "annotation": 6.0, "source": 6.0, "panel_label": 9.0,
        })
        plan = vs.plan_size(183, 0.42, theme=theme)
        theme = vs.bootstrap(theme, font_scale=plan["font_scale"])
        fig = plt.figure(figsize=plan["figsize"], dpi=110, facecolor="white")
        axes = [fig.add_axes([0.07, 0.24, 0.24, 0.64]),
                fig.add_axes([0.39, 0.24, 0.27, 0.64]),
                fig.add_axes([0.73, 0.24, 0.24, 0.64])]
        for ax in axes:
            vs.apply_style(ax, "clean_open", theme=theme)

        # a. Week 8 mean ± 95% CI
        ax = axes[0]
        x = np.arange(len(GROUPS))
        ax.bar(x, week8["mean"], yerr=week8["ci"], color=[vs.blend(c, "#FFFFFF", 0.22) for c in COLORS],
               edgecolor=COLORS, linewidth=0.8, capsize=2.2, error_kw={"elinewidth": 0.7, "capthick": 0.7})
        ax.set_xticks(x)
        ax.set_xticklabels([f"{g}\n(n={int(week8.loc[g,'count'])})" for g in GROUPS], fontsize=6.2)
        ax.set_ylabel("Score at Week 8 (0–100)", fontsize=7)
        ax.set_ylim(0, 100)
        for i, g in enumerate(GROUPS):
            ax.text(i, week8.loc[g, "mean"] + week8.loc[g, "ci"] + 2, f"{week8.loc[g,'mean']:.1f}",
                    ha="center", va="bottom", fontsize=6.5, color="#1F2937")
        vs.panel_label(ax, "a", theme=theme, x=-0.22, y=1.04)

        # b. trend with 95% CI bands
        ax = axes[1]
        for i, g in enumerate(GROUPS):
            part = stats[stats["group"] == g].set_index("condition").reindex(CONDS)
            y = part["mean"].to_numpy(float)
            ci = part["ci"].to_numpy(float)
            xs = np.arange(len(CONDS))
            ax.fill_between(xs, y - ci, y + ci, color=COLORS[i], alpha=0.16, linewidth=0)
            ax.plot(xs, y, color=COLORS[i], marker=MARKERS[i], linestyle=LINESTYLES[i],
                    linewidth=1.0, markersize=3.0, label=g)
        ax.set_xticks(np.arange(len(CONDS)))
        ax.set_xticklabels(CONDS, fontsize=6.2)
        ax.set_ylabel("Score (0–100)", fontsize=7)
        ax.set_ylim(0, 100)
        ax.legend(loc="upper left", frameon=False, fontsize=6.0, handlelength=1.4)
        vs.panel_label(ax, "b", theme=theme, x=-0.20, y=1.04)

        # c. paired change (Week 8 - Baseline)
        ax = axes[2]
        pivot = df.pivot_table(index=["subject_id", "group"], columns="condition", values="score").reset_index()
        pivot["change"] = pivot["Week 8"] - pivot["Baseline"]
        rng = np.random.default_rng(20261025)
        for i, g in enumerate(GROUPS):
            vals = pivot[pivot["group"] == g]["change"].to_numpy(float)
            bp = ax.boxplot([vals], positions=[i], widths=0.42, patch_artist=True,
                            showfliers=False, medianprops={"color": "#1F2937", "linewidth": 1.0},
                            boxprops={"facecolor": vs.blend(COLORS[i], "#FFFFFF", 0.75),
                                      "edgecolor": COLORS[i], "linewidth": 0.8},
                            whiskerprops={"color": COLORS[i], "linewidth": 0.7},
                            capprops={"color": COLORS[i], "linewidth": 0.7})
            jitter = rng.normal(0, 0.045, len(vals))
            ax.scatter(np.full(len(vals), i) + jitter, vals, s=5, color=COLORS[i],
                       alpha=0.42, linewidths=0, zorder=3)
            ax.scatter([i], [vals.mean()], marker="D", s=18, color="#FFFFFF",
                       edgecolor=COLORS[i], linewidth=0.8, zorder=4)
        ax.axhline(0, color="#6B7280", linestyle="--", linewidth=0.7, zorder=1)
        ax.set_xticks(np.arange(len(GROUPS)))
        ax.set_xticklabels(["Control", "A", "B"], fontsize=6.2)
        ax.set_ylabel("Change from baseline", fontsize=7)
        vs.panel_label(ax, "c", theme=theme, x=-0.24, y=1.04)

        vs.add_source(fig, "Source: synthetic experiment (n=30/group), error bars = 95% CI; no p-values fabricated.",
                      theme=theme)
        outputs = vs.save_figure(fig, OUT, "fig-academic-multipanel", formats=("pdf", "svg", "png"),
                                 dpi=(300, 600), theme=theme)
        caption = OUT / "caption.txt"
        caption.write_text(
            "Figure 1 | Mean scores at Week 8 (a), trajectories with 95% CI bands (b), and paired change from baseline (c). "
            "Bars/boxes are means with 95% CI; points are individual participants (n=30/group).\n"
            "Synthetic demonstration data. No p-values are shown because no hypothesis test was supplied.\n",
            encoding="utf-8")
        outputs.append(str(caption))
        result.update({
            "status": "success", "outputs": outputs, "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "figure": {"recipe": "custom-multipanel", "width_mm": plan["width_mm"],
                       "height_mm": plan["height_mm"], "panels": ["a", "b", "c"],
                       "visual_verified": False},
        })
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{type(exc).__name__}: {exc}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

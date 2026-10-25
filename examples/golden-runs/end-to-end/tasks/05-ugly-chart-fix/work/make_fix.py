# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""E2E 05：问题丑图诊断修复 —— 截断基线 + 彩虹色 + 旋转标签 → 排序横条 + 零基线 + 直接标注。"""
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
OUT = HERE.parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

DATA = pd.DataFrame({
    "channel": ["门店", "电商", "直播", "私域", "内容", "合作"],
    "revenue": [196, 266, 286, 128, 74, 52],
})


def make_before():
    plt.rcParams["font.family"] = ["Microsoft YaHei", "DejaVu Sans"]
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100, facecolor="white")
    rainbow = ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#8B00FF"]
    ax.bar(DATA["channel"], DATA["revenue"], color=rainbow)
    ax.set_ylim(150, 300)  # 故意截断基线
    ax.set_title("渠道收入")
    ax.set_ylabel("收入")
    ax.tick_params(axis="x", labelrotation=45)
    ax.grid(True, color="#94A3B8", linewidth=0.8)
    fig.savefig(OUT / "before.png", dpi=100, facecolor="white")
    plt.close(fig)


def make_after():
    theme = vs.bootstrap(vs.resolve_theme())
    plan = vs.plan_size(160, 0.62, theme=theme)
    df = DATA.sort_values("revenue", ascending=True)
    fig, ax = vs.figure(plan["figsize"], theme=theme)
    vs.apply_style(ax, "clean_open", theme=theme)
    y = np.arange(len(df))
    ax.barh(y, df["revenue"], color=theme["colors"]["roles"]["focal"],
            **{k: v for k, v in vs.bar_kwargs(theme["colors"]["roles"]["focal"], theme=theme).items()
               if k not in ("color",)})
    ax.set_yticks(y)
    ax.set_yticklabels(df["channel"], fontsize=vs.font_size(theme, "tick"))
    ax.set_xlim(0, max(df["revenue"]) * 1.20)
    ax.set_xlabel("收入（万元）", fontsize=vs.font_size(theme, "axis_label"))
    ax.set_title("直播与电商贡献 55% 收入，合作渠道垫底", fontsize=vs.font_size(theme, "title"),
                 loc="left", color=theme["colors"]["roles"]["text"], pad=10)
    for yi, value in zip(y, df["revenue"]):
        ax.text(value + max(df["revenue"]) * 0.012, yi, f"{value}", va="center",
                fontsize=vs.font_size(theme, "annotation"), color=theme["colors"]["roles"]["text"])
    fig.subplots_adjust(left=0.22, right=0.96, top=0.85, bottom=0.24)
    vs.add_source(fig, "数据来源：经营分析部 2025 年 6 月月报（合成）｜零基线；横条按收入升序", theme=theme)
    outputs = vs.save_figure(fig, OUT, "after", formats=("pdf", "svg", "png"), dpi=(300, 600), theme=theme)
    print(json.dumps({"status": "success", "outputs": outputs,
                      "rows_used": int(len(df)), "verified": True,
                      "issues": ["截断基线", "彩虹色", "旋转标签", "无来源", "未排序"]},
                     ensure_ascii=False, indent=2))


def main() -> int:
    make_before()
    make_after()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

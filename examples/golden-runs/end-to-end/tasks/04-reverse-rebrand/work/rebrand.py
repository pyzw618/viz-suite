# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""E2E 04：从截图反推数据，再用品牌 EXTEND 重新绘制（B 级 → 品牌换肤）。"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "skills" / "viz-python" / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "outputs" / "source_data.csv"
OUT = HERE.parent / "outputs"


def main() -> int:
    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "figure": {"recipe": "reverse-rebrand"}}
    try:
        df = pd.read_csv(DATA, encoding="utf-8-sig")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        dropped = int(df["value"].isna().sum())
        df = df.dropna(subset=["value"])
        theme = vs.bootstrap(vs.resolve_theme())
        plan = vs.plan_size(180, 0.70, theme=theme)
        fig, ax = vs.figure(plan["figsize"], theme=theme)
        vs.apply_style(ax, "clean_open", theme=theme)
        colors = [theme["colors"]["roles"]["focal"] for _ in range(len(df))]
        ax.bar(df["category"].astype(str), df["value"], color=colors, width=0.62,
               **{k: v for k, v in vs.bar_kwargs(theme["colors"]["roles"]["focal"], theme=theme).items()
                  if k not in ("color",)})
        ax.set_ylim(0, max(df["value"]) * 1.18)
        ax.set_ylabel("收入（万元）", fontsize=vs.font_size(theme, "axis_label"))
        ax.set_xlabel("渠道", fontsize=vs.font_size(theme, "axis_label"))
        ax.set_title("6 月渠道收入 · 品牌换肤版", fontsize=vs.font_size(theme, "title"),
                     color=theme["colors"]["roles"]["text"], loc="left", pad=10)
        for i, (cat, value) in enumerate(zip(df["category"].astype(str), df["value"])):
            ax.text(i, value + max(df["value"]) * 0.025, f"{value:.1f}", ha="center", va="bottom",
                    fontsize=vs.font_size(theme, "annotation"), color=theme["colors"]["roles"]["text"])
        vs.add_source(fig, "数据来源：截图逆向（B 级，中位误差 0.19%）｜品牌：focal #0F62FE", theme=theme)
        outputs = vs.save_figure(fig, OUT, "branded", formats=("pdf", "svg", "png"),
                                 dpi=(300, 600), theme=theme)
        result.update({
            "status": "success", "outputs": outputs, "rows_used": len(df), "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "figure": {**result["figure"], "width_mm": plan["width_mm"], "height_mm": plan["height_mm"],
                       "evidence_level": "B", "brand_focal": theme["colors"]["roles"]["focal"],
                       "visual_verified": False},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""E2E 06：分析 → 统计 → 绘图 → PDF/PPT 交接包。"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "skills" / "viz-figure" / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "input" / "regional_sales.csv"
OUT = HERE.parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "report": {}}
    try:
        df = pd.read_csv(DATA)
        for col in ("收入_万元", "目标_万元", "新客数", "满意度"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        dropped = int(df.isna().any(axis=1).sum())
        df = df.dropna()
        df["完成率"] = df["收入_万元"] / df["目标_万元"] * 100
        total = float(df["收入_万元"].sum())
        target = float(df["目标_万元"].sum())
        total_new = int(df["新客数"].sum())
        top = df.loc[df["收入_万元"].idxmax()]
        summary = pd.DataFrame([
            {"指标": "总收入_万元", "值": round(total, 1)},
            {"指标": "总目标_万元", "值": round(target, 1)},
            {"指标": "目标完成率", "值": f"{total / target * 100:.1f}%"},
            {"指标": "新客数", "值": total_new},
            {"指标": "最高收入区域", "值": top["区域"]},
        ])
        summary.to_csv(OUT / "summary.csv", index=False, encoding="utf-8-sig")

        theme = vs.bootstrap(vs.resolve_theme())
        theme.setdefault("typography", {}).setdefault("size_pt", {}).update({
            "title": 12, "axis_label": 8, "tick": 7, "annotation": 7, "source": 7,
        })
        fig = plt.figure(figsize=(8.27, 11.69), dpi=110, facecolor="white")
        fig.text(0.08, 0.93, "区域经营分析简报", fontsize=20, fontweight="bold", color="#1F2937")
        fig.text(0.08, 0.895, "2025 年 6 月｜确认收入口径｜合成演示数据", fontsize=9, color="#6B7280")
        fig.text(0.08, 0.84, f"总收入 {total:.0f} 万元，目标完成率 {total/target*100:.1f}%",
                 fontsize=14, color="#0F62FE", fontweight="bold")
        fig.text(0.08, 0.815, f"华东贡献最高（{top['收入_万元']:.0f} 万元）；东北完成率最低，需要复盘。",
                 fontsize=9.5, color="#374151")
        ax = fig.add_axes([0.10, 0.42, 0.82, 0.32])
        vs.apply_style(ax, "clean_open", theme=theme)
        order = df.sort_values("收入_万元", ascending=True)
        y = np.arange(len(order))
        ax.barh(y - 0.18, order["收入_万元"], height=0.34, color="#0072B2", label="实际")
        ax.barh(y + 0.18, order["目标_万元"], height=0.34, color="#FFFFFF",
                edgecolor="#6B7280", linewidth=0.8, linestyle="--", label="目标")
        ax.set_yticks(y); ax.set_yticklabels(order["区域"], fontsize=8)
        ax.set_xlabel("收入（万元）", fontsize=8)
        ax.legend(loc="lower right", frameon=False, fontsize=7)
        ax.set_title("各区域收入：实际 vs 目标", fontsize=10, loc="left")
        fig.text(0.08, 0.36, "关键指标", fontsize=11, fontweight="bold")
        fig.text(0.08, 0.32, f"总收入 {total:.0f} 万元｜目标 {target:.0f} 万元｜完成率 {total/target*100:.1f}%｜新客 {total_new:,} 人",
                 fontsize=8.5, color="#374151")
        fig.text(0.08, 0.05, "数据来源：区域经营月报（合成演示）｜分析：vize2e｜图：viz-python｜交接：PDF + 汇总 CSV + PPT 提纲",
                 fontsize=6.5, color="#6B7280")

        with PdfPages(OUT / "report.pdf") as pdf:
            pdf.savefig(fig, facecolor="white")
            plt.close(fig)
            fig2 = plt.figure(figsize=(8.27, 11.69), dpi=110, facecolor="white")
            fig2.text(0.08, 0.93, "附录：区域明细与交接说明", fontsize=18, fontweight="bold")
            headers = ["区域", "收入", "目标", "完成率", "新客", "满意度"]
            rows = [[r["区域"], f"{r['收入_万元']:.0f}", f"{r['目标_万元']:.0f}",
                     f"{r['完成率']:.1f}%", f"{r['新客数']:,}", f"{r['满意度']:.1f}"] for _, r in df.iterrows()]
            table = fig2.add_axes([0.08, 0.55, 0.84, 0.30])
            table.axis("off")
            tbl = table.table(cellText=rows, colLabels=headers, loc="upper left", cellLoc="center")
            tbl.auto_set_font_size(False); tbl.set_fontsize(8); tbl.scale(1, 1.5)
            fig2.text(0.08, 0.48, "统计口径", fontsize=11, fontweight="bold")
            fig2.text(0.08, 0.44, "完成率 = 实际收入 ÷ 目标收入；收入为确认收入；缺失行已剔除；数值四舍五入。",
                      fontsize=9, color="#374151")
            fig2.text(0.08, 0.36, "PPT 交接（5 页）", fontsize=11, fontweight="bold")
            slides = ["1. 标题：区域经营 6 月复盘",
                      f"2. 结论：总收入 {total:.0f} 万元，完成率 {total/target*100:.1f}%",
                      "3. 图：各区域实际 vs 目标", "4. 表：区域明细与完成率", "5. 行动：东北复盘、华东复制"]
            for i, line in enumerate(slides):
                fig2.text(0.10, 0.32 - i * 0.035, line, fontsize=9, color="#374151")
            fig2.text(0.08, 0.05, "交接包：report.pdf / summary.csv / chart.png / handoff.md",
                      fontsize=7, color="#6B7280")
            pdf.savefig(fig2, facecolor="white")
            plt.close(fig2)

        # chart 单独导出
        fig3, ax3 = vs.figure((6.4, 3.6), theme=theme)
        vs.apply_style(ax3, "clean_open", theme=theme)
        ax3.bar(order["区域"], order["收入_万元"], color="#0072B2")
        ax3.set_ylim(0, max(order["目标_万元"]) * 1.2)
        ax3.set_ylabel("收入（万元）", fontsize=8)
        ax3.set_title("各区域收入", fontsize=10, loc="left")
        chart_paths = vs.save_figure(fig3, OUT, "chart", formats=("png",), dpi=(300,), theme=theme)

        handoff = OUT / "handoff.md"
        handoff.write_text(
            "# 区域经营分析交接\n\n"
            f"- 总收入：{total:.0f} 万元；目标：{target:.0f} 万元；完成率：{total/target*100:.1f}%。\n"
            f"- 最高收入区域：{top['区域']}（{top['收入_万元']:.0f} 万元）；新客合计：{total_new:,}。\n"
            "- 图表：chart.png；明细：summary.csv；完整报告：report.pdf。\n"
            "- PPT 建议 5 页：标题 / 结论 / 实际 vs 目标 / 区域明细 / 行动。\n"
            "- 口径：确认收入；完成率=实际÷目标；合成演示数据。\n",
            encoding="utf-8")
        outputs = [str(OUT / "report.pdf"), str(OUT / "summary.csv"), str(handoff), *chart_paths]
        result.update({
            "status": "success", "outputs": outputs, "rows_used": len(df), "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "report": {"total_revenue": total, "total_target": target,
                       "completion": round(total / target * 100, 2), "top_region": top["区域"],
                       "slides": 5, "visual_verified": False},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "Pillow>=10"]
# ///
# -*- coding: utf-8 -*-
"""生成 Stage 4 逆向基准图：5 类核心干净图 + 低清图 + 3D 饼图。

这些图由已知数据生成，但逆向脚本只读取图像与人工/VLM 读出的刻度 JSON，
不读取 ground truth；ground truth 仅用于误差打分。
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
TICKS = HERE / "ticks"
GROUND = HERE / "ground-truth"
W, H, DPI = 1000, 700, 100
BLUE, ORANGE, GREEN, PINK, SKY = "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#56B4E9"
COLORS = [BLUE, ORANGE, GREEN, PINK, SKY]


def base(figsize=(W / DPI, H / DPI)):
    fig = plt.figure(figsize=figsize, dpi=DPI, facecolor="white")
    ax = fig.add_axes([0.13, 0.15, 0.80, 0.70])
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#1F2937")
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(direction="out", length=4, width=0.9, colors="#1F2937", labelsize=9)
    ax.grid(False)
    return fig, ax


def save(fig, path):
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)


def make_bar():
    cats = ["A", "B", "C", "D", "E"]
    values = [12, 18, 9, 24, 15]
    fig, ax = base()
    ax.bar(cats, values, color=BLUE, width=0.62)
    ax.set_ylim(0, 28)
    ax.set_yticks([0, 5, 10, 15, 20, 25])
    ax.set_xlabel("Channel", fontsize=10)
    ax.set_ylabel("Revenue (k)", fontsize=10)
    ax.set_title("Monthly Revenue by Channel", fontsize=14, pad=12)
    save(fig, IMAGES / "bar.png")
    meta = {"title": "Monthly Revenue by Channel", "x_label": "Channel", "y_label": "Revenue (k)",
            "categories": cats, "values": values, "x_ticks": cats, "y_ticks": [0, 5, 10, 15, 20, 25]}
    (GROUND / "bar.csv").write_text("category,value\n" + "".join(f"{c},{v}\n" for c, v in zip(cats, values)),
                                    encoding="utf-8")
    return meta


def make_line():
    x = [0, 1, 2, 3, 4, 5]
    a = [12, 18, 15, 24, 20, 28]
    b = [8, 10, 14, 16, 19, 22]
    fig, ax = base()
    ax.plot(x, a, color=BLUE, marker="o", linewidth=2, markersize=5, label="Series A")
    ax.plot(x, b, color=ORANGE, marker="s", linewidth=2, markersize=5, label="Series B")
    ax.set_xlim(-0.3, 5.3)
    ax.set_ylim(0, 32)
    ax.set_xticks(x)
    ax.set_yticks([0, 5, 10, 15, 20, 25, 30])
    ax.set_xlabel("Week", fontsize=10)
    ax.set_ylabel("Value", fontsize=10)
    ax.set_title("Weekly Trend by Series", fontsize=14, pad=12)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    save(fig, IMAGES / "line.png")
    meta = {"title": "Weekly Trend by Series", "x_label": "Week", "y_label": "Value",
            "x": x, "series": [{"name": "Series A", "values": a, "color": BLUE},
                                {"name": "Series B", "values": b, "color": ORANGE}],
            "x_ticks": x, "y_ticks": [0, 5, 10, 15, 20, 25, 30]}
    with (GROUND / "line.csv").open("w", encoding="utf-8") as f:
        f.write("x,series,value\n")
        for name, vals in [("Series A", a), ("Series B", b)]:
            for xv, v in zip(x, vals):
                f.write(f"{xv},{name},{v}\n")
    return meta


def make_scatter():
    rng = np.random.default_rng(20261025)
    x = np.linspace(0.4, 9.6, 20)
    y = 2.4 * x + 4 + rng.normal(0, 2.2, len(x))
    fig, ax = base()
    ax.scatter(x, y, s=42, color=GREEN, edgecolor="white", linewidth=0.7, zorder=3)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 35)
    ax.set_xticks([0, 2, 4, 6, 8, 10])
    ax.set_yticks([0, 5, 10, 15, 20, 25, 30, 35])
    ax.set_xlabel("Spend", fontsize=10)
    ax.set_ylabel("Conversions", fontsize=10)
    ax.set_title("Spend vs Conversions", fontsize=14, pad=12)
    save(fig, IMAGES / "scatter.png")
    pts = [{"x": round(float(xv), 3), "y": round(float(yv), 3)} for xv, yv in zip(x, y)]
    meta = {"title": "Spend vs Conversions", "x_label": "Spend", "y_label": "Conversions",
            "points": pts, "x_ticks": [0, 2, 4, 6, 8, 10], "y_ticks": [0, 5, 10, 15, 20, 25, 30, 35]}
    with (GROUND / "scatter.csv").open("w", encoding="utf-8") as f:
        f.write("x,y\n")
        for p in pts:
            f.write(f"{p['x']},{p['y']}\n")
    return meta


def make_pie():
    labels = ["North", "South", "East", "West", "Central"]
    values = [35, 25, 20, 12, 8]
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor="white")
    ax = fig.add_axes([0.12, 0.10, 0.76, 0.76])
    ax.pie(values, labels=labels, colors=COLORS, startangle=90, counterclock=False,
           wedgeprops={"edgecolor": "white", "linewidth": 1.5}, textprops={"fontsize": 9})
    ax.set_title("Share by Region", fontsize=14, pad=14)
    ax.axis("equal")
    save(fig, IMAGES / "pie.png")
    meta = {"title": "Share by Region", "categories": labels, "values": values,
            "colors": COLORS, "unit": "percent"}
    with (GROUND / "pie.csv").open("w", encoding="utf-8") as f:
        f.write("category,value\n")
        for c, v in zip(labels, values):
            f.write(f"{c},{v}\n")
    return meta


def make_heatmap():
    matrix = np.array([
        [0.10, 0.25, 0.40, 0.55, 0.70, 0.85],
        [0.20, 0.35, 0.50, 0.65, 0.80, 0.95],
        [0.05, 0.18, 0.33, 0.48, 0.63, 0.78],
        [0.30, 0.45, 0.60, 0.75, 0.90, 1.00],
        [0.00, 0.15, 0.30, 0.45, 0.60, 0.72],
    ])
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor="white")
    ax = fig.add_axes([0.10, 0.15, 0.72, 0.68])
    im = ax.imshow(matrix, cmap="viridis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(6))
    ax.set_xticklabels([f"C{i+1}" for i in range(6)], fontsize=9)
    ax.set_yticks(np.arange(5))
    ax.set_yticklabels([f"R{i+1}" for i in range(5)], fontsize=9)
    ax.set_xticks(np.arange(-0.5, 6, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 5, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", length=0)
    ax.set_title("Activation by Cohort", fontsize=14, pad=12)
    cax = fig.add_axes([0.85, 0.15, 0.035, 0.68])
    cb = fig.colorbar(im, cax=cax, ticks=[0, 0.25, 0.5, 0.75, 1.0])
    cb.ax.tick_params(labelsize=8)
    save(fig, IMAGES / "heatmap.png")
    meta = {"title": "Activation by Cohort", "matrix": matrix.tolist(),
            "vmin": 0, "vmax": 1, "rows": 5, "cols": 6,
            "x_ticks": [f"C{i+1}" for i in range(6)],
            "y_ticks": [f"R{i+1}" for i in range(5)],
            "colorbar_ticks": [0, 0.25, 0.5, 0.75, 1.0]}
    with (GROUND / "heatmap.csv").open("w", encoding="utf-8") as f:
        f.write("row,col,value\n")
        for r in range(5):
            for c in range(6):
                f.write(f"{r},{c},{matrix[r,c]:.3f}\n")
    return meta


def make_lowres():
    src = Image.open(IMAGES / "bar.png").convert("RGB")
    w = 400
    h = round(src.height * w / src.width)
    src.resize((w, h), Image.LANCZOS).save(IMAGES / "bar_lowres.png")
    return {"title": "Monthly Revenue by Channel", "source": "bar.png"}


def make_3d_pie():
    # 将饼体压扁并加阴影，模拟透视 3D 饼图；数据不可逆，应触发 X 级拒绝。
    src = Image.open(IMAGES / "pie.png").convert("RGB")
    body = src.crop((220, 110, 780, 630)).resize((900, 420), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), "white")
    shadow = Image.new("RGBA", (900, 460), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((10, 60, 890, 440), fill=(0, 0, 0, 80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    canvas.paste(shadow, (50, 170), shadow)
    canvas.paste(body, (50, 150))
    draw = ImageDraw.Draw(canvas)
    draw.text((60, 30), "3D Share by Region", fill="#1F2937")
    draw.text((70, 610), "Perspective view — values not recoverable", fill="#6B7280")
    canvas.save(IMAGES / "pie_3d.png")
    return {"title": "3D Share by Region", "source": "pie.png", "expected": "X"}

def main() -> int:
    for d in (IMAGES, TICKS, GROUND):
        d.mkdir(parents=True, exist_ok=True)
    meta = {
        "bar": make_bar(),
        "line": make_line(),
        "scatter": make_scatter(),
        "pie": make_pie(),
        "heatmap": make_heatmap(),
        "bar_lowres": make_lowres(),
        "pie_3d": make_3d_pie(),
    }
    # ticks：只放人工/VLM 可读出的刻度、标题、系列颜色，不放数据值
    ticks = {
        "bar": {"title": "Monthly Revenue by Channel", "x_label": "Channel", "y_label": "Revenue (k)",
                "x": {"values": meta["bar"]["x_ticks"], "scale": "category"},
                "y": {"values": meta["bar"]["y_ticks"], "scale": "linear"}, "series": [{"name": "Revenue", "color": BLUE}]},
        "line": {"title": "Weekly Trend by Series", "x_label": "Week", "y_label": "Value",
                 "x": {"values": meta["line"]["x_ticks"], "scale": "linear"},
                 "y": {"values": meta["line"]["y_ticks"], "scale": "linear"},
                 "series": [{"name": s["name"], "color": s["color"]} for s in meta["line"]["series"]]},
        "scatter": {"title": "Spend vs Conversions", "x_label": "Spend", "y_label": "Conversions",
                    "x": {"values": meta["scatter"]["x_ticks"], "scale": "linear"},
                    "y": {"values": meta["scatter"]["y_ticks"], "scale": "linear"},
                    "series": [{"name": "Points", "color": GREEN}]},
        "pie": {"title": "Share by Region", "categories": meta["pie"]["categories"], "axes_rect": [0.12, 0.10, 0.76, 0.76],
                "series": [{"name": c, "color": col} for c, col in zip(meta["pie"]["categories"], COLORS)],
                "unit": "percent"},
        "heatmap": {"title": "Activation by Cohort", "rows": 5, "cols": 6,
                    "x": {"values": meta["heatmap"]["x_ticks"], "scale": "category"},
                    "y": {"values": meta["heatmap"]["y_ticks"], "scale": "category"},
                    "value_range": [0, 1], "colormap": "viridis",
                    "heatmap_rect": [0.10, 0.15, 0.72, 0.68],
                    "colorbar_rect": [0.85, 0.15, 0.035, 0.68],
                    "series": [{"name": "value", "color": "viridis"}]},
        "bar_lowres": {"title": "Monthly Revenue by Channel", "x_label": "Channel", "y_label": "Revenue (k)",
                       "x": {"values": meta["bar"]["x_ticks"], "scale": "category"},
                       "y": {"values": meta["bar"]["y_ticks"], "scale": "linear"},
                       "series": [{"name": "Revenue", "color": BLUE}]},
        "pie_3d": {"title": "3D Share by Region", "categories": meta["pie"]["categories"],
                   "series": [{"name": c, "color": col} for c, col in zip(meta["pie"]["categories"], COLORS)],
                   "unit": "percent"},
    }
    for key, value in ticks.items():
        (TICKS / f"{key}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "manifest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "success", "images": {k: f"images/{k}.png" for k in meta},
                      "ticks": len(ticks)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

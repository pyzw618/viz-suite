# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless>=4.9", "numpy>=1.24", "scipy>=1.10", "matplotlib>=3.8"]
# ///
# -*- coding: utf-8 -*-
"""轴标定与图元反推：图像 + measurements + 人工/VLM 刻度 → data.csv / reverse-spec / 复现代码。

支持 bar / line / scatter / pie / heatmap。严格只使用像素测量与刻度值；
不读取 ground truth，不为 SSIM 调数据。3D/透视直接拒绝数值反推。
"""
import argparse
import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")


def imread(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
    if img is None:
        raise ValueError(f"无法读取图像：{path}")
    return img


def hex_to_bgr(value: str):
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return np.array([b, g, r], dtype=np.float32)


def color_distance_mask(img, hex_color: str, tol: float = 42):
    target = cv2.cvtColor(np.uint8([[hex_to_bgr(hex_color)]]), cv2.COLOR_BGR2LAB)[0, 0].astype(np.float32)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    dist = np.linalg.norm(lab - target, axis=2)
    return (dist < tol).astype(np.uint8) * 255


def content_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return ((hsv[:, :, 1] > 45) & (hsv[:, :, 2] > 75)).astype(np.uint8) * 255


def parse_time(value):
    text = str(value)
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m", "%YQ%q"):
        try:
            if "%q" in fmt:
                year, q = text.upper().split("Q")
                month = (int(q) - 1) * 3 + 1
                return datetime(int(year), month, 1).toordinal()
            return datetime.strptime(text, fmt).toordinal()
        except (ValueError, TypeError):
            continue
    match = re.match(r"^(\d{4})[-/]?(\d{1,2})?", text)
    if match:
        year = int(match.group(1))
        month = int(match.group(2) or 1)
        return datetime(year, month, 1).toordinal()
    raise ValueError(f"无法解析时间：{value}")


def fit_axis(positions, values, scale: str, direction: str):
    positions = [float(p) for p in positions]
    if len(positions) != len(values):
        raise ValueError(f"刻度像素数 {len(positions)} 与刻度值数 {len(values)} 不一致")
    if len(positions) < 2:
        raise ValueError("至少需要两个刻度才能标定")
    if scale == "category":
        return {"scale": "category", "positions": positions, "values": values,
                "mapping": {str(v): p for v, p in zip(values, positions)}, "r2": 1.0}
    numeric = []
    if scale == "time":
        numeric = [parse_time(v) for v in values]
    else:
        numeric = [float(v) for v in values]
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    pos_sorted = [positions[i] for i in order]
    val_sorted = [numeric[i] for i in order]
    # y 轴：像素向下增大，数值应向下减小；x 轴：数值随像素增大。
    if direction == "y" and val_sorted[-1] > val_sorted[0]:
        val_sorted = val_sorted[::-1]
    elif direction == "x" and val_sorted[-1] < val_sorted[0]:
        val_sorted = val_sorted[::-1]
    transformed = [math.log10(v) for v in val_sorted] if scale == "log" else val_sorted
    a, b = np.polyfit(pos_sorted, transformed, 1)
    pred = [a * p + b for p in pos_sorted]
    mean = np.mean(transformed)
    ss_res = float(np.sum((np.array(transformed) - np.array(pred)) ** 2))
    ss_tot = float(np.sum((np.array(transformed) - mean) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
    return {"scale": scale, "a": float(a), "b": float(b), "r2": round(r2, 5),
            "positions": pos_sorted, "values": values, "direction": direction}


def value_at(pos: float, fit: dict):
    if fit["scale"] == "category":
        raise ValueError("category 轴不能做连续取值")
    raw = fit["a"] * pos + fit["b"]
    return 10 ** raw if fit["scale"] == "log" else raw


def pixel_to_date(pos: float, fit: dict):
    return datetime.fromordinal(int(round(value_at(pos, fit)))).strftime("%Y-%m-%d")


def main_repro_axes(plot, width, height):
    x0, y0, x1, y1 = plot
    return [x0 / width, 1 - y1 / height, (x1 - x0) / width, (y1 - y0) / height]


def largest_component(mask):
    num, labels, stats, cents = cv2.connectedComponentsWithStats(mask, 8)
    if num <= 1:
        return mask, None
    areas = stats[1:, cv2.CC_STAT_AREA]
    idx = int(np.argmax(areas)) + 1
    comp = (labels == idx).astype(np.uint8) * 255
    return comp, stats[idx]


def extract_bar(img, meas, ticks, axes):
    x0, y0, x1, y1 = [int(v) for v in meas["plot_bbox"]]
    roi = img[y0:y1 + 1, x0:x1 + 1]
    mask = content_mask(roi)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = roi.shape[:2]
    bars = []
    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        if area < 40 or bw < max(4, w * 0.008) or bh < max(6, h * 0.02):
            continue
        if bh / max(1, bw) < 0.25:
            continue
        center = x + bw / 2
        value = value_at(y0 + y, axes["y"])
        bars.append({"x_px": x0 + center, "top_px": y0 + y, "value": value})
    bars.sort(key=lambda b: b["x_px"])
    if not bars:
        raise ValueError("未找到柱形图元；请检查色彩阈值或图像类型")
    x_values = ticks["x"]["values"]
    # 用最近的 x 刻度/柱中心映射类别
    if len(bars) >= len(x_values):
        if len(bars) == len(x_values):
            for bar, cat in zip(bars, x_values):
                bar["category"] = str(cat)
        else:
            # 分组柱：按最近刻度分到类别，保留多条
            xpos = meas["x_ticks_px"] or [b["x_px"] for b in bars]
            for bar in bars:
                nearest = min(range(len(xpos)), key=lambda i: abs(bar["x_px"] - xpos[i]))
                bar["category"] = str(x_values[nearest])
    else:
        for i, bar in enumerate(bars):
            bar["category"] = str(x_values[i]) if i < len(x_values) else f"cat{i+1}"
    return [{"category": b["category"], "value": round(float(b["value"]), 3),
             "x_px": round(b["x_px"], 1)} for b in bars]


def extract_line(img, meas, ticks, axes):
    x0, y0, x1, y1 = [int(v) for v in meas["plot_bbox"]]
    roi = img[y0:y1 + 1, x0:x1 + 1]
    x_positions = meas.get("x_ticks_px") or []
    x_values = ticks["x"]["values"]
    if len(x_positions) != len(x_values):
        raise ValueError("line：x 刻度像素与刻度值数量不一致")
    rows = []
    for series in ticks.get("series", []):
        color = series.get("color")
        if not color or not color.startswith("#"):
            continue
        mask = color_distance_mask(roi, color)
        comp, stats = largest_component(mask)
        if stats is None or stats[cv2.CC_STAT_WIDTH] < (x1 - x0) * 0.25:
            # 连线段不连续时保留所有组件，按 x 采样
            comp = mask
        for px, xv in zip(x_positions, x_values):
            local = int(round(px - x0))
            band = comp[:, max(0, local - 2):min(comp.shape[1], local + 3)]
            ys = np.where(band > 0)[0]
            if len(ys) == 0:
                continue
            y_px = float(np.median(ys))
            value = value_at(y0 + y_px, axes["y"])
            rows.append({"x": xv, "series": series.get("name", "series"), "value": round(value, 3)})
    if not rows:
        raise ValueError("未找到折线图元；请检查系列颜色")
    return rows


def extract_scatter(img, meas, ticks, axes):
    x0, y0, x1, y1 = [int(v) for v in meas["plot_bbox"]]
    roi = img[y0:y1 + 1, x0:x1 + 1]
    rows = []
    for series in ticks.get("series", []):
        color = series.get("color")
        if not color or not color.startswith("#"):
            continue
        mask = color_distance_mask(roi, color)
        num, labels, stats, cents = cv2.connectedComponentsWithStats(mask, 8)
        for i in range(1, num):
            area = stats[i, cv2.CC_STAT_AREA]
            if area < 8:
                continue
            cx, cy = cents[i]
            rows.append({"x": round(value_at(x0 + cx, axes["x"]), 3),
                         "y": round(value_at(y0 + cy, axes["y"]), 3),
                         "series": series.get("name", "series")})
    if not rows:
        raise ValueError("未找到散点图元；请检查系列颜色")
    rows.sort(key=lambda r: (r["series"], r["x"]))
    return rows


def detect_colorbar(img, plot, ticks):
    x0, y0, x1, y1 = [int(v) for v in plot]
    roi = img[y0:y1 + 1, x0:x1 + 1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    sat = (hsv[:, :, 1] > 50).astype(np.float32)
    col_frac = sat.mean(axis=0)
    right_start = int(roi.shape[1] * 0.70)
    cols = np.where(col_frac[right_start:] > 0.55)[0] + right_start
    if len(cols) == 0:
        return None
    groups = []
    start = prev = int(cols[0])
    for c in cols[1:]:
        c = int(c)
        if c - prev > 2:
            groups.append((start, prev))
            start = c
        prev = c
    groups.append((start, prev))
    c0, c1 = max(groups, key=lambda g: g[1] - g[0])
    if (c1 - c0) > roi.shape[1] * 0.22:
        return None
    ys = np.where(sat[:, c0:c1 + 1].mean(axis=1) > 0.5)[0]
    if len(ys) == 0:
        return None
    return [x0 + c0, y0 + int(ys.min()), x0 + c1, y0 + int(ys.max())]


def extract_heatmap(img, meas, ticks, axes):
    x0, y0, x1, y1 = [int(v) for v in meas["plot_bbox"]]
    rows_n = int(ticks.get("rows", 0))
    cols_n = int(ticks.get("cols", 0))
    if rows_n <= 0 or cols_n <= 0:
        raise ValueError("heatmap 需要 ticks.rows/cols")
    vmin, vmax = ticks.get("value_range", [0, 1])
    heat_rect = ticks.get("heatmap_rect")
    colorbar_rect = ticks.get("colorbar_rect")
    h, w = img.shape[:2]
    if heat_rect:
        hx0, hx1 = int(heat_rect[0] * w), int((heat_rect[0] + heat_rect[2]) * w)
        hy0, hy1 = int((1 - heat_rect[1] - heat_rect[3]) * h), int((1 - heat_rect[1]) * h)
    else:
        cb = detect_colorbar(img, meas["plot_bbox"], ticks)
        hx0, hy0, hx1, hy1 = x0, y0, (cb[0] - 8 if cb else x1), y1
    if colorbar_rect:
        cx0, cx1 = int(colorbar_rect[0] * w), int((colorbar_rect[0] + colorbar_rect[2]) * w)
        cy0, cy1 = int((1 - colorbar_rect[1] - colorbar_rect[3]) * h), int((1 - colorbar_rect[1]) * h)
    else:
        cb = detect_colorbar(img, meas["plot_bbox"], ticks)
        if cb is None:
            raise ValueError("heatmap：未检测到颜色条，无法把颜色映射回数值")
        cx0, cy0, cx1, cy1 = cb
    # 颜色条 LUT：从下到上
    cxc = int((cx0 + cx1) / 2)
    samples = []
    for yy in range(cy1, cy0 - 1, -1):
        patch = img[yy, max(cx0, cxc - 2):min(w, cxc + 3)]
        bgr = patch.reshape(-1, 3).mean(axis=0)
        hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0, 0]
        if hsv[1] > 30:
            samples.append(bgr)
    if len(samples) < 10:
        raise ValueError("heatmap：颜色条采样不足")
    lut = cv2.cvtColor(np.uint8([[s for s in samples]]), cv2.COLOR_BGR2LAB)[0].astype(np.float32)
    cell_w = (hx1 - hx0) / cols_n
    cell_h = (hy1 - hy0) / rows_n
    matrix = []
    for r in range(rows_n):
        row = []
        for c in range(cols_n):
            cx = int(hx0 + (c + 0.5) * cell_w)
            cy = int(hy0 + (r + 0.5) * cell_h)
            patch = img[max(0, cy - 2):cy + 3, max(0, cx - 2):cx + 3].reshape(-1, 3).mean(axis=0)
            lab = cv2.cvtColor(np.uint8([[patch]]), cv2.COLOR_BGR2LAB)[0, 0].astype(np.float32)
            idx = int(np.argmin(np.linalg.norm(lut - lab, axis=1)))
            norm = idx / max(1, len(samples) - 1)
            row.append(round(float(vmin + norm * (vmax - vmin)), 4))
        matrix.append(row)
    return matrix, {"heatmap_bbox": [hx0, hy0, hx1, hy1], "colorbar_bbox": [cx0, cy0, cx1, cy1]}


def extract_pie(img, meas, ticks, axes):
    pie = meas.get("pie") or {}
    if not pie:
        raise ValueError("pie：缺少圆心/半径检测")
    cx, cy = pie["center"]
    radius = pie["radius"]
    series = ticks.get("series", [])
    if not series:
        raise ValueError("pie：ticks.series 需要颜色/名称")
    colors = [hex_to_bgr(s["color"]) for s in series if s.get("color", "").startswith("#")]
    if not colors:
        raise ValueError("pie：没有有效十六进制颜色")
    target_lab = cv2.cvtColor(np.uint8([[c for c in colors]]), cv2.COLOR_BGR2LAB)[0].astype(np.float32)
    counts = [0] * len(colors)
    total_samples = 0
    h, w = img.shape[:2]
    for angle in np.linspace(0, 2 * np.pi, 720, endpoint=False):
        for rf in (0.55, 0.65, 0.75):
            x = int(round(cx + radius * rf * math.cos(angle)))
            y = int(round(cy + radius * rf * math.sin(angle)))
            if not (0 <= x < w and 0 <= y < h):
                continue
            bgr = img[y, x].astype(np.float32)
            lab = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2LAB)[0, 0].astype(np.float32)
            dists = np.linalg.norm(target_lab - lab, axis=1)
            idx = int(np.argmin(dists))
            if dists[idx] <= 55:
                counts[idx] += 1
                total_samples += 1
            break
    if total_samples == 0:
        raise ValueError("pie：未能把扇区颜色映射到系列颜色")
    unit = ticks.get("unit", "percent")
    total_value = float(ticks.get("total", 0) or 0)
    out = []
    for s, count in zip(series, counts):
        share = count / total_samples * 100
        value = share if (unit == "percent" or total_value <= 0) else share / 100 * total_value
        out.append({"category": s.get("name", "slice"), "value": round(float(value), 3),
                    "share": round(float(share), 2), "color": s.get("color")})
    return out


def pylit(value):
    return "None" if value is None else json.dumps(value)


def write_reproduction_code(chart_type, data, spec, axes, ticks, width, height, code_path: Path):
    title = ticks.get("title", "")
    x_label = ticks.get("x_label", "")
    y_label = ticks.get("y_label", "")
    axes_rect = spec.get("axes_rect") or main_repro_axes(spec["plot_bbox"], width, height)
    ylim = spec.get("ylim")
    xlim = spec.get("xlim")
    if chart_type == "bar":
        cats = [r["category"] for r in data]
        vals = [r["value"] for r in data]
        color = (ticks.get("series") or [{"color": "#0072B2"}])[0].get("color", "#0072B2")
        body = f"""
CATS = {json.dumps(cats, ensure_ascii=False)}
VALS = {json.dumps(vals)}
COLOR = {json.dumps(color)}
AX_RECT = {json.dumps(axes_rect)}
XLIM = {pylit(xlim)}; YLIM = {pylit(ylim)}
TITLE = {json.dumps(title, ensure_ascii=False)}
XLABEL = {json.dumps(x_label, ensure_ascii=False)}
YLABEL = {json.dumps(y_label, ensure_ascii=False)}
YTICKS = {json.dumps(ticks.get('y', {}).get('values', []))}

def main():
    fig = plt.figure(figsize=({width / 100}, {height / 100}), dpi=100, facecolor='white')
    ax = fig.add_axes(AX_RECT)
    ax.bar(range(len(CATS)), VALS, color=COLOR, width=0.62)
    ax.set_xticks(range(len(CATS))); ax.set_xticklabels(CATS)
    if XLIM: ax.set_xlim(XLIM)
    if YLIM: ax.set_ylim(YLIM)
    if YTICKS: ax.set_yticks(YTICKS)
    ax.set_title(TITLE, fontsize=14, pad=12)
    if XLABEL: ax.set_xlabel(XLABEL, fontsize=10)
    if YLABEL: ax.set_ylabel(YLABEL, fontsize=10)
    style_axes(ax)
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)
"""
    elif chart_type == "line":
        series = [{"name": k, "values": [r["value"] for r in data if r["series"] == k],
                   "x": [r["x"] for r in data if r["series"] == k]}
                  for k in dict.fromkeys(r["series"] for r in data)]
        colors = {s.get("name"): s.get("color") for s in ticks.get("series", [])}
        body = f"""
SERIES = {json.dumps(series, ensure_ascii=False)}
COLORS = {json.dumps(colors, ensure_ascii=False)}
AX_RECT = {json.dumps(axes_rect)}
XLIM = {pylit(xlim)}; YLIM = {pylit(ylim)}
TITLE = {json.dumps(title, ensure_ascii=False)}
XLABEL = {json.dumps(x_label, ensure_ascii=False)}
YLABEL = {json.dumps(y_label, ensure_ascii=False)}
XTICKS = {json.dumps(ticks.get('x', {}).get('values', []))}
YTICKS = {json.dumps(ticks.get('y', {}).get('values', []))}

def main():
    fig = plt.figure(figsize=({width / 100}, {height / 100}), dpi=100, facecolor='white')
    ax = fig.add_axes(AX_RECT)
    for s in SERIES:
        ax.plot(s['x'], s['values'], color=COLORS.get(s['name'], '#0072B2'), marker='o',
                linewidth=2, markersize=5, label=s['name'])
    if XLIM: ax.set_xlim(XLIM)
    if YLIM: ax.set_ylim(YLIM)
    if XTICKS: ax.set_xticks(XTICKS)
    if YTICKS: ax.set_yticks(YTICKS)
    ax.legend(loc='upper left', frameon=False, fontsize=9)
    ax.set_title(TITLE, fontsize=14, pad=12)
    if XLABEL: ax.set_xlabel(XLABEL, fontsize=10)
    if YLABEL: ax.set_ylabel(YLABEL, fontsize=10)
    style_axes(ax)
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)
"""
    elif chart_type == "scatter":
        xs = [r["x"] for r in data]; ys = [r["y"] for r in data]
        color = (ticks.get("series") or [{"color": "#009E73"}])[0].get("color", "#009E73")
        body = f"""
X = {json.dumps(xs)}; Y = {json.dumps(ys)}
COLOR = {json.dumps(color)}
AX_RECT = {json.dumps(axes_rect)}
XLIM = {pylit(xlim)}; YLIM = {pylit(ylim)}
TITLE = {json.dumps(title, ensure_ascii=False)}
XLABEL = {json.dumps(x_label, ensure_ascii=False)}
YLABEL = {json.dumps(y_label, ensure_ascii=False)}
XTICKS = {json.dumps(ticks.get('x', {}).get('values', []))}
YTICKS = {json.dumps(ticks.get('y', {}).get('values', []))}

def main():
    fig = plt.figure(figsize=({width / 100}, {height / 100}), dpi=100, facecolor='white')
    ax = fig.add_axes(AX_RECT)
    ax.scatter(X, Y, s=42, color=COLOR, edgecolor='white', linewidth=0.7, zorder=3)
    if XLIM: ax.set_xlim(XLIM)
    if YLIM: ax.set_ylim(YLIM)
    if XTICKS: ax.set_xticks(XTICKS)
    if YTICKS: ax.set_yticks(YTICKS)
    ax.set_title(TITLE, fontsize=14, pad=12)
    if XLABEL: ax.set_xlabel(XLABEL, fontsize=10)
    if YLABEL: ax.set_ylabel(YLABEL, fontsize=10)
    style_axes(ax)
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)
"""
    elif chart_type == "pie":
        body = f"""
LABELS = {json.dumps([r['category'] for r in data], ensure_ascii=False)}
VALUES = {json.dumps([r['value'] for r in data])}
COLORS = {json.dumps([r.get('color', '#0072B2') for r in data], ensure_ascii=False)}
AX_RECT = {json.dumps(axes_rect)}
TITLE = {json.dumps(title, ensure_ascii=False)}

def main():
    fig = plt.figure(figsize=({width / 100}, {height / 100}), dpi=100, facecolor='white')
    ax = fig.add_axes(AX_RECT)
    ax.pie(VALUES, labels=LABELS, colors=COLORS, startangle=90, counterclock=False,
           wedgeprops={{'edgecolor': 'white', 'linewidth': 1.5}}, textprops={{'fontsize': 9}})
    ax.set_title(TITLE, fontsize=14, pad=14)
    ax.axis('equal')
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)
"""
    else:
        matrix = data
        vmin, vmax = spec.get("value_range", [0, 1])
        body = f"""
MATRIX = {json.dumps(matrix)}
VMIN, VMAX = {json.dumps([vmin, vmax])}
H_RECT = {pylit(spec.get('heatmap_rect') or axes_rect)}
CB_RECT = {pylit(spec.get("colorbar_rect"))}
TITLE = {json.dumps(title, ensure_ascii=False)}
XTICKS = {json.dumps([f'C{i+1}' for i in range(len(matrix[0]))])}
YTICKS = {json.dumps([f'R{i+1}' for i in range(len(matrix))])}

def main():
    fig = plt.figure(figsize=({width / 100}, {height / 100}), dpi=100, facecolor='white')
    ax = fig.add_axes(H_RECT)
    im = ax.imshow(MATRIX, cmap={json.dumps(ticks.get('colormap', 'viridis'))}, vmin=VMIN, vmax=VMAX, aspect='auto')
    ax.set_xticks(range(len(XTICKS))); ax.set_xticklabels(XTICKS, fontsize=9)
    ax.set_yticks(range(len(YTICKS))); ax.set_yticklabels(YTICKS, fontsize=9)
    ax.set_xticks(np.arange(-0.5, len(XTICKS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(YTICKS), 1), minor=True)
    ax.grid(which='minor', color='white', linewidth=2)
    ax.tick_params(which='minor', length=0)
    ax.set_title(TITLE, fontsize=14, pad=12)
    if CB_RECT:
        cax = fig.add_axes(CB_RECT)
        fig.colorbar(im, cax=cax, ticks={json.dumps(ticks.get('colorbar_ticks', [0, .25, .5, .75, 1]))})
    fig.savefig(Path(__file__).with_name('reproduction.png'), dpi=100, facecolor='white')
    plt.close(fig)
"""
    header = """# -*- coding: utf-8 -*-
# 由 viz-reverse/calibrate_and_extract.py 生成；只含反推数据与测得的样式参数。
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.family'] = 'DejaVu Sans'


def style_axes(ax):
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color('#1F2937')
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(direction='out', length=4, width=0.9, colors='#1F2937', labelsize=9)
    ax.grid(False)
"""
    code_path.write_text(header + body + "\n\nif __name__ == '__main__':\n    main()\n", encoding="utf-8")
    return code_path


def main() -> int:
    ap = argparse.ArgumentParser(description="轴标定与图元反推（B/C/X 级）")
    ap.add_argument("image")
    ap.add_argument("--measurements", required=True)
    ap.add_argument("--ticks", required=True)
    ap.add_argument("--chart-type", required=True, choices=["bar", "line", "scatter", "pie", "heatmap"])
    ap.add_argument("--outdir", default="reverse-output")
    ap.add_argument("--stem", default=None)
    ap.add_argument("--render", action="store_true", help="执行生成的 reproduction.py 并输出 PNG")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "reverse": {}}
    warnings = result["warnings"]
    try:
        image_path = Path(args.image)
        img = imread(image_path)
        height, width = img.shape[:2]
        measurements = json.loads(Path(args.measurements).read_text(encoding="utf-8"))
        ticks = json.loads(Path(args.ticks).read_text(encoding="utf-8"))
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        stem = args.stem or args.chart_type
        evidence = measurements.get("evidence_hint", "B")
        chart_type = args.chart_type
        if evidence == "X" or (measurements.get("pie") or {}).get("is_3d"):
            spec = {"chart_type": chart_type, "evidence_level": "X", "refused": True,
                    "reason": "3D/透视/不可逆图形：拒绝数值反推",
                    "measurements": measurements.get("plot_bbox"),
                    "warnings": warnings + ["仅提供 2D 规范化重构建议，不输出估算数据"]}
            spec_path = outdir / f"{stem}_reverse-spec.json"
            spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            suggestion = outdir / f"{stem}_2d-suggestion.md"
            suggestion.write_text(
                "# 2D 规范化重构建议\n\n"
                "该图使用了 3D 透视/椭圆投影，扇区面积与角度不可逆，不能据此反推比例。\n\n"
                "建议：改用 2D 饼/环图或条形图；保留原始类别名与业务口径；用直接标签标注百分比。\n"
                "如需复刻视觉，只能重建 2D 结构，不得声称还原了原始数值。\n",
                encoding="utf-8")
            result.update({"status": "partial", "outputs": [str(spec_path), str(suggestion)],
                           "verified": False, "reverse": spec})
            result["warnings"].append("X 级：3D/视角不可逆，已拒绝数值反推")
            payload = json.dumps(result, ensure_ascii=False, indent=2)
            if args.out:
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.out).write_text(payload + "\n", encoding="utf-8")
            print(payload)
            return 0

        # 轴标定
        x_positions = measurements.get("x_ticks_px") or []
        y_positions = measurements.get("y_ticks_px") or []
        if evidence == "C" and chart_type in ("bar", "line", "scatter"):
            x0, y0, x1, y1 = measurements["plot_bbox"]
            xv = ticks.get("x", {}).get("values", [])
            yv = ticks.get("y", {}).get("values", [])
            if len(x_positions) != len(xv):
                x_positions = list(np.linspace(x0 + (x1 - x0) * 0.06, x1 - (x1 - x0) * 0.06, len(xv)))
                warnings.append("C 级：x 刻度未检出，使用均匀位置近似")
            if len(y_positions) != len(yv):
                y_positions = list(np.linspace(y0 + (y1 - y0) * 0.08, y1 - (y1 - y0) * 0.02, len(yv)))
                warnings.append("C 级：y 刻度未检出，使用均匀位置近似")
        if chart_type in ("bar", "line", "scatter"):
            if len(x_positions) != len(ticks.get("x", {}).get("values", [])):
                warnings.append("x 刻度像素数与刻度值数不一致，尝试使用均匀位置")
                x_positions = list(np.linspace(measurements["plot_bbox"][0], measurements["plot_bbox"][2],
                                                len(ticks["x"]["values"])))
            axes = {
                "x": fit_axis(x_positions, ticks["x"]["values"], ticks["x"].get("scale", "linear"), "x"),
                "y": fit_axis(y_positions, ticks["y"]["values"], ticks["y"].get("scale", "linear"), "y"),
            }
        else:
            axes = {}

        # 限制/样式参数：由测得的 plot_bbox 与轴拟合反推
        spec = {"chart_type": chart_type, "evidence_level": evidence,
                "plot_bbox": measurements["plot_bbox"], "axes": axes,
                "series": ticks.get("series", []), "title": ticks.get("title", ""),
                "warnings": warnings, "no_compensation": True}
        if chart_type in ("bar", "line", "scatter"):
            x0, y0, x1, y1 = measurements["plot_bbox"]
            spec["ylim"] = [round(value_at(y1, axes["y"]), 3), round(value_at(y0, axes["y"]), 3)]
            if axes["x"]["scale"] == "linear":
                spec["xlim"] = [round(value_at(x0, axes["x"]), 3), round(value_at(x1, axes["x"]), 3)]
            else:
                spec["xlim"] = None

        if chart_type == "bar":
            data = extract_bar(img, measurements, ticks, axes)
            spec["xlim"] = [-0.65, len(data) - 0.35]
            csv_cols = ["category", "value"]
        elif chart_type == "line":
            data = extract_line(img, measurements, ticks, axes)
            csv_cols = ["x", "series", "value"]
        elif chart_type == "scatter":
            data = extract_scatter(img, measurements, ticks, axes)
            csv_cols = ["x", "y", "series"]
        elif chart_type == "pie":
            data = extract_pie(img, measurements, ticks, axes)
            spec["axes_rect"] = ticks.get("axes_rect") or [0.12, 0.10, 0.76, 0.76]
            csv_cols = ["category", "value", "share"]
        else:
            matrix, boxes = extract_heatmap(img, measurements, ticks, axes)
            data = matrix
            spec.update({"value_range": ticks.get("value_range", [0, 1]),
                         "heatmap_rect": ticks.get("heatmap_rect"), "colorbar_rect": ticks.get("colorbar_rect"),
                         "heatmap_bbox": boxes["heatmap_bbox"], "colorbar_bbox": boxes["colorbar_bbox"],
                         "rows": len(matrix), "cols": len(matrix[0]) if matrix else 0})
            csv_cols = ["row", "col", "value"]

        # 低清/C 级：明确降级，不声称精确
        if evidence == "C":
            warnings.append("C 级：低清/近似输入，数据仅作骨架参考，不承诺 5% 误差")
            spec["precision_claimed"] = False

        # 写 CSV
        csv_path = outdir / f"{stem}_data.csv"
        if chart_type == "heatmap":
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                f.write("row,col,value\n")
                for r, row in enumerate(data):
                    for c, value in enumerate(row):
                        f.write(f"{r},{c},{value}\n")
            result["rows_used"] = len(data) * (len(data[0]) if data else 0)
        else:
            with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
                f.write(",".join(csv_cols) + "\n")
                for row in data:
                    f.write(",".join(str(row.get(k, "")) for k in csv_cols) + "\n")
            result["rows_used"] = len(data)

        code_path = write_reproduction_code(chart_type, data, spec, axes, ticks, width, height,
                                            outdir / "reproduction.py")
        spec.update({"data_csv": str(csv_path), "code": str(code_path),
                     "rows": result["rows_used"], "status": "success" if evidence != "C" else "partial"})
        if args.render:
            proc = subprocess.run([sys.executable, str(code_path.resolve())], capture_output=True, text=True,
                                  cwd=str(outdir))
            if proc.returncode != 0:
                warnings.append(f"复现代码执行失败：{proc.stderr[-300:]}")
            else:
                spec["reproduction_png"] = str(outdir / "reproduction.png")
        spec_path = outdir / f"{stem}_reverse-spec.json"
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["outputs"] = [str(csv_path), str(spec_path), str(code_path)]
        if spec.get("reproduction_png"):
            result["outputs"].append(spec["reproduction_png"])
        result["status"] = "partial" if evidence == "C" else "success"
        result["verified"] = all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in result["outputs"])
        result["reverse"] = spec
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{type(exc).__name__}: {exc}")

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        result["outputs"].append(str(args.out))
        payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    return 0 if result["status"] in ("success", "partial") else 2


if __name__ == "__main__":
    raise SystemExit(main())

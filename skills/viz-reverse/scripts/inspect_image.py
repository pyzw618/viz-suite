# /// script
# requires-python = ">=3.10"
# dependencies = ["opencv-python-headless>=4.9", "numpy>=1.24", "Pillow>=10"]
# ///
# -*- coding: utf-8 -*-
"""像素级图表体检：绘图区定位、轴线/刻度检测、Lab 色彩聚类、文本裁剪放大。

输出 measurements.json 与 text-crops/*.png。刻度文本与图例名称由多模态读图
写入 ticks JSON；本脚本不读取 ground truth，也不反推数据。
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")


def imread(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    if data.size == 0:
        raise ValueError(f"无法读取文件：{path}")
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法解码图像：{path}")
    return img


def imwrite(path: Path, img) -> None:
    ok, buf = cv2.imencode(path.suffix or ".png", img)
    if not ok:
        raise ValueError(f"无法编码图像：{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    buf.tofile(str(path))


def rgb_hex(bgr) -> str:
    b, g, r = [int(round(v)) for v in bgr]
    return f"#{r:02X}{g:02X}{b:02X}"


def content_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    return ((sat > 45) & (val > 75)).astype(np.uint8) * 255


def bbox_of(mask):
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def dark_mask(gray):
    return ((gray < 115).astype(np.uint8)) * 255


def longest_line(mask, axis):
    h, w = mask.shape
    if axis == "v":
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(24, h // 8)))
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        score = opened.sum(axis=0) / 255.0
        positions = np.where(score > max(10, h * 0.18))[0]
        if len(positions) == 0:
            return None, None
        groups = []
        start = prev = int(positions[0])
        for p in positions[1:]:
            p = int(p)
            if p - prev > 2:
                groups.append((start, prev))
                start = p
            prev = p
        groups.append((start, prev))
        best = max(groups, key=lambda g: score[g[0]:g[1] + 1].max())
        x = int(round((best[0] + best[1]) / 2))
        rows = np.where(opened[:, best[0]:best[1] + 1].sum(axis=1) > 0)[0]
        return x, (int(rows.min()), int(rows.max())) if len(rows) else None
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(24, w // 8), 1))
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    score = opened.sum(axis=1) / 255.0
    positions = np.where(score > max(10, w * 0.18))[0]
    if len(positions) == 0:
        return None, None
    groups = []
    start = prev = int(positions[0])
    for p in positions[1:]:
        p = int(p)
        if p - prev > 2:
            groups.append((start, prev))
            start = p
        prev = p
    groups.append((start, prev))
    best = max(groups, key=lambda g: score[g[0]:g[1] + 1].max())
    y = int(round((best[0] + best[1]) / 2))
    cols = np.where(opened[best[0]:best[1] + 1, :].sum(axis=0) > 0)[0]
    return y, (int(cols.min()), int(cols.max())) if len(cols) else None


def detect_axes(gray, hint):
    mask = dark_mask(gray)
    vx, vext = longest_line(mask, "v")
    hy, hext = longest_line(mask, "h")
    h, w = gray.shape
    if hint in ("pie", "heatmap"):
        return (None, None), (None, None)
    if vx is not None and vx > w * 0.55:
        vx = None
    if hy is not None and hy < h * 0.45:
        hy = None
    return (vx, vext), (hy, hext)


def _peaks(values, min_score=1):
    peaks = []
    if values.size == 0:
        return peaks
    threshold = max(min_score, values.max() * 0.25)
    i = 0
    while i < len(values):
        if values[i] < threshold:
            i += 1
            continue
        j = i
        while j + 1 < len(values) and values[j + 1] >= threshold:
            j += 1
        segment = values[i:j + 1]
        center = i + int(np.argmax(segment))
        peaks.append(center)
        i = j + 1
    return peaks


def group_peaks(peaks, min_gap=6):
    if not peaks:
        return []
    groups = [[peaks[0]]]
    for p in peaks[1:]:
        if p - groups[-1][-1] <= min_gap:
            groups[-1].append(p)
        else:
            groups.append([p])
    return [int(round(sum(g) / len(g))) for g in groups]


def detect_ticks(gray, plot, axis):
    x0, y0, x1, y1 = plot
    dark = dark_mask(gray)
    h, w = gray.shape
    if axis == "y":
        band = dark[max(0, y0):min(h, y1 + 1), max(0, x0 - 14):max(1, x0 - 1)]
        if band.size == 0:
            return []
        profile = (band > 0).sum(axis=1).astype(float)
        peaks = _peaks(profile, 1)
        return group_peaks([max(0, y0) + p for p in peaks], 8)
    band = dark[max(0, y1 + 2):min(h, y1 + 14), max(0, x0):min(w, x1 + 1)]
    if band.size == 0:
        return []
    profile = (band > 0).sum(axis=0).astype(float)
    peaks = _peaks(profile, 1)
    return group_peaks([max(0, x0) + p for p in peaks], 10)


def detect_pie(img, hint):
    mask = content_mask(img)
    h, w = mask.shape
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(9, w // 45), max(9, w // 45)))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    if len(contour) < 5:
        return None
    area = cv2.contourArea(contour)
    if area < 0.03 * w * h:
        return None
    (cx, cy), (ma, mi), angle = cv2.fitEllipse(contour)
    aspect = max(ma, mi) / max(1e-6, min(ma, mi))
    fill = area / max(1e-6, np.pi * ma * mi / 4)
    is_pie = hint == "pie" or (area > 0.10 * w * h and aspect < 2.5 and fill > 0.55)
    if not is_pie:
        return None
    return {
        "center": [round(float(cx), 1), round(float(cy), 1)],
        "radius": round(float(max(ma, mi) / 2), 1),
        "aspect": round(float(aspect), 3),
        "fill_ratio": round(float(fill), 3),
        "is_3d": bool(aspect > 1.22),
    }


def detect_palette(img, bbox, k=8):
    if bbox is None:
        return []
    x0, y0, x1, y1 = bbox
    crop = img[max(0, y0):min(img.shape[0], y1 + 1), max(0, x0):min(img.shape[1], x1 + 1)]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = (hsv[:, :, 1] > 55) & (hsv[:, :, 2] > 75)
    pixels = crop[mask]
    if len(pixels) < 20:
        return []
    if len(pixels) > 40000:
        idx = np.linspace(0, len(pixels) - 1, 40000).astype(int)
        pixels = pixels[idx]
    k = int(max(2, min(k, len(pixels))))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1.0)
    _, labels, centers = cv2.kmeans(pixels.astype(np.float32), k, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=k)
    total = counts.sum()
    out = []
    for count, center in sorted(zip(counts, centers), key=lambda x: -x[0]):
        share = float(count / total)
        if share < 0.01:
            continue
        out.append({"hex": rgb_hex(center), "share": round(share, 4), "bgr": [int(round(v)) for v in center]})
    return out


def save_crop(img, bbox, path: Path, scale=2, pad=8):
    if bbox is None:
        return None
    h, w = img.shape[:2]
    x0, y0, x1, y1 = bbox
    x0 = max(0, int(x0) - pad); y0 = max(0, int(y0) - pad)
    x1 = min(w, int(x1) + pad); y1 = min(h, int(y1) + pad)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = img[y0:y1, x0:x1]
    if scale != 1:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    imwrite(path, crop)
    return {"path": str(path), "bbox": [x0, y0, x1, y1], "scale": scale}


def text_regions(gray, plot, pie):
    h, w = gray.shape
    x0, y0, x1, y1 = plot if plot else (0, 0, w - 1, h - 1)
    dark = dark_mask(gray)
    regions = {}
    # 标题：绘图区上方
    top = dark[0:max(1, y0 - 4), :]
    regions["title"] = bbox_of(top)
    # 横轴标签/刻度：绘图区下方
    bottom = dark[min(h - 1, y1 + 2):h, :]
    regions["x_axis"] = bbox_of(bottom)
    # 纵轴标签：绘图区左侧
    left = dark[:, 0:max(1, x0 - 2)]
    regions["y_axis"] = bbox_of(left)
    # 图例/右上：优先取右上彩色块；没有则取上方右侧
    right_top = dark[0:max(1, y0), max(0, x0):w]
    regions["legend"] = bbox_of(right_top)
    return regions


def main() -> int:
    ap = argparse.ArgumentParser(description="像素级图表体检（图像 → measurements.json）")
    ap.add_argument("image")
    ap.add_argument("--chart-type", choices=["bar", "line", "scatter", "pie", "heatmap"], default=None)
    ap.add_argument("--outdir", default="reverse-work")
    ap.add_argument("--out", default=None)
    ap.add_argument("--min-width", type=int, default=800)
    ap.add_argument("--text-scale", type=float, default=2.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "measurements": {}}
    warnings = result["warnings"]
    try:
        image_path = Path(args.image)
        img = imread(image_path)
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        outdir = Path(args.outdir)
        crops_dir = outdir / "text-crops"
        crops_dir.mkdir(parents=True, exist_ok=True)

        pie = detect_pie(img, args.chart_type)
        (vx, vext), (hy, hext) = detect_axes(gray, args.chart_type)
        content = bbox_of(content_mask(img))
        if pie:
            x0, y0, x1, y1 = content
            plot = [x0, y0, x1, y1]
            axis_info = {"type": "none", "note": "pie 无坐标轴"}
        elif vx is not None and hy is not None:
            axis_top = vext[0] if vext else max(0, content[1] - 10)
            axis_right = hext[1] if hext else (content[2] if content else w - 10)
            plot = [vx, axis_top, axis_right, hy]
            axis_info = {"type": "cartesian", "y_axis_x": vx, "x_axis_y": hy,
                         "y_extent": list(vext) if vext else None,
                         "x_extent": list(hext) if hext else None}
        elif content:
            plot = list(content)
            axis_info = {"type": "none", "note": "未检测到坐标轴，使用内容包围盒"}
        else:
            raise ValueError("未检测到图表内容包围盒")

        x_ticks = detect_ticks(gray, plot, "x") if axis_info["type"] == "cartesian" else []
        y_ticks = detect_ticks(gray, plot, "y") if axis_info["type"] == "cartesian" else []
        palette = detect_palette(img, content or plot)
        regions = text_regions(gray, plot, pie)

        crops = []
        for name, bbox in regions.items():
            saved = save_crop(img, bbox, crops_dir / f"{name}.png", args.text_scale, 8)
            if saved:
                crops.append({"name": name, **saved})
        # 刻度条放大，便于多模态读刻度
        if x_ticks:
            xb = [min(x_ticks) - 6, int(plot[3]) + 2, max(x_ticks) + 6, min(h - 1, int(plot[3]) + 24)]
            saved = save_crop(img, xb, crops_dir / "x-ticks.png", args.text_scale, 4)
            if saved: crops.append({"name": "x-ticks", **saved})
        if y_ticks:
            yb = [max(0, int(plot[0]) - 42), min(y_ticks) - 6, max(0, int(plot[0]) + 2), max(y_ticks) + 6]
            saved = save_crop(img, yb, crops_dir / "y-ticks.png", args.text_scale, 4)
            if saved: crops.append({"name": "y-ticks", **saved})

        quality = {"sharpness": round(sharpness, 2),
                   "low_resolution": bool(w < args.min_width),
                   "width": w, "height": h}
        evidence = "B"
        if quality["low_resolution"]:
            evidence = "C"
            warnings.append(f"图像宽度 {w}px < {args.min_width}px：仅可按 C 级骨架/近似处理，不承诺精确反推")
        if sharpness < 18:
            evidence = "C" if evidence == "B" else evidence
            warnings.append(f"图像清晰度偏低（Laplacian variance={sharpness:.1f}）：建议标注为 C 级")
        if pie and pie["is_3d"]:
            evidence = "X"
            warnings.append("检测到椭圆/透视饼图（aspect>1.22）：3D 透视不可逆，拒绝数值反推")
        chart_hint = args.chart_type or ("pie" if pie else "bar")

        measurements = {
            "image": str(image_path),
            "width": w, "height": h,
            "dpi": None,
            "plot_bbox": [int(round(v)) for v in plot],
            "axis": axis_info,
            "content_bbox": content,
            "x_ticks_px": x_ticks,
            "y_ticks_px": y_ticks,
            "palette": palette,
            "pie": pie,
            "quality": quality,
            "chart_type_hint": chart_hint,
            "evidence_hint": evidence,
            "text_crops": crops,
            "text_regions": {k: (list(v) if v else None) for k, v in regions.items()},
        }
        result["measurements"] = measurements
        measurements_path = outdir / "measurements.json"
        measurements_path.parent.mkdir(parents=True, exist_ok=True)
        measurements_path.write_text(json.dumps(measurements, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["outputs"] = [str(measurements_path)] + [c["path"] for c in crops]
        result["status"] = "success"
        result["verified"] = bool(x_ticks or y_ticks or pie)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"{type(exc).__name__}: {exc}")

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        result["outputs"].append(str(args.out))
        payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

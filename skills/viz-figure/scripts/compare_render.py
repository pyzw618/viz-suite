# /// script
# requires-python = ">=3.10"
# dependencies = ["scikit-image>=0.22", "numpy>=1.24", "Pillow>=10"]
# ///
# -*- coding: utf-8 -*-
"""原图与重绘图的往返比对：灰度 SSIM、CIEDE2000 ΔE、内容/布局 IoU、diff.png。"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.metrics import structural_similarity

sys.stdout.reconfigure(encoding="utf-8")


def load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0


def content_bbox(rgb: np.ndarray) -> tuple[int, int, int, int] | None:
    gray = rgb.mean(axis=2)
    mask = gray < 0.97
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def bbox_iou(a, b) -> float:
    if a is None or b is None:
        return 0.0
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    inter = max(0, ix1 - ix0 + 1) * max(0, iy1 - iy0 + 1)
    area_a = (ax1 - ax0 + 1) * (ay1 - ay0 + 1)
    area_b = (bx1 - bx0 + 1) * (by1 - by0 + 1)
    return float(inter / max(1, area_a + area_b - inter))


def main() -> int:
    ap = argparse.ArgumentParser(description="反向重绘往返比对")
    ap.add_argument("original")
    ap.add_argument("reproduction")
    ap.add_argument("--outdir", default="compare-output")
    ap.add_argument("--ssim-threshold", type=float, default=0.85)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "compare": {}}
    try:
        orig_path, repro_path = Path(args.original), Path(args.reproduction)
        orig = load(orig_path)
        repro = load(repro_path)
        if orig.shape[:2] != repro.shape[:2]:
            h, w = orig.shape[:2]
            repro_img = Image.fromarray((repro * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
            repro = np.asarray(repro_img, dtype=np.float32) / 255.0

        gray_o = np.dot(orig, [0.299, 0.587, 0.114])
        gray_r = np.dot(repro, [0.299, 0.587, 0.114])
        ssim = float(structural_similarity(gray_o, gray_r, data_range=1.0))
        lab_o = rgb2lab(orig)
        lab_r = rgb2lab(repro)
        d_e = deltaE_ciede2000(lab_o, lab_r)
        bbox_o, bbox_r = content_bbox(orig), content_bbox(repro)
        layout_iou = bbox_iou(bbox_o, bbox_r)
        mask_o = orig.mean(axis=2) < 0.97
        mask_r = repro.mean(axis=2) < 0.97
        union = np.logical_or(mask_o, mask_r).sum()
        content_iou = float(np.logical_and(mask_o, mask_r).sum() / union) if union else 1.0

        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        diff = ImageChops.difference(
            Image.fromarray((orig * 255).astype(np.uint8)),
            Image.fromarray((repro * 255).astype(np.uint8)))
        diff = ImageEnhance.Contrast(diff).enhance(2.2)
        diff_path = outdir / "diff.png"
        diff.save(diff_path)

        warnings = []
        if ssim < args.ssim_threshold:
            warnings.append(f"SSIM {ssim:.3f} < {args.ssim_threshold:.2f}：请检查结构/比例偏差，最多 3 轮；不得调数据")
        result.update({
            "status": "success",
            "outputs": [str(diff_path)],
            "verified": True,
            "warnings": warnings,
            "compare": {
                "original": str(orig_path), "reproduction": str(repro_path),
                "width": int(orig.shape[1]), "height": int(orig.shape[0]),
                "ssim": round(ssim, 4),
                "ssim_pass": bool(ssim >= args.ssim_threshold),
                "delta_e_mean": round(float(d_e.mean()), 3),
                "delta_e_median": round(float(np.median(d_e)), 3),
                "delta_e_content_mean": round(float(d_e[mask_o].mean()), 3) if mask_o.any() else None,
                "layout_iou": round(layout_iou, 4),
                "content_iou": round(content_iou, 4),
                "bbox_original": bbox_o, "bbox_reproduction": bbox_r,
                "diff": str(diff_path),
                "no_compensation": "本脚本只测量；未修改反推数据或添加像素偏移",
            },
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

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

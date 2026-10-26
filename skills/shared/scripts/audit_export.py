# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=10.0", "numpy>=1.24", "pypdf>=4.0", "defusedxml>=0.7"]
# ///
# -*- coding: utf-8 -*-
"""一站式成图体检：物理尺寸/DPI/白边、PDF 字体嵌入、WCAG 对比度、色盲色差、HTML 外链。

用法：
    uv run audit_export.py out/fig.pdf out/fig_300dpi.png --target-width-mm 160 --min-dpi 300 --json
    uv run audit_export.py out/fig.svg --palette "#0072B2,#E69F00,#CC79A7" --json
    uv run audit_export.py out/fig.png --fg "#1F2937" --bg "#FFFFFF" --json

分级：
    blocking = 数据失真风险（空图、字体未嵌入、外部 CDN、色盲不可分）
    warning  = 物理参数或可读性风险
    info     = 提示项
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

CVD = {
    "protanopia": [[0.152286, 1.052583, -0.204868],
                   [0.114503, 0.786281, 0.099216],
                   [-0.003882, -0.048116, 1.051998]],
    "deuteranopia": [[0.367322, 0.860646, -0.227968],
                     [0.280085, 0.672501, 0.047413],
                     [-0.011820, 0.042940, 0.968881]],
    "tritanopia": [[1.255528, -0.076749, -0.178779],
                   [-0.078411, 0.930809, 0.147602],
                   [0.004733, 0.691367, 0.303900]],
}


# --------------------------------------------------------------------------- #
# 色彩科学
# --------------------------------------------------------------------------- #
def hex2rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def srgb_to_linear(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = (srgb_to_linear(v) for v in rgb)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def hex_to_lab(value: str) -> tuple[float, float, float]:
    return rgb_to_lab(hex2rgb(value))


def ciede2000(lab1, lab2) -> float:
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    Cbar = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0.0
    dLp, dCp = L2 - L1, C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))
    Lbar, Cbarp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbarp = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbarp = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbarp = (h1p + h2p + 360) / 2
    else:
        hbarp = (h1p + h2p - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hbarp - 30))
         + 0.24 * math.cos(math.radians(2 * hbarp))
         + 0.32 * math.cos(math.radians(3 * hbarp + 6))
         - 0.20 * math.cos(math.radians(4 * hbarp - 63)))
    dtheta = 30 * math.exp(-(((hbarp - 275) / 25) ** 2))
    RC = 2 * math.sqrt(Cbarp ** 7 / (Cbarp ** 7 + 25 ** 7))
    SL = 1 + (0.015 * (Lbar - 50) ** 2) / math.sqrt(20 + (Lbar - 50) ** 2)
    SC, SH = 1 + 0.045 * Cbarp, 1 + 0.015 * Cbarp * T
    RT = -math.sin(math.radians(2 * dtheta)) * RC
    return math.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2
                     + RT * (dCp / SC) * (dHp / SH))


def simulate_cvd(value: str, mode: str) -> tuple[float, float, float]:
    lin = [srgb_to_linear(v) for v in hex2rgb(value)]
    matrix = CVD[mode]
    out = [sum(matrix[i][j] * lin[j] for j in range(3)) for i in range(3)]
    out = [min(1.0, max(0.0, v)) for v in out]

    def to_srgb(c: float) -> float:
        return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

    return rgb_to_lab(tuple(to_srgb(v) * 255 for v in out))


def relative_luminance(value: str) -> float:
    r, g, b = (srgb_to_linear(v) for v in hex2rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# --------------------------------------------------------------------------- #
# 检查项
# --------------------------------------------------------------------------- #
def add(checks: list, file: str, check: str, severity: str, passed: bool, detail: str, **extra):
    item = {"file": file, "check": check, "severity": severity,
            "passed": passed, "detail": detail}
    item.update(extra)
    checks.append(item)


def audit_png(path: Path, args) -> tuple[list, dict]:
    checks: list = []
    metrics: dict = {"file": str(path)}
    name = path.name
    raw_layout_audit = None
    try:
        with Image.open(path) as im:
            im.load()
            width_px, height_px = im.size
            mode = im.mode
            dpi_info = im.info.get("dpi")
            raw_layout_audit = im.info.get("viz_layout_audit")
            rgb = im.convert("RGB")
            gray_small = im.convert("L").resize((max(1, width_px // 8), max(1, height_px // 8)))
    except Exception as exc:  # noqa: BLE001
        add(checks, name, "read", "blocking", False, f"无法读取图像：{exc}")
        return checks, metrics

    metrics.update({"width_px": width_px, "height_px": height_px, "mode": mode})
    dpi = float(dpi_info[0]) if isinstance(dpi_info, tuple) and dpi_info else None
    metrics["dpi"] = round(dpi, 2) if dpi else None
    if dpi:
        width_mm = width_px / dpi * 25.4
        height_mm = height_px / dpi * 25.4
        metrics.update({"width_mm": round(width_mm, 2), "height_mm": round(height_mm, 2)})
        add(checks, name, "dpi", "info", True, f"{dpi:.0f} dpi，物理尺寸 {width_mm:.1f}×{height_mm:.1f} mm")
        if args.min_dpi and dpi + 0.6 < args.min_dpi:
            add(checks, name, "dpi_min", "warning", False,
                f"DPI {dpi:.0f} 低于要求 {args.min_dpi}")
        if args.target_width_mm:
            tol = max(0.6, args.target_width_mm * 0.01)
            ok = abs(width_mm - args.target_width_mm) <= tol
            add(checks, name, "physical_width", "warning" if not ok else "info", ok,
                f"实际宽 {width_mm:.2f}mm，目标 {args.target_width_mm}mm（容差 ±{tol:.2f}mm）")
    else:
        add(checks, name, "dpi", "warning", False,
            "PNG 未写入 DPI 元数据：无法核对物理尺寸，请用 savefig(dpi=...) 导出")

    gray = np.asarray(gray_small)
    if gray.size and int(gray.max()) - int(gray.min()) < 6:
        add(checks, name, "blank", "blocking", False, "图像近似纯色，可能白屏或渲染失败")
    else:
        add(checks, name, "blank", "info", True, "图像有可见内容")

    # 白边/裁切：在缩小图上估计内容包围盒
    scale = 400 / max(width_px, height_px)
    small = np.asarray(rgb.resize((max(1, int(width_px * scale)), max(1, int(height_px * scale)))), dtype=float)
    corners = np.concatenate([small[:4, :4].reshape(-1, 3), small[:4, -4:].reshape(-1, 3),
                              small[-4:, :4].reshape(-1, 3), small[-4:, -4:].reshape(-1, 3)])
    bg = np.median(corners, axis=0)
    metrics["background_rgb"] = [int(v) for v in bg]
    dist = np.linalg.norm(small - bg, axis=2)
    mask = dist > 18
    if mask.any():
        rows, cols = np.where(mask)
        top, bottom = rows.min() / small.shape[0], 1 - rows.max() / small.shape[0]
        left, right = cols.min() / small.shape[1], 1 - cols.max() / small.shape[1]
        margins = {"top": top, "bottom": bottom, "left": left, "right": right}
        metrics["content_margins_pct"] = {k: round(v * 100, 2) for k, v in margins.items()}
        if max(margins.values()) > 0.30:
            side = max(margins, key=margins.get)
            add(checks, name, "white_margin", "warning", False,
                f"{side} 侧空白占 {margins[side]:.0%}，可能布局失衡或裁剪过度")
        if min(margins.values()) < 0.002:
            side = min(margins, key=margins.get)
            add(checks, name, "cropping", "warning", False,
                f"{side} 侧内容贴边（{margins[side]:.2%}），可能被裁切")
        else:
            add(checks, name, "cropping", "info", True, "四周留有安全边距")
    else:
        add(checks, name, "cropping", "blocking", False, "未检测到内容像素")

    if args.fg and args.bg:
        ratio = contrast_ratio(args.fg, args.bg)
        level = "blocking" if ratio < 3.0 else ("warning" if ratio < 4.5 else "info")
        add(checks, name, "wcag_contrast", level, ratio >= 4.5,
            f"文本 {args.fg} / 背景 {args.bg} 对比度 {ratio:.2f}:1（正文要求 ≥4.5:1）",
            ratio=round(ratio, 2))
    else:
        add(checks, name, "wcag_contrast", "info", True,
            "未提供 --fg/--bg，跳过精确 WCAG 对比度；请在 SVG/HTML 或设计令牌中核对")

    if raw_layout_audit:
        try:
            la = json.loads(raw_layout_audit)
            metrics["layout_audit"] = la
            c_cnt = int(la.get("collision_count", 0))
            cl_cnt = int(la.get("clipped_count", 0))
            if c_cnt > 0:
                sample = la.get("collisions", [{}])[0]
                detail = (f"Renderer 检测到 {c_cnt} 处文本/图例重叠，首例："
                          f"{sample.get('a_role')}「{sample.get('a_text')}」× "
                          f"{sample.get('b_role')}「{sample.get('b_text')}」")
                add(checks, name, "text_collision", "blocking", False, detail,
                    collisions=la.get("collisions", []))
            else:
                add(checks, name, "text_collision", "info", True, "Renderer 文本与图例包围盒零重叠")
            if cl_cnt > 0:
                sample_cl = la.get("clipped", [{}])[0]
                add(checks, name, "text_clipped", "blocking", False,
                    f"检测到 {cl_cnt} 处文本超出画布边界，首例：{sample_cl.get('role')}「{sample_cl.get('text')}」",
                    clipped=la.get("clipped", []))
        except json.JSONDecodeError:
            pass

    return checks, metrics


def _resolve(obj):
    return obj.get_object() if hasattr(obj, "get_object") else obj


def pdf_fonts(page) -> list[dict]:
    records: list[dict] = []
    try:
        resources = _resolve(page.get("/Resources"))
        if not resources:
            return records
        fonts = _resolve(resources.get("/Font"))
        if not fonts:
            return records
        for key, ref in fonts.items():
            try:
                font = _resolve(ref)
                base = str(font.get("/BaseFont", key))
                subtype = str(font.get("/Subtype", "?"))
                embedded = False
                descriptors = []
                if font.get("/FontDescriptor"):
                    descriptors.append(_resolve(font["/FontDescriptor"]))
                descendants = _resolve(font.get("/DescendantFonts")) or []
                if not isinstance(descendants, (list, tuple)):
                    descendants = [descendants]
                for descendant in descendants:
                    desc = _resolve(descendant)
                    if desc.get("/FontDescriptor"):
                        descriptors.append(_resolve(desc["/FontDescriptor"]))
                for desc in descriptors:
                    if any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")):
                        embedded = True
                if subtype == "/Type3":
                    embedded = True
                records.append({"name": base, "subtype": subtype, "embedded": embedded})
            except Exception as exc:  # noqa: BLE001
                records.append({"name": str(key), "subtype": "?", "embedded": False, "error": str(exc)})
    except Exception:  # noqa: BLE001
        pass
    return records


def audit_pdf(path: Path, args) -> tuple[list, dict]:
    checks: list = []
    metrics: dict = {"file": str(path)}
    name = path.name
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            add(checks, name, "encryption", "warning", False, "PDF 已加密，字体与页面检查可能不完整")
        pages = len(reader.pages)
        metrics["pages"] = pages
        if pages == 0:
            add(checks, name, "pages", "blocking", False, "PDF 没有页面")
            return checks, metrics
        page = reader.pages[0]
        width_pt = float(page.mediabox.width)
        height_pt = float(page.mediabox.height)
        width_mm, height_mm = width_pt * 25.4 / 72, height_pt * 25.4 / 72
        metrics.update({"width_mm": round(width_mm, 2), "height_mm": round(height_mm, 2),
                        "page_size_mm": [round(width_mm, 2), round(height_mm, 2)]})
        add(checks, name, "pdf_page_size", "info", True,
            f"{pages} 页；首页 {width_mm:.1f}×{height_mm:.1f} mm")
        if args.target_width_mm:
            tol = max(0.6, args.target_width_mm * 0.01)
            ok = abs(width_mm - args.target_width_mm) <= tol
            add(checks, name, "physical_width", "warning" if not ok else "info", ok,
                f"首页宽 {width_mm:.2f}mm，目标 {args.target_width_mm}mm")

        fonts = pdf_fonts(page)
        metrics["fonts"] = fonts
        non_embedded = [f for f in fonts if not f.get("embedded")]
        if non_embedded:
            add(checks, name, "pdf_fonts", "blocking", False,
                f"{len(non_embedded)} 个字体未嵌入：{[f['name'] for f in non_embedded]}；跨机可能乱码")
        elif fonts:
            add(checks, name, "pdf_fonts", "info", True, f"{len(fonts)} 个字体全部嵌入")
        else:
            add(checks, name, "pdf_fonts", "info", True, "未检测到字体（可能为纯矢量图形）")

        text = (page.extract_text() or "").strip()
        images = 0
        try:
            xobj = page["/Resources"].get("/XObject")
            if xobj:
                for ref in xobj.get_object().values():
                    obj = ref.get_object()
                    if str(obj.get("/Subtype")) == "/Image":
                        images += 1
        except Exception:  # noqa: BLE001
            pass
        vector_ops = 0
        try:
            contents = page.get_contents()
            if contents is not None:
                data = contents.get_data()
                vector_ops = len(re.findall(rb"(?<![A-Za-z])(?:re|m|l|c|S|f|B|b)(?![A-Za-z])", data))
        except Exception:  # noqa: BLE001
            pass
        metrics["text_chars"] = len(text)
        metrics["images"] = images
        metrics["vector_ops_approx"] = vector_ops
        if vector_ops:
            add(checks, name, "pdf_vector", "info", True,
                f"内容流含约 {vector_ops} 个矢量绘制操作（文字/图元保持矢量）")
        else:
            add(checks, name, "pdf_vector", "warning", False,
                "未检测到矢量绘制操作：图形可能被栅格化")
        if not text and images == 0 and vector_ops == 0:
            add(checks, name, "pdf_content", "blocking", False, "首页既无文本也无图像，可能空白")
        else:
            add(checks, name, "pdf_content", "info", True,
                f"首页文本 {len(text)} 字符，图像 {images} 个，矢量操作约 {vector_ops} 个")
    except Exception as exc:  # noqa: BLE001
        add(checks, name, "read", "blocking", False, f"PDF 解析失败：{type(exc).__name__}: {exc}")
    return checks, metrics


SVG_UNITS = {"pt": 25.4 / 72, "px": 25.4 / 96, "mm": 1.0, "cm": 10.0, "in": 25.4}


def parse_length(value: str | None) -> float | None:
    if not value:
        return None
    match = re.match(r"^\s*([0-9.]+)\s*(pt|px|mm|cm|in)?\s*$", str(value))
    if not match:
        return None
    number = float(match.group(1))
    return number * SVG_UNITS.get(match.group(2) or "px", 25.4 / 96)


def audit_svg(path: Path, args) -> tuple[list, dict]:
    checks: list = []
    metrics: dict = {"file": str(path)}
    name = path.name
    try:
        from defusedxml import ElementTree as SafeET
        root = SafeET.parse(str(path)).getroot()
    except Exception as exc:  # noqa: BLE001
        add(checks, name, "read", "blocking", False, f"SVG 解析失败：{type(exc).__name__}: {exc}")
        return checks, metrics

    width_mm = parse_length(root.get("width"))
    height_mm = parse_length(root.get("height"))
    if width_mm and height_mm:
        metrics.update({"width_mm": round(width_mm, 2), "height_mm": round(height_mm, 2)})
        add(checks, name, "svg_size", "info", True, f"物理尺寸 {width_mm:.1f}×{height_mm:.1f} mm")
        if args.target_width_mm:
            tol = max(0.6, args.target_width_mm * 0.01)
            ok = abs(width_mm - args.target_width_mm) <= tol
            add(checks, name, "physical_width", "warning" if not ok else "info", ok,
                f"实际宽 {width_mm:.2f}mm，目标 {args.target_width_mm}mm")
    else:
        add(checks, name, "svg_size", "warning", False,
            "根元素缺少绝对 width/height，只有 viewBox：物理尺寸不可控")

    texts = [el for el in root.iter() if el.tag.endswith("text")]
    families, sizes = set(), []
    for el in texts:
        style = (el.get("style") or "") + " " + (el.get("font-family") or "")
        for match in re.findall(r"font-family:\s*([^;]+)", style):
            for family in match.split(","):
                cleaned = family.strip().strip("'\"")
                if cleaned:
                    families.add(cleaned)
        for match in re.findall(r"font(?:-size)?:\s*([0-9.]+)(?:px|pt)?", style):
            try:
                sizes.append(float(match))
            except ValueError:
                pass
    metrics.update({"text_elements": len(texts), "font_families": sorted(families)})
    if not texts:
        add(checks, name, "svg_text", "warning", False,
            "SVG 中没有文本节点：文字可能已转曲，无法检索与编辑")
    else:
        add(checks, name, "svg_text", "info", True, f"{len(texts)} 个文本节点，字体：{sorted(families) or '未标注'}")
        if sizes and min(sizes) < 6.0:
            add(checks, name, "svg_font_size", "warning", False,
                f"最小字号 {min(sizes)}pt 低于 6pt 可读底线")

    external = []
    for el in root.iter():
        for attr in ("href", "{http://www.w3.org/1999/xlink}href"):
            value = el.get(attr)
            if value and re.match(r"^(https?:)?//", value.strip()):
                external.append(value)
        for attr in ("src", "{http://www.w3.org/1999/xlink}href"):
            value = el.get(attr)
            if value and re.match(r"^(https?:)?//", value.strip()):
                external.append(value)
    if external:
        add(checks, name, "svg_external", "blocking", False,
            f"发现 {len(external)} 个外部引用：{external[:3]}；离线交付会失效")
    else:
        add(checks, name, "svg_external", "info", True, "无外部网络引用")

    if args.palette:
        palette = [c for c in re.split(r"[,;\s]+", args.palette) if c.strip()]
        add_palette_checks(checks, name, palette, args)
    return checks, metrics


def audit_html(path: Path, args) -> tuple[list, dict]:
    checks: list = []
    metrics: dict = {"file": str(path)}
    name = path.name
    text = path.read_text(encoding="utf-8", errors="replace")
    resource_refs = re.findall(
        r'(?:src)\s*=\s*["\']((?:https?:)?//[^"\']+)', text, flags=re.I)
    link_refs = re.findall(
        r'<link[^>]+href\s*=\s*["\']((?:https?:)?//[^"\']+)', text, flags=re.I)
    ext = resource_refs + link_refs
    if ext:
        add(checks, name, "html_external", "blocking", False,
            f"发现 {len(ext)} 个外部资源：{ext[:3]}；违反离线自包含要求")
    else:
        add(checks, name, "html_external", "info", True, "无外部资源引用")
    if "<html" in text.lower() and not re.search(r"<html[^>]+lang=", text, flags=re.I):
        add(checks, name, "html_lang", "warning", False, "html 根元素缺少 lang 属性")
    if "<html" not in text.lower():
        add(checks, name, "html_doc", "warning", False, "缺少 html 根元素")
    metrics.update({"chars": len(text), "external_refs": len(ext)})
    return checks, metrics


def add_palette_checks(checks: list, name: str, palette: list[str], args):
    palette = [c if c.startswith("#") else f"#{c}" for c in palette]
    try:
        labs = [hex_to_lab(c) for c in palette]
    except ValueError:
        add(checks, name, "palette", "warning", False, f"无法解析色板：{palette}")
        return
    pairs = [(i, j) for i in range(len(palette)) for j in range(i + 1, len(palette))]
    if not pairs:
        return
    normal = min(ciede2000(labs[i], labs[j]) for i, j in pairs)
    detail = [f"正常 ΔE={normal:.1f}"]
    worst = normal
    for mode in CVD:
        labs_cvd = [simulate_cvd(c, mode) for c in palette]
        value = min(ciede2000(labs_cvd[i], labs_cvd[j]) for i, j in pairs)
        detail.append(f"{mode} ΔE={value:.1f}")
        worst = min(worst, value)
    threshold = args.min_delta_e
    severity = "blocking" if worst < threshold * 0.6 else ("warning" if worst < threshold else "info")
    add(checks, name, "cvd_palette", severity, worst >= threshold,
        f"色板最小色差：{'；'.join(detail)}（阈值 ΔE≥{threshold}）",
        min_delta_e=round(worst, 2))


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="成图体检（viz-audit）")
    ap.add_argument("files", nargs="+", help="PNG/JPG/PDF/SVG/HTML 文件")
    ap.add_argument("--target-width-mm", type=float, default=None, help="目标物理宽度（mm）")
    ap.add_argument("--min-dpi", type=int, default=300, help="最低 DPI（默认 300）")
    ap.add_argument("--fg", default=None, help="正文前景色（WCAG 检查）")
    ap.add_argument("--bg", default=None, help="背景色（WCAG 检查）")
    ap.add_argument("--palette", default=None, help="逗号分隔的系列色，用于色盲色差检查")
    ap.add_argument("--min-delta-e", type=float, default=10.0, help="色盲最小色差阈值")
    ap.add_argument("--strict", action="store_true", help="warning 也返回非零退出码")
    ap.add_argument("--out", default=None, help="另存 JSON 报告")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks: list = []
    metrics: list = []
    warnings: list[str] = []
    for raw in args.files:
        path = Path(raw)
        if not path.is_file():
            add(checks, path.name, "exists", "blocking", False, f"文件不存在：{path}")
            continue
        suffix = path.suffix.lower()
        if suffix in (".png", ".jpg", ".jpeg", ".webp"):
            c, m = audit_png(path, args)
        elif suffix == ".pdf":
            c, m = audit_pdf(path, args)
        elif suffix == ".svg":
            c, m = audit_svg(path, args)
        elif suffix in (".html", ".htm"):
            c, m = audit_html(path, args)
        else:
            add(checks, path.name, "type", "warning", False, f"暂不支持的类型：{suffix}")
            continue
        if args.palette and suffix in (".png", ".jpg", ".jpeg", ".webp", ".pdf"):
            add_palette_checks(checks, path.name, [c for c in re.split(r"[,;\s]+", args.palette) if c], args)
        checks.extend(c)
        metrics.append(m)

    blocking = [c for c in checks if c["severity"] == "blocking" and not c["passed"]]
    warned = [c for c in checks if c["severity"] == "warning" and not c["passed"]]
    warnings.extend(c["detail"] for c in blocking + warned)
    warnings.append("本脚本只做确定性物理/色彩检查；文字重叠、审美与士气需按 references/audit-checklist.md 用宿主读图工具目检")

    result = {
        "status": "success" if not blocking else "partial",
        "outputs": [],
        "rows_used": 0,
        "rows_dropped": 0,
        "verified": not blocking,
        "visual_verified": False,
        "warnings": warnings,
        "summary": {
            "files": len(metrics),
            "blocking": len(blocking),
            "warning": len(warned),
            "passed": sum(1 for c in checks if c["passed"]),
            "total_checks": len(checks),
        },
        "checks": checks,
        "metrics": metrics,
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        result["outputs"].append(str(args.out))
        payload = json.dumps(result, ensure_ascii=False, indent=2)

    if args.json or not sys.stdout.isatty():
        print(payload)
    else:
        print(f"检查 {len(metrics)} 个文件：blocking {len(blocking)} / warning {len(warned)}")
        for c in checks:
            if not c["passed"]:
                print(f"  [{c['severity']}] {c['file']} · {c['check']}: {c['detail']}")
        if not blocking:
            print("  ✓ 无阻塞级问题（仍需宿主读图工具目检排版与文字）")

    if blocking:
        return 1
    if args.strict and warned:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24"]
# ///
# -*- coding: utf-8 -*-
"""viz_style.py — viz-suite 共享视觉运行时（MIT）。

设计原则：语义归模型，计算归脚本。本模块只提供确定性的版式、取色与导出能力，
不包含任何图表模板逻辑（模板在 recipes/ 下）。

典型用法：
    import viz_style as vs
    theme = vs.bootstrap()                       # 读取 tokens / EXTEND.md / figure-manifest.json
    pal = vs.palette("okabe_ito", theme=theme)
    fig, ax = vs.figure(vs.plan_size(160, aspect=0.62)["figsize"])
    vs.apply_style(ax, "soft_grid", theme=theme)
    ax.barh(y, v, **vs.bar_kwargs(pal.pick(1)[0], theme))
    vs.save_figure(fig, "out", "fig-01")
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
import unicodedata
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, to_hex, to_rgba

__version__ = "2026.10"

_WARNED: set[str] = set()
_CACHE: dict[str, object] = {}

# --------------------------------------------------------------------------- #
# 资产定位
# --------------------------------------------------------------------------- #
def _asset_candidates() -> list[Path]:
    here = Path(__file__).resolve().parent
    cands: list[Path] = []
    if os.environ.get("VIZ_SUITE_ASSETS"):
        cands.append(Path(os.environ["VIZ_SUITE_ASSETS"]))
    seen: set[Path] = set()
    bases = [Path.cwd(), *Path.cwd().parents, here, *here.parents]
    for base in bases:
        for p in (base / ".viz-suite" / "assets",
                  base / "skills" / "viz-core" / "assets",
                  base / "viz-core" / "assets",
                  base / "assets"):
            if p not in seen:
                seen.add(p)
                cands.append(p)
    cands.append(here.parent / "assets")  # 直接放在 viz-python/scripts 时
    return cands


def _load_json_asset(filename: str) -> dict | None:
    for cand in _asset_candidates():
        path = cand / filename
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                warn_once(f"{path} 解析失败，继续尝试下一处资产")
    return None


_FALLBACK_TOKENS = {
    "colors": {
        "roles": {"focal": "#0072B2", "context": "#CBD5E1", "positive": "#198038",
                  "negative": "#DA1E28", "alert": "#D97706", "grid": "#E2E8F0",
                  "background": "#FFFFFF", "text": "#1F2937", "muted_text": "#6B7280"},
        "default_palette": "okabe_ito",
        "backgrounds": {"white": "#FFFFFF", "soft_tint": "#F8FAFC"},
    },
    "typography": {
        "font_zh": ["Microsoft YaHei", "SimHei", "sans-serif"],
        "font_en": ["Inter", "Arial", "DejaVu Sans"],
        "size_pt": {"title": 13, "subtitle": 10.5, "axis_label": 10, "tick": 9,
                     "legend": 9, "annotation": 8.5, "source": 7.5, "panel_label": 12},
        "font_size_levels": {"small": 0.9, "regular": 1.0, "large": 1.12},
        "min_effective_pt": 6.0,
    },
    "layout": {
        "families": {
            "clean_open": {"spines": ["left", "bottom"], "spine_width": 0.9,
                           "tick_direction": "out", "tick_length": 3.0,
                           "grid": "none", "canvas": "white", "legend_frame": False}
        },
        "line_widths": {"thin": 0.8, "regular": 1.1, "bold": 1.5},
        "grid_alpha": 0.35, "grid_linewidth": 0.6,
    },
    "marks": {"fill_alpha": 0.18, "edge_width": 1.0, "marker_edge": "#FFFFFF",
              "marker_edge_width": 0.6, "scatter_size": 14.0, "violin_alpha": 0.22,
              "box_alpha": 0.30, "jitter_width": 0.09,
              "mean_line": {"color": "#6B7280", "linestyle": "--", "linewidth": 0.9},
              "zero_line": {"color": "#9CA3AF", "linewidth": 0.8}},
    "figure": {"single_column_mm": 89, "double_column_mm": 183, "default_width_mm": 160,
               "default_aspect": 0.62,
               "export": {"vector": ["pdf", "svg"], "raster_dpi": [300, 600], "preview_dpi": 300}},
    "rules": {"zero_baseline": True, "horizontal_label_units": 12,
              "horizontal_category_count": 5, "cvd_min_delta_e": 10.0,
              "min_text_contrast_wcag": 4.5, "min_graphic_contrast_wcag": 3.0},
}

_FALLBACK_PALETTE = {
    "id": "okabe_ito",
    "name_zh": "Okabe-Ito 色盲安全",
    "colors": ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442"],
    "category_order": [0, 3, 2, 4, 5, 1, 6],
    "min_delta_e": {"normal": 21.7, "deuteranopia": 11.6, "protanopia": 12.3, "tritanopia": 10.9},
}


def warn_once(message: str) -> None:
    if message not in _WARNED:
        _WARNED.add(message)
        warnings.warn(message, stacklevel=2)


class _BenignFontWeightFilter(logging.Filter):
    """SimHei 等单字重字体在标题加粗时会打出可用性提示；中文实际由 YaHei Bold 回退，属良性噪音。"""

    def filter(self, record: logging.LogRecord) -> bool:
        return "Failed to find font weight" not in record.getMessage()


def _silence_benign_font_warnings() -> None:
    logger = logging.getLogger("matplotlib.font_manager")
    if not any(isinstance(f, _BenignFontWeightFilter) for f in logger.filters):
        logger.addFilter(_BenignFontWeightFilter())


def load_tokens() -> dict:
    if "tokens" not in _CACHE:
        data = _load_json_asset("tokens.json")
        if data is None:
            warn_once("未找到 tokens.json，已启用内置最小令牌集（请检查 skills/viz-core/assets 或 .viz-suite/assets）")
            data = _FALLBACK_TOKENS
        _CACHE["tokens"] = data
    return _CACHE["tokens"]  # type: ignore[return-value]


def load_palettes() -> dict:
    if "palettes" not in _CACHE:
        data = _load_json_asset("palettes.json")
        if data is None:
            warn_once("未找到 palettes.json，已启用内置 Okabe-Ito 色板")
            data = {"palettes": [_FALLBACK_PALETTE]}
        _CACHE["palettes"] = {p["id"]: p for p in data.get("palettes", [])}
    return _CACHE["palettes"]  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# 极简 YAML 子集解析（EXTEND.md：两层扁平映射，零额外依赖）
# --------------------------------------------------------------------------- #
def _parse_scalar(raw: str):
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("[") and raw.endswith("]"):
        return [_parse_scalar(x) for x in raw[1:-1].split(",") if x.strip()]
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    low = raw.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~"):
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def read_extend(path: str | Path) -> dict:
    """读取 EXTEND.md 内的 YAML 代码块（或裸 YAML），返回两层字典。"""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    blocks = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_block:
                in_block = False
            elif stripped.lower() in ("```yaml", "```yml", "```"):
                in_block = True
            continue
        if in_block:
            blocks.append(line)
    if not blocks:  # 允许直接把 YAML 写进 .viz-suite/EXTEND.md
        blocks = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    data: dict = {}
    section = None
    for line in blocks:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        key, _, value = line.strip().partition(":")
        key = key.strip()
        if indent == 0:
            if value.strip():
                data[key] = _parse_scalar(value)
                section = None
            else:
                section = key
                data.setdefault(section, {})
        elif section:
            data[section][key] = _parse_scalar(value)
    return data


def _find_upwards(name: str, start: Path | None = None) -> Path | None:
    start = start or Path.cwd()
    for base in [start, *start.parents]:
        p = base / name
        if p.is_file():
            return p
    return None


def resolve_theme(overrides: dict | None = None) -> dict:
    """优先级：显式 overrides > 项目 EXTEND.md > 用户 EXTEND.md > figure-manifest.json > tokens。"""
    tokens = json.loads(json.dumps(load_tokens()))  # deep copy
    theme = dict(tokens)
    theme["_source"] = "tokens"

    # manifest 提供任务级锁定默认值，但显式的团队/用户品牌规则（EXTEND）优先
    manifest_path = _find_upwards("figure-manifest.json")
    if manifest_path:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            theme["manifest"] = manifest
            theme["manifest_path"] = str(manifest_path)
            if manifest.get("palette"):
                theme.setdefault("colors", {})["default_palette"] = manifest["palette"]
            if manifest.get("layout_family"):
                theme["layout_family"] = manifest["layout_family"]
            if manifest.get("series_color_map"):
                theme["series_color_map"] = manifest["series_color_map"]
            if manifest.get("width_mm"):
                theme.setdefault("figure", {})["default_width_mm"] = manifest["width_mm"]
            if manifest.get("footer"):
                theme.setdefault("brand", {})["footer"] = manifest["footer"]
            if manifest.get("fonts"):
                theme.setdefault("typography", {}).update(manifest["fonts"])
        except json.JSONDecodeError:
            warn_once(f"figure-manifest.json 解析失败，已忽略：{manifest_path}")

    user_ext = Path.home() / ".viz-suite" / "EXTEND.md"
    if user_ext.is_file():
        _merge_extend(theme, read_extend(user_ext))

    proj_ext = _find_upwards(".viz-suite/EXTEND.md") or _find_upwards("EXTEND.md")
    if proj_ext:
        _merge_extend(theme, read_extend(proj_ext))

    if overrides:
        _deep_merge(theme, overrides)
        theme["_source"] = "overrides"

    theme.setdefault("palette_id", theme.get("colors", {}).get("default_palette", "okabe_ito"))
    theme.setdefault("layout_family", "clean_open")
    theme.setdefault("series_color_map", {})
    return theme


def _merge_extend(theme: dict, ext: dict) -> None:
    if not ext:
        return
    colors = ext.get("colors") or {}
    if colors:
        theme.setdefault("colors", {}).setdefault("roles", {}).update(
            {str(k).lower(): v for k, v in colors.items() if isinstance(v, str)}
        )
    typo = ext.get("typography") or {}
    if typo:
        theme.setdefault("typography", {})
        for key in ("font_zh", "font_en", "font_serif_zh"):
            if typo.get(key):
                value = typo[key]
                theme["typography"][key] = value if isinstance(value, list) else [
                    v.strip() for v in str(value).split(",") if v.strip()
                ]
    brand = ext.get("brand") or {}
    if brand:
        theme.setdefault("brand", {}).update(brand)
    stack = ext.get("stack") or {}
    if stack:
        theme.setdefault("stack", {}).update(stack)


def _deep_merge(base: dict, over: dict) -> None:
    for key, value in over.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# --------------------------------------------------------------------------- #
# 色彩：色板、派生色阶、合成对比度
# --------------------------------------------------------------------------- #
class Palette:
    def __init__(self, data: dict):
        self.id = data.get("id", "unknown")
        self.name_zh = data.get("name_zh", self.id)
        self.colors = [c.upper() for c in data.get("colors", [])]
        self.order = list(data.get("category_order") or range(len(self.colors)))
        self.min_delta_e = data.get("min_delta_e", {})
        self.colorblind_safe = bool(data.get("computed_colorblind_safe", False))
        self.safe_k = int(data.get("safe_k", len(self.colors)))
        self.note = data.get("note", "")
        self.low_contrast = set(c.upper() for c in data.get("low_contrast_colors", []))

    def __len__(self) -> int:
        return len(self.colors)

    def __getitem__(self, index: int) -> str:
        return self.colors[index]

    def pick(self, n: int) -> list[str]:
        if n > len(self.colors):
            raise ValueError(
                f"色板 {self.id} 只有 {len(self.colors)} 色，无法区分 {n} 个分类；"
                "请改用更大色板或将小类合并为「其他」"
            )
        return [self.colors[i] for i in self.order[:n]]

    def pick_safe(self, n: int) -> list[str]:
        colors = self.pick(n)
        if n > self.safe_k:
            warn_once(
                f"色板 {self.id} 在 protanopia/deuteranopia 下最多安全区分 {self.safe_k} 类；"
                "请叠加线型/纹理，或改用更大色板/合并小类"
            )
        bad = [c for c in colors if c in self.low_contrast]
        if bad:
            warn_once(f"色板 {self.id} 中 {bad} 与白底对比度偏低，请搭配深色描边或改用浅底")
        return colors

    def rgba(self, index: int, alpha: float) -> tuple[float, float, float, float]:
        return to_rgba(self.colors[index], alpha)

    def index_of(self, name_or_hex: str) -> int | None:
        target = name_or_hex.upper()
        for i, c in enumerate(self.colors):
            if c == target:
                return i
        return None


def palette(palette_id: str | None = None, theme: dict | None = None) -> Palette:
    theme = theme or resolve_theme()
    pid = palette_id or theme.get("palette_id") or "okabe_ito"
    palettes = load_palettes()
    if pid not in palettes:
        warn_once(f"未知色板 {pid}，已回退 okabe_ito")
        pid = "okabe_ito"
    return Palette(palettes.get(pid, _FALLBACK_PALETTE))


def series_color_map(names: list[str], pal: Palette | None = None,
                     theme: dict | None = None) -> dict[str, str]:
    """锁定同一业务实体的跨图同色：manifest.series_color_map 优先，其余按 category_order 分配。"""
    theme = theme or resolve_theme()
    pal = pal or palette(theme=theme)
    if len(names) > len(pal):
        raise ValueError(
            f"系列数 {len(names)} 超过色板 {pal.id} 的 {len(pal)} 色上限；"
            "请合并小类或改用更大色板"
        )
    if len(names) > pal.safe_k:
        warn_once(
            f"色板 {pal.id} 对 {len(names)} 个系列在色盲模拟下安全上限为 {pal.safe_k}；"
            "请叠加线型/纹理，或改用更大色板/合并小类"
        )
    locked = dict(theme.get("series_color_map") or {})
    colors = pal.pick(min(len(pal), max(len(names), 1)))
    used = set(locked.values())
    free = [c for c in colors if c not in used]
    out: dict[str, str] = {}
    cursor = 0
    for name in names:
        if name in locked:
            out[name] = locked[name]
        else:
            out[name] = free[cursor % len(free)] if free else colors[cursor % len(colors)]
            cursor += 1
    return out


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    r, g, b, _ = to_rgba(value)
    return r, g, b


def mix(color_a: str, color_b: str, ratio: float) -> str:
    """ratio=0 → a，ratio=1 → b（sRGB 空间线性混合）。"""
    a, b = _hex_to_rgb(color_a), _hex_to_rgb(color_b)
    return to_hex(tuple(a[i] + (b[i] - a[i]) * ratio for i in range(3)))


def blend(fill: str, background: str = "#FFFFFF", alpha: float = 1.0) -> str:
    """按真实合成公式计算：fill×alpha + background×(1-alpha)。"""
    return mix(background, fill, alpha)


def relative_luminance(color: str) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _hex_to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color_a: str, color_b: str) -> float:
    la, lb = relative_luminance(color_a), relative_luminance(color_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def contrast_text(fill: str, background: str = "#FFFFFF", alpha: float = 1.0,
                  dark: str = "#2D2D2D", light: str = "#FFFFFF") -> str:
    """热力图单元格/半透明色块上的标签自动黑白：取对比度更高者。"""
    composed = blend(fill, background, alpha)
    return dark if contrast_ratio(composed, dark) >= contrast_ratio(composed, light) else light


def sequential_cmap(base: str, name: str | None = None, n: int = 256,
                    light: str = "#FFFFFF", light_mix: float = 0.9) -> LinearSegmentedColormap:
    start = mix(light, base, 1.0 - light_mix)
    return LinearSegmentedColormap.from_list(name or f"seq_{base.strip('#')}", [start, base], N=n)


def _hex_to_lab(color: str) -> tuple[float, float, float]:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _hex_to_rgb(color))
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e2000(color_a: str, color_b: str) -> float:
    """CIEDE2000 色差，用于发散色阶两极选择与重复色检测。"""
    L1, a1, b1 = _hex_to_lab(color_a)
    L2, a2, b2 = _hex_to_lab(color_b)
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


def diverging_cmap(base: str, other: str | None = None, name: str | None = None,
                   midpoint: str = "#FFFFFF", n: int = 257,
                   palette_id: str | None = None, theme: dict | None = None) -> LinearSegmentedColormap:
    """两极取 base 与色板中距其最远的颜色；奇数 LUT 锁死纯白中性零点。"""
    if other is None:
        pal = palette(palette_id, theme=theme)
        candidates = [c for c in pal.colors if c.upper() != base.upper()]
        other = max(candidates, key=lambda c: delta_e2000(base, c)) if candidates else "#333333"
    half = max(1, n // 2)
    low = [mix(base, midpoint, i / half) for i in range(half)]
    high = [mix(midpoint, other, i / half) for i in range(half + 1)]
    cmap = LinearSegmentedColormap.from_list(name or f"div_{base.strip('#')}", low + high, N=n)
    return cmap


# --------------------------------------------------------------------------- #
# 字体与 rcParams
# --------------------------------------------------------------------------- #
def _installed_fonts() -> set[str]:
    if "font_names" not in _CACHE:
        _CACHE["font_names"] = {f.name for f in font_manager.fontManager.ttflist}
    return _CACHE["font_names"]  # type: ignore[return-value]


def available_fonts(candidates: list[str]) -> list[str]:
    installed = _installed_fonts()
    return [f for f in candidates if f in installed]


def bootstrap(theme: dict | None = None, font_scale: float = 1.0) -> dict:
    """应用字体与全局 rcParams，返回 theme。"""
    theme = theme or resolve_theme()
    _silence_benign_font_warnings()
    typo = theme.get("typography", {})
    zh = available_fonts(typo.get("font_zh", []))
    en = available_fonts(typo.get("font_en", []))
    if not zh:
        warn_once("未检测到任何可用的中文字体，中文可能显示为方块；请先运行 detect_fonts.py")
    stack = en + zh + ["DejaVu Sans", "sans-serif"]
    stack = list(dict.fromkeys(stack))
    mpl.rcParams.update({
        # 直接给 font.family 一个有序列表，matplotlib 才会按字形回退到中文字体；
        # 只写 "sans-serif" 时只会解析到列表第一个字体，中文会变成方块。
        "font.family": stack,
        "font.sans-serif": stack,
        "font.serif": available_fonts(typo.get("font_serif_zh", [])) + ["DejaVu Serif"],
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "figure.dpi": 110,
        "savefig.dpi": 300,
        "axes.titlesize": typo.get("size_pt", {}).get("title", 13) * font_scale,
        "axes.labelsize": typo.get("size_pt", {}).get("axis_label", 10) * font_scale,
        "xtick.labelsize": typo.get("size_pt", {}).get("tick", 9) * font_scale,
        "ytick.labelsize": typo.get("size_pt", {}).get("tick", 9) * font_scale,
        "legend.fontsize": typo.get("size_pt", {}).get("legend", 9) * font_scale,
        "axes.linewidth": theme.get("layout", {}).get("families", {})
                          .get(theme.get("layout_family", "clean_open"), {})
                          .get("spine_width", 0.9),
        "grid.alpha": theme.get("layout", {}).get("grid_alpha", 0.35),
        "grid.linewidth": theme.get("layout", {}).get("grid_linewidth", 0.6),
        "axes.facecolor": theme.get("colors", {}).get("roles", {}).get("background", "#FFFFFF"),
        "figure.facecolor": theme.get("colors", {}).get("backgrounds", {})
                            .get("white", "#FFFFFF"),
        "savefig.facecolor": "auto",
        "figure.autolayout": False,
    })
    theme["_font_stack"] = stack
    theme["_font_scale"] = font_scale
    return theme


# --------------------------------------------------------------------------- #
# 版式
# --------------------------------------------------------------------------- #
def font_size(theme: dict | None, key: str = "tick", scale: bool = True) -> float:
    """读取字号令牌，并应用 plan_size 推导出的字体缩放（引用宽度缩小时自动放大）。"""
    theme = theme or resolve_theme()
    base = theme.get("typography", {}).get("size_pt", {}).get(key, 9.0)
    factor = theme.get("_font_scale", 1.0) if scale else 1.0
    return float(base) * factor


def apply_style(ax, family: str | None = None, theme: dict | None = None,
                grid: str | None = None, border: str | None = None,
                line_width: str | None = None, font_size: str | None = None,
                legend_frame: bool | None = None, canvas: str | None = None):
    """应用受约束版式族。六个安全旋钮之外的分支不开放。"""
    theme = theme or resolve_theme()
    layout = theme.get("layout", {})
    families = layout.get("families", {})
    name = family or theme.get("layout_family", "clean_open")
    fallback = {"spines": ["left", "bottom"], "spine_width": 0.9, "tick_direction": "out",
                "tick_length": 3.0, "grid": "none", "canvas": "white", "legend_frame": False}
    spec = dict(families.get(name) or next(iter(families.values()), fallback))
    roles = theme.get("colors", {}).get("roles", {})
    levels = theme.get("typography", {}).get("font_size_levels", {})
    scale = levels.get(font_size or "regular", 1.0) if font_size else 1.0
    fscale = theme.get("_font_scale", 1.0)
    tick_pt = theme.get("typography", {}).get("size_pt", {}).get("tick", 9) * scale * fscale
    label_pt = theme.get("typography", {}).get("size_pt", {}).get("axis_label", 10) * scale * fscale

    if border:
        spec["spines"] = ["left", "bottom", "top", "right"] if border == "journal" else ["left", "bottom"]
    grid_mode = grid or spec.get("grid", "none")
    if grid_mode == "x":  # 旋钮只开放 none/y/both
        grid_mode = "both"
    if canvas:
        spec["canvas"] = canvas

    for side, spine in ax.spines.items():
        spine.set_visible(side in spec.get("spines", []))
        spine.set_linewidth(spec.get("spine_width", 0.9))
        spine.set_color(roles.get("text", "#1F2937"))

    tick_dir = spec.get("tick_direction", "out")
    ax.tick_params(axis="both", which="major", direction=tick_dir,
                   length=spec.get("tick_length", 3.0),
                   width=spec.get("tick_width", 0.8),
                   color=roles.get("text", "#1F2937"),
                   labelcolor=roles.get("text", "#1F2937"),
                   labelsize=tick_pt, top=False, right=False)
    if "top" in spec.get("spines", []) and tick_dir == "in":
        ax.tick_params(axis="x", top=True, labeltop=False)
    if "right" in spec.get("spines", []) and tick_dir == "in":
        ax.tick_params(axis="y", right=True, labelright=False)

    ax.grid(False)
    if grid_mode in ("y", "both"):
        ax.grid(True, axis="y", linestyle=spec.get("grid_style", "dashed"),
                linewidth=spec.get("grid_width", layout.get("grid_linewidth", 0.6)),
                color=spec.get("grid_color", roles.get("grid", "#E2E8F0")),
                alpha=layout.get("grid_alpha", 0.35))
    if grid_mode == "both":
        ax.grid(True, axis="x", linestyle=spec.get("grid_style", "dashed"),
                linewidth=spec.get("grid_width", layout.get("grid_linewidth", 0.6)),
                color=spec.get("grid_color", roles.get("grid", "#E2E8F0")),
                alpha=layout.get("grid_alpha", 0.35))
    ax.set_axisbelow(True)

    bg = theme.get("colors", {}).get("backgrounds", {}).get(spec.get("canvas", "white"), "#FFFFFF")
    ax.set_facecolor(bg)
    ax.xaxis.label.set_color(roles.get("text", "#1F2937"))
    ax.yaxis.label.set_color(roles.get("text", "#1F2937"))
    ax.xaxis.label.set_size(label_pt)
    ax.yaxis.label.set_size(label_pt)
    ax.title.set_color(roles.get("text", "#1F2937"))
    theme["_legend_frame"] = spec.get("legend_frame", False) if legend_frame is None else legend_frame
    return ax


def style_legend(legend, theme: dict | None = None, frame: bool | None = None):
    theme = theme or resolve_theme()
    roles = theme.get("colors", {}).get("roles", {})
    use_frame = theme.get("_legend_frame", False) if frame is None else frame
    legend.get_frame().set_visible(use_frame)
    if use_frame:
        legend.get_frame().set_edgecolor(roles.get("grid", "#E2E8F0"))
        legend.get_frame().set_linewidth(0.6)
    for text in legend.get_texts():
        text.set_color(roles.get("text", "#1F2937"))
    return legend


def figure(figsize, theme: dict | None = None, **kwargs):
    theme = theme or resolve_theme()
    fig, ax = plt.subplots(figsize=figsize, **kwargs)
    fig.set_facecolor(theme.get("colors", {}).get("backgrounds", {}).get("white", "#FFFFFF"))
    return fig, ax


# --------------------------------------------------------------------------- #
# 尺寸反推与标签预算
# --------------------------------------------------------------------------- #
def display_units(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in str(text))


def plan_size(width_mm: float | None = None, aspect: float | None = None,
              theme: dict | None = None, cite_mm: float | None = None,
              min_pt: float | None = None, base_pt: float | None = None,
              base_font: float | None = None) -> dict:
    """按目标引用宽度反推 figsize 与基准字号。

    上页实际字号 = 代码字号 × 目标引用宽度 ÷ 原生画布宽度。
    若最终会被缩放到 cite_mm，则代码字号需 ≥ min_pt × width_mm / cite_mm。
    """
    theme = theme or resolve_theme()
    fig_cfg = theme.get("figure", {})
    width_mm = width_mm or fig_cfg.get("default_width_mm", 160)
    aspect = aspect or fig_cfg.get("default_aspect", 0.62)
    min_pt = min_pt or theme.get("typography", {}).get("min_effective_pt", 6.0)
    base_pt = base_pt or theme.get("typography", {}).get("size_pt", {}).get("axis_label", 10.0)
    notes: list[str] = []

    font_scale = 1.0
    if cite_mm and cite_mm < width_mm:
        needed = min_pt * width_mm / cite_mm
        if base_pt < needed:
            font_scale = needed / base_pt
            notes.append(
                f"目标引用宽度 {cite_mm:.0f}mm 小于原生 {width_mm:.0f}mm，"
                f"字号已放大 {font_scale:.2f}× 以保证上页 {min_pt:.1f}pt 可读"
            )
        else:
            notes.append(f"上页实际字号约 {base_pt * cite_mm / width_mm:.1f}pt，满足 ≥{min_pt:.1f}pt")
    if base_font and base_font < min_pt:
        notes.append(f"基准字号 {base_font}pt 低于最小可读 {min_pt}pt")

    width_in = width_mm / 25.4
    return {
        "figsize": (round(width_in, 3), round(width_in * aspect, 3)),
        "width_mm": width_mm,
        "height_mm": round(width_mm * aspect, 1),
        "base_pt": round(base_pt * font_scale, 2),
        "font_scale": round(font_scale, 3),
        "min_effective_pt": min_pt,
        "notes": notes,
    }


def pick_orientation(labels: list[str], threshold: int | None = None,
                     min_count: int | None = None, theme: dict | None = None) -> str:
    theme = theme or resolve_theme()
    rules = theme.get("rules", {})
    threshold = threshold or rules.get("horizontal_label_units", 12)
    min_count = min_count or rules.get("horizontal_category_count", 5)
    if not labels:
        return "vertical"
    longest = max(display_units(x) for x in labels)
    return "horizontal" if longest > threshold and len(labels) > min_count else "vertical"


def ensure_zero_baseline(ax, axis: str = "y"):
    """柱状/面积图强制零基线（统计诚实规则）。"""
    if axis == "y":
        lo, hi = ax.get_ylim()
        if lo > 0:
            ax.set_ylim(0, hi)
        elif hi < 0:
            ax.set_ylim(lo, 0)
    else:
        lo, hi = ax.get_xlim()
        if lo > 0:
            ax.set_xlim(0, hi)
        elif hi < 0:
            ax.set_xlim(lo, 0)
    return ax


# --------------------------------------------------------------------------- #
# 微质感与标注
# --------------------------------------------------------------------------- #
def bar_kwargs(color: str, alpha: float | None = None, theme: dict | None = None) -> dict:
    """浅填深边：同色系半透明填充 + 深色实线描边。"""
    theme = theme or resolve_theme()
    marks = theme.get("marks", {})
    return {
        "color": to_rgba(color, marks.get("fill_alpha", 0.18) if alpha is None else alpha),
        "edgecolor": color,
        "linewidth": marks.get("edge_width", 1.0),
        # 不要传 alpha=1.0：Patch.set_alpha 会覆盖 facecolor 里的透明度，导致浅填失效
    }


def marker_kwargs(color: str, size: float | None = None, alpha: float = 1.0,
                  theme: dict | None = None) -> dict:
    """散点/折线节点统一细白边防糊团。"""
    theme = theme or resolve_theme()
    marks = theme.get("marks", {})
    return {
        "s": marks.get("scatter_size", 14.0) if size is None else size,
        "color": to_rgba(color, alpha),
        "edgecolor": marks.get("marker_edge", "#FFFFFF"),
        "linewidth": marks.get("marker_edge_width", 0.6),
    }


def line_kwargs(color: str, theme: dict | None = None, width: str = "regular", **extra) -> dict:
    theme = theme or resolve_theme()
    lw = theme.get("layout", {}).get("line_widths", {}).get(width, 1.1)
    return {"color": color, "linewidth": lw, **extra}


def sig_bracket(ax, x1: float, x2: float, y: float, label: str,
                h_frac: float = 0.02, color: str | None = None,
                fontsize: float | None = None, theme: dict | None = None):
    """显著性括号。p 值/星号必须由上游统计给出，本函数绝不计算 p 值。"""
    theme = theme or resolve_theme()
    roles = theme.get("colors", {}).get("roles", {})
    color = color or roles.get("text", "#1F2937")
    lo, hi = ax.get_ylim()
    h = (hi - lo) * h_frac
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], color=color, linewidth=0.9,
            clip_on=False, solid_capstyle="butt")
    ax.text((x1 + x2) / 2, y + h, label, ha="center", va="bottom", color=color,
            fontsize=fontsize or font_size(theme, "annotation"))
    return ax


def add_source(fig, text: str, theme: dict | None = None, x: float = 0.01, y: float = 0.005):
    theme = theme or resolve_theme()
    roles = theme.get("colors", {}).get("roles", {})
    fig.text(x, y, text, ha="left", va="bottom",
             fontsize=font_size(theme, "source"),
             color=roles.get("muted_text", "#6B7280"))
    return fig


# --------------------------------------------------------------------------- #
# 导出
# --------------------------------------------------------------------------- #
def save_figure(fig, outdir: str | Path = ".", stem: str = "figure",
                formats: tuple[str, ...] = ("pdf", "png"),
                dpi: tuple[int, ...] | list[int] = (300, 600),
                theme: dict | None = None, tight: bool = False,
                close: bool = True) -> list[str]:
    """按格式导出；PNG 以 <stem>_<dpi>dpi.png 命名，PDF/SVG 保持矢量。

    不使用 tight bbox：物理尺寸必须可预测，否则 audit 的栏宽校验会失真。
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    meta = {"Creator": f"viz-suite {__version__}", "Producer": "matplotlib"}
    for fmt in formats:
        if fmt in ("pdf", "svg"):
            path = outdir / f"{stem}.{fmt}"
            fig.savefig(path, format=fmt, bbox_inches="tight" if tight else None,
                        metadata=meta if fmt == "pdf" else None)
            outputs.append(str(path))
        elif fmt in ("png", "jpg", "jpeg", "webp"):
            for d in dpi:
                path = outdir / f"{stem}_{d}dpi.{fmt}"
                fig.savefig(path, format=fmt, dpi=d, bbox_inches="tight" if tight else None,
                            facecolor=fig.get_facecolor())
                outputs.append(str(path))
    if close:
        plt.close(fig)
    return outputs


def describe_theme(theme: dict) -> dict:
    return {
        "palette": theme.get("palette_id"),
        "layout_family": theme.get("layout_family"),
        "fonts": theme.get("_font_stack", [])[:4],
        "source": theme.get("_source"),
        "manifest": theme.get("manifest_path"),
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    t = bootstrap()
    pal = palette(theme=t)
    print(json.dumps({
        "theme": describe_theme(t),
        "palette_pick_4": pal.pick(4),
        "cvd_min_delta_e": pal.min_delta_e,
        "contrast_on_white": {c: round(contrast_ratio(c, "#FFFFFF"), 2) for c in pal.colors},
        "sequential_mid": to_hex(sequential_cmap(pal.colors[0])(0.5)),
        "diverging_mid": to_hex(diverging_cmap(pal.colors[0], theme=t)(0.5)),
        "auto_text_on_focal": contrast_text(pal.colors[0], alpha=0.18),
        "size_plan": plan_size(89, cite_mm=85, theme=t),
    }, ensure_ascii=False, indent=2))

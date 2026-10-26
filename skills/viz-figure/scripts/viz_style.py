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

__version__ = "2026.10-p2"

_WARNED: set[str] = set()
_CACHE: dict[str, object] = {}
_REGISTERED_FONT_FILES: set[str] = set()

# --------------------------------------------------------------------------- #
# 资产定位与自带开源字体注册
# --------------------------------------------------------------------------- #
def _asset_candidates() -> list[Path]:
    here = Path(__file__).resolve().parent
    cands: list[Path] = []
    if os.environ.get("VIZ_SUITE_ASSETS"):
        cands.append(Path(os.environ["VIZ_SUITE_ASSETS"]))
    seen: set[Path] = set()
    bases = [Path.cwd(), *Path.cwd().parents, here, *here.parents]
    for base in bases:
        # 支持外部工作区通过 .viz-suite/font_source.json 或 runtime.json 指向技能根资产
        for ptr_name in ("font_source.json", "runtime.json"):
            ptr = base / ".viz-suite" / ptr_name
            if ptr.is_file():
                try:
                    pdata = json.loads(ptr.read_text(encoding="utf-8"))
                    for key in ("shared_assets", "skill_root"):
                        val = pdata.get(key)
                        if val:
                            cand_p = Path(val) if key == "shared_assets" else Path(val) / "shared" / "assets"
                            if cand_p not in seen:
                                seen.add(cand_p)
                                cands.append(cand_p)
                except Exception:  # noqa: BLE001
                    pass
        for p in (base / ".viz-suite" / "assets",
                  base / "skills" / "shared" / "assets",
                  base / "shared" / "assets",
                  base / "skills" / "viz-core" / "assets",
                  base / "viz-core" / "assets",
                  base / "assets"):
            if p not in seen:
                seen.add(p)
                cands.append(p)
    cands.append(here.parent / "assets")  # 直接放在 viz-figure/scripts 时
    return cands


def register_bundled_fonts() -> list[str]:
    """自动扫描并向 Matplotlib 注册技能自带的 SIL OFL 多字重静态 TTF 字体。"""
    font_dirs: list[Path] = []
    if os.environ.get("VIZ_SUITE_FONTS"):
        font_dirs.append(Path(os.environ["VIZ_SUITE_FONTS"]))
    if os.environ.get("VIZ_SUITE_SKILL_ROOT"):
        font_dirs.append(Path(os.environ["VIZ_SUITE_SKILL_ROOT"]) / "shared" / "assets" / "fonts")
    here = Path(__file__).resolve().parent
    for base in [Path.cwd(), *Path.cwd().parents, here, *here.parents]:
        ptr = base / ".viz-suite" / "font_source.json"
        if ptr.is_file():
            try:
                fdir = json.loads(ptr.read_text(encoding="utf-8")).get("fonts_dir")
                if fdir:
                    font_dirs.append(Path(fdir))
            except Exception:  # noqa: BLE001
                pass
    for cand in _asset_candidates():
        font_dirs.append(cand / "fonts")

    added: list[str] = []
    seen_dirs: set[Path] = set()
    for fdir in font_dirs:
        try:
            resolved = fdir.resolve()
        except OSError:
            continue
        if resolved in seen_dirs or not resolved.is_dir():
            continue
        seen_dirs.add(resolved)
        for ext in ("*.ttf", "*.TTF"):
            for fp in sorted(resolved.glob(ext)):
                key = str(fp)
                if key in _REGISTERED_FONT_FILES:
                    continue
                try:
                    n_before = len(font_manager.fontManager.ttflist)
                    font_manager.fontManager.addfont(key)
                    if len(font_manager.fontManager.ttflist) > n_before:
                        entry = font_manager.fontManager.ttflist.pop()
                        font_manager.fontManager.ttflist.insert(0, entry)
                    _REGISTERED_FONT_FILES.add(key)
                    added.append(key)
                except Exception as exc:  # noqa: BLE001
                    warn_once(f"注册自带字体失败 {fp.name}: {exc}")
    if added:
        _CACHE.pop("font_names", None)
        if hasattr(font_manager.fontManager, "_findfont_cached"):
            font_manager.fontManager._findfont_cached.cache_clear()
    return added


def _load_json_asset(filename: str) -> dict | None:
    for cand in _asset_candidates():
        path = cand / filename
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                warn_once(f"{path} 解析失败，继续尝试下一处资产")
    return None


def load_geo_asset(filename: str) -> dict:
    """加载 skills/shared/assets/geo/ 下的合规底图（如 china_prov_tile_grid.json / ne_110m_countries.geojson）。"""
    rel = filename if filename.startswith("geo/") else f"geo/{filename}"
    data = _load_json_asset(rel)
    if data is None:
        raise FileNotFoundError(f"未找到地理底图资产：{rel}（请检查 skills/shared/assets/geo）")
    return data


def load_publisher_profile(journal: str) -> dict | None:
    """读取 publisher_profiles.json 中的期刊出版规范（nature/science/cell/ieee/elsevier/plos/bmc/acs）。"""
    data = _load_json_asset("publisher_profiles.json")
    if not data:
        return None
    journals = data.get("journals", {})
    return journals.get(str(journal).strip().lower())


_LAST_LAYOUT_AUDIT: dict | None = None
_CLOSING_PUNCT = set("，。；：、,.!?;:)]}》」』】%")


_FALLBACK_TOKENS = {
    "colors": {
        "roles": {"focal": "#0072B2", "context": "#CBD5E1", "positive": "#198038",
                  "negative": "#DA1E28", "alert": "#D97706", "grid": "#E2E8F0",
                  "background": "#FFFFFF", "text": "#1F2937", "muted_text": "#6B7280"},
        "default_palette": "okabe_ito",
        "palette_by_scene": {"academic": "okabe_ito", "bi": "bi_ibcs",
                             "story": "editorial_warm", "geo": "met_egypt", "default": "okabe_ito"},
        "backgrounds": {"white": "#FFFFFF", "soft_tint": "#F8FAFC", "warm_paper": "#FBF7F0"},
    },
    "typography": {
        "font_zh": ["Noto Sans SC", "Microsoft YaHei", "SimHei", "sans-serif"],
        "font_en": ["Inter", "Arial", "DejaVu Sans"],
        "font_serif_zh": ["IBM Plex Serif", "SimSun", "DejaVu Serif"],
        "font_mono": ["JetBrains Mono", "Consolas", "DejaVu Sans Mono"],
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
    "marks": {"fill_alpha": 0.78, "default_preset": "solid_vivid", "edge_width": 1.0, "marker_edge": "#FFFFFF",
              "marker_edge_width": 0.6, "scatter_size": 18.0, "violin_alpha": 0.32,
              "box_alpha": 0.45, "jitter_width": 0.09,
              "mean_line": {"color": "#6B7280", "linestyle": "--", "linewidth": 0.9},
              "zero_line": {"color": "#9CA3AF", "linewidth": 0.8}},
    "figure": {"single_column_mm": 89, "double_column_mm": 183, "default_width_mm": 160,
               "default_aspect": 0.62,
               "export": {"vector": ["pdf", "svg"], "raster_dpi": [300, 600], "preview_dpi": 300}},
    "rules": {"zero_baseline": True, "horizontal_label_units": 12,
              "horizontal_category_count": 5, "cvd_min_delta_e": 10.0,
              "min_text_contrast_wcag": 4.5, "min_graphic_contrast_wcag": 3.0},
    "scenes": {
        "academic": {"palette": "okabe_ito", "layout_family": "clean_open", "in_canvas_title": False,
                     "width_mm": 89, "double_column_mm": 183, "aspect": 0.68,
                     "font_size_level": "small", "formats": ["pdf", "svg", "png"], "dpi": [300, 600],
                     "top_no_title": 0.93},
        "bi": {"palette": "bi_ibcs", "layout_family": "soft_grid", "in_canvas_title": True,
               "width_mm": 180, "aspect": 0.58, "font_size_level": "regular",
               "formats": ["pdf", "png"], "dpi": [300]},
        "story": {"palette": "editorial_warm", "layout_family": "clean_open", "in_canvas_title": True,
                  "focal_context_only": True, "width_mm": 254, "aspect": 0.5625,
                  "font_size_level": "large", "formats": ["svg", "png"], "dpi": [300, 600]},
        "geo": {"palette": "met_egypt", "layout_family": "clean_open", "in_canvas_title": True,
                "width_mm": 170, "aspect": 0.72, "font_size_level": "regular",
                "formats": ["svg", "png"], "dpi": [300]},
    },
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
        try:
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
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
            warn_once("未找到 tokens.json，已启用内置最小令牌集（请检查 skills/shared/assets 或 .viz-suite/assets）")
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


def _normalize_scene(scene: str | None) -> str | None:
    if not scene:
        return None
    s = str(scene).strip().lower()
    if s.startswith("viz-scene-"):
        s = s[len("viz-scene-"):]
    return s or None


def _apply_scene(theme: dict, scene: str | None) -> bool:
    sid = _normalize_scene(scene)
    if not sid:
        return False
    file_preset = _load_json_asset(f"scenes/{sid}.json")
    scenes = theme.get("scenes") or _FALLBACK_TOKENS.get("scenes", {})
    pal_by_scene = theme.get("colors", {}).get("palette_by_scene") or {}
    preset = file_preset if file_preset is not None else scenes.get(sid)
    if preset is None and sid not in pal_by_scene:
        warn_once(f"未知场景预设 {scene!r}（支持 academic/bi/story/geo），已保持基线配置")
        return False
    preset = dict(preset or {})
    pal_id = preset.get("palette") or pal_by_scene.get(sid)
    if pal_id:
        theme.setdefault("colors", {})["default_palette"] = pal_id
        theme["palette_id"] = pal_id
    if preset.get("layout_family"):
        theme["layout_family"] = preset["layout_family"]
    if "in_canvas_title" in preset:
        theme["in_canvas_title"] = bool(preset["in_canvas_title"])
    if preset.get("width_mm"):
        theme.setdefault("figure", {})["default_width_mm"] = preset["width_mm"]
    if preset.get("aspect"):
        theme.setdefault("figure", {})["default_aspect"] = preset["aspect"]
    if preset.get("font_size_level"):
        theme["font_size_level"] = preset["font_size_level"]
    theme["scene"] = sid
    theme["scene_preset"] = preset
    return True


def resolve_theme(overrides: dict | None = None, scene: str | None = None) -> dict:
    """优先级：显式 overrides / scene > 项目 EXTEND.md > 用户 EXTEND.md > figure-manifest.json > 环境变量 VIZ_SCENE > tokens。"""
    tokens = json.loads(json.dumps(load_tokens()))  # deep copy
    theme = dict(tokens)
    theme["_source"] = "tokens"
    theme.setdefault("in_canvas_title", True)
    theme.setdefault("font_size_level", "regular")

    manifest_path = _find_upwards("figure-manifest.json")
    manifest: dict = {}
    if manifest_path:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            warn_once(f"figure-manifest.json 解析失败，已忽略：{manifest_path}")
            manifest = {}

    user_ext_path = Path.home() / ".viz-suite" / "EXTEND.md"
    user_ext = read_extend(user_ext_path) if user_ext_path.is_file() else {}
    proj_ext_path = _find_upwards(".viz-suite/EXTEND.md") or _find_upwards("EXTEND.md")
    proj_ext = read_extend(proj_ext_path) if proj_ext_path else {}

    # 1. 环境级或 manifest 声明的场景差分（位于 tokens 之上、manifest 具体字段之下）
    env_or_manifest_scene = manifest.get("scene") or os.environ.get("VIZ_SCENE")
    if env_or_manifest_scene and _apply_scene(theme, str(env_or_manifest_scene)):
        theme["_source"] = f"scene:{theme['scene']}"

    # 2. figure-manifest.json 任务级锁定
    if manifest:
        theme["manifest"] = manifest
        theme["manifest_path"] = str(manifest_path)
        if manifest.get("palette"):
            theme.setdefault("colors", {})["default_palette"] = manifest["palette"]
            theme["palette_id"] = manifest["palette"]
        if manifest.get("layout_family"):
            theme["layout_family"] = manifest["layout_family"]
        if manifest.get("series_color_map"):
            theme["series_color_map"] = manifest["series_color_map"]
        if manifest.get("width_mm"):
            theme.setdefault("figure", {})["default_width_mm"] = manifest["width_mm"]
        if manifest.get("aspect"):
            theme.setdefault("figure", {})["default_aspect"] = manifest["aspect"]
        if "in_canvas_title" in manifest:
            theme["in_canvas_title"] = bool(manifest["in_canvas_title"])
        if manifest.get("footer"):
            theme.setdefault("brand", {})["footer"] = manifest["footer"]
        if manifest.get("fonts"):
            theme.setdefault("typography", {}).update(manifest["fonts"])
        theme["_source"] = "manifest"

    # 3. 用户与项目 EXTEND.md
    if user_ext:
        _merge_extend(theme, user_ext)
        theme["_source"] = "user_extend"
    if proj_ext:
        _merge_extend(theme, proj_ext)
        theme["_source"] = "project_extend"

    # 4. 当前指令显式传入的 scene 与 overrides 优先级最高
    explicit_scene = scene or (overrides or {}).get("scene")
    if explicit_scene and _apply_scene(theme, str(explicit_scene)):
        theme["_source"] = f"scene:{theme['scene']}"

    if overrides:
        clean_overrides = {k: v for k, v in overrides.items() if k != "scene"}
        if clean_overrides:
            _deep_merge(theme, clean_overrides)
            if "colors" in clean_overrides and "default_palette" in clean_overrides["colors"]:
                theme["palette_id"] = clean_overrides["colors"]["default_palette"]
            theme["_source"] = "overrides"

    theme.setdefault("palette_id", theme.get("colors", {}).get("default_palette", "okabe_ito"))
    theme.setdefault("layout_family", "clean_open")
    theme.setdefault("series_color_map", {})
    return theme


def _merge_extend(theme: dict, ext: dict) -> None:
    if not ext:
        return
    if ext.get("scene"):
        _apply_scene(theme, str(ext["scene"]))
    if "in_canvas_title" in ext and ext["in_canvas_title"] is not None:
        theme["in_canvas_title"] = bool(ext["in_canvas_title"])
    colors = ext.get("colors") or {}
    if isinstance(colors, dict) and colors:
        if colors.get("palette"):
            theme.setdefault("colors", {})["default_palette"] = str(colors["palette"])
            theme["palette_id"] = str(colors["palette"])
        role_updates = {str(k).lower(): v for k, v in colors.items()
                        if isinstance(v, str) and str(k).lower() != "palette"}
        if role_updates:
            theme.setdefault("colors", {}).setdefault("roles", {}).update(role_updates)
    typo = ext.get("typography") or {}
    if isinstance(typo, dict) and typo:
        theme.setdefault("typography", {})
        for key in ("font_zh", "font_en", "font_serif_zh"):
            if typo.get(key):
                value = typo[key]
                theme["typography"][key] = value if isinstance(value, list) else [
                    v.strip() for v in str(value).split(",") if v.strip()
                ]
    brand = ext.get("brand") or {}
    if isinstance(brand, dict) and brand:
        theme.setdefault("brand", {}).update(brand)
    stack = ext.get("stack") or {}
    if isinstance(stack, dict) and stack:
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


def select_palette(default_id: str | None = None, theme: dict | None = None,
                   cli_palette: str | None = None) -> Palette:
    """按优先级解析色板：CLI --palette > 显式场景/EXTEND/manifest > 配方推荐默认色板 > tokens 默认色板。"""
    theme = theme or resolve_theme()
    if cli_palette:
        return palette(cli_palette, theme=theme)
    if theme.get("_source") not in (None, "tokens"):
        return palette(None, theme=theme)
    return palette(default_id, theme=theme)


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


def group_lightness_ramp(base_color: str, n: int,
                         light_range: tuple[float, float] = (0.38, 0.96),
                         reverse: bool = False) -> list[str]:
    """同组单主色明度阶梯（组间分色、组内明度阶梯）：消除彩虹杂乱感，构建层次纵深。"""
    n = max(1, int(n))
    if n == 1:
        return [base_color]
    deep_anchor = mix("#0F172A", base_color, 0.80)
    stops = np.linspace(light_range[0], light_range[1], n)
    ramp = []
    for t in stops:
        if t <= 0.85:
            ramp.append(mix("#FFFFFF", base_color, float(t / 0.85)))
        else:
            ramp.append(mix(base_color, deep_anchor, float((t - 0.85) / 0.15)))
    return list(reversed(ramp)) if reverse else ramp


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
    register_bundled_fonts()
    if "font_names" not in _CACHE:
        _CACHE["font_names"] = {f.name for f in font_manager.fontManager.ttflist}
    return _CACHE["font_names"]  # type: ignore[return-value]


def available_fonts(candidates: list[str]) -> list[str]:
    installed = _installed_fonts()
    return [f for f in candidates if f in installed]


def bootstrap(theme: dict | None = None, font_scale: float = 1.0,
              scene: str | None = None) -> dict:
    """应用自带开源字体、场景预设与全局 rcParams，返回 theme。"""
    register_bundled_fonts()
    if theme is None:
        theme = resolve_theme(scene=scene)
    elif scene:
        _apply_scene(theme, scene)
    _silence_benign_font_warnings()
    typo = theme.get("typography", {})
    levels = typo.get("font_size_levels", {})
    level_scale = float(levels.get(theme.get("font_size_level", "regular"), 1.0))
    effective_scale = font_scale * level_scale if not theme.get("_level_applied_in_plan") else font_scale
    zh = available_fonts(typo.get("font_zh", []))
    en = available_fonts(typo.get("font_en", []))
    mono = available_fonts(typo.get("font_mono", []))
    if not zh:
        warn_once("未检测到任何可用的中文字体，中文可能显示为方块；请先运行 detect_fonts.py")
    stack = en + zh + ["DejaVu Sans", "sans-serif"]
    stack = list(dict.fromkeys(stack))
    mpl.rcParams.update({
        # 直接给 font.family 一个有序列表，matplotlib 才会按字形回退到中文字体；
        # 只写 "sans-serif" 时只会解析到列表第一个字体，中文会变成方块。
        "font.family": stack,
        "font.sans-serif": stack,
        "font.serif": available_fonts(typo.get("font_serif_zh", [])) + zh + ["DejaVu Serif"],
        "font.monospace": mono + ["DejaVu Sans Mono", "monospace"],
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "figure.dpi": 110,
        "savefig.dpi": 300,
        "axes.titlesize": typo.get("size_pt", {}).get("title", 13) * effective_scale,
        "axes.labelsize": typo.get("size_pt", {}).get("axis_label", 10) * effective_scale,
        "xtick.labelsize": typo.get("size_pt", {}).get("tick", 9) * effective_scale,
        "ytick.labelsize": typo.get("size_pt", {}).get("tick", 9) * effective_scale,
        "legend.fontsize": typo.get("size_pt", {}).get("legend", 9) * effective_scale,
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
    theme["_font_scale"] = effective_scale
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


def silverman_bandwidth(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    n = len(values)
    if n < 2:
        return 0.0
    sd = float(values.std(ddof=1))
    q1, q3 = np.percentile(values, [25, 75])
    iqr = float(q3 - q1)
    sigma = min(sd, iqr / 1.34) if iqr > 0 else sd
    if sigma <= 0:
        sigma = sd if sd > 0 else 1.0
    return max(0.9 * sigma * n ** (-1 / 5), 1e-9)


def kde_1d(values, grid=None, bw: float | None = None, n: int = 256,
           cut: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """一维高斯核密度（numpy 实现）。cut=0 严格落在实测范围内。"""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return np.array([]), np.array([])
    if values.size == 1:
        lo = hi = float(values[0])
    else:
        lo, hi = float(values.min()), float(values.max())
    span = max(hi - lo, 1e-9)
    if grid is None:
        grid = np.linspace(lo - cut * span, hi + cut * span, n)
    grid = np.asarray(grid, dtype=float)
    if values.size < 2:
        dens = np.zeros_like(grid)
        dens[np.argmin(np.abs(grid - values[0]))] = 1.0
        return grid, dens
    bw = bw or silverman_bandwidth(values)
    diff = (grid[:, None] - values[None, :]) / bw
    dens = np.exp(-0.5 * diff ** 2).sum(axis=1) / (values.size * bw * np.sqrt(2 * np.pi))
    return grid, dens


def panel_label(ax, label: str, theme: dict | None = None,
                x: float = -0.07, y: float = 1.02):
    """期刊式面板标号 a/b/c（左下或左上）。"""
    theme = theme or resolve_theme()
    ax.text(x, y, label, transform=ax.transAxes, ha="left", va="bottom",
            fontweight="bold", fontsize=font_size(theme, "panel_label"),
            color=theme.get("colors", {}).get("roles", {}).get("text", "#1F2937"))
    return ax


def fill_title(template: str, **values) -> str:
    """把统计量填入标题模板；缺字段时原样返回，绝不因格式化失败中断绘图。"""
    try:
        return template.format(**values)
    except (KeyError, ValueError, IndexError):
        return template


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
    typo = theme.get("typography", {})
    min_pt = min_pt or typo.get("min_effective_pt", 6.0)
    base_pt = base_pt or typo.get("size_pt", {}).get("axis_label", 10.0)
    levels = typo.get("font_size_levels", {})
    level_scale = float(levels.get(theme.get("font_size_level", "regular"), 1.0))
    notes: list[str] = []

    font_scale = level_scale
    if cite_mm and cite_mm < width_mm:
        needed = min_pt * width_mm / cite_mm
        if base_pt * level_scale < needed:
            font_scale = needed / base_pt
            notes.append(
                f"目标引用宽度 {cite_mm:.0f}mm 小于原生 {width_mm:.0f}mm，"
                f"字号已放大 {font_scale:.2f}× 以保证上页 {min_pt:.1f}pt 可读"
            )
        else:
            notes.append(f"上页实际字号约 {base_pt * level_scale * cite_mm / width_mm:.1f}pt，满足 ≥{min_pt:.1f}pt")
    if base_font and base_font < min_pt:
        notes.append(f"基准字号 {base_font}pt 低于最小可读 {min_pt}pt")

    theme["_level_applied_in_plan"] = True
    theme["_planned_width_mm"] = float(width_mm)
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
                     min_count: int | None = None, theme: dict | None = None,
                     width_mm: float | None = None) -> str:
    theme = theme or resolve_theme()
    rules = theme.get("rules", {})
    threshold = threshold or rules.get("horizontal_label_units", 12)
    min_count = min_count or rules.get("horizontal_category_count", 5)
    if not labels:
        return "vertical"
    line_units = [max((display_units(part) for part in str(x).splitlines()), default=0) for x in labels]
    longest = max(line_units)
    if longest > threshold and len(labels) > min_count:
        return "horizontal"
    w_mm = float(width_mm or theme.get("_planned_width_mm") or theme.get("figure", {}).get("default_width_mm", 160))
    plot_w_pt = w_mm * 0.88 * (72.0 / 25.4)
    tick_pt = font_size(theme, "tick")
    needed_pt = sum((u * 0.50 + 1.15) * tick_pt for u in line_units)
    return "horizontal" if needed_pt > plot_w_pt and len(labels) >= 3 else "vertical"


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
# 微质感、反空洞复合组件与语义标注
# --------------------------------------------------------------------------- #
def bar_kwargs(color: str, alpha: float | dict | None = None, theme: dict | None = None,
               preset: str | None = None, is_focal: bool | None = None) -> dict:
    """多档饱满微质感（取代单一 0.18 浅淡填充）：
    - solid_vivid（默认）：82% 饱和度实心饱满色块 + 同色系深色微描边；
    - focal_context：焦点序列高饱和实心 + 背景序列低饱和高级冷灰；
    - translucent_outline：半透明填充 + 原色实线描边（仅重叠直方图/密度对比使用）。
    """
    if isinstance(alpha, dict) and theme is None:
        theme = alpha
        alpha = None
    theme = theme or resolve_theme()
    marks = theme.get("marks", {})
    roles = theme.get("colors", {}).get("roles", {})
    mode = preset or marks.get("default_preset", "solid_vivid")

    if alpha is not None:
        edge = mix("#0F172A", color, 0.72)
        return {
            "color": to_rgba(color, float(alpha)),
            "edgecolor": edge,
            "linewidth": marks.get("edge_width", 0.9),
        }

    if mode == "focal_context" or is_focal is not None:
        focal = True if is_focal is None else bool(is_focal)
        if focal:
            fill = mix("#FFFFFF", color, 0.90)
            edge = mix("#0F172A", color, 0.70)
            return {"color": to_rgba(fill, 0.95), "edgecolor": edge, "linewidth": 1.1}
        ctx = roles.get("context", "#CBD5E1")
        fill = mix("#FFFFFF", ctx, 0.70)
        edge = mix("#64748B", ctx, 0.55)
        return {"color": to_rgba(fill, 0.78), "edgecolor": edge, "linewidth": 0.75}

    if mode == "translucent_outline":
        return {
            "color": to_rgba(color, 0.26),
            "edgecolor": color,
            "linewidth": marks.get("edge_width", 1.0),
        }

    # 默认 solid_vivid：饱满温润出版级实心质感
    fill = mix("#FFFFFF", color, 0.84)
    edge = mix("#0F172A", color, 0.72)
    fill_alpha = float(marks.get("fill_alpha", 0.88))
    if fill_alpha < 0.55:
        fill_alpha = 0.86
    return {
        "color": to_rgba(fill, min(0.95, fill_alpha)),
        "edgecolor": edge,
        "linewidth": marks.get("edge_width", 0.95),
    }


def plot_feathered_band(ax, x, lo, hi, color: str, steps: int = 4,
                        max_alpha: float = 0.28, horizontal: bool = False,
                        zorder: float = 1.5, label: str | None = None):
    """多层羽化置信带 / 分位区间带：外缘柔和过渡 + 核心区加密 + 细微上下边界线。"""
    x_arr = np.asarray(x, dtype=float)
    lo_arr = np.asarray(lo, dtype=float)
    hi_arr = np.asarray(hi, dtype=float)
    mid = 0.5 * (lo_arr + hi_arr)
    half = 0.5 * (hi_arr - lo_arr)
    steps = max(2, int(steps))
    fn = ax.fill_betweenx if horizontal else ax.fill_between
    layer_alpha = max_alpha / steps * 1.45
    for idx, frac in enumerate(np.linspace(1.0, 0.30, steps)):
        lbl = label if idx == 0 else None
        fn(x_arr, mid - half * frac, mid + half * frac,
           color=color, alpha=min(0.45, layer_alpha), linewidth=0, zorder=zorder, label=lbl)
    edge_col = to_rgba(color, min(0.48, max_alpha * 1.4))
    if horizontal:
        ax.plot(lo_arr, x_arr, color=edge_col, linewidth=0.55, linestyle="-", zorder=zorder + 0.1)
        ax.plot(hi_arr, x_arr, color=edge_col, linewidth=0.55, linestyle="-", zorder=zorder + 0.1)
    else:
        ax.plot(x_arr, lo_arr, color=edge_col, linewidth=0.55, linestyle="-", zorder=zorder + 0.1)
        ax.plot(x_arr, hi_arr, color=edge_col, linewidth=0.55, linestyle="-", zorder=zorder + 0.1)
    return ax


def dual_metric_label(value: float, total_or_ref: float | None = None,
                      mode: str = "share", fmt: str = "{:.1f}",
                      pct_fmt: str = "{:.1f}%", unit: str = "") -> str:
    """生成复合双指标文本（消除单调裸数字）：支持 绝对值+占比% 或 绝对值+涨跌Δ%。"""
    head = f"{fmt.format(value)}{unit}"
    if total_or_ref is None or not np.isfinite(total_or_ref):
        return head
    if mode == "share":
        if abs(total_or_ref) < 1e-12:
            return head
        pct = 100.0 * value / total_or_ref
        return f"{head} ({pct_fmt.format(pct)})"
    if mode == "delta":
        if abs(total_or_ref) < 1e-12:
            return head
        d_pct = 100.0 * (value - total_or_ref) / abs(total_or_ref)
        sign = "+" if d_pct >= 0 else ""
        return f"{head} ({sign}{pct_fmt.format(d_pct)})"
    if mode == "raw_delta":
        sign = "+" if total_or_ref >= 0 else ""
        return f"{head} ({sign}{pct_fmt.format(total_or_ref)})"
    return head


def annotate_champion(ax, x: float, y: float, text: str, color: str | None = None,
                      offset_xy: tuple[float, float] = (0.0, 14.0),
                      theme: dict | None = None, ha: str = "center",
                      va: str = "bottom", star: bool = True):
    """冠军组/拐点语义胶囊标注（★ 焦点徽章 + 细引线），强化主次视觉锚点。"""
    theme = theme or resolve_theme()
    roles = theme.get("colors", {}).get("roles", {})
    accent = color or roles.get("focal", "#0072B2")
    badge_bg = mix("#FFFFFF", accent, 0.14)
    badge_edge = mix("#FFFFFF", accent, 0.68)
    badge_txt = mix("#0F172A", accent, 0.58)
    prefix = "★ " if star and not str(text).lstrip().startswith("★") else ""
    ann = ax.annotate(
        f"{prefix}{text}",
        xy=(x, y),
        xytext=offset_xy,
        textcoords="offset points",
        ha=ha,
        va=va,
        fontsize=font_size(theme, "annotation"),
        fontweight="bold",
        color=badge_txt,
        bbox={"boxstyle": "round,pad=0.28,rounding_size=0.35",
              "facecolor": badge_bg, "edgecolor": badge_edge, "linewidth": 0.9},
        arrowprops={"arrowstyle": "-", "color": badge_edge, "linewidth": 0.85,
                    "shrinkA": 0, "shrinkB": 3},
        zorder=6,
    )
    return ann


def smooth_trend(x, y, frac: float = 0.42, n_grid: int = 160) -> tuple[np.ndarray, np.ndarray]:
    """纯 NumPy 一维三次立方加权局部线性平滑（LOWESS），零额外依赖生成平滑趋势拟合曲线。"""
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    mask = np.isfinite(xv) & np.isfinite(yv)
    xv, yv = xv[mask], yv[mask]
    n = len(xv)
    if n < 3:
        return xv, yv
    order = np.argsort(xv)
    xv, yv = xv[order], yv[order]
    xg = np.linspace(float(xv.min()), float(xv.max()), max(n, int(n_grid)))
    k = max(3, min(n, int(math.ceil(frac * n))))
    yg = np.empty_like(xg)
    for i, x0 in enumerate(xg):
        dists = np.abs(xv - x0)
        idx = np.argpartition(dists, k - 1)[:k]
        d_max = float(dists[idx].max())
        if d_max <= 1e-12:
            yg[i] = float(yv[idx].mean())
            continue
        u = np.clip(dists[idx] / (d_max * 1.001), 0.0, 1.0)
        w = (1.0 - u ** 3) ** 3
        dx = xv[idx] - x0
        sw = float(w.sum())
        swx = float((w * dx).sum())
        swx2 = float((w * dx * dx).sum())
        swy = float((w * yv[idx]).sum())
        swxy = float((w * dx * yv[idx]).sum())
        denom = sw * swx2 - swx * swx
        if abs(denom) > 1e-12:
            yg[i] = (swx2 * swy - swx * swxy) / denom
        else:
            yg[i] = swy / max(sw, 1e-12)
    return xg, yg


def add_dead_space_inset(ax_main, rect: tuple[float, float, float, float],
                         theme: dict | None = None, title: str = "",
                         facecolor: str | None = None, border: bool = True):
    """在主图结构性留白区（如降序长尾条形右下角）开辟精巧内嵌副图卡片（Dead-Space Inset）。"""
    theme = theme or resolve_theme()
    roles = theme.get("colors", {}).get("roles", {})
    bgs = theme.get("colors", {}).get("backgrounds", {})
    ax_in = ax_main.inset_axes(list(rect))
    ax_in.set_facecolor(facecolor or bgs.get("soft_tint", "#F8FAFC"))
    for sp in ax_in.spines.values():
        sp.set_visible(border)
        sp.set_color(roles.get("grid", "#CBD5E1"))
        sp.set_linewidth(0.75)
    if title:
        ax_in.set_title(title, fontsize=font_size(theme, "annotation") * 0.95,
                        fontweight="bold", color=roles.get("text", "#1F2937"), pad=4)
    ax_in.tick_params(labelsize=font_size(theme, "source"), length=2.0, width=0.6)
    return ax_in


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


def wrap_text_units(text: str, max_units: int) -> str:
    """按中英文显示宽度（CJK=2, ASCII=1）安全折行，避免行首孤立标点与画布右侧裁切。"""
    text = "" if text is None else str(text).strip()
    if not text or max_units <= 4:
        return text
    out_lines: list[str] = []
    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line or display_units(raw_line) <= max_units:
            out_lines.append(raw_line)
            continue
        cur: list[str] = []
        cur_u = 0
        i = 0
        n = len(raw_line)
        while i < n:
            ch = raw_line[i]
            # 保持连续 ASCII 词/数字不被拆断
            if ch.isascii() and (ch.isalnum() or ch in "._%+-/"):
                j = i + 1
                while j < n and raw_line[j].isascii() and (raw_line[j].isalnum() or raw_line[j] in "._%+-/"):
                    j += 1
                tok = raw_line[i:j]
                i = j
            else:
                tok = ch
                i += 1
            tok_u = display_units(tok)
            if cur and cur_u + tok_u > max_units:
                if tok in _CLOSING_PUNCT:
                    cur.append(tok)
                    out_lines.append("".join(cur).rstrip())
                    cur, cur_u = [], 0
                    continue
                out_lines.append("".join(cur).rstrip())
                cur = [] if tok.isspace() else [tok]
                cur_u = 0 if tok.isspace() else tok_u
            else:
                cur.append(tok)
                cur_u += tok_u
        if cur:
            out_lines.append("".join(cur).rstrip())
    return "\n".join(out_lines)


def _max_units_for_fig(fig, fontsize_pt: float, x_left: float = 0.015, x_right: float = 0.985) -> int:
    fig_w_pt = float(fig.get_size_inches()[0]) * 72.0
    avail_pt = max(36.0, fig_w_pt * max(0.2, x_right - x_left))
    return max(14, int(avail_pt / max(fontsize_pt * 0.53, 1.0)))


def add_header(fig, title: str = "", subtitle: str = "", theme: dict | None = None,
               x: float = 0.015, top_y: float = 0.972, force: bool = False):
    """流式页眉：自动适应画布宽度折行、动态串联标题与副标题间距，并响应场景无标题配置。"""
    theme = theme or resolve_theme()
    if not force and not theme.get("in_canvas_title", True):
        fig._viz_header_suppressed = True  # type: ignore[attr-defined]
        return fig
    if force:
        fig._viz_force_header = True  # type: ignore[attr-defined]
    roles = theme.get("colors", {}).get("roles", {})
    title_str = (title or "").strip()
    sub_str = (subtitle or "").strip()
    cur_y = top_y

    if title_str:
        t_pt = font_size(theme, "title")
        wrapped_t = wrap_text_units(title_str, _max_units_for_fig(fig, t_pt, x))
        t_obj = fig.text(x, cur_y, wrapped_t, ha="left", va="top", fontweight="bold",
                         fontsize=t_pt, color=roles.get("text", "#1F2937"))
        t_obj._viz_role = "title"  # type: ignore[attr-defined]
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        t_bbox = t_obj.get_window_extent(renderer).transformed(fig.transFigure.inverted())
        cur_y = float(t_bbox.y0) - 0.011

    if sub_str:
        s_pt = font_size(theme, "subtitle")
        wrapped_s = wrap_text_units(sub_str, _max_units_for_fig(fig, s_pt, x))
        s_obj = fig.text(x, cur_y, wrapped_s, ha="left", va="top",
                         fontsize=s_pt, color=roles.get("muted_text", "#6B7280"))
        s_obj._viz_role = "subtitle"  # type: ignore[attr-defined]
    return fig


def add_source(fig, text: str, theme: dict | None = None, x: float = 0.01, y: float = 0.005):
    theme = theme or resolve_theme()
    roles = theme.get("colors", {}).get("roles", {})
    color = roles.get("muted_text", "#6B7280")
    if text and str(text).strip():
        src_obj = fig.text(x, y, text, ha="left", va="bottom",
                           fontsize=font_size(theme, "source"), color=color)
        src_obj._viz_role = "source"  # type: ignore[attr-defined]
    # 品牌页脚与数据来源分列左右；两者都保留，避免品牌声明覆盖数据出处。
    footer = theme.get("brand", {}).get("footer")
    if footer and footer not in (text or ""):
        ft_obj = fig.text(0.99, y, footer, ha="right", va="bottom",
                          fontsize=font_size(theme, "source"), color=color)
        ft_obj._viz_role = "footer"  # type: ignore[attr-defined]
    return fig


def _is_header_text(t) -> bool:
    if not t.get_visible() or not t.get_text().strip():
        return False
    role = getattr(t, "_viz_role", None)
    if role in ("title", "subtitle"):
        return True
    if role in ("source", "footer"):
        return False
    _, y = t.get_position()
    txt = t.get_text().strip()
    # 排除短面板标号如 (a) / a / B
    if len(txt) <= 4 and (txt.isalpha() or (txt.startswith("(") and txt.endswith(")"))):
        return False
    return float(y) >= 0.85


def _auto_reflow_figure(fig, theme: dict | None = None) -> None:
    """渲染前流式避让：
    1) 学术等无图内标题场景自动隐藏顶栏标题并回收顶部空白；
    2) 超宽标题/副标题自动折行并消除上下重叠；
    3) 当轴外右上/左上图例或顶轴标题与页眉碰撞时，动态下调 subplots_adjust(top=...)。
    """
    theme = theme or resolve_theme()
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()

    # 1. 场景级无标题抑制（兼容仍直接写 fig.text(0.015, 0.965, ...) 的旧脚本）
    if not theme.get("in_canvas_title", True) and not getattr(fig, "_viz_force_header", False):
        for t in fig.texts:
            if _is_header_text(t):
                t.set_visible(False)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

    header_texts = [t for t in fig.texts if _is_header_text(t)]
    header_texts.sort(key=lambda obj: float(obj.get_position()[1]), reverse=True)

    # 2. 超宽页眉折行与标题-副标题纵向防叠
    changed = False
    for t in header_texts:
        bb = t.get_window_extent(renderer).transformed(inv)
        if bb.x1 > 0.988 and "\n" not in t.get_text():
            units = display_units(t.get_text())
            avail_ratio = max(0.35, (0.975 - float(bb.x0)) / max(float(bb.width), 0.05))
            t.set_text(wrap_text_units(t.get_text(), max(14, int(units * avail_ratio))))
            changed = True
    if changed:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

    if len(header_texts) >= 2:
        prev_bb = header_texts[0].get_window_extent(renderer).transformed(inv)
        for t in header_texts[1:]:
            bb = t.get_window_extent(renderer).transformed(inv)
            if bb.y1 > prev_bb.y0 - 0.008:
                new_y = float(prev_bb.y0) - 0.011
                t.set_position((t.get_position()[0], new_y))
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()
                bb = t.get_window_extent(renderer).transformed(inv)
            prev_bb = bb

    # 底部来源与品牌页脚水平碰撞避让
    bottom_texts = [t for t in fig.texts if t.get_visible() and t.get_text().strip()
                    and (getattr(t, "_viz_role", None) in ("source", "footer") or float(t.get_position()[1]) <= 0.04)]
    if len(bottom_texts) == 2:
        b0 = bottom_texts[0].get_window_extent(renderer).transformed(inv)
        b1 = bottom_texts[1].get_window_extent(renderer).transformed(inv)
        if min(b0.x1, b1.x1) > max(b0.x0, b1.x0) - 0.01 and min(b0.y1, b1.y1) > max(b0.y0, b1.y0):
            right_t = bottom_texts[1] if bottom_texts[1].get_ha() == "right" else bottom_texts[0]
            left_bb = b0 if right_t is bottom_texts[1] else b1
            right_t.set_position((right_t.get_position()[0], float(left_bb.y1) + 0.004))
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()

    has_subplot_axes = any(
        ax.get_visible() and getattr(ax, "get_subplotspec", lambda: None)() is not None
        for ax in fig.axes
    )
    if not has_subplot_axes:
        return

    cur_top = float(fig.subplotpars.top)
    cur_bottom = float(fig.subplotpars.bottom)

    # 收集轴外上方的图例、轴标题与面板标号
    decor_boxes = []
    ax_boxes = []
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        ax_bb = ax.get_window_extent(renderer).transformed(inv)
        if getattr(ax, "get_subplotspec", lambda: None)() is not None:
            ax_boxes.append(ax_bb)
        leg = ax.get_legend()
        if leg is not None and leg.get_visible():
            l_bb = leg.get_window_extent(renderer).transformed(inv)
            if l_bb.y1 > ax_bb.y1 + 0.002:
                decor_boxes.append(l_bb)
        for ttl in (ax.title, getattr(ax, "_left_title", None), getattr(ax, "_right_title", None)):
            if ttl is not None and ttl.get_visible() and ttl.get_text().strip():
                t_bb = ttl.get_window_extent(renderer).transformed(inv)
                if t_bb.y1 > ax_bb.y1 + 0.002:
                    decor_boxes.append(t_bb)
        for ann in ax.texts:
            if ann.get_visible() and ann.get_text().strip():
                a_bb = ann.get_window_extent(renderer).transformed(inv)
                if a_bb.y0 >= ax_bb.y1 - 0.01 and a_bb.y1 <= 0.99:
                    decor_boxes.append(a_bb)

    # 3A. 无页眉时自动回收顶部 20% 空白（例如 academic 场景或 TITLE=SUBTITLE=""）
    if not header_texts:
        if 0.68 <= cur_top <= 0.84:
            above_pad = max(( float(b.y1) - cur_top for b in decor_boxes ), default=0.0)
            above_pad = max(0.0, above_pad)
            target_top = float(theme.get("scene_preset", {}).get("top_no_title", 0.93))
            new_top = min(target_top, 0.965 - above_pad)
            if new_top > cur_top + 0.02:
                fig.subplots_adjust(top=round(new_top, 4))
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()
    else:
        # 3B. 有页眉时检测绘图轴顶边、轴上方装饰（图例/子标题）与页眉的碰撞，动态下移 top
        h_boxes = [t.get_window_extent(renderer).transformed(inv) for t in header_texts]
        min_shift = 0.0
        for hb in h_boxes:
            for db in [*decor_boxes, *ax_boxes]:
                horiz_overlap = min(float(hb.x1), float(db.x1)) > max(float(hb.x0), float(db.x0)) - 0.018
                if horiz_overlap and float(db.y1) > float(hb.y0) - 0.014:
                    needed = float(db.y1) - (float(hb.y0) - 0.020)
                    if needed > min_shift:
                        min_shift = needed

        if min_shift > 0.001:
            new_top = max(cur_bottom + 0.30, cur_top - min_shift)
            if new_top < cur_top - 0.001:
                fig.subplots_adjust(top=round(new_top, 4))
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()

    # 4. 左边缘刻度/轴标签防裁切 & 底部来源页脚防碰撞
    cur_left = float(fig.subplotpars.left)
    cur_right = float(fig.subplotpars.right)
    cur_bottom = float(fig.subplotpars.bottom)
    cur_top = float(fig.subplotpars.top)
    left_boxes = []
    bottom_axis_boxes = []
    for ax in fig.axes:
        if not ax.get_visible() or getattr(ax, "get_subplotspec", lambda: None)() is None:
            continue
        if ax.yaxis.label.get_visible() and ax.yaxis.label.get_text().strip():
            left_boxes.append(ax.yaxis.label.get_window_extent(renderer).transformed(inv))
        for tl in _in_range_tick_labels(ax, "y"):
            bb = tl.get_window_extent(renderer).transformed(inv)
            if bb.x0 < cur_left + 0.02:
                left_boxes.append(bb)
        if ax.xaxis.label.get_visible() and ax.xaxis.label.get_text().strip():
            bottom_axis_boxes.append(ax.xaxis.label.get_window_extent(renderer).transformed(inv))
        for tl in _in_range_tick_labels(ax, "x"):
            bb = tl.get_window_extent(renderer).transformed(inv)
            if bb.y0 < cur_bottom + 0.02:
                bottom_axis_boxes.append(bb)

    margin_kw = {}
    if left_boxes:
        min_x0 = min(float(b.x0) for b in left_boxes)
        if min_x0 < 0.008 and cur_left < 0.44:
            new_left = min(0.45, min(cur_right - 0.28, cur_left + (0.014 - min_x0)))
            if new_left > cur_left + 0.002:
                margin_kw["left"] = round(new_left, 4)

    if bottom_axis_boxes:
        src_top = max((float(t.get_window_extent(renderer).transformed(inv).y1) for t in bottom_texts), default=0.0)
        floor_y = max(0.008, src_top + 0.010)
        min_y0 = min(float(b.y0) for b in bottom_axis_boxes)
        if min_y0 < floor_y and cur_bottom < 0.30:
            new_bottom = min(0.32, min(cur_top - 0.28, cur_bottom + (floor_y - min_y0)))
            if new_bottom > cur_bottom + 0.002:
                margin_kw["bottom"] = round(new_bottom, 4)

    if margin_kw:
        fig.subplots_adjust(**margin_kw)
        fig.canvas.draw()


def adjust_layout(fig, left: float | None = None, right: float | None = None,
                  top: float | None = None, bottom: float | None = None,
                  wspace: float | None = None, hspace: float | None = None,
                  theme: dict | None = None):
    """封装 subplots_adjust 并立即执行页眉/图例流式避让，确保后续 get_position() 读取最终坐标。"""
    kwargs = {k: v for k, v in (("left", left), ("right", right), ("top", top),
                                ("bottom", bottom), ("wspace", wspace), ("hspace", hspace))
              if v is not None}
    if kwargs:
        fig.subplots_adjust(**kwargs)
    _auto_reflow_figure(fig, theme=theme)
    return fig


def _iter_all_axes(fig) -> list:
    out: list = []
    seen: set[int] = set()

    def visit(ax):
        aid = id(ax)
        if aid in seen:
            return
        seen.add(aid)
        out.append(ax)
        for child in getattr(ax, "child_axes", ()):
            visit(child)

    for ax in fig.axes:
        visit(ax)
    return out


def _in_range_tick_labels(ax, axis_name: str) -> list:
    if getattr(ax, "name", "") == "3d":
        return []
    try:
        if axis_name == "x":
            lo, hi = sorted(ax.get_xlim())
            ticks = ax.xaxis.get_major_ticks()
        else:
            lo, hi = sorted(ax.get_ylim())
            ticks = ax.yaxis.get_major_ticks()
    except Exception:  # noqa: BLE001
        return []
    span = max(hi - lo, 1e-9)
    out = []
    for tick in ticks:
        loc = tick.get_loc()
        if not (lo - 0.02 * span <= loc <= hi + 0.02 * span):
            continue
        for lbl in (tick.label1, tick.label2):
            if lbl.get_visible() and lbl.get_text().strip():
                out.append(lbl)
    return out


def check_text_collisions(fig, pad_px: float = 1.5) -> dict:
    """利用 Agg Renderer 精确像素包围盒检测全图文本重叠、图例遮挡与边缘裁切。"""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fig_w, fig_h = fig.canvas.get_width_height()

    items: list[dict] = []

    def push(obj, role: str, group: str | None = None, is_box: bool = False, label_override: str | None = None):
        if obj is None or not obj.get_visible():
            return
        text_val = label_override if label_override is not None else getattr(obj, "get_text", lambda: "")()
        text_val = " ".join(str(text_val).split()).strip()
        if not text_val:
            return
        alpha = obj.get_alpha()
        if alpha is not None and alpha <= 0.01:
            return
        try:
            bb = obj.get_window_extent(renderer)
        except Exception:  # noqa: BLE001
            return
        if bb.width <= 1.0 or bb.height <= 1.0 or not (np.isfinite(bb.x0) and np.isfinite(bb.y0)):
            return
        items.append({
            "role": role,
            "text": text_val[:60],
            "group": group,
            "is_box": is_box,
            "raw": (float(bb.x0), float(bb.y0), float(bb.x1), float(bb.y1)),
        })

    for t in fig.texts:
        push(t, getattr(t, "_viz_role", "fig_text"))

    for idx, leg in enumerate(fig.legends):
        gid = f"fig_leg_{idx}"
        ltxt = " | ".join(t.get_text().strip() for t in leg.get_texts() if t.get_text().strip())
        push(leg, "legend", group=gid, is_box=True, label_override=f"[图例] {ltxt}")
        for t in leg.get_texts():
            push(t, "legend_text", group=gid)

    for ax_i, ax in enumerate(_iter_all_axes(fig)):
        if not ax.get_visible():
            continue
        for ttl in (ax.title, getattr(ax, "_left_title", None), getattr(ax, "_right_title", None)):
            push(ttl, "ax_title")
        push(ax.xaxis.label, "xlabel")
        push(ax.yaxis.label, "ylabel")
        for lbl in _in_range_tick_labels(ax, "x"):
            push(lbl, f"xtick_{ax_i}")
        for lbl in _in_range_tick_labels(ax, "y"):
            push(lbl, f"ytick_{ax_i}")
        for ann in ax.texts:
            push(ann, "annotation")
        leg = ax.get_legend()
        if leg is not None and leg.get_visible():
            gid = f"ax_leg_{ax_i}"
            ltxt = " | ".join(t.get_text().strip() for t in leg.get_texts() if t.get_text().strip())
            push(leg, "legend", group=gid, is_box=True, label_override=f"[图例] {ltxt}")
            for t in leg.get_texts():
                push(t, "legend_text", group=gid)

    clipped: list[dict] = []
    for it in items:
        if it["is_box"]:
            continue
        x0, y0, x1, y1 = it["raw"]
        if x0 < -3.0 or y0 < -3.0 or x1 > fig_w + 3.0 or y1 > fig_h + 3.0:
            clipped.append({
                "role": it["role"],
                "text": it["text"],
                "bbox_px": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                "canvas_px": [int(fig_w), int(fig_h)],
            })

    collisions: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()
    n_items = len(items)
    for i in range(n_items):
        a = items[i]
        ax0, ay0, ax1, ay1 = a["raw"]
        p_a = 0.5 if a["is_box"] else pad_px
        ax0, ay0, ax1, ay1 = ax0 + p_a, ay0 + p_a, ax1 - p_a, ay1 - p_a
        if ax1 <= ax0 or ay1 <= ay0:
            continue
        area_a = (ax1 - ax0) * (ay1 - ay0)
        for j in range(i + 1, n_items):
            b = items[j]
            if a["group"] and a["group"] == b["group"]:
                if a["is_box"] or b["is_box"]:
                    continue
            bx0, by0, bx1, by1 = b["raw"]
            p_b = 0.5 if b["is_box"] else pad_px
            bx0, by0, bx1, by1 = bx0 + p_b, by0 + p_b, bx1 - p_b, by1 - p_b
            if bx1 <= bx0 or by1 <= by0:
                continue
            iw = min(ax1, bx1) - max(ax0, bx0)
            ih = min(ay1, by1) - max(ay0, by0)
            if iw <= 0 or ih <= 0:
                continue
            inter = iw * ih
            min_area = min(area_a, (bx1 - bx0) * (by1 - by0))
            ratio = inter / max(min_area, 1.0)
            if inter >= 6.0 and ratio >= 0.05:
                pair_key = tuple(sorted((f"{a['role']}:{a['text']}", f"{b['role']}:{b['text']}")))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                collisions.append({
                    "a_role": a["role"],
                    "a_text": a["text"],
                    "b_role": b["role"],
                    "b_text": b["text"],
                    "overlap_px2": round(inter, 1),
                    "overlap_ratio": round(ratio, 3),
                })

    return {
        "passed": len(collisions) == 0 and len(clipped) == 0,
        "collision_count": len(collisions),
        "clipped_count": len(clipped),
        "collisions": collisions,
        "clipped": clipped,
    }


def last_layout_audit() -> dict | None:
    """获取最近一次 save_figure 执行的 Renderer 文本碰撞与裁切自检结果。"""
    return _LAST_LAYOUT_AUDIT


# --------------------------------------------------------------------------- #
# 导出
# --------------------------------------------------------------------------- #
def save_figure(fig, outdir: str | Path = ".", stem: str = "figure",
                formats: tuple[str, ...] = ("pdf", "svg", "png")[:2],
                dpi: tuple[int, ...] | list[int] = (300, 600),
                theme: dict | None = None, tight: bool = False,
                close: bool = True, auto_layout: bool = True) -> list[str]:
    """按格式导出；PNG 以 <stem>_<dpi>dpi.png 命名，PDF/SVG 保持矢量。

    保存前自动执行页眉/图例流式避让与 Renderer 文本包围盒碰撞自检，
    并将碰撞审计元数据写入 PNG tEXt 块供 viz-audit 闭环核查。
    """
    global _LAST_LAYOUT_AUDIT
    if auto_layout and not tight:
        _auto_reflow_figure(fig, theme=theme)
    audit = check_text_collisions(fig)
    _LAST_LAYOUT_AUDIT = audit
    if theme is not None:
        theme["_layout_audit"] = audit
    if not audit["passed"]:
        for c in audit["collisions"][:3]:
            warn_once(f"检测到文本/图例重叠：{c['a_role']}「{c['a_text']}」× {c['b_role']}「{c['b_text']}」（重叠 {c['overlap_ratio']:.0%}）")
        for cl in audit["clipped"][:3]:
            warn_once(f"检测到文本超出画布边界：{cl['role']}「{cl['text']}」")

    pnginfo = None
    try:
        from PIL.PngImagePlugin import PngInfo
        pnginfo = PngInfo()
        pnginfo.add_text("Software", f"viz-suite {__version__}")
        pnginfo.add_text("viz_layout_audit", json.dumps(audit, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        pnginfo = None

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
                pil_kw = {"pnginfo": pnginfo} if (fmt == "png" and pnginfo is not None) else None
                fig.savefig(path, format=fmt, dpi=d, bbox_inches="tight" if tight else None,
                            facecolor=fig.get_facecolor(), pil_kwargs=pil_kw)
                outputs.append(str(path))
    if close:
        plt.close(fig)
    return outputs


def describe_theme(theme: dict) -> dict:
    return {
        "scene": theme.get("scene"),
        "palette": theme.get("palette_id"),
        "layout_family": theme.get("layout_family"),
        "in_canvas_title": theme.get("in_canvas_title", True),
        "font_size_level": theme.get("font_size_level", "regular"),
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
        "scenes_available": sorted((t.get("scenes") or {}).keys()),
        "palette_pick_4": pal.pick(4),
        "cvd_min_delta_e": pal.min_delta_e,
        "contrast_on_white": {c: round(contrast_ratio(c, "#FFFFFF"), 2) for c in pal.colors},
        "sequential_mid": to_hex(sequential_cmap(pal.colors[0])(0.5)),
        "diverging_mid": to_hex(diverging_cmap(pal.colors[0], theme=t)(0.5)),
        "auto_text_on_focal": contrast_text(pal.colors[0], alpha=0.18),
        "size_plan": plan_size(89, cite_mm=85, theme=t),
    }, ensure_ascii=False, indent=2))

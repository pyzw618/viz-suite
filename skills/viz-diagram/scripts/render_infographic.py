# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""结构化信息图渲染器：12 种布局 × 4 种皮肤，输出离线 HTML 与 SVG。

数据是紧凑 JSON：一个核心主张、若干模块（单模块 ≤7 个要点）、来源与口径。
渲染器负责中文折行、卡片对齐、图标解析、对比度检查与 JSON 协议输出。

用法：
    uv run render_infographic.py data.json --outdir outputs --json
    uv run render_infographic.py data.json --layout timeline --style technical \
        --formats html,svg --outdir outputs --stem timeline-tech --json
    uv run render_infographic.py --list --json
"""
import argparse
import html
import json
import math
import re
import sys
from pathlib import Path
from string import Template

import infographic_svg

sys.stdout.reconfigure(encoding="utf-8")

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS = SKILL_ROOT / "assets"
ICON_DIR = ASSETS / "icons"
ICON_INDEX = ICON_DIR / "index.json"
LAYOUTS_PATH = ASSETS / "layouts.json"
STYLES_PATH = ASSETS / "styles.json"

LAYOUT_IDS = ["list-grid", "list-row", "sequence-steps", "timeline", "pyramid", "funnel",
              "quadrant", "compare-binary", "hierarchy-tree", "mindmap", "cycle", "stat-cards"]
STYLE_IDS = ["editorial", "minimal", "technical", "warm", "mckinsey", "academic_blueprint"]

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[._%+\-/][A-Za-z0-9]+)*|\s+|.", re.S)
CLOSING_PUNCT = set("，。；：、,.!?;:!?)]}》」』】")


# --------------------------------------------------------------------------- #
# 基础工具：颜色、文本度量、折行
# --------------------------------------------------------------------------- #
def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in rgb)


def mix(color_a: str, color_b: str, ratio: float) -> str:
    a, b = hex_to_rgb(color_a), hex_to_rgb(color_b)
    return rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * ratio for i in range(3)))


def luminance(color: str) -> float:
    def channel(v):
        v = v / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in hex_to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def text_on(color: str) -> str:
    return "#FFFFFF" if contrast_ratio("#FFFFFF", color) >= contrast_ratio("#111111", color) else "#111111"


def char_units(ch: str) -> float:
    """按 1 em ≈ 1 个汉字估算排版宽度；仅用于 SVG 折行与保守截断。"""
    if ch.isspace():
        return 0.36
    code = ord(ch)
    if code >= 0x2E80 or ch in "，。；：、！？（）【】《》「」『』":
        return 1.0
    if ch in "ilI.,;:'!|":
        return 0.28
    if ch in "MW@%&":
        return 0.9
    if ch.isupper():
        return 0.66
    if ch.isdigit():
        return 0.6
    return 0.56


def display_units(text: str) -> float:
    return sum(char_units(ch) for ch in str(text))


def split_tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def wrap_text(text: str, max_units: float, max_lines: int | None = None) -> list[str]:
    """中英文混排折行；CJK 逐字、拉丁按词，行首避头点尽量回退。"""
    text = "" if text is None else str(text).strip()
    if not text:
        return []
    paragraphs = text.splitlines() or [text]
    lines: list[str] = []
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            if lines:
                lines.append("")
            continue
        line = ""
        line_units = 0.0
        for token in split_tokens(paragraph):
            if not token:
                continue
            if token.isspace():
                if line:
                    line += " "
                    line_units += char_units(" ")
                continue
            token_units = display_units(token)
            if token_units > max_units and not line:
                # 超长英文串/URL：按字符硬切
                for ch in token:
                    u = char_units(ch)
                    if line_units + u > max_units and line:
                        lines.append(line)
                        line, line_units = "", 0.0
                    line += ch
                    line_units += u
                continue
            if line_units + token_units > max_units and line:
                lines.append(line.rstrip())
                line, line_units = "", 0.0
                if token in CLOSING_PUNCT and lines:
                    lines[-1] += token
                    continue
            line += token
            line_units += token_units
        if line:
            lines.append(line.rstrip())
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and display_units(last + "…") > max_units:
            last = last[:-1]
        lines[-1] = last.rstrip("，。；：、,.!?;: ") + "…"
    return lines


def fit_text(text: str, width: float, height: float, max_size: float, min_size: float,
             line_height: float = 1.28, max_lines: int | None = None) -> tuple[float, list[str]]:
    size = max_size
    while size >= min_size:
        max_units = max(1.0, width / size)
        lines = wrap_text(text, max_units, max_lines)
        if lines and len(lines) * size * line_height <= height + size * 0.15:
            return size, lines
        size *= 0.94
    max_units = max(1.0, width / min_size)
    lines = wrap_text(text, max_units, max_lines)
    return min_size, lines


def radial_positions(n: int) -> list[tuple[float, float]]:
    """思维导图/循环图的百分比坐标；四节点用矩形分布，其余用椭圆。"""
    if n <= 0:
        return []
    if n == 4:
        return [(22, 28), (78, 28), (22, 72), (78, 72)]
    positions = []
    for i in range(n):
        angle = math.radians(-90 + i * 360 / n)
        positions.append((50 + 36 * math.cos(angle), 50 + 34 * math.sin(angle)))
    return positions


# --------------------------------------------------------------------------- #
# 资产加载
# --------------------------------------------------------------------------- #
def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_assets() -> tuple[dict, dict, dict]:
    layouts = {item["id"]: item for item in load_json(LAYOUTS_PATH)["layouts"]}
    styles = {item["id"]: item for item in load_json(STYLES_PATH)["styles"]}
    icon_index = load_json(ICON_INDEX)
    icons = {item["name"]: item for item in icon_index["icons"]}
    return layouts, styles, icons


LAYOUTS, STYLES, ICONS = load_assets()
_ICON_RAW: dict[str, str] = {}


def icon_raw(name: str) -> str | None:
    if name in _ICON_RAW:
        return _ICON_RAW[name]
    meta = ICONS.get(name)
    if not meta:
        return None
    path = ICON_DIR / meta["file"]
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    _ICON_RAW[name] = raw
    return raw


def html_icon(name: str, cls: str = "icon", warnings: list[str] | None = None) -> str:
    raw = icon_raw(name)
    if raw is None:
        if warnings is not None and name:
            warnings.append(f"未知图标「{name}」，已回退 circle-dot")
        raw = icon_raw("circle-dot") or ""
        cls += " icon-fallback"
    raw = raw.replace("<svg ", '<svg class="icon-svg" aria-hidden="true" focusable="false" ', 1)
    return f'<span class="{cls}">{raw}</span>'


def svg_icon_inner(name: str, warnings: list[str] | None = None) -> str:
    raw = icon_raw(name)
    if raw is None:
        if warnings is not None and name:
            warnings.append(f"未知图标「{name}」，已回退 circle-dot")
        raw = icon_raw("circle-dot") or ""
    inner = re.sub(r"^.*?<svg[^>]*>", "", raw, count=1, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner, flags=re.S)
    return inner.strip()


# --------------------------------------------------------------------------- #
# 数据规范化与校验
# --------------------------------------------------------------------------- #
def safe_text(value) -> str:
    return "" if value is None else str(value).strip()


def normalize_module(raw, warnings: list[str]) -> dict:
    if not isinstance(raw, dict):
        raw = {"title": safe_text(raw)}
    module = {
        "title": safe_text(raw.get("title") or raw.get("heading") or raw.get("label")),
        "kicker": safe_text(raw.get("kicker")),
        "body": safe_text(raw.get("body") or raw.get("text") or raw.get("description")),
        "value": safe_text(raw.get("value")),
        "unit": safe_text(raw.get("unit")),
        "label": safe_text(raw.get("label")),
        "delta": safe_text(raw.get("delta")),
        "progress": raw.get("progress"),
        "tags": raw.get("tags") or [],
        "zone": safe_text(raw.get("zone")),
        "meta": safe_text(raw.get("meta") or raw.get("date") or raw.get("time")),
        "icon": safe_text(raw.get("icon") or "circle-dot"),
        "side": safe_text(raw.get("side")).lower(),
        "x": raw.get("x"),
        "y": raw.get("y"),
        "size": raw.get("size"),
        "items": [],
        "children": [],
    }
    if module["icon"] and module["icon"] not in ICONS:
        warnings.append(f"模块「{module['title'] or '未命名'}」使用未知图标 {module['icon']}，已回退 circle-dot")
        module["icon"] = "circle-dot"
    items = raw.get("items") or []
    if len(items) > 7:
        warnings.append(f"模块「{module['title'] or '未命名'}」有 {len(items)} 个要点，超过单模块 ≤7；已截断")
        items = items[:7]
    for item in items:
        if isinstance(item, dict):
            module["items"].append({
                "title": safe_text(item.get("title") or item.get("label")),
                "body": safe_text(item.get("body") or item.get("text")),
                "value": safe_text(item.get("value")),
            })
        else:
            module["items"].append({"title": safe_text(item), "body": "", "value": ""})
    for child in raw.get("children") or []:
        module["children"].append(normalize_module(child, warnings))
    if len(module["title"]) > 60:
        warnings.append(f"模块标题超过 60 字，已截断：{module['title'][:30]}…")
        module["title"] = module["title"][:59] + "…"
    if len(module["body"]) > 240:
        warnings.append(f"模块「{module['title'][:20]}」正文超过 240 字，已截断")
        module["body"] = module["body"][:239] + "…"
    for item in module["items"]:
        if len(item["title"]) > 80:
            item["title"] = item["title"][:79] + "…"
    return module


def normalize_spec(spec: dict, layout: str, style: str, warnings: list[str]) -> dict:
    if layout not in LAYOUTS:
        raise ValueError(f"未知布局 {layout}；可用：{', '.join(LAYOUT_IDS)}")
    if style not in STYLES:
        raise ValueError(f"未知风格 {style}；可用：{', '.join(STYLE_IDS)}")

    modules = [normalize_module(m, warnings) for m in (spec.get("modules") or [])]
    layout_meta = LAYOUTS[layout]
    max_modules = int(layout_meta.get("max_modules", 12))
    min_modules = int(layout_meta.get("min_modules", 1))
    if len(modules) > max_modules:
        warnings.append(f"布局 {layout} 最多 {max_modules} 个模块；已截断 {len(modules) - max_modules} 个")
        modules = modules[:max_modules]
    if len(modules) < min_modules:
        warnings.append(f"布局 {layout} 至少需要 {min_modules} 个模块；当前 {len(modules)} 个")

    root = None
    if layout == "hierarchy-tree":
        if isinstance(spec.get("root"), dict):
            root = normalize_module(spec["root"], warnings)
        elif modules and modules[0].get("children"):
            root = modules[0]
            modules = root["children"]
        else:
            root = {"title": safe_text(spec.get("title") or "核心主题"), "body": "",
                    "icon": safe_text(spec.get("icon") or "circle-dot"), "children": modules,
                    "items": [], "value": "", "unit": "", "label": "", "delta": "",
                    "meta": "", "side": "", "x": None, "y": None, "size": None, "kicker": ""}
    hub = None
    if layout in ("mindmap", "cycle"):
        hub = normalize_module(spec.get("hub") or {
            "title": spec.get("title") or "核心主题",
            "icon": spec.get("icon") or "circle-dot",
        }, warnings)

    source = safe_text(spec.get("source"))
    numbers = any(re.search(r"\d", m["value"] + m["body"] + m["label"] + m["title"])
                  for m in modules)
    if numbers and not source:
        warnings.append("内容含数值但缺少 source；已在图脚显示「数据来源：未提供」")
        source = "数据来源：未提供"

    title = safe_text(spec.get("title") or spec.get("claim") or "信息图")
    claim = safe_text(spec.get("claim") or spec.get("subtitle"))
    if source and "数据来源" not in source:
        source = "数据来源：" + source

    def shorten(value: str, limit: int, label: str) -> str:
        value = safe_text(value)
        if len(value) > limit:
            warnings.append(f"{label}超过 {limit} 字，已截断")
            return value[:limit - 1] + "…"
        return value

    title = shorten(title, 90, "标题")
    claim = shorten(claim, 160, "核心主张")
    subtitle = shorten(spec.get("subtitle"), 100, "副标题")
    footnote = shorten(spec.get("footnote"), 160, "脚注")
    source = shorten(source, 180, "来源")
    # 规范化阶段底框 / 泳道容器（Zones）
    raw_zones = spec.get("zones") or []
    zones = []
    if raw_zones:
        for z in raw_zones:
            if isinstance(z, dict):
                m_list = []
                for idx in z.get("modules", []):
                    try:
                        i_val = int(idx)
                        if 0 <= i_val < len(modules):
                            m_list.append(i_val)
                    except (ValueError, TypeError):
                        pass
                if m_list:
                    zones.append({
                        "label": safe_text(z.get("label") or z.get("title") or "分组"),
                        "kicker": safe_text(z.get("kicker") or f"PHASE {len(zones)+1:02d}"),
                        "modules": m_list,
                        "tone": safe_text(z.get("tone") or "default"),
                    })
    elif any(m.get("zone") for m in modules):
        z_map = {}
        for idx, m in enumerate(modules):
            z_name = m.get("zone") or "未分类"
            z_map.setdefault(z_name, []).append(idx)
        for z_name, m_indices in z_map.items():
            zones.append({
                "label": z_name,
                "kicker": f"PHASE {len(zones)+1:02d}",
                "modules": m_indices,
                "tone": "default",
            })

    normalized = {
        "eyebrow": safe_text(spec.get("eyebrow")),
        "title": title,
        "claim": claim,
        "subtitle": subtitle,
        "footnote": footnote,
        "source": source,
        "icon": safe_text(spec.get("icon") or "circle-dot"),
        "layout": layout,
        "style": style,
        "modules": modules,
        "zones": zones,
        "root": root,
        "hub": hub,
        "left_label": safe_text(spec.get("left_label") or "现状"),
        "right_label": safe_text(spec.get("right_label") or "目标"),
        "as_of": safe_text(spec.get("as_of")),
    }

    style_meta = STYLES[style]
    colors = style_meta["colors"]
    checks = [
        ("ink_on_bg", colors["ink"], colors["bg"]),
        ("ink_on_surface", colors["ink"], colors["surface"]),
        ("muted_on_surface", colors["muted"], colors["surface"]),
        ("on_accent", colors["on_accent"], colors["accent"]),
    ]
    normalized["_contrast"] = {name: round(contrast_ratio(fg, bg), 2) for name, fg, bg in checks}
    for name, ratio in normalized["_contrast"].items():
        if ratio < 4.5:
            warnings.append(f"风格 {style} 的 {name} 对比度 {ratio:.2f}:1 低于 4.5:1")
    return normalized


# --------------------------------------------------------------------------- #
# HTML 渲染
# --------------------------------------------------------------------------- #
CSS_TEMPLATE = Template(r"""
:root{
  --bg:$bg;--surface:$surface;--surface2:$surface2;--ink:$ink;--muted:$muted;
  --accent:$accent;--accent2:$accent2;--positive:$positive;--negative:$negative;
  --border:$border;--on-accent:$on_accent;--radius:${radius}px;--border-w:${border_width}px;
  --shadow:$shadow;--font-display:$font_display;--font-body:$font_body;
  --font-label:$font_label;--font-mono:$font_mono;--title:${size_title}px;
  --claim:${size_claim}px;--body:${size_body}px;--small:${size_small}px;
  --micro:${size_micro}px;--value:${size_value}px;--label:${size_label}px;
  --lh:$line_height;--pad:${card_padding}px;--texture:$texture_css;--texture-size:$texture_size;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink)}
body{font-family:var(--font-body);font-size:var(--body);line-height:var(--lh);-webkit-font-smoothing:antialiased}
body{padding:clamp(16px,4vw,64px)}
.poster{position:relative;max-width:1240px;height:auto;margin:0 auto;isolation:isolate}
.poster::before{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;background-image:var(--texture);background-size:var(--texture-size);opacity:.9}
.masthead{position:relative;padding:26px 0 30px;margin-bottom:30px;border-top:6px solid var(--accent)}
.style-minimal .masthead{border-top:0;padding-top:12px}
.style-warm .masthead{border-top:0;padding:22px 26px;background:var(--surface);border-radius:calc(var(--radius) + 8px);box-shadow:var(--shadow)}
.style-technical .masthead{border-top:0;border-left:6px solid var(--accent);padding-left:22px}
.eyebrow{display:flex;align-items:center;gap:10px;font-family:var(--font-label);font-size:var(--label);
  letter-spacing:.14em;text-transform:$label_transform;color:var(--accent);font-weight:700;margin-bottom:14px}
.eyebrow .icon{width:22px;height:22px}
h1{font-family:var(--font-display);font-size:clamp(34px,var(--title),var(--title));line-height:1.08;
  margin:0 0 14px;max-width:24ch;letter-spacing:-.015em;overflow-wrap:anywhere}
.claim{font-size:clamp(20px,var(--claim),var(--claim));line-height:1.38;color:var(--ink);max-width:48ch;
  margin:0 0 12px;padding-left:16px;border-left:3px solid var(--accent)}
.style-warm .claim{border-left:0;background:var(--surface2);border-radius:12px;padding:12px 16px}
.meta-row{display:flex;gap:18px;flex-wrap:wrap;color:var(--muted);font-size:var(--small);margin-top:8px}
.meta-row span{overflow-wrap:anywhere}
.layout-body{display:block}
.icon{display:inline-flex;width:42px;height:42px;color:var(--accent);flex:0 0 auto}
.icon svg{width:100%;height:100%;display:block;stroke-width:1.8}
.card{background:var(--surface);border:var(--border-w) solid var(--border);border-radius:var(--radius);
  padding:var(--pad);box-shadow:var(--shadow);min-width:0;overflow-wrap:anywhere}
.card h3{font-family:var(--font-display);font-size:clamp(18px,calc(var(--body) * 1.25),26px);
  line-height:1.25;margin:10px 0 8px;overflow-wrap:anywhere}
.card p{margin:0;color:var(--muted);font-size:var(--body);line-height:var(--lh);overflow-wrap:anywhere}
.card .kicker{font-family:var(--font-label);font-size:var(--micro);letter-spacing:.12em;text-transform:$label_transform;color:var(--accent);font-weight:700}
.card .value{font-family:var(--font-display);font-size:calc(var(--value) * .72);line-height:1;color:var(--ink);
  font-variant-numeric:tabular-nums;margin:8px 0 6px;overflow-wrap:anywhere}
.card .value small{font-size:.42em;color:var(--muted);font-weight:500;margin-left:4px}
.card .label{font-family:var(--font-label);font-size:var(--micro);letter-spacing:.1em;text-transform:$label_transform;color:var(--muted);font-weight:700}
.card ul{margin:8px 0 0;padding-left:1.1em;color:var(--muted);font-size:var(--small)}
.card li{margin:3px 0;overflow-wrap:anywhere}
.delta{display:inline-flex;align-items:center;gap:4px;font-family:var(--font-label);font-size:var(--small);
  font-weight:700;color:var(--muted);margin-top:6px}
.delta.up{color:var(--positive)}.delta.down{color:var(--negative)}

/* list-grid / list-row */
.grid{display:grid;grid-template-columns:repeat(var(--cols,3),minmax(0,1fr));gap:18px;align-items:stretch}
.rows{display:flex;flex-direction:column;gap:12px}
.row{display:grid;grid-template-columns:54px minmax(0,1fr) auto;gap:16px;align-items:start;
  background:var(--surface);border:var(--border-w) solid var(--border);border-radius:var(--radius);
  padding:calc(var(--pad) * .8);box-shadow:var(--shadow)}
.row .row-main h3{margin:0 0 4px;font-family:var(--font-display);font-size:calc(var(--body) * 1.3);line-height:1.3;overflow-wrap:anywhere}
.row .row-main p{margin:0;color:var(--muted);font-size:var(--body);overflow-wrap:anywhere}
.row .row-value{font-family:var(--font-display);font-size:calc(var(--value) * .55);font-variant-numeric:tabular-nums;line-height:1;white-space:nowrap}
.row .row-value small{font-size:.42em;color:var(--muted);margin-left:3px}

/* steps */
.steps{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px;counter-reset:step}
.step{position:relative;background:var(--surface);border:var(--border-w) solid var(--border);border-radius:var(--radius);
  padding:calc(var(--pad) * .9);box-shadow:var(--shadow)}
.step-num{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;border-radius:50%;
  background:var(--accent);color:var(--on-accent);font-family:var(--font-label);font-size:var(--small);font-weight:700;margin-bottom:12px}
.step h3{font-family:var(--font-display);font-size:calc(var(--body) * 1.3);line-height:1.28;margin:0 0 6px;overflow-wrap:anywhere}
.step p{margin:0;color:var(--muted);font-size:var(--body);overflow-wrap:anywhere}
.steps .step:not(:last-child)::after{content:"→";position:absolute;right:-15px;top:50%;transform:translateY(-50%);
  color:var(--accent);font-size:22px;font-weight:700;z-index:2}
.style-warm .steps .step:not(:last-child)::after{content:"›"}

/* timeline */
.timeline{list-style:none;margin:0;padding:0 0 0 28px;position:relative}
.timeline::before{content:"";position:absolute;left:7px;top:6px;bottom:6px;width:2px;background:var(--border)}
.timeline li{position:relative;display:grid;grid-template-columns:120px minmax(0,1fr);gap:18px;padding:0 0 22px}
.timeline .when{font-family:var(--font-label);font-size:var(--small);font-weight:700;color:var(--accent);
  text-align:right;padding-top:8px;overflow-wrap:anywhere}
.timeline .dot{position:absolute;left:-28px;top:8px;width:16px;height:16px;border-radius:50%;background:var(--surface);
  border:4px solid var(--accent);z-index:1}
.timeline .event{padding:calc(var(--pad) * .85)}
.timeline .event h3{margin:0 0 6px;font-family:var(--font-display);font-size:calc(var(--body) * 1.3);line-height:1.3;overflow-wrap:anywhere}
.timeline .event p{margin:0;color:var(--muted);font-size:var(--body);overflow-wrap:anywhere}

/* pyramid */
.pyramid{display:flex;flex-direction:column;align-items:center;gap:7px;max-width:980px;margin:0 auto}
.pyramid-layer{position:relative;width:var(--w);min-height:112px;display:grid;grid-template-columns:48px minmax(0,1fr) auto;
  align-items:center;gap:14px;padding:18px 30px;border:var(--border-w) solid var(--border);
  clip-path:polygon(4% 0,96% 0,100% 100%,0 100%);background:var(--tone);overflow-wrap:anywhere}
.py-level{font-family:var(--font-label);font-size:var(--micro);font-weight:700;color:var(--accent);letter-spacing:.1em}
.pyramid-layer h3{margin:0 0 4px;font-family:var(--font-display);font-size:calc(var(--body) * 1.35);line-height:1.25}
.pyramid-layer p{margin:0;color:var(--muted);font-size:var(--small);line-height:1.45}
.py-value{font-family:var(--font-display);font-size:calc(var(--value) * .42);color:var(--ink);font-variant-numeric:tabular-nums;white-space:nowrap}

/* funnel */
.funnel{display:flex;flex-direction:column;align-items:center;gap:6px;max-width:900px;margin:0 auto}
.funnel-step{width:100%;display:flex;flex-direction:column;align-items:center}
.funnel-bar{width:var(--w);min-height:84px;display:flex;align-items:center;justify-content:space-between;gap:16px;
  padding:13px 24px;border-radius:var(--radius);background:var(--tone);border:var(--border-w) solid var(--border);
  overflow-wrap:anywhere}
.funnel-title{font-family:var(--font-display);font-size:calc(var(--body) * 1.15);font-weight:700}
.funnel-value{font-family:var(--font-display);font-size:calc(var(--value) * .42);font-variant-numeric:tabular-nums;white-space:nowrap}
.funnel-meta{font-family:var(--font-label);font-size:var(--small);color:var(--muted);padding:4px 0 2px}
.funnel-arrow{color:var(--accent);font-size:18px;line-height:1;margin:1px 0}

/* quadrant */
.quadrant{position:relative;aspect-ratio:1.18/1;max-width:820px;margin:0 auto;background:var(--surface);
  border:var(--border-w) solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);
  padding:28px 34px 44px 54px}
.quadrant::before,.quadrant::after{content:"";position:absolute;background:var(--border);opacity:.8}
.quadrant::before{left:50%;top:24px;bottom:42px;width:1px}
.quadrant::after{top:50%;left:44px;right:26px;height:1px}
.q-label{position:absolute;font-family:var(--font-label);font-size:var(--micro);letter-spacing:.08em;
  text-transform:$label_transform;color:var(--muted);font-weight:700}
.q-tl{left:28px;top:16px}.q-tr{right:18px;top:16px}.q-bl{left:28px;bottom:12px}.q-br{right:18px;bottom:12px}
.q-axis-x{position:absolute;left:50%;bottom:10px;transform:translateX(-50%);font-size:var(--small);color:var(--muted)}
.q-axis-y{position:absolute;left:10px;top:50%;transform:translateY(-50%) rotate(-90deg);font-size:var(--small);color:var(--muted);white-space:nowrap}
.q-point{position:absolute;left:calc(var(--x) * 1%);bottom:calc(var(--y) * 1%);transform:translate(-50%,50%);
  display:flex;flex-direction:column;align-items:center;gap:3px;max-width:140px;text-align:center;z-index:2}
.q-dot{width:var(--dot,24px);height:var(--dot,24px);border-radius:50%;background:var(--accent);border:3px solid var(--surface);
  box-shadow:0 0 0 1px var(--accent);flex:0 0 auto}
.q-name{font-family:var(--font-label);font-size:var(--micro);font-weight:700;color:var(--ink);line-height:1.2;overflow-wrap:anywhere}
.q-note{font-size:10px;color:var(--muted);line-height:1.2;overflow-wrap:anywhere}
.q-legend{display:flex;gap:16px;flex-wrap:wrap;margin:18px auto 0;justify-content:center;color:var(--muted);font-size:var(--small)}

/* compare */
.compare{display:grid;grid-template-columns:minmax(0,1fr) 64px minmax(0,1fr);gap:14px;align-items:stretch}
.compare-side{display:flex;flex-direction:column;gap:12px;padding:20px;border:var(--border-w) solid var(--border);
  border-radius:var(--radius);background:var(--surface);box-shadow:var(--shadow);min-width:0}
.compare-side h2{font-family:var(--font-display);font-size:calc(var(--body) * 1.45);margin:0 0 4px}
.compare-side .side-kicker{font-family:var(--font-label);font-size:var(--micro);letter-spacing:.12em;text-transform:$label_transform;color:var(--muted);font-weight:700}
.compare-side .mini{display:grid;grid-template-columns:32px minmax(0,1fr);gap:10px;align-items:start;padding:9px 0;border-top:1px solid var(--border)}
.compare-side .mini:first-of-type{border-top:0}
.compare-side .mini .icon{width:28px;height:28px;color:var(--accent2)}
.compare-side .mini h3{font-size:calc(var(--body) * 1.05);margin:0 0 3px;line-height:1.3}
.compare-side .mini p{margin:0;color:var(--muted);font-size:var(--small);line-height:1.45}
.vs{align-self:center;justify-self:center;width:52px;height:52px;border-radius:50%;background:var(--accent);
  color:var(--on-accent);display:flex;align-items:center;justify-content:center;font-family:var(--font-label);
  font-size:var(--micro);font-weight:700;letter-spacing:.04em}

/* tree / mindmap / cycle */
.tree-wrap{background:var(--surface);border:var(--border-w) solid var(--border);border-radius:var(--radius);
  box-shadow:var(--shadow);padding:24px 26px;overflow-x:auto}
.tree,.tree ul{list-style:none;margin:0;padding:0}
.tree ul{margin-left:26px;position:relative;padding-left:18px;border-left:1px solid var(--border)}
.tree li{position:relative;padding:9px 0}
.tree li::before{content:"";position:absolute;left:-19px;top:26px;width:18px;height:1px;background:var(--border)}
.tree>li::before{display:none}
.tree .node{display:inline-flex;align-items:center;gap:10px;background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius);padding:9px 13px;font-family:var(--font-label);font-size:var(--small);font-weight:700;
  max-width:100%;overflow-wrap:anywhere}
.tree .node .icon{width:20px;height:20px;color:var(--accent)}
.tree .branch-body{display:block;font-weight:400;color:var(--muted);font-size:var(--micro);margin-top:3px}
.tree ul .node{background:var(--surface)}

.mindmap,.cycle{position:relative;height:640px;background:var(--surface);border:var(--border-w) solid var(--border);
  border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden}
.mindmap .connectors,.cycle .connectors{position:absolute;inset:0;width:100%;height:100%;z-index:0}
.mindmap .connectors path,.cycle .connectors path{fill:none;stroke:var(--accent);stroke-width:1.6;opacity:.55;vector-effect:non-scaling-stroke}
.mindmap .hub,.cycle .hub{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);z-index:2;
  width:220px;min-height:120px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;
  padding:18px;border-radius:50%;background:var(--accent);color:var(--on-accent);text-align:center;box-shadow:var(--shadow)}
.mindmap .hub .icon,.cycle .hub .icon{color:var(--on-accent);width:30px;height:30px}
.mindmap .hub strong,.cycle .hub strong{font-family:var(--font-display);font-size:calc(var(--body) * 1.2);line-height:1.25;overflow-wrap:anywhere}
.mindmap .branch,.cycle .branch{position:absolute;left:calc(var(--x) * 1%);top:calc(var(--y) * 1%);transform:translate(-50%,-50%);
  z-index:2;width:230px;background:var(--surface);border:var(--border-w) solid var(--border);border-radius:var(--radius);
  padding:12px 14px;box-shadow:var(--shadow);overflow-wrap:anywhere}
.mindmap .branch{display:grid;grid-template-columns:26px minmax(0,1fr);gap:9px;align-items:start}
.mindmap .branch .icon,.cycle .branch .icon{width:24px;height:24px;color:var(--accent2)}
.mindmap .branch h3,.cycle .branch h3{margin:0 0 3px;font-size:calc(var(--body) * .98);line-height:1.25}
.mindmap .branch p,.cycle .branch p{margin:0;color:var(--muted);font-size:var(--micro);line-height:1.4}

/* stat cards */
.stat-grid{display:grid;grid-template-columns:repeat(var(--cols,3),minmax(0,1fr));gap:18px}
.stat-card{display:flex;flex-direction:column;gap:8px}
.stat-card .topline{display:flex;align-items:center;justify-content:space-between;gap:12px}
.stat-card .value{font-size:var(--value);line-height:1;margin:4px 0 0}
.stat-card .value small{font-size:.38em}
.stat-card .label{margin-top:2px}
.stat-card .body{margin:6px 0 0;color:var(--muted);font-size:var(--small);line-height:1.5}

/* footer */
.source{margin-top:34px;padding-top:14px;border-top:1px solid var(--border);display:flex;gap:18px;
  justify-content:space-between;flex-wrap:wrap;color:var(--muted);font-size:var(--micro);line-height:1.5}
.source span{overflow-wrap:anywhere}
.footnote{max-width:52ch;text-align:right}

/* style-specific */
.style-editorial .card{border-top:3px solid var(--accent)}
.style-editorial .grid .card:nth-child(3n+2){border-top-color:var(--accent2)}
.style-minimal .card{box-shadow:none}
.style-minimal .masthead{border-bottom:1px solid var(--border);padding-bottom:22px}
.style-technical h1,.style-technical .card h3,.style-technical .stat-card .value{font-family:var(--font-mono)}
.style-technical .card{border-left:3px solid var(--accent)}
.style-warm .card{box-shadow:var(--shadow)}
.style-warm .step-num,.style-warm .vs{border-radius:14px}
/* zones / swimlane containers */
.zone-container{background:var(--surface2, rgba(0,0,0,0.025));border:1px dashed var(--border);border-radius:calc(var(--radius) + 4px);padding:18px 20px;margin-bottom:24px;position:relative}
.zone-header{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.zone-kicker{font-family:var(--font-label);font-size:var(--micro);font-weight:700;letter-spacing:.12em;text-transform:$label_transform;color:var(--accent);background:var(--surface);border:1px solid var(--border);padding:2px 8px;border-radius:4px}
.zone-title{font-family:var(--font-display);font-size:calc(var(--body) * 1.15);font-weight:700;color:var(--ink)}

.style-warm .poster::before{border-radius:28px}

@media (max-width:900px){
  .grid,.stat-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .compare{grid-template-columns:1fr;gap:10px}
  .vs{width:44px;height:44px}
  .timeline li{grid-template-columns:86px minmax(0,1fr);gap:12px}
  .mindmap,.cycle{height:auto;padding:18px;display:grid;gap:10px}
  .mindmap .connectors,.cycle .connectors{display:none}
  .mindmap .hub,.cycle .hub{position:static;transform:none;width:100%;border-radius:var(--radius);flex-direction:row;justify-content:flex-start;text-align:left}
  .mindmap .branch,.cycle .branch{position:static;transform:none;width:100%;box-shadow:none}
  .q-point{max-width:100px}
}
@media (max-width:620px){
  body{padding:12px}
  .masthead{padding-top:18px;margin-bottom:20px}
  .eyebrow{font-size:11px}
  .claim{font-size:18px;padding-left:12px}
  .grid,.stat-grid{grid-template-columns:1fr}
  .row{grid-template-columns:42px minmax(0,1fr);gap:10px}
  .row .row-value{grid-column:2;font-size:26px}
  .steps{grid-template-columns:1fr}
  .steps .step:not(:last-child)::after{content:"↓";right:auto;left:50%;top:auto;bottom:-20px;transform:translateX(-50%)}
  .timeline{padding-left:20px}
  .timeline li{grid-template-columns:1fr;gap:4px;padding-bottom:18px}
  .timeline .when{text-align:left;padding-top:0}
  .timeline .dot{left:-20px;top:2px;width:14px;height:14px;border-width:3px}
  .pyramid-layer{grid-template-columns:40px minmax(0,1fr);padding:12px 18px;clip-path:none;border-radius:var(--radius)}
  .py-value{grid-column:2;font-size:24px}
  .funnel-bar{width:100% !important;padding:11px 14px}
  .quadrant{aspect-ratio:1/1.05;padding:24px 12px 40px 34px}
  .q-label{display:none}
  .q-point{max-width:76px}
  .q-name{font-size:9px}.q-note{display:none}
  .compare-side{padding:14px}
  .source{flex-direction:column;gap:6px}
  .footnote{text-align:left}
  .style-warm .masthead{padding:16px}
}
@media print{
  body{padding:0;background:#fff}
  .poster{max-width:none}
  .card,.row,.step,.compare-side,.tree-wrap,.mindmap,.cycle{box-shadow:none}
}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto !important;transition:none !important}}
""")

TEXTURE_MAP = {
    "none": ("none", "auto"),
    "rules": ("repeating-linear-gradient(0deg,transparent 0 31px,rgba(28,27,25,.055) 31px 32px)", "32px 32px"),
    "grid": ("linear-gradient(rgba(0,98,155,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(0,98,155,.07) 1px,transparent 1px)", "32px 32px"),
    "dots": ("radial-gradient(circle,rgba(59,47,47,.10) 1px,transparent 1.3px)", "18px 18px"),
}


def build_css(style: dict) -> str:
    colors = style["colors"]
    fonts = style["fonts"]
    sizes = style["sizes"]
    texture, texture_size = TEXTURE_MAP.get(style.get("texture", "none"), TEXTURE_MAP["none"])
    return CSS_TEMPLATE.substitute(
        bg=colors["bg"], surface=colors["surface"], surface2=colors["surface2"],
        ink=colors["ink"], muted=colors["muted"], accent=colors["accent"],
        accent2=colors["accent2"], positive=colors["positive"], negative=colors["negative"],
        border=colors["border"], on_accent=colors["on_accent"],
        radius=style.get("radius", 0), border_width=style.get("border_width", 1),
        shadow=style.get("shadow", "none"), font_display=fonts["display"],
        font_body=fonts["body"], font_label=fonts["label"], font_mono=fonts["mono"],
        size_title=sizes["title"], size_claim=sizes["claim"], size_body=sizes["body"],
        size_small=sizes["small"], size_micro=sizes["micro"], size_value=sizes["value"],
        size_label=sizes["label"], line_height=style.get("line_height", 1.55),
        card_padding=style.get("card_padding", 22),
        texture_css=texture, texture_size=texture_size,
        label_transform="uppercase" if style.get("uppercase_labels") else "none",
    )


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def meta_row(spec: dict) -> str:
    pieces = [spec.get("subtitle"), spec.get("as_of")]
    pieces = [p for p in pieces if p]
    if not pieces:
        return ""
    return '<div class="meta-row">' + "".join(f"<span>{esc(p)}</span>" for p in pieces) + "</div>"


def footer_html(spec: dict) -> str:
    footnote = f'<span class="footnote">{esc(spec["footnote"])}</span>' if spec.get("footnote") else ""
    return f'<figcaption class="source"><span>{esc(spec["source"])}</span>{footnote}</figcaption>'


def html_header(spec: dict, style: dict, warnings: list[str]) -> str:
    eyebrow = ""
    if spec.get("eyebrow"):
        eyebrow = (f'<div class="eyebrow">{html_icon(spec.get("icon"), "icon", warnings)}'
                   f'<span>{esc(spec["eyebrow"])}</span></div>')
    claim = f'<p class="claim">{esc(spec["claim"])}</p>' if spec.get("claim") else ""
    return (f'<header class="masthead">{eyebrow}<h1>{esc(spec["title"])}</h1>{claim}'
            f'{meta_row(spec)}</header>')


def card_html(module: dict, warnings: list[str], cls: str = "") -> str:
    kicker = f'<div class="kicker">{esc(module["kicker"])}</div>' if module.get("kicker") else ""
    value = ""
    if module.get("value"):
        unit = f'<small>{esc(module["unit"])}</small>' if module.get("unit") else ""
        value = f'<div class="value">{esc(module["value"])}{unit}</div>'
    label = f'<div class="label">{esc(module["label"])}</div>' if module.get("label") else ""
    delta = ""
    if module.get("delta"):
        cls_delta = "down" if str(module["delta"]).strip().startswith(("-", "↓", "−")) else "up"
        arrow = "↓" if cls_delta == "down" else "↑"
        delta = f'<div class="delta {cls_delta}">{arrow} {esc(module["delta"].lstrip("+-↑↓− "))}</div>'
    progress = ""
    if module.get("progress") is not None:
        p_val = max(0.0, min(100.0, float(module["progress"])))
        progress = f'<div class="progress-bar" style="background:var(--surface2, #E5E7EB);height:6px;border-radius:3px;margin:8px 0;overflow:hidden"><div style="background:var(--accent, #00205B);height:100%;width:{p_val:.1f}%"></div></div>'
    tags = ""
    if module.get("tags"):
        chips = "".join(f'<span class="tag-chip" style="display:inline-block;padding:2px 8px;font-size:11px;background:var(--surface2, #E5E7EB);color:var(--muted);border-radius:4px;margin-right:4px;margin-top:4px">{esc(t)}</span>' for t in module["tags"])
        tags = f'<div class="tags-container" style="margin-top:6px">{chips}</div>'
    items = ""
    if module.get("items"):
        lis = "".join(
            f'<li>{esc(item["title"])}' + (f'：{esc(item["body"])}' if item.get("body") else "") + "</li>"
            for item in module["items"])
        items = f"<ul>{lis}</ul>"
    body = f'<p>{esc(module["body"])}</p>' if module.get("body") else ""
    icon = html_icon(module.get("icon"), "icon", warnings)
    return (f'<article class="card {cls}">{icon}{kicker}{value}{label}{delta}{progress}'
            f'<h3>{esc(module["title"])}</h3>{body}{items}{tags}</article>')


def layout_list_grid(spec, style, warnings):
    zones = spec.get("zones") or []
    if not zones:
        cols = 2 if len(spec["modules"]) <= 4 else 3
        return (f'<section class="grid" style="--cols:{cols}">'
                + "".join(card_html(m, warnings) for m in spec["modules"]) + "</section>")

    out = []
    for z in zones:
        z_kicker = f'<span class="zone-kicker">{esc(z["kicker"])}</span>' if z.get("kicker") else ""
        z_title = f'<span class="zone-title">{esc(z["label"])}</span>'
        z_head = f'<div class="zone-header">{z_kicker}{z_title}</div>'
        z_mods = [spec["modules"][idx] for idx in z["modules"] if 0 <= idx < len(spec["modules"])]
        cols = 2 if len(z_mods) <= 4 else 3
        cards_html = f'<div class="grid" style="--cols:{cols}">' + "".join(card_html(m, warnings) for m in z_mods) + "</div>"
        out.append(f'<section class="zone-container">{z_head}{cards_html}</section>')
    return "".join(out)


def layout_list_row(spec, style, warnings):
    rows = []
    for m in spec["modules"]:
        value = ""
        if m.get("value"):
            unit = f'<small>{esc(m["unit"])}</small>' if m.get("unit") else ""
            value = f'<div class="row-value">{esc(m["value"])}{unit}</div>'
        body = f'<p>{esc(m["body"])}</p>' if m.get("body") else ""
        rows.append(
            f'<article class="row">{html_icon(m.get("icon"), "icon", warnings)}'
            f'<div class="row-main"><h3>{esc(m["title"])}</h3>{body}</div>{value}</article>')
    return '<section class="rows">' + "".join(rows) + "</section>"


def layout_sequence(spec, style, warnings):
    zones = spec.get("zones") or []
    if not zones:
        steps = []
        for i, m in enumerate(spec["modules"], start=1):
            body = f'<p>{esc(m["body"])}</p>' if m.get("body") else ""
            steps.append(f'<li class="step"><div class="step-num">{i:02d}</div>'
                         f'<h3>{esc(m["title"])}</h3>{body}</li>')
        return '<ol class="steps">' + "".join(steps) + "</ol>"

    out = []
    for z in zones:
        z_kicker = f'<span class="zone-kicker">{esc(z["kicker"])}</span>' if z.get("kicker") else ""
        z_title = f'<span class="zone-title">{esc(z["label"])}</span>'
        z_head = f'<div class="zone-header">{z_kicker}{z_title}</div>'
        sub_steps = []
        for idx in z["modules"]:
            if 0 <= idx < len(spec["modules"]):
                m = spec["modules"][idx]
                body = f'<p>{esc(m["body"])}</p>' if m.get("body") else ""
                sub_steps.append(f'<li class="step"><div class="step-num">{idx + 1:02d}</div>'
                                 f'<h3>{esc(m["title"])}</h3>{body}</li>')
        out.append(f'<section class="zone-container">{z_head}<ol class="steps">{"".join(sub_steps)}</ol></section>')
    return "".join(out)


def layout_timeline(spec, style, warnings):
    items = []
    for m in spec["modules"]:
        body = f'<p>{esc(m["body"])}</p>' if m.get("body") else ""
        when = esc(m.get("meta") or m.get("kicker") or "")
        items.append(f'<li><div class="when">{when}</div><div class="dot"></div>'
                     f'<div class="card event"><h3>{esc(m["title"])}</h3>{body}</div></li>')
    return '<ol class="timeline">' + "".join(items) + "</ol>"


def layout_pyramid(spec, style, warnings):
    colors = style["colors"]
    layers = []
    n = max(1, len(spec["modules"]))
    for i, m in enumerate(spec["modules"]):
        width = 36 + 64 * (i + 1) / n
        tone = mix(colors["surface"], colors["accent"], 0.07 + 0.11 * (n - i - 1) / max(1, n - 1))
        body = f'<p>{esc(m["body"])}</p>' if m.get("body") else ""
        value = f'<span class="py-value">{esc(m["value"])}{esc(m["unit"])}</span>' if m.get("value") else ""
        layers.append(
            f'<div class="pyramid-layer" style="--w:{width:.1f}%;--tone:{tone}">'
            f'<span class="py-level">L{i + 1}</span><div><h3>{esc(m["title"])}</h3>{body}</div>{value}</div>')
    return '<section class="pyramid">' + "".join(layers) + "</section>"


def layout_funnel(spec, style, warnings):
    colors = style["colors"]
    blocks = []
    n = max(1, len(spec["modules"]))
    for i, m in enumerate(spec["modules"]):
        width = 100 - 52 * i / max(1, n - 1)
        tone = mix(colors["surface"], colors["accent"], 0.10 + 0.10 * i / max(1, n - 1))
        body = f'<p>{esc(m["body"])}</p>' if m.get("body") else ""
        meta = f'<div class="funnel-meta">{esc(m["meta"])}{("｜" + body) if body else ""}</div>' if (m.get("meta") or body) else ""
        blocks.append(
            f'<div class="funnel-step"><div class="funnel-bar" style="--w:{width:.1f}%;--tone:{tone}">'
            f'<span class="funnel-title">{esc(m["title"])}</span>'
            f'<span class="funnel-value">{esc(m["value"])}{esc(m["unit"])}</span></div>{meta}</div>')
        if i < n - 1:
            blocks.append('<div class="funnel-arrow">▼</div>')
    return '<section class="funnel">' + "".join(blocks) + "</section>"


def layout_quadrant(spec, style, warnings):
    points = []
    for m in spec["modules"]:
        try:
            x = float(m.get("x", 50))
            y = float(m.get("y", 50))
        except (TypeError, ValueError):
            x, y = 50.0, 50.0
            warnings.append(f"四象限模块「{m['title']}」缺少合法 x/y，已放在中心")
        x = max(2, min(98, x))
        y = max(2, min(98, y))
        size = m.get("size")
        try:
            dot = max(16, min(54, 16 + float(size or 24)))
        except (TypeError, ValueError):
            dot = 24
        note = f'<span class="q-note">{esc(m["body"])}</span>' if m.get("body") else ""
        points.append(
            f'<div class="q-point" style="--x:{x:.1f};--y:{y:.1f};--dot:{dot}px">'
            f'<span class="q-dot"></span><span class="q-name">{esc(m["title"])}</span>{note}</div>')
    x_label = esc(spec.get("x_label") or "维度 X →")
    y_label = esc(spec.get("y_label") or "维度 Y →")
    x_short = esc(str(spec.get("x_label") or "维度 X").replace("→", "").strip())
    y_short = esc(str(spec.get("y_label") or "维度 Y").replace("→", "").strip())
    return (f'<div class="quadrant"><span class="q-label q-tl">低 {x_short} · 高 {y_short}</span>'
            f'<span class="q-label q-tr">高 {x_short} · 高 {y_short}</span>'
            f'<span class="q-label q-bl">低 {x_short} · 低 {y_short}</span>'
            f'<span class="q-label q-br">高 {x_short} · 低 {y_short}</span>'
            f'<span class="q-axis-x">{x_label}</span><span class="q-axis-y">{y_label}</span>'
            + "".join(points) + "</div>")


def layout_compare(spec, style, warnings):
    modules = spec["modules"]
    left = [m for m in modules if m.get("side") in ("left", "a", "before", "现状")]
    right = [m for m in modules if m.get("side") in ("right", "b", "after", "目标")]
    if not left and not right:
        mid = (len(modules) + 1) // 2
        left, right = modules[:mid], modules[mid:]

    def side(mods, label, kicker):
        inner = []
        for m in mods:
            body = f'<p>{esc(m["body"])}</p>' if m.get("body") else ""
            inner.append(f'<div class="mini">{html_icon(m.get("icon"), "icon", warnings)}'
                         f'<div><h3>{esc(m["title"])}</h3>{body}</div></div>')
        return (f'<section class="compare-side"><div class="side-kicker">{esc(kicker)}</div>'
                f'<h2>{esc(label)}</h2>{"".join(inner)}</section>')

    return ('<section class="compare">' + side(left, spec["left_label"], "方案 A")
            + '<div class="vs">VS</div>' + side(right, spec["right_label"], "方案 B") + "</section>")


def tree_node_html(node: dict, warnings: list[str]) -> str:
    body = f'<span class="branch-body">{esc(node["body"])}</span>' if node.get("body") else ""
    inner = (f'{html_icon(node.get("icon"), "icon", warnings)}'
             f'<span>{esc(node["title"])}{body}</span>')
    children = ""
    if node.get("children"):
        children = "<ul>" + "".join(f"<li>{tree_node_html(c, warnings)}</li>" for c in node["children"]) + "</ul>"
    return f'<div class="node">{inner}</div>{children}'


def layout_hierarchy(spec, style, warnings):
    return '<div class="tree-wrap"><ul class="tree"><li>' + tree_node_html(spec["root"], warnings) + "</li></ul></div>"


def radial_positions(n: int) -> list[tuple[float, float]]:
    if n <= 0:
        return []
    if n == 4:
        return [(24, 28), (76, 28), (24, 72), (76, 72)]
    positions = []
    for i in range(n):
        angle = math.radians(-90 + i * 360 / n)
        positions.append((50 + 36 * math.cos(angle), 50 + 34 * math.sin(angle)))
    return positions


def layout_mindmap(spec, style, warnings):
    modules = spec["modules"]
    pos = radial_positions(len(modules))
    paths = []
    branches = []
    for (x, y), m in zip(pos, modules):
        paths.append(f'<path d="M50 50 Q{50 + (x - 50) * 0.45} {50 + (y - 50) * 0.2} {x} {y}"/>')
        body = f'<p>{esc(m["body"])}</p>' if m.get("body") else ""
        branches.append(
            f'<div class="branch" style="--x:{x:.1f};--y:{y:.1f}">'
            f'{html_icon(m.get("icon"), "icon", warnings)}<div><h3>{esc(m["title"])}</h3>{body}</div></div>')
    hub = spec["hub"]
    hub_html = (f'<div class="hub">{html_icon(hub.get("icon"), "icon", warnings)}'
                f'<strong>{esc(hub["title"])}</strong></div>')
    return ('<div class="mindmap"><svg class="connectors" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
            + "".join(paths) + "</svg>" + hub_html + "".join(branches) + "</div>")


def layout_cycle(spec, style, warnings):
    modules = spec["modules"]
    pos = radial_positions(len(modules))
    paths = []
    branches = []
    for i, ((x, y), m) in enumerate(zip(pos, modules)):
        nx, ny = pos[(i + 1) % len(pos)]
        mx, my = (x + nx) / 2, (y + ny) / 2
        paths.append(f'<path d="M{x} {y} Q{mx + (50 - mx) * 0.15} {my + (50 - my) * 0.15} {nx} {ny}" marker-end="url(#arrow)"/>')
        body = f'<p>{esc(m["body"])}</p>' if m.get("body") else ""
        branches.append(
            f'<div class="branch" style="--x:{x:.1f};--y:{y:.1f}">'
            f'{html_icon(m.get("icon"), "icon", warnings)}<h3>{esc(m["title"])}</h3>{body}</div>')
    hub = spec["hub"]
    hub_html = (f'<div class="hub">{html_icon(hub.get("icon"), "icon", warnings)}'
                f'<strong>{esc(hub["title"])}</strong></div>')
    defs = ('<defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">'
            f'<path d="M0 0 L6 3 L0 6 z" fill="{style["colors"]["accent"]}"/></marker></defs>')
    return ('<div class="cycle"><svg class="connectors" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
            + defs + "".join(paths) + "</svg>" + hub_html + "".join(branches) + "</div>")


def layout_stat_cards(spec, style, warnings):
    cards = []
    for m in spec["modules"]:
        unit = f'<small>{esc(m["unit"])}</small>' if m.get("unit") else ""
        delta = ""
        if m.get("delta"):
            cls = "down" if str(m["delta"]).strip().startswith(("-", "↓", "−")) else "up"
            arrow = "↓" if cls == "down" else "↑"
            delta = f'<div class="delta {cls}">{arrow} {esc(m["delta"].lstrip("+-↑↓− "))}</div>'
        body = f'<p class="body">{esc(m["body"])}</p>' if m.get("body") else ""
        cards.append(
            f'<article class="card stat-card"><div class="topline">{html_icon(m.get("icon"), "icon", warnings)}'
            f'<div class="label">{esc(m["label"])}</div></div>'
            f'<div class="value">{esc(m["value"])}{unit}</div>{delta}'
            f'<h3>{esc(m["title"])}</h3>{body}</article>')
    cols = 2 if len(spec["modules"]) <= 4 else 3
    return f'<section class="stat-grid" style="--cols:{cols}">' + "".join(cards) + "</section>"


HTML_LAYOUTS = {
    "list-grid": layout_list_grid,
    "list-row": layout_list_row,
    "sequence-steps": layout_sequence,
    "timeline": layout_timeline,
    "pyramid": layout_pyramid,
    "funnel": layout_funnel,
    "quadrant": layout_quadrant,
    "compare-binary": layout_compare,
    "hierarchy-tree": layout_hierarchy,
    "mindmap": layout_mindmap,
    "cycle": layout_cycle,
    "stat-cards": layout_stat_cards,
}


def render_html(spec: dict, style: dict, warnings: list[str]) -> str:
    layout = spec["layout"]
    body = HTML_LAYOUTS[layout](spec, style, warnings)
    css = build_css(style)
    aria = esc((spec.get("claim") or spec.get("title") or "信息图")[:160])
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(spec['title'])} · 信息图</title>
<style>{css}</style>
</head>
<body class="style-{style['id']} layout-{layout}">
<figure class="poster" role="img" aria-label="{aria}">
{html_header(spec, style, warnings)}
<main class="layout-body">
{body}
</main>
{footer_html(spec)}
</figure>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def list_assets() -> dict:
    return {
        "layouts": [{"id": key, **LAYOUTS[key]} for key in LAYOUT_IDS],
        "styles": [{"id": key, "name_zh": STYLES[key]["name_zh"],
                    "description": STYLES[key]["description"]} for key in STYLE_IDS],
        "icons": {"count": len(ICONS), "version": load_json(ICON_INDEX).get("version"),
                  "license": "ISC"},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="结构化信息图渲染器（12 布局 × 4 风格）")
    ap.add_argument("data", nargs="?", help="JSON 数据文件")
    ap.add_argument("--layout", default=None, help="覆盖 JSON 中的 layout")
    ap.add_argument("--style", default=None, help="覆盖 JSON 中的 style")
    ap.add_argument("--outdir", default="outputs")
    ap.add_argument("--stem", default="infographic")
    ap.add_argument("--formats", default="html,svg", help="逗号分隔：html,svg")
    ap.add_argument("--list", action="store_true", help="列出布局、风格与图标库")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None, help="另存 JSON 报告")
    args = ap.parse_args()

    if args.list or not args.data:
        payload = {"status": "success", "outputs": [], "rows_used": 0, "rows_dropped": 0,
                   "verified": True, "warnings": [], "assets": list_assets()}
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0

    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "infographic": {}}
    warnings: list[str] = result["warnings"]
    try:
        spec_raw = load_json(Path(args.data))
        if not isinstance(spec_raw, dict):
            raise ValueError("数据 JSON 顶层必须是对象")
        layout = args.layout or spec_raw.get("layout") or "list-grid"
        style_id = args.style or spec_raw.get("style") or "editorial"
        spec = normalize_spec(spec_raw, layout, style_id, warnings)
        style = STYLES[style_id]
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
        if not formats or any(f not in ("html", "svg") for f in formats):
            raise ValueError("--formats 仅支持 html,svg")
        if "html" in formats:
            path = outdir / f"{args.stem}.html"
            path.write_text(render_html(spec, style, warnings), encoding="utf-8")
            result["outputs"].append(str(path))
        if "svg" in formats:
            path = outdir / f"{args.stem}.svg"
            path.write_text(infographic_svg.render_svg(spec, style, warnings,
                                                       sys.modules[__name__]), encoding="utf-8")
            result["outputs"].append(str(path))
        result.update({
            "status": "success",
            "rows_used": len(spec["modules"]),
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0
                            for p in result["outputs"]),
            "infographic": {
                "layout": layout,
                "style": style_id,
                "title": spec["title"],
                "modules": len(spec["modules"]),
                "icons_used": sorted({m.get("icon") for m in spec["modules"] if m.get("icon")}),
                "canvas": [infographic_svg.SVG_W, infographic_svg.SVG_H],
                "contrast": spec["_contrast"],
                "source": spec["source"],
                "visual_verified": False,
                "note": "脚本只保证折行与结构；仍需浏览器截图与宿主读图工具目检",
            },
        })
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


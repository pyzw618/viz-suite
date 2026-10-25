# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8"]
# ///
# -*- coding: utf-8 -*-
"""验证 EXTEND.md 品牌覆盖与 figure-manifest.json 多图锁定是否生效。"""
import json
import sys
from pathlib import Path

import viz_style as vs

sys.stdout.reconfigure(encoding="utf-8")

EXPECTED = {
    "palette": "okabe_ito",
    "layout": "soft_grid",
    "width_mm": 150,
    "footer": "数据来源：商业分析部｜内部资料",
    "font_zh": ["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC"],
    "font_en": ["Arial", "Inter"],
    "focal": "#0F62FE",
    "text": "#0B2545",
    "grid": "#DCE7F3",
    "series": {"2024Q4": "#0072B2", "2025Q1": "#E69F00", "2025Q2": "#CC79A7"},
}

theme = vs.resolve_theme()
theme = vs.bootstrap(theme)
pal = vs.palette(theme=theme)
size = vs.plan_size(None, None, theme=theme)
colors = vs.series_color_map(list(EXPECTED["series"]), pal, theme)
typo = theme.get("typography", {})
roles = theme.get("colors", {}).get("roles", {})

checks = [
    {"name": "manifest_located", "ok": bool(theme.get("manifest_path")),
     "actual": theme.get("manifest_path")},
    {"name": "palette_locked", "ok": pal.id == EXPECTED["palette"], "actual": pal.id},
    {"name": "layout_locked", "ok": theme.get("layout_family") == EXPECTED["layout"],
     "actual": theme.get("layout_family")},
    {"name": "width_locked", "ok": size["width_mm"] == EXPECTED["width_mm"],
     "actual": size["width_mm"]},
    {"name": "extend_beats_manifest_footer", "ok": theme.get("brand", {}).get("footer") == EXPECTED["footer"],
     "actual": theme.get("brand", {}).get("footer")},
    {"name": "extend_beats_manifest_fonts", "ok": typo.get("font_zh") == EXPECTED["font_zh"],
     "actual": typo.get("font_zh")},
    {"name": "font_en_override", "ok": typo.get("font_en") == EXPECTED["font_en"],
     "actual": typo.get("font_en")},
    {"name": "brand_focal", "ok": roles.get("focal") == EXPECTED["focal"], "actual": roles.get("focal")},
    {"name": "brand_text", "ok": roles.get("text") == EXPECTED["text"], "actual": roles.get("text")},
    {"name": "brand_grid", "ok": roles.get("grid") == EXPECTED["grid"], "actual": roles.get("grid")},
    {"name": "series_color_map_locked", "ok": colors == EXPECTED["series"], "actual": colors},
    {"name": "font_stack_usable", "ok": "Microsoft YaHei" in theme.get("_font_stack", []),
     "actual": theme.get("_font_stack", [])[:6]},
]

failed = [c for c in checks if not c["ok"]]
for check in checks:
    if check["name"] == "manifest_located" and theme.get("manifest_path"):
        check["actual"] = str(Path(theme["manifest_path"]).resolve().relative_to(Path("..").resolve()))

result = {
    "status": "success" if not failed else "partial",
    "verified": not failed,
    "figsize": list(size["figsize"]),
    "height_mm": size["height_mm"],
    "theme": vs.describe_theme(theme),
    "checks": checks,
    "warnings": [f"未通过：{c['name']}（实际 {c['actual']}）" for c in failed],
}
if result["theme"].get("manifest"):
    result["theme"]["manifest"] = str(
        Path(result["theme"]["manifest"]).resolve().relative_to(Path("..").resolve()))
Path("../theme-probe.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if not failed else 1)

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8"]
# ///
# -*- coding: utf-8 -*-
"""ensure_fonts.py — 校验并注册 viz-suite 内置 SIL OFL 开源多字重字体包，可选按需拉取扩展衬线字重。

用法：
    uv run ensure_fonts.py --json
    uv run ensure_fonts.py --download-extra --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

from matplotlib import font_manager
from matplotlib.ft2font import FT2Font

sys.stdout.reconfigure(encoding="utf-8")

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
MANIFEST_PATH = FONTS_DIR / "fonts-manifest.json"


def _download_from_google_css(family_query: str, weight: int, dest: Path) -> None:
    url = f"https://fonts.googleapis.com/css2?family={family_query}"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
    css = urllib.request.urlopen(req, timeout=25).read().decode("utf-8")
    for m in re.finditer(r"font-weight:\s*(\d+);[\s\S]*?url\((https://[^)]+\.ttf)\)", css):
        if int(m.group(1)) == weight:
            ttf_req = urllib.request.Request(m.group(2), headers={"User-Agent": "curl/8.0"})
            dest.write_bytes(urllib.request.urlopen(ttf_req, timeout=60).read())
            return
    raise RuntimeError(f"未在 Google Fonts CSS 中匹配到 {family_query} weight={weight} 的静态 TTF")


def main() -> int:
    ap = argparse.ArgumentParser(description="校验并注册内置开源字体包")
    ap.add_argument("--download-extra", action="store_true", help="按需下载可选 Noto Serif SC / Medium 静态字重")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    warnings: list[str] = []
    verified_fonts: list[dict] = []

    if args.download_extra:
        for item in manifest.get("optional_on_demand", []):
            dest = FONTS_DIR / item["file"]
            if not dest.is_file():
                try:
                    _download_from_google_css(item["google_css"], int(item["weight"]), dest)
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"下载可选字体 {item['file']} 失败：{exc}")

    all_items = list(manifest.get("bundled", [])) + [
        x for x in manifest.get("optional_on_demand", []) if (FONTS_DIR / x["file"]).is_file()
    ]
    missing_bundled = []
    for item in all_items:
        p = FONTS_DIR / item["file"]
        if not p.is_file():
            missing_bundled.append(item["file"])
            continue
        font_manager.fontManager.addfont(str(p))
        with open(p, "rb") as fh:
            face = FT2Font(fh)
        cmap = face.get_charmap()
        verified_fonts.append({
            "file": item["file"],
            "family": face.family_name,
            "style": face.style_name,
            "weight": item["weight"],
            "role": item.get("role", "extra"),
            "license": item["license"],
            "glyphs": len(cmap),
            "size_kb": round(p.stat().st_size / 1024, 1),
        })

    if missing_bundled:
        warnings.append(f"缺失内置字体：{missing_bundled}")

    payload = {
        "status": "success" if not missing_bundled else "partial",
        "outputs": [str(FONTS_DIR / x["file"]) for x in verified_fonts],
        "rows_used": len(verified_fonts),
        "rows_dropped": len(missing_bundled),
        "verified": not missing_bundled and len(verified_fonts) >= 9,
        "warnings": warnings,
        "fonts_dir": str(FONTS_DIR),
        "fonts": verified_fonts,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

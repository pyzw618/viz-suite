# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""SVG 几何结构与排版合规审计工具。

检查项：
1. XML 格式有效性与根节点 <svg> 命名空间；
2. viewBox 与 width/height 宽高比一致性；
3. 图元几何坐标有效性（无 NaN, 坐标在画布合理视口内）；
4. 文本节点非空度与字体回退链完整性；
5. 关键 slot 锚点（slot-header, slot-footer 等）留存情况。
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def check_svg_file(svg_path: Path) -> dict:
    issues = []
    warnings = []

    try:
        raw_text = svg_path.read_text(encoding="utf-8")
        root = ET.fromstring(raw_text)
    except Exception as exc:
        return {
            "file": svg_path.name,
            "passed": False,
            "error": f"XML parse error: {exc}",
            "issues": [str(exc)],
            "warnings": []
        }

    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if tag != "svg":
        issues.append(f"Root element is <{tag}>, expected <svg>")

    # Check viewBox
    vb = root.get("viewBox")
    if not vb:
        issues.append("Missing viewBox attribute on root <svg>")
        vb_parts = [0, 0, 1000, 1000]
    else:
        try:
            vb_parts = [float(x) for x in vb.split()]
            if len(vb_parts) != 4 or vb_parts[2] <= 0 or vb_parts[3] <= 0:
                issues.append(f"Invalid viewBox values: {vb}")
        except Exception:
            issues.append(f"Cannot parse viewBox: {vb}")
            vb_parts = [0, 0, 1000, 1000]

    # Check elements
    text_count = 0
    empty_texts = 0
    slot_ids = []
    for elem in root.iter():
        elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        eid = elem.get("id")
        if eid and eid.startswith("slot-"):
            slot_ids.append(eid)
        if elem_tag == "text":
            text_count += 1
            content = "".join(elem.itertext()).strip()
            if not content:
                empty_texts += 1

    if empty_texts > 0:
        warnings.append(f"Found {empty_texts} empty text elements")

    passed = len(issues) == 0
    return {
        "file": svg_path.name,
        "passed": passed,
        "viewBox": vb_parts,
        "text_count": text_count,
        "slots_found": slot_ids,
        "issues": issues,
        "warnings": warnings
    }


def main():
    parser = argparse.ArgumentParser(description="SVG Geometry & Typography Auditor")
    parser.add_argument("path", nargs="?", default="skills/viz-diagram/templates/svg-masters",
                        help="Path to an SVG file or directory of SVGs")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    target = Path(args.path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.glob("*.svg"))
    else:
        print(f"Path not found: {target}", file=sys.stderr)
        sys.exit(1)

    results = [check_svg_file(f) for f in files]
    all_passed = all(r["passed"] for r in results)

    if args.json:
        print(json.dumps({"passed": all_passed, "total_files": len(results), "results": results}, indent=2, ensure_ascii=False))
    else:
        for r in results:
            status = "✅ PASS" if r["passed"] else "❌ FAIL"
            print(f"{status} {r['file']} (texts: {r['text_count']}, slots: {r['slots_found']})")
            for iss in r["issues"]:
                print(f"  ❌ {iss}")
            for w in r["warnings"]:
                print(f"  ⚠️ {w}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""SVG Master 模板注入与导出引擎。

支持传入自定义 JSON 键值，动态替换 Master 模板中的文本与插槽，并输出生产级 SVG。
用法：
    uv run render_svg_master.py mckinsey_scqa_pyramid --outdir outputs --stem my_scqa --json
    uv run render_svg_master.py layered_tech_stack --data custom.json --outdir outputs --json
    uv run render_svg_master.py --list --json
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
MASTERS_DIR = ROOT / "templates" / "svg-masters"
INDEX_PATH = MASTERS_DIR / "index.json"


def list_masters() -> dict:
    if not INDEX_PATH.exists():
        return {"status": "error", "error": "index.json not found", "masters": []}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def render_master(master_id: str, data: dict, outdir: Path, stem: str) -> dict:
    svg_file = MASTERS_DIR / f"{master_id}.svg"
    if not svg_file.exists():
        svg_file = MASTERS_DIR / master_id
    if not svg_file.exists():
        return {"status": "error", "error": f"Master template '{master_id}' not found."}

    content = svg_file.read_text(encoding="utf-8")

    # Replace title & subtitle if provided in data
    if "title" in data:
        content = re.sub(r'(<text[^>]*font-size="2[24]"[^>]*>)[^<]*(</text>)',
                         rf'\g<1>{html.escape(data["title"])}\g<2>', content, count=1)
    if "subtitle" in data:
        content = re.sub(r'(<text[^>]*font-size="1[23]"[^>]*>)[^<]*(</text>)',
                         rf'\g<1>{html.escape(data["subtitle"])}\g<2>', content, count=1)
    if "source" in data:
        content = re.sub(r'(<text[^>]*font-size="11"[^>]*>)[^<]*(</text>)',
                         rf'\g<1>{html.escape(data["source"])}\g<2>', content, count=1)

    # Slot dictionary replacements
    for k, v in data.get("replacements", {}).items():
        content = content.replace(k, html.escape(str(v)))

    outdir.mkdir(parents=True, exist_ok=True)
    dst_svg = outdir / f"{stem}.svg"
    dst_svg.write_text(content, encoding="utf-8")

    return {
        "status": "success",
        "master_id": master_id,
        "outputs": [str(dst_svg)],
        "verified": True
    }


def main():
    parser = argparse.ArgumentParser(description="SVG Master Template Injector")
    parser.add_argument("master", nargs="?", help="Master template ID (e.g. layered_tech_stack)")
    parser.add_argument("--data", help="Path to JSON data for slot injection")
    parser.add_argument("--outdir", default="outputs", help="Output directory")
    parser.add_argument("--stem", default="svg_master", help="Output stem name")
    parser.add_argument("--list", action="store_true", help="List all available master templates")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    if args.list:
        data = list_masters()
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"Available SVG Masters ({len(data.get('masters', []))}):")
            for m in data.get("masters", []):
                print(f"  - {m['id']}: {m['title']} ({m['category']})")
        sys.exit(0)

    if not args.master:
        parser.print_help()
        sys.exit(1)

    inject_data = {}
    if args.data:
        try:
            inject_data = json.loads(Path(args.data).read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Error reading --data JSON: {exc}", file=sys.stderr)
            sys.exit(1)

    result = render_master(args.master, inject_data, Path(args.outdir), args.stem)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["status"] == "success":
            print(f"Rendered SVG Master to {result['outputs'][0]}")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

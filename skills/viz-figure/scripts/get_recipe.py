# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""按配方 ID 拉取黄金底稿、共享视觉库与资产到工作区。

用法：
    uv run get_recipe.py --list --json
    uv run get_recipe.py --id raincloud_fusion --dest ./viz-work --json
    uv run get_recipe.py --id grouped_errorbar_bar --dest . --force
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SKILL_ROOT = Path(__file__).resolve().parent.parent
CATALOG = SKILL_ROOT / "catalog" / "selection-index.jsonl"
RECIPES = SKILL_ROOT / "recipes"
SHARED = Path(__file__).resolve().parent / "viz_style.py"


def load_index() -> list[dict]:
    if not CATALOG.is_file():
        return []
    entries = []
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def locate_assets() -> list[Path]:
    here = Path(__file__).resolve()
    candidates = []
    for base in [here.parent, *here.parents, Path.cwd(), *Path.cwd().parents]:
        for cand in (base / "skills" / "shared" / "assets", base / "shared" / "assets",
                     base / "skills" / "viz-core" / "assets", base / "viz-core" / "assets",
                     base / ".viz-suite" / "assets", base / "assets"):
            if (cand / "tokens.json").is_file() and (cand / "palettes.json").is_file():
                if cand not in candidates:
                    candidates.append(cand)
    return candidates


def main() -> int:
    ap = argparse.ArgumentParser(description="配方拉取器（viz-figure）")
    ap.add_argument("--list", action="store_true", help="列出全部配方")
    ap.add_argument("--id", help="配方 ID")
    ap.add_argument("--dest", default="./viz-work", help="工作区目录（默认 ./viz-work）")
    ap.add_argument("--force", action="store_true", help="覆盖已存在文件")
    ap.add_argument("--no-assets", action="store_true", help="不复制 tokens/palettes")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    entries = load_index()
    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "recipe": None}

    if args.list or not args.id:
        result["status"] = "success" if entries else "partial"
        result["verified"] = bool(entries)
        result["recipes"] = [
            {k: e.get(k) for k in ("id", "title_zh", "family", "series_limit", "preview", "keywords")}
            for e in entries
        ]
        if not entries:
            result["warnings"].append(f"未找到配方索引：{CATALOG}")
        if args.json or not sys.stdout.isatty():
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for e in result["recipes"]:
                print(f"{e['id']:<26} {e['title_zh']}  [系列≤{e['series_limit']}]")
        return 0 if entries else 2

    entry = next((e for e in entries if e["id"] == args.id), None)
    if entry is None:
        result["warnings"].append(f"未知配方 {args.id}；可用：{[e['id'] for e in entries]}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    recipe_path = SKILL_ROOT / entry["recipe"]
    if not recipe_path.is_file() or not SHARED.is_file():
        result["warnings"].append(f"底稿或共享库缺失：{recipe_path} / {SHARED}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    jobs = [(recipe_path, dest / recipe_path.name), (SHARED, dest / "viz_style.py")]
    assets_written: list[str] = []
    if not args.no_assets:
        assets = locate_assets()
        if assets:
            target = dest / ".viz-suite" / "assets"
            target.mkdir(parents=True, exist_ok=True)
            jobs += [(assets[0] / "tokens.json", target / "tokens.json"),
                     (assets[0] / "palettes.json", target / "palettes.json")]
            scenes_src = assets[0] / "scenes"
            if scenes_src.is_dir():
                scenes_dst = target / "scenes"
                scenes_dst.mkdir(parents=True, exist_ok=True)
                for sp in sorted(scenes_src.glob("*.json")):
                    jobs.append((sp, scenes_dst / sp.name))
        else:
            result["warnings"].append("未找到 shared/assets，已跳过资产复制；viz_style 将使用内置回退令牌")

    for src, dst in jobs:
        if dst.exists() and not args.force:
            result["warnings"].append(f"已存在，跳过（--force 可覆盖）：{dst}")
            continue
        shutil.copy2(src, dst)
        result["outputs"].append(str(dst))
        if dst.parent.name == "assets":
            assets_written.append(str(dst))

    card = SKILL_ROOT / entry.get("card", "")
    result.update({
        "status": "success",
        "verified": all(Path(p).is_file() for p in result["outputs"]),
        "recipe": {
            "id": entry["id"],
            "title_zh": entry.get("title_zh"),
            "script": str(dest / recipe_path.name),
            "card": str(card) if card.is_file() else None,
            "preview": str(SKILL_ROOT / entry.get("preview", "")) if entry.get("preview") else None,
            "params_hint": entry.get("params_hint", {}),
        },
    })
    if not card.is_file():
        result["warnings"].append(f"保真卡片缺失：{card}")

    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"配方 {entry['id']} → {dest}")
        print(f"  脚本: {dest / recipe_path.name}")
        print(f"  卡片: {card}")
        for w in result["warnings"]:
            print("  警告:", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.7"]
# ///
# -*- coding: utf-8 -*-
"""扫描本机可用中英文字体，输出不会出现方块乱码的 rcParams。

用法：
    uv run detect_fonts.py --json
    uv run detect_fonts.py --json --sample-text "数据可视化报告"
    uv run detect_fonts.py --list          # 只看检测结果
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
from matplotlib import font_manager
from matplotlib.ft2font import FT2Font

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT_ZH = [
    "Noto Sans SC", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Source Han Sans SC",
    "HarmonyOS Sans SC", "SimHei", "Source Han Sans CN", "WenQuanYi Zen Hei",
    "Microsoft JhengHei", "DengXian", "SimSun", "STSong", "Songti SC", "Noto Serif CJK SC",
]
DEFAULT_EN = ["Inter", "Arial", "Helvetica", "Segoe UI", "Roboto", "DejaVu Sans"]
SERIF_ZH = ["Noto Serif SC", "IBM Plex Serif", "Source Han Serif SC", "Noto Serif CJK SC", "SimSun", "STSong", "Songti SC", "serif"]
TEST_ZH = "数据可视化图表样本量均值中位数显著"
TEST_EN = "ABCDEFGabcdefg0123456789-%"


def register_bundled_fonts() -> list[str]:
    here = Path(__file__).resolve().parent
    added: list[str] = []
    seen_dirs: set[Path] = set()
    for base in [Path.cwd(), *Path.cwd().parents, here, *here.parents]:
        for cand in (base / ".viz-suite" / "assets" / "fonts",
                     base / "skills" / "shared" / "assets" / "fonts",
                     base / "shared" / "assets" / "fonts"):
            if cand.is_dir():
                resolved = cand.resolve()
                if resolved in seen_dirs:
                    continue
                seen_dirs.add(resolved)
                for fp in sorted(resolved.glob("*.ttf")):
                    try:
                        n_before = len(font_manager.fontManager.ttflist)
                        font_manager.fontManager.addfont(str(fp))
                        if len(font_manager.fontManager.ttflist) > n_before:
                            entry = font_manager.fontManager.ttflist.pop()
                            font_manager.fontManager.ttflist.insert(0, entry)
                        added.append(str(fp))
                    except Exception:  # noqa: BLE001
                        pass
    if added and hasattr(font_manager.fontManager, "_findfont_cached"):
        font_manager.fontManager._findfont_cached.cache_clear()
    return added


def _norm_weight(weight) -> int:
    if isinstance(weight, (int, float)):
        return int(weight)
    s = str(weight).strip().lower()
    if s in ("normal", "regular", "book"):
        return 400
    if s == "medium":
        return 500
    if s in ("semibold", "demibold"):
        return 600
    if s == "bold":
        return 700
    try:
        return int(s)
    except ValueError:
        return 400


def load_font_candidates() -> tuple[list[str], list[str], list[str]]:
    """优先读取 shared/assets/tokens.json 的字体栈，找不到则用内置清单。"""
    here = Path(__file__).resolve().parent
    for base in [Path.cwd(), *Path.cwd().parents, here, *here.parents]:
        for cand in (base / ".viz-suite" / "assets", base / "skills" / "shared" / "assets",
                     base / "shared" / "assets", base / "skills" / "viz-core" / "assets",
                     base / "viz-core" / "assets", base / "assets"):
            path = cand / "tokens.json"
            if path.is_file():
                try:
                    typo = json.loads(path.read_text(encoding="utf-8")).get("typography", {})
                    return (typo.get("font_zh") or DEFAULT_ZH,
                            typo.get("font_en") or DEFAULT_EN,
                            typo.get("font_serif_zh") or SERIF_ZH)
                except json.JSONDecodeError:
                    pass
    return DEFAULT_ZH, DEFAULT_EN, SERIF_ZH


def font_records(names: list[str]) -> list[dict]:
    by_name: dict[str, list] = {}
    for entry in font_manager.fontManager.ttflist:
        by_name.setdefault(entry.name, []).append(entry)
    records = []
    for name in names:
        entries = by_name.get(name)
        if not entries:
            continue
        entry = min(
            entries,
            key=lambda e: (
                e.style != "normal",
                abs(_norm_weight(e.weight) - 400),
                any(tag in Path(e.fname).name.lower() for tag in ("narrow", "cond", "arialn")),
            ),
        )
        record = {"name": name, "file": entry.fname, "style": entry.style, "weight": entry.weight}
        try:
            with open(entry.fname, "rb") as fh:
                face = FT2Font(fh)
            cmap = face.get_charmap()
            missing_zh = sorted({ch for ch in TEST_ZH if ord(ch) not in cmap})
            missing_en = sorted({ch for ch in TEST_EN if ord(ch) not in cmap})
            record["missing_zh"] = missing_zh
            record["missing_en"] = missing_en
            record["covers_zh"] = not missing_zh
            record["covers_en"] = not missing_en
            record["glyph_count"] = len(cmap)
        except Exception as exc:  # noqa: BLE001
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["covers_zh"] = False
            record["covers_en"] = False
        records.append(record)
    return records


def main() -> int:
    ap = argparse.ArgumentParser(description="字体探测（viz-python）")
    ap.add_argument("--json", action="store_true", help="输出标准 JSON 协议")
    ap.add_argument("--list", action="store_true", help="列出全部候选字体与覆盖情况")
    ap.add_argument("--sample-text", default=TEST_ZH, help="额外校验的样本文本")
    ap.add_argument("--out", default=None, help="另存 JSON 到文件")
    args = ap.parse_args()

    bundled = register_bundled_fonts()
    zh_names, en_names, serif_names = load_font_candidates()
    zh = font_records(zh_names)
    en = font_records(en_names)
    serif = font_records(serif_names)

    sample_missing: dict[str, list[str]] = {}
    for rec in zh:
        if "file" not in rec:
            continue
        try:
            with open(rec["file"], "rb") as fh:
                cmap = FT2Font(fh).get_charmap()
            missing = sorted({ch for ch in args.sample_text if ord(ch) not in cmap})
            if missing:
                sample_missing[rec["name"]] = missing
        except Exception:  # noqa: BLE001
            continue

    good_zh = [r["name"] for r in zh if r.get("covers_zh")]
    good_en = [r["name"] for r in en if r.get("covers_en")]
    warnings: list[str] = []
    if not good_zh:
        warnings.append("未找到完整覆盖常用汉字的字体：中文将出现方块，请安装 Microsoft YaHei / Noto Sans CJK SC")
    if not good_en:
        warnings.append("未找到完整覆盖拉丁字母的字体，已回退 DejaVu Sans")
    if sample_missing:
        warnings.append(f"以下字体缺少样本文本中的字形：{sample_missing}")

    stack = (good_en or ["DejaVu Sans"]) + (good_zh or ["SimHei"]) + ["DejaVu Sans", "sans-serif"]
    stack = list(dict.fromkeys(stack))
    rc = {
        # 有序列表才能触发按字形回退；仅写 "sans-serif" 时中文会变成方块
        "font.family": stack,
        "font.sans-serif": stack,
        "font.serif": [r["name"] for r in serif if r.get("covers_zh")] + ["DejaVu Serif"],
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    }
    result = {
        "status": "success" if good_zh else "partial",
        "outputs": [],
        "rows_used": 0,
        "rows_dropped": 0,
        "verified": bool(good_zh and good_en),
        "warnings": warnings,
        "recommended": {"zh": good_zh[0] if good_zh else None,
                        "en": good_en[0] if good_en else "DejaVu Sans"},
        "rcParams": rc,
        "fonts": {"zh": zh, "en": en, "serif_zh": serif},
        "sample_text": args.sample_text,
        "sample_missing": sample_missing,
        "matplotlib": matplotlib.__version__,
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
        print(f"matplotlib {matplotlib.__version__}")
        print(f"可用中文字体: {', '.join(good_zh) or '无'}")
        print(f"可用英文字体: {', '.join(good_en) or '无'}")
        if args.list:
            for group, records in (("ZH", zh), ("EN", en), ("SERIF", serif)):
                for r in records:
                    status = "✓" if r.get("covers_zh", r.get("covers_en")) else "✗"
                    print(f"  [{group}] {status} {r['name']}  {r.get('file', '')}")
        for w in warnings:
            print("警告:", w)
    return 0 if result["status"] != "error" else 2


if __name__ == "__main__":
    raise SystemExit(main())

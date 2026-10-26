# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""静态 AST 比对黄金底稿与适配脚本，提供非阻断式样式保真审查线索（Review Hints）。

设计原则（P0 升级）：
    真实业务数据往往需要改写数据聚合管道、调整分类方向（如 bar ↔ barh）、裁剪无数据支撑的条件参考线或子面板。
    因此默认模式仅输出只读审查线索（exit code = 0），绝不一票否决合理的业务结构适配；
    仅当显式传入 --strict 时才将 warning/hint 作为非零退出码用于严格回归测试。

用法：
    uv run check_recipe_fidelity.py --base recipes/raincloud_fusion.py --adapted viz-work/raincloud_fusion.py --json
    uv run check_recipe_fidelity.py --base X.py --adapted Y.py --strict

判定分级：
    warning = 疑似误删核心初始化或引入高风险反模式（如丢失 bootstrap、引入 jet/rainbow 彩虹色阶、残留 plt.show）
    hint    = 图层或样式参数相对底稿发生变化（供多模态审图核对：属合理数据适配可保留，属误删微质感请恢复）
    info    = 适配脚本新增的样式特征
"""
import argparse
import ast
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BANNED_CMAPS = {"jet", "rainbow", "hsv", "gist_rainbow", "nipy_spectral"}

STYLE_KEYS = {
    "alpha", "color", "colors", "edgecolor", "facecolor", "linewidth", "linewidths",
    "linestyle", "marker", "markersize", "s", "capsize", "elinewidth", "capthick",
    "zorder", "width", "height", "hatch", "fill", "where", "density", "bins",
    "histtype", "orientation", "stacked", "style", "ec", "fc", "lw", "ls", "ms",
}
LAYER_CALLS = {
    "fill_between", "fill_betweenx", "errorbar", "violinplot", "boxplot", "scatter",
    "bar", "barh", "plot", "stackplot", "contourf", "pcolormesh", "imshow",
    "axhline", "axvline", "axhspan", "axvspan", "pie", "annotate",
}
IGNORED_FUNCS = {"savefig", "set", "update", "rcParams", "subplots"}


def call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def literal(value: ast.AST):
    try:
        raw = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return "<expr>"
    if isinstance(raw, float):
        return round(raw, 4)
    if isinstance(raw, (list, tuple)):
        return tuple(literal(ast.Constant(v)) for v in raw)
    if isinstance(raw, dict):
        return tuple(sorted((str(k), v) for k, v in raw.items()))
    return raw


def collect(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    features: Counter = Counter()
    layers: Counter = Counter()
    styles_by_key: dict[tuple[str, str], list] = {}
    has_bootstrap = False
    has_plt_show = False
    banned_cmaps: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node.func)
        if name == "bootstrap":
            has_bootstrap = True
        elif name == "show":
            has_plt_show = True
        if not name or name in IGNORED_FUNCS:
            continue
        if name in LAYER_CALLS:
            layers[name] += 1
        kwargs = {}
        for kw in node.keywords:
            if kw.arg == "cmap":
                cval = literal(kw.value)
                if isinstance(cval, str) and cval.lower() in BANNED_CMAPS:
                    banned_cmaps.add(cval)
            if kw.arg is None or kw.arg not in STYLE_KEYS:
                continue
            val = literal(kw.value)
            kwargs[kw.arg] = val
            features[(name, kw.arg, str(val))] += 1
            styles_by_key.setdefault((name, kw.arg), []).append(val)
    return {
        "features": features,
        "layers": layers,
        "styles_by_key": styles_by_key,
        "n_style_args": sum(features.values()),
        "has_bootstrap": has_bootstrap,
        "has_plt_show": has_plt_show,
        "banned_cmaps": sorted(banned_cmaps),
    }


def diff(base: dict, adapted: dict) -> dict:
    missing = []
    for feat, count in base["features"].items():
        have = adapted["features"].get(feat, 0)
        if have < count:
            missing.extend([feat] * (count - have))
    added = []
    for feat, count in adapted["features"].items():
        have = base["features"].get(feat, 0)
        if count > have:
            added.extend([feat] * (count - have))
    missing_layers = {k: v - adapted["layers"].get(k, 0)
                      for k, v in base["layers"].items() if v > adapted["layers"].get(k, 0)}

    changed = []
    for key, base_vals in base["styles_by_key"].items():
        if key not in adapted["styles_by_key"]:
            continue
        base_lit = [v for v in base_vals if v != "<expr>"]
        new_lit = [v for v in adapted["styles_by_key"][key] if v != "<expr>"]
        if base_lit and new_lit and Counter(base_lit) != Counter(new_lit):
            changed.append({"call": key[0], "arg": key[1],
                            "base": [str(v) for v in base_lit],
                            "adapted": [str(v) for v in new_lit]})
    return {
        "missing_features": [{"call": c, "arg": a, "value": v} for c, a, v in missing],
        "added_features": [{"call": c, "arg": a, "value": v} for c, a, v in added],
        "missing_layers": missing_layers,
        "changed_values": changed,
    }


def verdict(base: dict, adapted: dict, d: dict) -> tuple[str, list[dict]]:
    issues: list[dict] = []
    if base["has_bootstrap"] and not adapted["has_bootstrap"]:
        issues.append({"severity": "warning", "code": "bootstrap_removed",
                       "detail": "适配脚本移除了 viz_style.bootstrap()，中文字体栈与全局 rcParams 可能失效"})
    if adapted["banned_cmaps"]:
        issues.append({"severity": "warning", "code": "banned_cmap",
                       "detail": f"检测到禁用彩虹色阶 {adapted['banned_cmaps']}，请改用 sequential_cmap / diverging_cmap / viridis"})
    if adapted["has_plt_show"]:
        issues.append({"severity": "warning", "code": "interactive_show",
                       "detail": "检测到 plt.show()，无头批处理环境可能阻塞"})

    for layer, gap in d["missing_layers"].items():
        issues.append({
            "severity": "hint",
            "code": "layer_adapted",
            "detail": (f"图层调用 {layer} 减少 {gap} 次（审查线索：若因真实数据无对应分组/参考线"
                       f"或方向切换如 bar↔barh 所致可保留；若误删核心微质感层请恢复）"),
        })
    for item in d["changed_values"]:
        if item["arg"] in ("alpha", "linewidth", "edgecolor", "facecolor", "elinewidth", "capthick", "markersize"):
            issues.append({
                "severity": "hint",
                "code": "style_value_changed",
                "detail": f"{item['call']}({item['arg']}) 由 {item['base']} 调整为 {item['adapted']}（请结合成图确认视觉层次）",
            })
    n_base = max(base["n_style_args"], 1)
    lost = len(d["missing_features"])
    if lost / n_base > 0.4:
        issues.append({
            "severity": "hint",
            "code": "style_loss_large",
            "detail": f"样式字面参数变化较大（差异 {lost}/{n_base}）：若重写了绘图结构，请重点目检填充描边与留白层次",
        })
    elif lost:
        issues.append({
            "severity": "hint",
            "code": "style_loss",
            "detail": f"样式字面参数差异 {lost}/{n_base}，属只读审查线索",
        })

    if issues:
        return "review_hints", issues
    return "pass", issues


def main() -> int:
    ap = argparse.ArgumentParser(description="底稿样式保真非阻断审查线索（viz-python）")
    ap.add_argument("--base", required=True, help="原始黄金底稿路径")
    ap.add_argument("--adapted", required=True, help="适配后脚本路径")
    ap.add_argument("--strict", action="store_true", help="严格回归模式：存在 warning/hint 时返回非零退出码")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "report": None}
    base_path, adapted_path = Path(args.base), Path(args.adapted)
    for path in (base_path, adapted_path):
        if not path.is_file():
            result["warnings"].append(f"文件不存在：{path}")
    if result["warnings"]:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    try:
        base = collect(base_path)
        adapted = collect(adapted_path)
    except SyntaxError as exc:
        result["warnings"].append(f"语法错误：{exc}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    d = diff(base, adapted)
    status, issues = verdict(base, adapted, d)
    result.update({
        "status": "success",
        "verified": True,
        "non_blocking": not args.strict,
        "verdict": status,
        "report": {
            "note": "所有 AST 差异仅作审查线索（Review Hints），合理的业务数据管道与布局适配无需回退。",
            "base": str(base_path),
            "adapted": str(adapted_path),
            "base_style_args": base["n_style_args"],
            "adapted_style_args": adapted["n_style_args"],
            "base_layers": dict(base["layers"]),
            "adapted_layers": dict(adapted["layers"]),
            "missing_layers": d["missing_layers"],
            "missing_features": d["missing_features"][:40],
            "added_features": d["added_features"][:40],
            "changed_values": d["changed_values"],
            "issues": issues,
        },
    })
    result["warnings"] = [i["detail"] for i in issues if i["severity"] == "warning"]
    result["hints"] = [i["detail"] for i in issues if i["severity"] == "hint"]

    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"审查结果：{status}（非阻断线索模式）")
        print(f"样式参数 {base['n_style_args']} → {adapted['n_style_args']}")
        for i in issues:
            print(f"  [{i['severity']}] {i['detail']}")
        if status == "pass":
            print("  底稿图层与样式特征完整一致")

    if args.strict and issues:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

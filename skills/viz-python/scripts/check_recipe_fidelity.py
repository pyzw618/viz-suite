# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""静态 AST 比对黄金底稿与适配脚本，核查透明度层、描边与图层调用是否误丢。

用法：
    uv run check_recipe_fidelity.py --base recipes/raincloud_fusion.py --adapted viz-work/raincloud_fusion.py --json
    uv run check_recipe_fidelity.py --base X.py --adapted Y.py --strict

判定：
    blocking = 关键图层调用消失（例如 fill_between / errorbar / violinplot / scatter）
    warning  = 样式参数键丢失或数值被改写（alpha / edgecolor / linewidth / marker ...）
    info     = 适配脚本新增的样式特征
"""
import argparse
import ast
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

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
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node.func)
        if not name or name in IGNORED_FUNCS:
            continue
        if name in LAYER_CALLS:
            layers[name] += 1
        kwargs = {}
        for kw in node.keywords:
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


def verdict(base: dict, d: dict) -> tuple[str, list[dict]]:
    issues: list[dict] = []
    for layer, gap in d["missing_layers"].items():
        issues.append({"severity": "blocking", "code": "layer_missing",
                       "detail": f"图层调用 {layer} 减少 {gap} 次：底稿的核心编码可能被删除"})
    for item in d["changed_values"]:
        if item["arg"] in ("alpha", "linewidth", "edgecolor", "facecolor", "elinewidth", "capthick", "markersize"):
            issues.append({"severity": "warning", "code": "style_value_changed",
                           "detail": f"{item['call']}({item['arg']}) 由 {item['base']} 改为 {item['adapted']}"})
    n_base = max(base["n_style_args"], 1)
    lost = len(d["missing_features"])
    if lost / n_base > 0.4:
        issues.append({"severity": "blocking", "code": "style_loss",
                       "detail": f"样式参数丢失 {lost}/{n_base}（>40%）：可能整段样式被删"})
    elif lost:
        issues.append({"severity": "warning", "code": "style_loss",
                       "detail": f"样式参数丢失 {lost}/{n_base}，请逐项确认是否为有意简化"})
    if any(i["severity"] == "blocking" for i in issues):
        return "fail", issues
    if issues:
        return "review", issues
    return "pass", issues


def main() -> int:
    ap = argparse.ArgumentParser(description="底稿样式保真 AST 比对（viz-python）")
    ap.add_argument("--base", required=True, help="原始黄金底稿路径")
    ap.add_argument("--adapted", required=True, help="适配后脚本路径")
    ap.add_argument("--strict", action="store_true", help="warning 也返回非零退出码")
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
    status, issues = verdict(base, d)
    result.update({
        "status": "success",
        "verified": True,
        "verdict": status,
        "report": {
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
    result["warnings"] = [i["detail"] for i in issues if i["severity"] != "info"]

    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"判定：{status}")
        print(f"样式参数 {base['n_style_args']} → {adapted['n_style_args']}")
        for i in issues:
            print(f"  [{i['severity']}] {i['detail']}")
        if status == "pass":
            print("  底稿图层与样式特征完整保留")

    if status == "fail":
        return 1
    if args.strict and issues:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

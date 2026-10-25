# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas>=2.0", "numpy>=1.24", "openpyxl>=3.1", "xlrd>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""轻量数据画像：把大表压成 <100 行 JSON，供 viz-core 选型使用。

用法：
    uv run profile_data.py data.csv --json
    uv run profile_data.py data.xlsx --sheet 明细 --json --out profile.json
    uv run profile_data.py data.csv              # 人读摘要

输出协议（PLAN.md §3.4）：
    {"status": "success|partial|error", "outputs": [], "rows_used": n,
     "rows_dropped": n, "verified": bool, "warnings": [...], "profile": {...}}
"""
import argparse
import json
import re
import sys
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5", "latin-1")
DATE_HINTS = ("date", "time", "day", "month", "year", "日期", "时间", "月", "年", "季度", "周")
ID_HINTS = ("id", "编号", "代码", "code", "key", "uuid")
QUARTER_RE = re.compile(r"^\d{4}\s*[Qq][1-4]$")
YEAR_RE = re.compile(r"^(19|20)\d{2}\s*年?$")


def display_units(text: str) -> int:
    """中文/全角按 2 个字符宽度计，用于预判标签空间。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in str(text))


def detect_encoding(path: Path) -> tuple[str, str | None]:
    raw = path.open("rb").read(65536)
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16", None
    for enc in ENCODINGS:
        text = None
        # 64KB 切片可能截断多字节字符：最多回退 4 字节再试，而不是 ignore 掉非法字节
        for trim in range(0, 5):
            chunk = raw if trim == 0 else raw[:-trim]
            try:
                text = chunk.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            continue
        if enc == "latin-1" and any(0x80 <= b <= 0xFF for b in raw):
            continue
        if enc.startswith("utf-8"):
            return enc, None
        # 非 UTF 编码必须能解出汉字，避免把西文 cp1252 误判为 GB18030
        if any(unicodedata.east_asian_width(ch) in ("W", "F") for ch in text):
            return enc, None
        continue
    return "latin-1", "无法可靠识别编码，已回退 latin-1；中文字段可能出现乱码"


def read_table(path: Path, sheet: str | None, max_rows: int | None) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    suffix = path.suffix.lower()
    if suffix in (".csv", ".txt", ".tsv"):
        enc, warn = detect_encoding(path)
        if warn:
            warnings.append(warn)
        sep = "\t" if suffix == ".tsv" else None
        try:
            df = pd.read_csv(path, encoding=enc, sep=sep, engine="python", nrows=max_rows)
        except Exception:
            df = pd.read_csv(path, encoding=enc, sep=sep, engine="python", nrows=max_rows,
                             on_bad_lines="skip")
            warnings.append("存在无法解析的畸形行，已跳过（on_bad_lines=skip）")
        df.attrs["encoding"] = enc
    elif suffix in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path, sheet_name=sheet or 0, nrows=max_rows)
        df.attrs["sheet"] = sheet or 0
    elif suffix == ".json":
        df = pd.read_json(path)
    else:
        raise ValueError(f"暂不支持的文件类型：{suffix}（支持 csv/tsv/xlsx/xls/json）")
    return df, warnings


def infer_kind(series: pd.Series, name: str) -> tuple[str, bool]:
    """返回 (kind, numeric_text)。kind ∈ numeric / datetime / boolean / categorical / text。"""
    if pd.api.types.is_bool_dtype(series):
        return "boolean", False
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime", False
    if pd.api.types.is_numeric_dtype(series):
        return "numeric", False

    s = series.dropna().astype(str)
    if s.empty:
        return "text", False
    sample = s.head(500)
    lowered = name.lower()

    num = pd.to_numeric(sample.str.replace(",", "", regex=False), errors="coerce")
    if num.notna().mean() >= 0.9 and num.dropna().nunique() >= 3:
        return "numeric", True

    # 季度/年份标签是有序分类，不是连续时间戳（避免把 2025Q1 解析成日期）
    if sample.map(lambda v: bool(QUARTER_RE.match(str(v).strip()))).mean() >= 0.9:
        return "categorical", False
    if sample.map(lambda v: bool(YEAR_RE.match(str(v).strip()))).mean() >= 0.9:
        return "categorical", False

    if any(h in lowered for h in DATE_HINTS):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        if parsed.notna().mean() >= 0.9:
            return "datetime", False
    return ("categorical" if s.nunique() <= 50 else "text"), False


def numeric_stats(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {}
    q = s.quantile([0.01, 0.25, 0.5, 0.75, 0.99]).round(4)
    iqr = float(q.loc[0.75] - q.loc[0.25])
    lo, hi = float(q.loc[0.25] - 1.5 * iqr), float(q.loc[0.75] + 1.5 * iqr)
    outliers = int(((s < lo) | (s > hi)).sum())
    return {
        "min": round(float(s.min()), 4),
        "p01": float(q.loc[0.01]),
        "q1": float(q.loc[0.25]),
        "median": float(q.loc[0.5]),
        "mean": round(float(s.mean()), 4),
        "q3": float(q.loc[0.75]),
        "p99": float(q.loc[0.99]),
        "max": round(float(s.max()), 4),
        "std": round(float(s.std(ddof=1)), 4) if len(s) > 1 else 0.0,
        "skew": round(float(s.skew()), 3) if len(s) > 2 else None,
        "zeros": int((s == 0).sum()),
        "negatives": int((s < 0).sum()),
        "outlier_share": round(outliers / len(s), 4),
    }


def column_profile(series: pd.Series, name: str, top_k: int = 5) -> tuple[dict, list[str]]:
    # 局部告警列表用 warns，避免遮蔽标准库 warnings 模块（datetime 分支需要它）
    warns: list[str] = []
    n = len(series)
    kind, numeric_text = infer_kind(series, name)
    miss = int(series.isna().sum())
    info: dict = {
        "name": name,
        "kind": kind,
        "missing": miss,
        "missing_rate": round(miss / n, 4) if n else 0.0,
        "unique": int(series.nunique(dropna=True)),
    }
    if numeric_text:
        info["numeric_text"] = True
        warns.append(f"列「{name}」的数值以文本存储，统计前已强制转换；交付时应在图注说明清洗口径")
    if miss / n > 0.30 if n else False:
        warns.append(f"列「{name}」缺失率 {miss / n:.0%}，超过 30%：需确认剔除口径或改用可用样本量标注")

    if kind == "numeric":
        info.update(numeric_stats(series))
        if info.get("unique", 0) <= 8:
            info["small_integer_set"] = sorted(
                {round(float(v), 4) for v in pd.to_numeric(series, errors="coerce").dropna().unique()}
            )[:8]
    elif kind == "datetime":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = pd.to_datetime(series, errors="coerce", format="mixed")
        info["min"] = str(parsed.min())[:19]
        info["max"] = str(parsed.max())[:19]
    else:
        s = series.dropna().astype(str)
        lengths = s.map(len)
        units = s.map(display_units)
        info["max_label_chars"] = int(lengths.max()) if len(s) else 0
        info["max_label_units"] = int(units.max()) if len(s) else 0
        info["median_label_units"] = float(units.median()) if len(s) else 0.0
        info["top_values"] = [
            {"value": str(v)[:40], "count": int(c)} for v, c in series.value_counts().head(top_k).items()
        ]
        ordered = sorted(set(s))
        if ordered and all(QUARTER_RE.match(v.strip()) for v in ordered):
            info["period"] = "quarter"
            info["ordered_values"] = sorted(ordered, key=lambda v: (int(v.strip()[:4]), int(v.strip()[-1])))
        elif ordered and all(YEAR_RE.match(v.strip()) for v in ordered):
            info["period"] = "year"
            info["ordered_values"] = sorted(ordered)
        if info["max_label_units"] > 24:
            warns.append(f"列「{name}」最长标签约 {info['max_label_units']} 个显示单位：优先横向条形图，禁止 45° 斜排")
        if info["unique"] > 30 and kind == "text":
            warns.append(f"列「{name}」为高基数文本（{info['unique']} 个唯一值）：不宜直接作图，需聚合或取 Top-N")
    return info, warns


def chart_hints(columns: list[dict], rules: dict) -> list[dict]:
    numeric = [c['name'] for c in columns if c['kind'] == 'numeric']
    categorical = [c['name'] for c in columns if c['kind'] in ('categorical', 'boolean')]
    dates = [c['name'] for c in columns if c['kind'] == 'datetime']
    hints: list[dict] = []
    if dates and numeric:
        hints.append({"family": "line_area", "why": "时间维 + 数值维：折线/面积优先，禁止用柱状图掩盖连续趋势"})
    if categorical and numeric:
        first = next((c for c in columns if c['name'] == categorical[0]), {})
        long_labels = first.get('max_label_units', 0) > rules.get('horizontal_label_units', 12)
        hints.append({
            "family": "bar_grouped_horizontal" if long_labels else "bar_grouped_vertical",
            "why": "分类 + 数值：分组/排序条形图；长标签自动横排",
        })
    if len(numeric) >= 2:
        hints.append({"family": "scatter", "why": "双数值维：散点或带边际密度的回归图"})
    if numeric and not categorical and not dates:
        hints.append({"family": "distribution", "why": "单/多数值列：雨云图、箱线图或直方图"})
    if len(categorical) >= 2 and numeric:
        hints.append({"family": "heatmap_or_grouped", "why": "双分类维：聚合热力矩阵或分组小多图"})
    return hints


def profile_frame(df: pd.DataFrame, path: Path, max_cols: int, rules: dict) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    metadata = dict(df.attrs)
    raw_rows = len(df)
    blank_mask = df.isna().all(axis=1)
    df = df.loc[~blank_mask].copy()
    rows_dropped = int(blank_mask.sum())
    if rows_dropped:
        warnings.append(f"已剔除 {rows_dropped} 行全空行；作图样本量请使用 rows_used")
    if df.empty:
        raise ValueError("清洗全空行后数据为空，无法画像")
    if len(df.columns) > max_cols:
        warnings.append(f"列数 {len(df.columns)} 超过 --max-cols={max_cols}，仅画像前 {max_cols} 列")

    columns: list[dict] = []
    for name in list(df.columns)[:max_cols]:
        info, warns = column_profile(df[name], str(name))
        columns.append(info)
        warnings.extend(warns)

    cat_cols = [c for c in columns if c['kind'] in ('categorical', 'boolean')]
    group_candidates = [
        c['name'] for c in cat_cols
        if 2 <= c.get('unique', 0) <= 20
        and c.get('missing_rate', 0) <= 0.30
        and not any(h in str(c['name']).lower() for h in ID_HINTS)
    ][:5]
    value_candidates = [c['name'] for c in columns if c['kind'] == 'numeric'][:8]
    time_candidates = [c['name'] for c in columns if c['kind'] == 'datetime'][:3]

    dup = int(df.duplicated().sum())
    if dup:
        warnings.append(f"存在 {dup} 行完全重复记录：确认是重复采集还是合法重复观测")

    label_units = [c.get('max_label_units', 0) for c in cat_cols]
    max_units = max(label_units) if label_units else 0
    max_card = max([c.get('unique', 0) for c in cat_cols], default=0)
    long_label_cols = [c['name'] for c in cat_cols if c.get('max_label_units', 0) > rules.get('horizontal_label_units', 12)]

    group_sizes = None
    if group_candidates:
        gc = group_candidates[0]
        counts = df[gc].value_counts(dropna=True)
        group_sizes = {
            "column": gc,
            "n_groups": int(len(counts)),
            "min": int(counts.min()),
            "max": int(counts.max()),
            "top": [{"value": str(v)[:30], "count": int(c)} for v, c in counts.head(8).items()],
        }
        if int(counts.min()) < 30:
            warnings.append(f"分组列「{gc}」最小样本量 {int(counts.min())} <30：组内误差估计与分布图不稳定")

    profile = {
        "file": str(path),
        "encoding": metadata.get("encoding"),
        "sheet": metadata.get("sheet"),
        "rows": len(df),
        "cols": len(df.columns),
        "rows_with_missing": int(df.isna().any(axis=1).sum()),
        "missing_cells": int(df.isna().sum().sum()),
        "duplicate_rows": dup,
        "label_budget": {
            "max_label_units": int(max_units),
            "max_cardinality": int(max_card),
            "long_label_columns": long_label_cols,
            "orientation_hint": "horizontal" if (max_units > rules.get('horizontal_label_units', 12)
                                                  and max_card > rules.get('horizontal_category_count', 5)) else "vertical",
        },
        "group_candidates": group_candidates,
        "group_sizes": group_sizes,
        "value_candidates": value_candidates,
        "time_candidates": time_candidates,
        "columns": columns,
        "chart_hints": chart_hints(columns, rules),
    }
    if not group_candidates and not value_candidates:
        warnings.append("未识别出可用于作图的分类/数值字段：请检查表头与数据类型")
    return profile, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="轻量数据画像（viz-core）")
    ap.add_argument("data", help="CSV/TSV/XLSX/JSON 路径")
    ap.add_argument("--sheet", default=None, help="Excel 工作表名或索引")
    ap.add_argument("--max-rows", type=int, default=None, help="最多读取行数（默认全量）")
    ap.add_argument("--max-cols", type=int, default=40, help="最多画像列数（默认 40）")
    ap.add_argument("--json", action="store_true", help="输出标准 JSON 协议")
    ap.add_argument("--out", default=None, help="将 JSON 画像另存到文件")
    args = ap.parse_args()

    path = Path(args.data)
    result: dict = {
        "status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
        "verified": False, "warnings": [], "profile": None,
    }
    if not path.exists():
        result["warnings"].append(f"文件不存在：{path}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    # 工作区令牌用于标签阈值；找不到时使用内置默认值
    rules = {"horizontal_label_units": 12, "horizontal_category_count": 5}
    for candidate in [Path.cwd() / ".viz-suite" / "assets" / "tokens.json",
                      Path(__file__).resolve().parent.parent / "assets" / "tokens.json"]:
        if candidate.exists():
            try:
                rules.update(json.loads(candidate.read_text(encoding="utf-8")).get("rules", {}))
                break
            except json.JSONDecodeError:
                result["warnings"].append(f"令牌文件解析失败，已忽略：{candidate}")

    try:
        df, read_warnings = read_table(path, args.sheet, args.max_rows)
        result["warnings"].extend(read_warnings)
        profile, warns = profile_frame(df, path, args.max_cols, rules)
        result["warnings"].extend(warns)
        result["rows_used"] = profile["rows"]
        result["rows_dropped"] = int(len(df) - profile["rows"])
        result["profile"] = profile
        result["status"] = "partial" if result["warnings"] else "success"
        result["verified"] = True
    except Exception as exc:  # noqa: BLE001 - 协议要求如实返回而非崩溃
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        result["outputs"].append(str(args.out))
        payload = json.dumps(result, ensure_ascii=False, indent=2)

    if args.json or not sys.stdout.isatty():
        print(payload)
    else:
        if result["status"] == "error":
            print("画像失败：")
            for w in result["warnings"]:
                print(" -", w)
            return 2
        p = result["profile"]
        print(f"{p['file']}  {p['rows']} 行 × {p['cols']} 列  "
              f"(缺失 {p['missing_cells']} 格, 重复 {p['duplicate_rows']} 行)")
        print(f"分组候选: {', '.join(p['group_candidates']) or '无'}")
        print(f"数值候选: {', '.join(p['value_candidates']) or '无'}")
        print(f"标签预算: 最长 {p['label_budget']['max_label_units']} 单位 → {p['label_budget']['orientation_hint']}")
        for hint in p["chart_hints"]:
            print(f"建议: {hint['family']} — {hint['why']}")
        for w in result["warnings"]:
            print("警告:", w)

    if args.out:
        print(f"\n已写出 {args.out}", file=sys.stderr)
    return 0 if result["status"] != "error" else 2


if __name__ == "__main__":
    raise SystemExit(main())

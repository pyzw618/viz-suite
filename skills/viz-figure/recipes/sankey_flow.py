# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：流量分配桑基图（自定义贝塞尔带 + 自动分层）。

    uv run sankey_flow.py --json
    uv run sankey_flow.py --data flows.csv --json   # 列：source,target,value
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgba
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path as MplPath

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
DATA_PATH = None
SHEET = None
SOURCE_COL = "source"
TARGET_COL = "target"
VALUE_COL = "value"
STAGE_NAMES = ["流量来源", "承接渠道", "转化结果"]
SCENE = None
PALETTE = None
LAYOUT = "clean_open"
TITLE = "自然流量与付费投放贡献主要成交，社交平台流量主要经直播承接"
SUBTITLE = "带宽为流量规模｜颜色区分来源阶段｜自动按有向流量分层"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 165
ASPECT = 0.58
CITE_MM = None
NODE_WIDTH = 0.045
NODE_GAP = 0.028
FLOW_ALPHA = 0.36
MIN_FLOW_SHARE = 0.10
OUTDIR = "outputs"
STEM = "sankey_flow"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_flows() -> pd.DataFrame:
    rows = [
        ("自然流量", "落地页", 320), ("自然流量", "直播", 120), ("自然流量", "私域", 60),
        ("付费投放", "落地页", 260), ("付费投放", "直播", 180),
        ("社交平台", "直播", 220), ("社交平台", "私域", 110),
        ("落地页", "成交", 430), ("落地页", "流失", 150),
        ("直播", "成交", 380), ("直播", "流失", 140),
        ("私域", "成交", 140), ("私域", "流失", 30),
    ]
    return pd.DataFrame(rows, columns=[SOURCE_COL, TARGET_COL, VALUE_COL])


def read_table(path, sheet=None) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, sheet_name=sheet or 0)
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="latin-1")


def infer_stages(node_order: list[str], flows: list[tuple[str, str, float]]) -> dict[str, int]:
    indeg = {n: 0 for n in node_order}
    adj = defaultdict(list)
    for src, dst, _ in flows:
        adj[src].append(dst)
        indeg[dst] += 1
    level = {n: 0 for n in node_order}
    queue = [n for n in node_order if indeg[n] == 0]
    seen = 0
    while queue:
        node = queue.pop(0)
        seen += 1
        for nxt in adj[node]:
            level[nxt] = max(level[nxt], level[node] + 1)
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if seen != len(node_order):
        raise ValueError("流量数据存在环，无法分层；请先处理循环流量")
    return level


def ribbon(xs: float, xt: float, ys0: float, ys1: float, yt0: float, yt1: float):
    xm = (xs + xt) / 2
    verts = [
        (xs, ys0), (xm, ys0), (xm, yt0), (xt, yt0),
        (xt, yt1), (xm, yt1), (xm, ys1), (xs, ys1), (xs, ys0),
    ]
    codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
             MplPath.CLOSEPOLY]
    return MplPath(verts, codes)


def main() -> int:
    ap = argparse.ArgumentParser(description="流量分配桑基图")
    ap.add_argument("--data", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--stem", default=None)
    ap.add_argument("--palette", default=None)
    ap.add_argument("--layout", default=None)
    ap.add_argument("--scene", default=None, choices=["academic", "bi", "story", "geo"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    global DATA_PATH, OUTDIR, STEM, PALETTE, LAYOUT, SCENE, WIDTH_MM, ASPECT
    if args.data:
        DATA_PATH = args.data
    if args.outdir:
        OUTDIR = args.outdir
    if args.stem:
        STEM = args.stem
    if args.palette:
        PALETTE = args.palette
    if args.layout:
        LAYOUT = args.layout
    if args.scene:
        SCENE = args.scene

    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "figure": {"recipe": "sankey_flow"}}
    warnings: list[str] = []
    try:
        df = demo_flows() if DATA_PATH is None else read_table(DATA_PATH, SHEET)
        for col in (SOURCE_COL, TARGET_COL, VALUE_COL):
            if col not in df.columns:
                raise ValueError(f"缺少列「{col}」；现有列：{list(df.columns)}")
        df[VALUE_COL] = pd.to_numeric(df[VALUE_COL], errors="coerce")
        dropped = int(df[[SOURCE_COL, TARGET_COL, VALUE_COL]].isna().any(axis=1).sum())
        df = df.dropna(subset=[SOURCE_COL, TARGET_COL, VALUE_COL])
        df = df[df[VALUE_COL] > 0]
        if df.empty:
            raise ValueError("清洗后没有正流量")

        node_order: list[str] = []
        flows: list[tuple[str, str, float]] = []
        for src, dst, value in df[[SOURCE_COL, TARGET_COL, VALUE_COL]].itertuples(index=False):
            src, dst = str(src), str(dst)
            for node in (src, dst):
                if node not in node_order:
                    node_order.append(node)
            flows.append((src, dst, float(value)))
        level = infer_stages(node_order, flows)

        # 节点吞吐：源看流出，汇看流入，中间取较大值
        out_sum = defaultdict(float)
        in_sum = defaultdict(float)
        for src, dst, value in flows:
            out_sum[src] += value
            in_sum[dst] += value
        node_value = {n: max(in_sum[n], out_sum[n]) for n in node_order}
        stage_totals = defaultdict(float)
        for n in node_order:
            stage_totals[level[n]] += node_value[n]
        max_stage_total = max(stage_totals.values())
        stage_nodes = defaultdict(list)
        for n in node_order:
            stage_nodes[level[n]].append(n)
        max_nodes = max(len(v) for v in stage_nodes.values())
        top_limit = 0.94  # 给最上层节点标签与阶段标题留出安全间距
        scale = (top_limit - NODE_GAP * (max_nodes - 1)) / max(max_stage_total, 1e-9)

        theme = vs.resolve_theme(scene=SCENE)
        if theme.get("scene"):
            if not args.layout:
                LAYOUT = theme.get("layout_family", LAYOUT)
            if args.scene:
                WIDTH_MM = theme.get("scene_preset", {}).get("double_column_mm", 183) if (False and theme.get("scene") == "academic") else theme["figure"]["default_width_mm"]
                ASPECT = theme["figure"]["default_aspect"]
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        warnings.extend(size["notes"])

        stages = sorted(stage_nodes)
        n_stages = len(stages)
        stage_x = {s: float(i) * 1.0 for i, s in enumerate(stages)}
        node_pos = {}
        for stage in stages:
            names = stage_nodes[stage]
            heights = [node_value[n] * scale for n in names]
            block = sum(heights) + NODE_GAP * (len(names) - 1)
            cursor = top_limit / 2 - block / 2
            for n, h in zip(names, heights):
                node_pos[n] = (stage_x[stage], cursor, cursor + h, h)
                cursor += h + NODE_GAP

        # 节点配色：源阶段用分类色，中间阶段用后续色，汇阶段用语义色
        colors = {}
        base_colors = pal.pick(min(len(pal), max(3, len(node_order))))
        middle_colors = ["#3B7C70", "#5C8AA8", "#8C8C8C"]
        for stage_idx, stage in enumerate(stages):
            for j, n in enumerate(stage_nodes[stage]):
                if stage == stages[0]:
                    colors[n] = base_colors[j % len(base_colors)]
                elif stage == stages[-1]:
                    colors[n] = theme["colors"]["roles"]["context"]
                else:
                    colors[n] = middle_colors[j % len(middle_colors)]
        sink_nodes = stage_nodes[stages[-1]]
        for i, n in enumerate(sink_nodes):
            if i == 0:
                colors[n] = theme["colors"]["roles"]["positive"]
            elif i == len(sink_nodes) - 1:
                colors[n] = theme["colors"]["roles"]["negative"]
            else:
                colors[n] = theme["colors"]["roles"]["context"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        ax.axis("off")
        ax.set_xlim(-0.38, n_stages - 0.62)
        ax.set_ylim(-0.06, 1.14)

        # 先画流量带，再画节点，保证节点在上层
        out_cursor = {n: node_pos[n][1] + (node_pos[n][3] - out_sum[n] * scale) / 2 for n in node_order}
        in_cursor = {n: node_pos[n][1] + (node_pos[n][3] - in_sum[n] * scale) / 2 for n in node_order}
        ordered_flows = sorted(flows, key=lambda f: (level[f[0]], node_order.index(f[0]),
                                                     level[f[1]], node_order.index(f[1])))
        for idx, (src, dst, value) in enumerate(ordered_flows):
            thickness = value * scale
            xs = node_pos[src][0] + NODE_WIDTH
            xt = node_pos[dst][0]
            ys0 = out_cursor[src]
            ys1 = ys0 + thickness
            yt0 = in_cursor[dst]
            yt1 = yt0 + thickness
            out_cursor[src] = ys1
            in_cursor[dst] = yt1
            path = ribbon(xs, xt, ys0, ys1, yt0, yt1)
            ax.add_patch(PathPatch(path, facecolor=to_rgba(colors[src], FLOW_ALPHA),
                                   edgecolor="none", zorder=1))
            if value / max_stage_total >= MIN_FLOW_SHARE:
                t = 0.38 if idx % 2 == 0 else 0.62
                label_x = xs + t * (xt - xs)
                label_y = ((ys0 + ys1) / 2) * (1 - t) + ((yt0 + yt1) / 2) * t
                ax.text(label_x, label_y, f"{value:,.0f}", ha="center", va="center",
                        fontsize=vs.font_size(theme, "source"),
                        color=theme["colors"]["roles"]["muted_text"],
                        bbox=dict(facecolor="#FFFFFF", edgecolor="none", alpha=0.78, pad=0.8),
                        zorder=4)

        for n in node_order:
            x, y0, y1, h = node_pos[n]
            ax.add_patch(Rectangle((x, y0), NODE_WIDTH, h, facecolor=colors[n],
                                   edgecolor="#FFFFFF", linewidth=1.0, zorder=3))
            stage = level[n]
            label = f"{n}\n{node_value[n]:,.0f}"
            if stage == stages[0]:
                ax.text(x - 0.035, (y0 + y1) / 2, label, ha="right", va="center",
                        fontsize=vs.font_size(theme, "annotation"),
                        color=theme["colors"]["roles"]["text"], linespacing=1.3, zorder=5)
            elif stage == stages[-1]:
                ax.text(x + NODE_WIDTH + 0.035, (y0 + y1) / 2, label, ha="left", va="center",
                        fontsize=vs.font_size(theme, "annotation"),
                        color=theme["colors"]["roles"]["text"], linespacing=1.3, zorder=5)
            else:
                ax.text(x + NODE_WIDTH / 2, y1 + 0.010, label, ha="center", va="bottom",
                        fontsize=vs.font_size(theme, "source"),
                        color=theme["colors"]["roles"]["text"], linespacing=1.25, zorder=6,
                        bbox=dict(facecolor="#FFFFFF", edgecolor="none", alpha=0.82, pad=0.6))

        for i, stage in enumerate(stages):
            name = STAGE_NAMES[i] if i < len(STAGE_NAMES) else f"第 {i + 1} 阶段"
            ax.text(stage_x[stage] + NODE_WIDTH / 2, 1.085, name, ha="center", va="bottom",
                    fontsize=vs.font_size(theme, "annotation"), fontweight="bold",
                    color=theme["colors"]["roles"]["muted_text"])

        vs.add_header(fig, TITLE, SUBTITLE, theme=theme)
        vs.add_source(fig, SOURCE, theme=theme)
        vs.adjust_layout(fig, left=0.02, right=0.98, top=0.80, bottom=0.06, theme=theme)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        data_path = Path(OUTDIR) / f"{STEM}_data.csv"
        export = df.copy()
        export["source_stage"] = export[SOURCE_COL].astype(str).map(level)
        export["target_stage"] = export[TARGET_COL].astype(str).map(level)
        export.to_csv(data_path, index=False, encoding="utf-8-sig")
        outputs.append(str(data_path))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(df)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "sankey_flow", "stages": {str(k): v for k, v in stage_nodes.items()},
                       "nodes": node_order, "flows": int(len(flows)), "palette": pal.id,
                       "layout": LAYOUT, "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "scene": theme.get("scene"), "layout_audit": vs.last_layout_audit(), "visual_verified": False,
                       "note": "脚本已验证文件与文本包围盒；审美与可读性仍须经 audit_export 与宿主读图工具复核"},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

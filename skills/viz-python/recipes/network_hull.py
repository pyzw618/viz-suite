# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24", "pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
"""配方：社区网络 + 半透明凸包（可选力导向布局）。

    uv run network_hull.py --json
    uv run network_hull.py --nodes nodes.csv --edges edges.csv --json
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
from matplotlib.patches import Patch, Polygon

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

# ============================== PARAMS ==============================
NODES_PATH = None
EDGES_PATH = None
NODE_ID_COL = "节点"
GROUP_COL = "社区"
X_COL = "x"
Y_COL = "y"
SOURCE_COL = "source"
TARGET_COL = "target"
WEIGHT_COL = "weight"
PALETTE = None
LAYOUT = "clean_open"
TITLE = "{n_groups} 个社区内部连接紧密，跨社区桥接集中在枢纽节点"
SUBTITLE = "半透明凸包为社区范围｜线宽=连接权重｜灰色为跨社区边"
SOURCE = "数据来源：演示数据（合成）"
WIDTH_MM = 160
ASPECT = 0.82
CITE_MM = None
LABEL_TOP_N = 8
LABELS_PER_GROUP = 1
FORCE_ITERATIONS = 160
OUTDIR = "outputs"
STEM = "network_hull"
FORMATS = ("pdf", "png")
DPI = (300, 600)
DEMO_SEED = 20261025
# ====================================================================


def demo_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(DEMO_SEED)
    centers = {"社区 A": (0.22, 0.74), "社区 B": (0.78, 0.70), "社区 C": (0.50, 0.24)}
    nodes, groups = [], []
    for group, (cx, cy) in centers.items():
        for i in range(18):
            node_id = f"{group[-1]}{i:02d}"
            nodes.append({NODE_ID_COL: node_id, GROUP_COL: group,
                          X_COL: float(np.clip(cx + rng.normal(0, 0.065), 0.03, 0.97)),
                          Y_COL: float(np.clip(cy + rng.normal(0, 0.065), 0.03, 0.97))})
            groups.append((node_id, group))
    edges = []
    by_group = defaultdict(list)
    for node_id, group in groups:
        by_group[group].append(node_id)
    for group, members in by_group.items():
        for _ in range(55):
            a, b = rng.choice(members, 2, replace=False)
            edges.append({SOURCE_COL: a, TARGET_COL: b, WEIGHT_COL: int(rng.integers(1, 4))})
    hubs = [by_group[g][0] for g in centers]
    for i in range(len(hubs)):
        for j in range(i + 1, len(hubs)):
            edges.append({SOURCE_COL: hubs[i], TARGET_COL: hubs[j], WEIGHT_COL: 3})
    return pd.DataFrame(nodes), pd.DataFrame(edges)


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


def force_layout(node_ids: list[str], edges: list[tuple[str, str, float]]) -> dict[str, tuple[float, float]]:
    rng = np.random.default_rng(DEMO_SEED)
    n = len(node_ids)
    index = {name: i for i, name in enumerate(node_ids)}
    pos = rng.uniform(0.05, 0.95, size=(n, 2))
    k = np.sqrt(1.0 / max(n, 2))
    for it in range(FORCE_ITERATIONS):
        disp = np.zeros_like(pos)
        for i in range(n):
            delta = pos[i] - pos
            dist = np.maximum(np.linalg.norm(delta, axis=1), 1e-4)
            force = k ** 2 / dist
            np.fill_diagonal(force, 0.0)
            disp[i] += (delta / dist[:, None] * force[:, None]).sum(axis=0)
        for src, dst, weight in edges:
            i, j = index[src], index[dst]
            delta = pos[i] - pos[j]
            dist = max(float(np.linalg.norm(delta)), 1e-4)
            force = (dist ** 2 / k) * (0.6 + 0.4 * weight)
            disp[i] -= delta / dist * force
            disp[j] += delta / dist * force
        length = np.maximum(np.linalg.norm(disp, axis=1), 1e-6)
        step = 0.06 * (1 - it / FORCE_ITERATIONS) + 0.005
        pos += disp / length[:, None] * np.minimum(length, step)[:, None]
        pos = np.clip(pos, 0.03, 0.97)
    return {name: (float(pos[i, 0]), float(pos[i, 1])) for name, i in index.items()}


def convex_hull(points: np.ndarray) -> np.ndarray:
    pts = sorted(set(map(tuple, points.tolist())))
    if len(pts) < 3:
        return np.asarray(pts, dtype=float)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.asarray(lower[:-1] + upper[:-1], dtype=float)


def main() -> int:
    ap = argparse.ArgumentParser(description="社区网络 + 凸包")
    ap.add_argument("--nodes", default=None)
    ap.add_argument("--edges", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--stem", default=None)
    ap.add_argument("--palette", default=None)
    ap.add_argument("--layout", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    global NODES_PATH, EDGES_PATH, OUTDIR, STEM, PALETTE, LAYOUT
    NODES_PATH = args.nodes or NODES_PATH
    EDGES_PATH = args.edges or EDGES_PATH
    if args.outdir:
        OUTDIR = args.outdir
    if args.stem:
        STEM = args.stem
    if args.palette:
        PALETTE = args.palette
    if args.layout:
        LAYOUT = args.layout

    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "figure": {"recipe": "network_hull"}}
    warnings: list[str] = []
    try:
        if NODES_PATH is None and EDGES_PATH is None:
            nodes_df, edges_df = demo_tables()
        else:
            nodes_df = read_table(NODES_PATH) if NODES_PATH else pd.DataFrame(columns=[NODE_ID_COL, GROUP_COL])
            edges_df = read_table(EDGES_PATH) if EDGES_PATH else pd.DataFrame(columns=[SOURCE_COL, TARGET_COL, WEIGHT_COL])
        for col in (SOURCE_COL, TARGET_COL):
            if col not in edges_df.columns:
                raise ValueError(f"边表缺少列「{col}」；现有列：{list(edges_df.columns)}")
        if WEIGHT_COL not in edges_df.columns:
            edges_df[WEIGHT_COL] = 1.0
        edges_df[WEIGHT_COL] = pd.to_numeric(edges_df[WEIGHT_COL], errors="coerce").fillna(1.0)

        node_ids: list[str] = []
        group_of: dict[str, str] = {}
        coords: dict[str, tuple[float, float]] = {}
        for _, row in nodes_df.iterrows():
            node = str(row[NODE_ID_COL])
            if node not in group_of:
                node_ids.append(node)
            group_of[node] = str(row[GROUP_COL]) if GROUP_COL in nodes_df.columns else "未分组"
            if X_COL in nodes_df.columns and Y_COL in nodes_df.columns:
                try:
                    coords[node] = (float(row[X_COL]), float(row[Y_COL]))
                except (TypeError, ValueError):
                    pass
        for src, dst in edges_df[[SOURCE_COL, TARGET_COL]].itertuples(index=False):
            for node in (str(src), str(dst)):
                if node not in group_of:
                    node_ids.append(node)
                    group_of[node] = "未分组"

        dropped = 0
        edges: list[tuple[str, str, float]] = []
        for src, dst, weight in edges_df[[SOURCE_COL, TARGET_COL, WEIGHT_COL]].itertuples(index=False):
            src, dst = str(src), str(dst)
            if src == dst or src not in group_of or dst not in group_of:
                dropped += 1
                continue
            edges.append((src, dst, float(weight)))
        if len(node_ids) < 3:
            raise ValueError("有效节点少于 3 个")
        if not coords or len(coords) < len(node_ids):
            warnings.append("节点缺少 x/y 或坐标不完整，已使用力导向布局补全")
            layout = force_layout(node_ids, edges)
            coords = {n: layout[n] for n in node_ids}
        else:
            coords = {n: coords[n] for n in node_ids}

        degree = defaultdict(float)
        for src, dst, weight in edges:
            degree[src] += weight
            degree[dst] += weight
        max_degree = max(degree.values()) if degree else 1.0
        groups = list(dict.fromkeys(group_of[n] for n in node_ids))

        theme = vs.resolve_theme()
        if PALETTE:
            theme["palette_id"] = PALETTE
        size = vs.plan_size(WIDTH_MM, ASPECT, theme=theme, cite_mm=CITE_MM)
        theme = vs.bootstrap(theme, font_scale=size["font_scale"])
        pal = vs.palette(theme=theme)
        colors = vs.series_color_map(groups, pal, theme)
        warnings.extend(size["notes"])
        roles = theme["colors"]["roles"]

        fig, ax = vs.figure(size["figsize"], theme=theme)
        vs.apply_style(ax, LAYOUT, theme=theme)
        ax.axis("off")
        xs = [coords[n][0] for n in node_ids]
        ys = [coords[n][1] for n in node_ids]
        pad = 0.08 * max(max(xs) - min(xs), max(ys) - min(ys), 0.1)
        ax.set_xlim(min(xs) - pad, max(xs) + pad)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
        ax.set_aspect("equal")

        # 凸包在下层
        for group in groups:
            pts = np.asarray([coords[n] for n in node_ids if group_of[n] == group], dtype=float)
            if len(pts) < 3:
                continue
            hull = convex_hull(pts)
            if len(hull) < 3:
                continue
            center = hull.mean(axis=0)
            expanded = center + (hull - center) * 1.10
            ax.add_patch(Polygon(expanded, closed=True, facecolor=colors[group], alpha=0.09,
                                 edgecolor=colors[group], linewidth=1.0, linestyle="--", zorder=0))

        for src, dst, weight in edges:
            x1, y1 = coords[src]
            x2, y2 = coords[dst]
            same = group_of[src] == group_of[dst]
            if same:
                ax.plot([x1, x2], [y1, y2], color=colors[group_of[src]],
                        linewidth=0.45 + 0.35 * weight, alpha=0.20, zorder=2)
            else:
                ax.plot([x1, x2], [y1, y2], color=roles["muted_text"],
                        linewidth=0.8 + 0.3 * weight, alpha=0.42, zorder=3)

        xvals = [coords[n][0] for n in node_ids]
        yvals = [coords[n][1] for n in node_ids]
        sizes = [26 + 95 * (degree[n] / max_degree) for n in node_ids]
        ax.scatter(xvals, yvals, s=sizes, c=[colors[group_of[n]] for n in node_ids],
                   edgecolors="white", linewidths=0.7, alpha=0.92, zorder=4)

        if LABELS_PER_GROUP and LABELS_PER_GROUP > 0:
            labelled = []
            for group in groups:
                members = sorted([n for n in node_ids if group_of[n] == group],
                                 key=lambda n: -degree[n])
                labelled.extend(members[:LABELS_PER_GROUP])
        else:
            labelled = sorted(node_ids, key=lambda n: -degree[n])[:LABEL_TOP_N]
        for node in labelled:
            x, y = coords[node]
            ax.annotate(node, xy=(x, y), xytext=(6, 6), textcoords="offset points",
                        fontsize=vs.font_size(theme, "source"), color=roles["text"],
                        bbox=dict(facecolor="#FFFFFF", edgecolor="none", alpha=0.78, pad=0.6),
                        zorder=6)

        handles = [Patch(facecolor=colors[g], edgecolor=colors[g], alpha=0.55, label=str(g))
                   for g in groups]
        leg = ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 1.005),
                        ncol=len(groups), frameon=False, fontsize=vs.font_size(theme, "legend"),
                        handlelength=1.0, columnspacing=1.2)
        vs.style_legend(leg, theme)

        fig.text(0.015, 0.965, vs.fill_title(TITLE, n_groups=len(groups)), ha="left", va="top",
                 fontweight="bold", fontsize=vs.font_size(theme, "title"), color=roles["text"])
        fig.text(0.015, 0.902, SUBTITLE, ha="left", va="top",
                 fontsize=vs.font_size(theme, "subtitle"), color=roles["muted_text"])
        vs.add_source(fig, SOURCE, theme=theme)
        fig.subplots_adjust(left=0.02, right=0.98, top=0.79, bottom=0.05)

        outputs = vs.save_figure(fig, OUTDIR, STEM, formats=FORMATS, dpi=DPI, theme=theme)
        nodes_out = Path(OUTDIR) / f"{STEM}_nodes.csv"
        pd.DataFrame([{NODE_ID_COL: n, GROUP_COL: group_of[n], "x": coords[n][0],
                       "y": coords[n][1], "degree": degree[n]} for n in node_ids]).to_csv(
            nodes_out, index=False, encoding="utf-8-sig")
        outputs.append(str(nodes_out))

        result.update({
            "status": "success" if outputs else "error",
            "outputs": outputs,
            "rows_used": int(len(node_ids)),
            "rows_dropped": dropped,
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "warnings": warnings,
            "figure": {"recipe": "network_hull", "nodes": len(node_ids), "edges": len(edges),
                       "groups": groups, "palette": pal.id, "layout": LAYOUT,
                       "width_mm": size["width_mm"], "height_mm": size["height_mm"],
                       "visual_verified": False,
                       "note": "脚本只验证文件生成；审美与可读性须由 viz-audit / ViewImage 复核"},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

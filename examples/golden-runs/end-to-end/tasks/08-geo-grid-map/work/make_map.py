# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib>=3.8", "numpy>=1.24"]
# ///
# -*- coding: utf-8 -*-
"""E2E 08：geo scene —— 合成网格分级设色 + 缺失区域斜纹 + 独立图例 + CRS 说明。"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
import numpy as np

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "skills" / "viz-figure" / "scripts"))
import viz_style as vs  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
GEO = HERE.parent / "input" / "grid.geojson"
OUT = HERE.parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    result = {"status": "error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
              "verified": False, "warnings": [], "figure": {"recipe": "geo-grid"}}
    try:
        data = json.loads(GEO.read_text(encoding="utf-8"))
        features = data["features"]
        values = [f["properties"]["value"] for f in features if f["properties"]["value"] is not None]
        vmin, vmax = min(values), max(values)
        theme = vs.bootstrap(vs.resolve_theme())
        theme.setdefault("typography", {}).setdefault("size_pt", {}).update({
            "title": 12, "axis_label": 8, "tick": 7, "annotation": 7, "source": 6.5,
        })
        plan = vs.plan_size(160, 0.70, theme=theme)
        fig = plt.figure(figsize=plan["figsize"], dpi=110, facecolor="white")
        ax = fig.add_axes([0.04, 0.22, 0.68, 0.62])
        ax.set_aspect("equal")
        ax.axis("off")
        cmap = vs.sequential_cmap(theme["colors"]["roles"]["focal"])
        norm = Normalize(vmin=vmin, vmax=vmax)
        for f in features:
            name = f["properties"]["name"]
            value = f["properties"]["value"]
            pts = f["geometry"]["coordinates"][0]
            if value is None:
                patch = Polygon(pts, closed=True, facecolor="#E5E7EB", edgecolor="#9CA3AF",
                                linewidth=0.8, hatch="//////", zorder=2)
                ax.add_patch(patch)
                ax.text(np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts]), "无数据",
                        ha="center", va="center", fontsize=6.5, color="#6B7280")
            else:
                color = cmap(norm(value))
                patch = Polygon(pts, closed=True, facecolor=color, edgecolor="white", linewidth=1.0, zorder=2)
                ax.add_patch(patch)
                ax.text(np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts]), f"{name}\n{value}",
                        ha="center", va="center", fontsize=6.8, color=vs.contrast_text(color, "#FFFFFF"))
        ax.set_xlim(0, 4); ax.set_ylim(0, 3)
        ax.set_title("区域经营指数（合成网格）", fontsize=11, loc="left", color="#1F2937")
        cax = fig.add_axes([0.76, 0.30, 0.18, 0.035])
        cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="horizontal",
                          ticks=[vmin, (vmin+vmax)/2, vmax])
        cb.ax.tick_params(labelsize=6.5)
        cb.outline.set_linewidth(0.5)
        fig.text(0.76, 0.36, "指数（0–100）", fontsize=6.5, color="#6B7280")
        fig.text(0.04, 0.14, "缺失区域固定浅灰斜纹；分箱：连续顺序色阶；图例独立。",
                 fontsize=7, color="#374151")
        vs.add_source(fig, "CRS：local synthetic Cartesian（非真实行政区边界）｜投影：无｜底图：synthetic grid｜数据：合成", theme=theme)
        outputs = vs.save_figure(fig, OUT, "geo-grid", formats=("pdf", "svg", "png"), dpi=(300, 600), theme=theme)
        csv_path = OUT / "geo-grid_data.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            fh.write("region,value\n")
            for f in features:
                fh.write(f"{f['properties']['name']},{f['properties']['value'] if f['properties']['value'] is not None else ''}\n")
        outputs.append(str(csv_path))
        result.update({
            "status": "success", "outputs": outputs, "rows_used": len(features),
            "verified": all(Path(p).is_file() and Path(p).stat().st_size > 0 for p in outputs),
            "figure": {**result["figure"], "width_mm": plan["width_mm"],
                       "crs": "local synthetic Cartesian", "projection": "none",
                       "missing_regions": [f["properties"]["name"] for f in features if f["properties"]["value"] is None],
                       "visual_verified": False},
        })
    except Exception as exc:  # noqa: BLE001
        result["warnings"].append(f"{type(exc).__name__}: {exc}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "success" else 2


if __name__ == "__main__":
    raise SystemExit(main())

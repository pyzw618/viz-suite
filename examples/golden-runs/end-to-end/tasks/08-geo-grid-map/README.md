# 08-geo-grid-map · 区域经营地图（合成网格）

**任务**：用合成网格 GeoJSON 做区域经营指数分级设色，缺失区域斜纹，独立图例，标注 CRS/底图来源。

**路由**：primary `viz-python`；scenes `viz-scene-geo`；support `viz-audit`；不要用 `viz-web`。

**输入**：
- `examples/golden-runs/end-to-end/tasks/08-geo-grid-map/input/grid.geojson`

**产物**：
- `examples/golden-runs/end-to-end/tasks/08-geo-grid-map/outputs/geo-grid.pdf`
- `examples/golden-runs/end-to-end/tasks/08-geo-grid-map/outputs/geo-grid.svg`
- `examples/golden-runs/end-to-end/tasks/08-geo-grid-map/outputs/geo-grid_300dpi.png`
- `examples/golden-runs/end-to-end/tasks/08-geo-grid-map/outputs/geo-grid_600dpi.png`
- `examples/golden-runs/end-to-end/tasks/08-geo-grid-map/outputs/geo-grid_data.csv`
- `examples/golden-runs/end-to-end/tasks/08-geo-grid-map/audit.json`
- `examples/golden-runs/end-to-end/tasks/08-geo-grid-map/render.json`

**验证**：160 mm；12 区域，C4 无数据斜纹；顺序色阶；audit 19/19；CRS local synthetic Cartesian。

**说明**：合成网格，不是真实行政区；不下载边界；绝对总量未直接着色面积。

**复现**：`cd .../08-geo-grid-map/work && python make_map.py`

# 02-sales-dashboard · 销售联动看板

**任务**：用经营数据做一个可筛选月份/渠道的销售驾驶舱，KPI、实际 vs 目标、渠道构成、明细表，桌面和手机都要验收。

**路由**：primary `viz-web`；scenes `viz-scene-bi`；support `viz-audit`；不要用 `viz-python`, `viz-infographic`。

**输入**：
- `examples/fixtures/经营实验_渠道月度.csv`

**产物**：
- `examples/golden-runs/scene-gate3/bi/index.html`
- `examples/golden-runs/scene-gate3/bi/summary.csv`
- `examples/golden-runs/scene-gate3/bi/shots/index_desktop.png`
- `examples/golden-runs/scene-gate3/bi/shots/index_mobile.png`
- `examples/golden-runs/scene-gate3/bi/lint.json`
- `examples/golden-runs/scene-gate3/bi/layout.json`
- `examples/golden-runs/scene-gate3/bi/audit.json`

**验证**：1280×800 / 390×844；lint 8 项 0 warning；layout 2 视口 0 issue；HTML audit 0 warning；筛选交互无 JS 错误。

**说明**：IBCS：实际实心/目标虚线；As-of 2025-06-30；12 列栅格。

**复现**：`cd .../scene-gate3/bi && python build_dashboard.py`

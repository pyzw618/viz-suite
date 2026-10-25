# 07-academic-forest · 科研森林图（A/B 实验）

**任务**：把 A/B 实验按渠道汇总成森林图，双栏、95% CI、n、汇总菱形，适合期刊投稿。

**路由**：primary `viz-python`；scenes `viz-scene-academic`；support `viz-audit`；不要用 `viz-web`。

**输入**：
- `examples/golden-runs/scene-gate3/academic/forest_data.csv`

**产物**：
- `examples/golden-runs/scene-gate3/academic/outputs/fig-ab-conversion.pdf`
- `examples/golden-runs/scene-gate3/academic/outputs/fig-ab-conversion.svg`
- `examples/golden-runs/scene-gate3/academic/outputs/fig-ab-conversion_300dpi.png`
- `examples/golden-runs/scene-gate3/academic/outputs/fig-ab-conversion_600dpi.png`
- `examples/golden-runs/scene-gate3/academic/caption.txt`
- `examples/golden-runs/scene-gate3/academic/audit.json`

**验证**：183 mm；4 渠道 + 汇总；汇总 2.71 [1.78,3.63]；audit 23/23；门店 CI 跨 0 明示。

**说明**：无编造 p 值；无 Jet/Rainbow；图注独立。

**复现**：`cd .../scene-gate3/academic/work && python forest_interval_diamond.py`

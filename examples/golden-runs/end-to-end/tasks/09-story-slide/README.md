# 09-story-slide · 高管汇报 16:9 故事图

**任务**：把上半年渠道变化做成一页 16:9 高管汇报图：Action Title、单焦点色、灰色背景系列、直接标注。

**路由**：primary `viz-python`；scenes `viz-scene-story`；support `viz-audit`；不要用 `viz-web`。

**输入**：
- `examples/fixtures/经营实验_渠道月度.csv`

**产物**：
- `examples/golden-runs/scene-gate3/story/outputs/story-revenue-shift.svg`
- `examples/golden-runs/scene-gate3/story/outputs/story-revenue-shift_300dpi.png`
- `examples/golden-runs/scene-gate3/story/outputs/story-revenue-shift_600dpi.png`
- `examples/golden-runs/scene-gate3/story/audit.json`
- `examples/golden-runs/scene-gate3/story/render.json`

**验证**：254×142.9 mm；Action Title；直播焦点/其余冷灰；audit 17/17；目检通过。

**说明**：标题是结论；来源/假设左下；没有截断基线。

**复现**：`cd .../scene-gate3/story/work && python stacked_bar_total_line.py`

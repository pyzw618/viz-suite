# 01-academic-multipanel · 科研多面板组图

**任务**：把这份三组前后测实验数据做成期刊双栏三面板图：均值 95% CI、趋势带、配对变化，注明 n/CI，不编造显著性。

**路由**：primary `viz-python`；scenes `viz-scene-academic`；support `viz-audit`；不要用 `viz-web`, `viz-infographic`。

**输入**：
- `examples/golden-runs/end-to-end/tasks/01-academic-multipanel/input/experiment.csv`

**产物**：
- `examples/golden-runs/end-to-end/tasks/01-academic-multipanel/outputs/fig-academic-multipanel.pdf`
- `examples/golden-runs/end-to-end/tasks/01-academic-multipanel/outputs/fig-academic-multipanel.svg`
- `examples/golden-runs/end-to-end/tasks/01-academic-multipanel/outputs/fig-academic-multipanel_300dpi.png`
- `examples/golden-runs/end-to-end/tasks/01-academic-multipanel/outputs/fig-academic-multipanel_600dpi.png`
- `examples/golden-runs/end-to-end/tasks/01-academic-multipanel/outputs/caption.txt`
- `examples/golden-runs/end-to-end/tasks/01-academic-multipanel/audit.json`
- `examples/golden-runs/end-to-end/tasks/01-academic-multipanel/render.json`

**验证**：183 mm；3 panels a/b/c；n=30/组；95% CI；audit 23/23 通过；目检通过。

**说明**：academic scene：无大标题，图注独立；不使用彩虹色；不写 p 值。

**复现**：`cd .../01-academic-multipanel/work && python make_figure.py`

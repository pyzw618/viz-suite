# 10-technical-infographic · 技术管线信息图

**任务**：把离线可视化管线做成技术风步骤信息图，输出 HTML/SVG，桌面与手机无溢出。

**路由**：primary `viz-infographic`；scenes —；support `viz-web`, `viz-audit`；不要用 `viz-python`。

**输入**：
- `examples/golden-runs/end-to-end/tasks/10-technical-infographic/input/pipeline.json`

**产物**：
- `examples/golden-runs/end-to-end/tasks/10-technical-infographic/outputs/pipeline.html`
- `examples/golden-runs/end-to-end/tasks/10-technical-infographic/outputs/pipeline.svg`
- `examples/golden-runs/end-to-end/tasks/10-technical-infographic/shots/pipeline_desktop.png`
- `examples/golden-runs/end-to-end/tasks/10-technical-infographic/lint.json`
- `examples/golden-runs/end-to-end/tasks/10-technical-infographic/layout.json`
- `examples/golden-runs/end-to-end/tasks/10-technical-infographic/capture.json`
- `examples/golden-runs/end-to-end/tasks/10-technical-infographic/render.json`

**验证**：sequence-steps + technical；lint 0 warning；layout 2 视口 0 issue；整页截图；目检通过。

**说明**：技术风等宽标签/网格；步骤有顺序；不堆 Emoji。

**复现**：`cd .../10-technical-infographic && render_infographic.py input/pipeline.json --outdir outputs --stem pipeline --json`

# 03-retro-infographic · 复盘一页纸信息图

**任务**：把 2025 上半年复盘做成一张一页纸信息图，四个核心数字，报刊风格，带来源与口径，输出 HTML/SVG 并检查手机布局。

**路由**：primary `viz-infographic`；scenes —；support `viz-web`, `viz-audit`；不要用 `viz-python`。

**输入**：
- `examples/golden-runs/end-to-end/tasks/03-retro-infographic/input/retro.json`

**产物**：
- `examples/golden-runs/end-to-end/tasks/03-retro-infographic/outputs/retro.html`
- `examples/golden-runs/end-to-end/tasks/03-retro-infographic/outputs/retro.svg`
- `examples/golden-runs/end-to-end/tasks/03-retro-infographic/shots/retro_desktop.png`
- `examples/golden-runs/end-to-end/tasks/03-retro-infographic/lint.json`
- `examples/golden-runs/end-to-end/tasks/03-retro-infographic/layout.json`
- `examples/golden-runs/end-to-end/tasks/03-retro-infographic/capture.json`
- `examples/golden-runs/end-to-end/tasks/03-retro-infographic/render.json`

**验证**：12 布局引擎中的 stat-cards；lint 0 warning；layout 2 视口 0 issue；整页截图；目检通过。

**说明**：editorial 皮肤；单模块要点≤7；有数值必注来源。

**复现**：`cd .../03-retro-infographic && render_infographic.py input/retro.json --outdir outputs --stem retro --json`

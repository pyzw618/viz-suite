# 04-reverse-rebrand · 截图逆向换品牌色

**任务**：这张别人的柱状图截图，反推数据后换成我们的品牌色重绘，保留数据但不要复制原图风格。

**路由**：primary `viz-reverse`；scenes —；support `viz-python`, `viz-audit`；不要用 `viz-web`。

**输入**：
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/input/source.png`
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/input/ticks.json`

**产物**：
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/outputs/source_data.csv`
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/outputs/source_reverse-spec.json`
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/outputs/branded.pdf`
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/outputs/branded.svg`
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/outputs/branded_300dpi.png`
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/outputs/branded_600dpi.png`
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/audit.json`
- `examples/golden-runs/end-to-end/tasks/04-reverse-rebrand/render.json`

**验证**：B 级反推；中位误差 0.19%（对照已知基准）；品牌 focal #0F62FE；audit 19/19 通过。

**说明**：先定证据等级；不从截图直接猜数；品牌页脚由 EXTEND 注入。

**复现**：`inspect_image.py → calibrate_and_extract.py --render → rebrand.py`

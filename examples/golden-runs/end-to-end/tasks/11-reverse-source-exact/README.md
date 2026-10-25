# 11-reverse-source-exact · 源码级精确提取

**任务**：从这个本地 ECharts 页面精确提取数据和配置，输出可复现的 JS/data.csv，不要做像素猜测。

**路由**：primary `viz-reverse`；scenes —；support `viz-audit`；不要用 `viz-python`, `viz-web`。

**输入**：
- `examples/golden-runs/reverse-benchmark/web/echarts_source.html`

**产物**：
- `examples/golden-runs/reverse-benchmark/reverse-output/web/echarts_source.html/echarts_source_data.csv`
- `examples/golden-runs/reverse-benchmark/reverse-output/web/echarts_source.html/echarts_source_reverse-spec.json`
- `examples/golden-runs/reverse-benchmark/reverse-output/web/echarts_source.html/echarts_source_reproduction.js`
- `examples/golden-runs/reverse-benchmark/reverse-output/web/echarts_source.html/echarts_source_browser-extract.js`

**验证**：SOURCE 级；5 行精确数据，误差 0.0%；browser snippet 生成。

**说明**：只解析本地文件；不执行未知脚本；实时页面用只读 Browser 片段。

**复现**：`cd .../reverse-benchmark && web_extract.py web/echarts_source.html --outdir ... --emit-browser`

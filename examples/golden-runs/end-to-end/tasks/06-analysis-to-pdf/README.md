# 06-analysis-to-pdf · 分析→统计→绘图→PDF/PPT 交接

**任务**：从区域销售表完成统计摘要、图表和两页 PDF 报告，并给出 5 页 PPT 交接提纲。

**路由**：primary `viz-core`；scenes —；support `viz-python`, `viz-audit`, `host:pdf`, `host:pptx`；不要用 `viz-web`。

**输入**：
- `examples/golden-runs/end-to-end/tasks/06-analysis-to-pdf/input/regional_sales.csv`

**产物**：
- `examples/golden-runs/end-to-end/tasks/06-analysis-to-pdf/outputs/report.pdf`
- `examples/golden-runs/end-to-end/tasks/06-analysis-to-pdf/outputs/summary.csv`
- `examples/golden-runs/end-to-end/tasks/06-analysis-to-pdf/outputs/chart_300dpi.png`
- `examples/golden-runs/end-to-end/tasks/06-analysis-to-pdf/outputs/handoff.md`
- `examples/golden-runs/end-to-end/tasks/06-analysis-to-pdf/audit.json`
- `examples/golden-runs/end-to-end/tasks/06-analysis-to-pdf/render.json`

**验证**：6 区域；完成率 97.4%；PDF 2 页；audit 8/8 通过；图表零基线；PPT 提纲 5 页。

**说明**：PDF 由 matplotlib PdfPages；PPT 只交接提纲/素材，不冒充已生成 deck。

**复现**：`cd .../06-analysis-to-pdf/work && python make_report.py`

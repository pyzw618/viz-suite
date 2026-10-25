# 05-ugly-chart-fix · 问题丑图诊断与修复

**任务**：这张图基线截断、彩虹色、标签旋转、没有来源；诊断问题并重绘一张可信的排序横条图。

**路由**：primary `viz-audit`；scenes —；support `viz-python`, `viz-core`；不要用 `viz-reverse`。

**输入**：
- `examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/outputs/before.png`

**产物**：
- `examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/outputs/before.png`
- `examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/outputs/after.pdf`
- `examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/outputs/after.svg`
- `examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/outputs/after_300dpi.png`
- `examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/outputs/after_600dpi.png`
- `examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/audit-before.json`
- `examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/audit-after.json`
- `examples/golden-runs/end-to-end/tasks/05-ugly-chart-fix/render.json`

**验证**：before：CVD protanopia ΔE=3.8、DPI 100；after：19/19 audit 通过；零基线、排序、直接标注、来源齐全。

**说明**：不是所有丑图都要重做；先诊断数据/编码问题再重绘。

**复现**：`cd .../05-ugly-chart-fix/work && python make_fix.py`

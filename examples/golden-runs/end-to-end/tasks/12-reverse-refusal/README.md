# 12-reverse-refusal · 低清/3D 逆向降级

**任务**：这张低清柱图和 3D 饼图能不能反推数据？请给出证据等级、风险和可用替代。

**路由**：primary `viz-reverse`；scenes —；support `viz-audit`；不要用 `viz-python`, `viz-infographic`。

**输入**：
- `examples/golden-runs/reverse-benchmark/images/bar_lowres.png`
- `examples/golden-runs/reverse-benchmark/images/pie_3d.png`

**产物**：
- `examples/golden-runs/reverse-benchmark/reverse-output/lowres/bar_lowres_reverse-spec.json`
- `examples/golden-runs/reverse-benchmark/reverse-output/lowres/bar_lowres_data.csv`
- `examples/golden-runs/reverse-benchmark/reverse-output/pie_3d/pie_3d_reverse-spec.json`
- `examples/golden-runs/reverse-benchmark/reverse-output/pie_3d/pie_3d_2d-suggestion.md`
- `examples/golden-runs/reverse-benchmark/reverse-output/results.json`

**验证**：低清：C 级 partial、precision_claimed=false；3D：X 级 refused=true、仅 2D 建议；Gate 4 100% 正确。

**说明**：低清不输出精确 CSV；3D 透视物理不可逆；不硬猜。

**复现**：`inspect_image.py + calibrate_and_extract.py on lowres/pie_3d`

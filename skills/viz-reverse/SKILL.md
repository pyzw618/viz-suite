---
name: viz-reverse
description: 源码/DOM 与像素级图表逆向工程。用于(1)从本地 HTML/SVG/ECharts/Chart.js/Plotly 配置精确提取数据（SOURCE 级）；(2)从清晰位图反推柱/折线/散点/饼/热力数据并生成可运行复现代码（B 级，目标 MAPE ≤5%）；(3)用 SSIM/ΔE/IoU 与 diff.png 做往返核验；(4)对低清、3D、实拍、手绘等不可逆图诚实降级或拒绝。不用于正向绘图/看板/信息图（用对应引擎）、登录/付费墙绕过、未知页面脚本执行、版权图/商标复制、把 3D 透视硬猜成精确数据。
---

# viz-reverse：源码/DOM 与像素级逆向

目标是把“别人的图表”转化为**可追溯的证据、可编辑的代码与可复核的数据**，而不是“看起来差不多”。先找硬证据，再做测量；测量不确定就降级，不可逆就拒绝。

## 一、证据等级（先定级，再动手）

| 等级 | 输入 | 通道 | 承诺 |
| :--- | :--- | :--- | :--- |
| **SOURCE** | 本地 HTML/SVG、ECharts/Chart.js/Plotly 配置、旧源码 | `web_extract.py` | 精确原始数据 + 精确结构 + 对应栈代码 |
| **B** | ≥800px 清晰位图，柱/折线/散点/饼/热力 | `inspect_image.py` + `calibrate_and_extract.py` | 带置信度的估算 CSV；干净图目标 MAPE ≤5% |
| **C** | 低清、压缩、复杂分布/网络/桑基、无源码纯图 | 多模态结构拆解 + 颜色/布局 Token | 代码骨架 + TODO 占位数据；不得声称精确 |
| **X** | 3D 透视、实拍扭曲、手绘、动态视频帧 | 识别失真原因 | 拒绝数值反推，仅给 2D 规范化建议 |

**No-Compensation**：不得为了 SSIM 调数据、平滑曲线或塞硬编码像素偏移。只允许修正有视觉证据的样式/轴/布局参数。

## 二、五步管线（B 级）

1. **体检**：`inspect_image.py`
   - 绘图区/内容包围盒、轴线/刻度像素、Lab 色彩聚类；
   - 文本区裁剪放大（标题/轴/图例/刻度）；
   - 质量评估：低清、模糊、3D 椭圆透视。
2. **读刻度**：用多模态看 `text-crops/*.png`，写 `ticks.json`（只写刻度值、标题、系列颜色/名称，不写数据）。
3. **标定 + 反推**：`calibrate_and_extract.py`
   - 线性/对数/时间/分类轴最小二乘拟合与 R²；
   - 颜色掩膜 → 柱/折线/散点/饼角/热力格；
   - 输出 `*_data.csv`、`*_reverse-spec.json`、`reproduction.py`。
4. **复现**：运行生成的 `reproduction.py`（或 A 级 `reproduction.js`），得到 `reproduction.png`。
5. **往返核验**：`compare_render.py` 计算灰度 SSIM、CIEDE2000 ΔE、布局/内容 IoU，输出 `diff.png`；SSIM <0.85 时最多修正 3 轮，只改有证据的样式/轴/布局。

## 三、命令

```bash
# A 级：源码/DOM（本地文件，不执行未知脚本）
uv run scripts/web_extract.py page.html --outdir rev --emit-browser --json
uv run scripts/web_extract.py chart.svg --outdir rev --json

# B 级：体检
uv run scripts/inspect_image.py chart.png --chart-type bar \
  --outdir rev/inspect --json

# 人工/VLM 读 text-crops 后写 rev/ticks.json
# B 级：标定 + 反推 + 复现
uv run scripts/calibrate_and_extract.py chart.png \
  --measurements rev/inspect/measurements.json \
  --ticks rev/ticks.json --chart-type bar \
  --outdir rev --stem chart --render --json

# 往返比对
uv run scripts/compare_render.py chart.png rev/reproduction.png \
  --outdir rev/compare --json
```

`web_extract.py --emit-browser` 生成只读片段，供 Browser 工具在**已授权页面**执行；不要用它绕过登录/付费墙或执行未知脚本。

## 四、支持范围

- **A 级**：ECharts option、Chart.js config、Plotly data/layout、带 `data-*` 元数据的 SVG。
- **B 级**：柱/条、折线、散点/气泡、饼/环、矩阵热力五类；轴支持线性、对数、时间、分类。
- **C 级**：未知配置页面、低清图、复杂网络/桑基/分布细节；只给骨架与 TODO。
- **X 级**：3D 饼/柱、透视照片、手绘、视频帧；拒绝反推。

不支持的输入要如实说明，不要用“近似”伪装成精确。

## 五、ticks.json（供 VLM 填写）

```json
{
  "title": "Monthly Revenue by Channel",
  "x_label": "Channel",
  "y_label": "Revenue (k)",
  "x": {"values": ["A", "B", "C", "D", "E"], "scale": "category"},
  "y": {"values": [0, 5, 10, 15, 20, 25], "scale": "linear"},
  "series": [{"name": "Revenue", "color": "#0072B2"}]
}
```

- 只放**刻度值**与图例/标题/颜色，不放反推数据。
- 饼图可用 `categories` + `series` 颜色；热力图需 `rows`/`cols`、`value_range`、颜色条刻度。
- 坐标轴像素位置由 `measurements.json` 提供，不要手填。

## 六、输出协议

```json
{
  "status": "success | partial | error",
  "outputs": ["chart_data.csv", "chart_reverse-spec.json", "reproduction.py"],
  "rows_used": 12,
  "rows_dropped": 0,
  "verified": true,
  "warnings": [],
  "reverse": {"chart_type": "line", "evidence_level": "B", "axes": {}, "data_csv": "..."}
}
```

- X 级返回 `status=partial`、`refused=true`、`evidence_level=X`，不输出估算 CSV。
- C 级返回 `status=partial`、`precision_claimed=false`，明确“仅供骨架参考”。
- 不得静默丢行、伪造 R² 或隐藏 warning。

## 七、验收清单

- [ ] 先判证据等级；SOURCE/B/C/X 与实际输入一致。
- [ ] 轴拟合 R² ≥0.98；否则降级并说明。
- [ ] 数据误差以 ground truth 只做打分，绝不参与反推。
- [ ] 5 类清晰图 MAPE 中位数 ≤5%，SSIM ≥0.85。
- [ ] 低清图必须 C 级降级并写风险；3D/透视必须 X 级拒绝。
- [ ] 复现代码可运行；不硬编码原始像素偏移/魔数。
- [ ] 交付说明包含通道、证据等级、误差、SSIM/ΔE/IoU、未解决项。
- [ ] 不绕过登录/付费墙；不执行未知页面脚本；不复制商标/版权图。

## 八、文件索引

```text
scripts/web_extract.py          # 静态 ECharts/Chart.js/Plotly/SVG + 浏览器片段
scripts/inspect_image.py        # 绘图区、轴/刻度、色彩、文本裁剪、3D 检测
scripts/calibrate_and_extract.py# 轴拟合、五类图元反推、CSV、复现代码
scripts/compare_render.py       # SSIM / ΔE / IoU / diff.png
references/reverse-pipeline.md
references/evidence-grading-rules.md
```

## 九、边界

- 不做登录/付费墙绕过；不执行未知页面脚本；不下载未授权数据。
- 不把 3D/实拍/低清图的估算包装成精确数据。
- 不复制原图、商标、版式文件；只复用可复核的数据结构与样式 Token。
- 若输入是“聊天窗口里的纯图片”且无路径，先落盘再体检；不能落盘则只做 C 级结构建议。

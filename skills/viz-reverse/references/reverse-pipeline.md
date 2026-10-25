# 逆向管线

本文件是 `viz-reverse` 的按需参考。先定证据等级，再选通道；不要跳过体检直接猜数据。

## 一、通道优先级

```text
本地 HTML/SVG/配置（SOURCE）
  > 清晰位图 + 轴标定（B）
  > 低清/复杂图结构骨架（C）
  > 3D/实拍/手绘拒绝（X）
```

- 能拿到 `getOption()` / `config` / `_fullData` / SVG 元数据时，不要做像素猜测。
- 只有位图时，先跑 `inspect_image.py`；质量不达标直接降级。
- 低清图不应输出“精确 CSV”；3D 饼/柱不应反推数值。

## 二、`inspect_image.py` 做什么

1. 读取图像（支持中文路径的 `np.fromfile + cv2.imdecode`）。
2. 估计质量：宽度、Laplacian 方差、彩色像素比例。
3. 检测内容包围盒与坐标轴：
   - 暗色掩膜 + 形态学开运算找长垂直线/水平线；
   - 左/下轴线 → `plot_bbox = [x0,y0,x1,y1]`；
   - 饼/热力无轴时回退内容包围盒。
4. 检测刻度像素：
   - y 轴左侧/ x 轴下方的短刻度带 → 投影峰值 → 像素位置；
   - 不读取刻度文本，文本由多模态看 `text-crops/*.png`。
5. Lab 色彩聚类：
   - 输出主要颜色 HEX/share，用于识别系列色；
   - 精确系列色仍建议由 VLM 读图例后写入 `ticks.json`。
6. 文本裁剪：
   - `title.png`、`x_axis.png`、`y_axis.png`、`legend.png`、`x-ticks.png`、`y-ticks.png`；
   - 放大 2×（可调）供读刻度/图例。
7. 3D 检测：
   - 最大彩色轮廓 fitEllipse；aspect >1.22 且填充率高 → `is_3d=true`，证据 X。

### `measurements.json` 关键字段

```json
{
  "width": 1000, "height": 700,
  "plot_bbox": [130, 105, 930, 595],
  "axis": {"type": "cartesian", "y_axis_x": 130, "x_axis_y": 595},
  "x_ticks_px": [215, 373, 530, 687, 844],
  "y_ticks_px": [156, 245, 333, 420, 506, 595],
  "palette": [{"hex": "#0072B2", "share": 0.98}],
  "pie": null,
  "quality": {"width": 1000, "sharpness": 120.5, "low_resolution": false},
  "evidence_hint": "B",
  "text_crops": [{"name": "x-ticks", "path": "..."}]
}
```

## 三、刻度 JSON（VLM 填写）

```json
{
  "title": "Weekly Trend by Series",
  "x_label": "Week", "y_label": "Value",
  "x": {"values": [0,1,2,3,4,5], "scale": "linear"},
  "y": {"values": [0,5,10,15,20,25,30], "scale": "linear"},
  "series": [{"name": "Series A", "color": "#0072B2"}]
}
```

- `scale`: `linear | log | time | category`。
- y 轴值按数值升序填写；脚本会将像素位置（自上而下）与数值反向配对。
- 饼图：`categories` + `series` 颜色；`unit: percent` 或 `total`。
- 热力图：`rows`、`cols`、`value_range`、颜色条刻度、可选的 `heatmap_rect`/`colorbar_rect` 布局 Token。

## 四、轴标定

- 线性：`value = a * pixel + b`；最小二乘拟合，输出 R²。
- 对数：先 `log10(value)` 再线性拟合；适用于 OR/倍数/长尾。
- 时间：日期转 ordinal 后拟合，输出日期。
- 分类：建立 `category -> pixel` 映射，不做连续外推。
- R² <0.98：必须降级或说明；不允许硬调斜率。

## 五、五类图元反推

### 柱/条

- 彩色掩膜 → 外轮廓 → 过滤面积/宽高；
- 柱顶 y → y 轴映射 → 值；
- 柱中心 x → 最近刻度/类别；
- 分组柱需按颜色拆系列；当前基准为单系列。

### 折线

- 每个系列颜色掩膜 → 最大连通域（去掉图例小色块）；
- 在 x 刻度位置取 y 中位数 → 值；
- 数据点未对齐刻度时，应检测 marker 中心或使用 x 轴连续映射；不要假设所有线都有 marker。

### 散点/气泡

- 系列颜色掩膜 → 连通域质心 → x/y；
- 面积编码需额外标定半径-数值关系；当前只反推位置；
- 重叠点会合并，报告中说明。

### 饼/环

- 圆心/半径来自 `inspect_image`；
- 在 0.55/0.65/0.75R 采样角度 → 最近系列色 → 角度占比；
- 无总数时输出百分比；有 `total` 时换算绝对值；
- 3D/椭圆/透视直接 X 级拒绝。

### 矩阵热力

- 颜色条检测（右侧窄高饱和条）→ 下到上采样 LUT；
- 热力图区域按 `rows/cols` 切格，取中心色；
- 最近 LUT 索引 → 归一化 → `value_range` 映射；
- 无颜色条时不得凭颜色猜数值；可降级 C。

## 六、复现代码

- `reproduction.py` 只含反推数据、轴拟合参数、测得的 plot_bbox/颜色/标题/刻度；
- 用 `fig.add_axes` 对齐原图绘图区，保持宽高/DPI；
- 柱宽、marker 大小、网格线等是样式 Token，不是数据；
- 不得把原始像素偏移、原图路径或 ground truth 塞进复现代码。

## 七、往返比对

`compare_render.py` 输出：

- 灰度 SSIM（`skimage.metrics.structural_similarity`）；
- CIEDE2000 ΔE 均值/中位数（含内容区均值）；
- 内容 bbox 布局 IoU 与非白像素 IoU；
- `diff.png`（差异增强）。

判定：SSIM ≥0.85 为通过；<0.85 时最多 3 轮，只修正轴范围/边距/字体/颜色等有证据的样式问题。**不得通过修改数据或加偏移提高 SSIM**。

## 八、基准图集

`examples/golden-runs/reverse-benchmark/`：

- 5 类清晰图（bar/line/scatter/pie/heatmap）；
- 低清柱图（400px）→ C 级降级；
- 3D 透视饼图 → X 级拒绝；
- 4 个源码级夹具（ECharts/Chart.js/Plotly/SVG）+ 1 个无配置 C 级页面；
- `run_benchmark.py` 自动跑全管线并写 `results.json` / `contact.png`。

## 九、常见失败模式

| 现象 | 原因 | 处理 |
| :--- | :--- | :--- |
| 柱值从顶部算起全错 | 颜色掩膜包含深色轴线 | 提高 value 阈值/排除深灰 |
| 折线取到图例色块 | 未取最大连通域 | 只保留跨绘图区的主连通域 |
| 饼图角度偏 | 采样半径落在标签/白边 | 用 0.55–0.75R 多半径投票 |
| 热力值整体偏移 | 色条方向/范围读错 | 下到上采样；核对 vmin/vmax |
| SSIM 低但数据对 | 版式/字体/边距不同 | 修样式，不修数据 |
| 低清仍输出精确 CSV | 未降级 | 强制 C 级 + `precision_claimed=false` |
| 3D 饼仍反推 | 只看扇形未看椭圆 | aspect>1.22 → X 级拒绝 |

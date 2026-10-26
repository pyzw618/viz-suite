# ECharts 5 / D3 v7 护栏

本文件是 `viz-web` 的按需参考。先读模板，再查本文件；不要凭记忆拼 option。

## 一、ECharts 5

### 1. 最小可靠骨架

```html
<figure>
  <div id="chart" role="img" aria-label="一句话描述图表结论"></div>
  <figcaption>数据来源：…｜ECharts 5｜离线自包含</figcaption>
</figure>
<script src="../../assets/vendor/echarts.min.js"></script>
<script>
const css = getComputedStyle(document.documentElement);
const C = k => css.getPropertyValue(k).trim();
const chart = echarts.init(document.getElementById('chart'), null, {renderer: 'canvas'});

function buildOption(width) {
  const mobile = width < 600;
  return {
    aria: {enabled: true, label: {description: '给读屏软件的一句话结论'}},
    color: [C('--viz-focal'), '#E69F00', '#CC79A7'],
    grid: {left: mobile ? 44 : 56, right: mobile ? 16 : 28, top: 52, bottom: 38},
    xAxis: {type: 'category', data: labels, axisLabel: {fontSize: mobile ? 10 : 12}},
    yAxis: {type: 'value', min: 0},
    series: [{type: 'bar', data: values}]
  };
}
function render() { chart.resize(); chart.setOption(buildOption(window.innerWidth), true); }
render();
window.addEventListener('resize', () => chart.resize());
</script>
```

必查项：

- **容器高度**：`#chart { height: calc(100vh - 150px); min-height: 420px; }`。没有高度时 ECharts 画布为 0。
- **本地脚本**：`../../assets/vendor/echarts.min.js`；不得用 CDN。
- **`series[].data`**：每个系列都必须有 `data`；漏写会得到「只有坐标轴和 legend」的空图。
- **`aria`**：`aria.enabled=true` 与一段 `description`；容器保留 `role="img"` + `aria-label`。
- **重建而非只 `resize`**：字号、刻度密度、legend 位置随宽度变化时，用 `setOption(buildOption(width), true)` 重建；只 `resize()` 不会切换移动端配置。

### 2. 轴与基线

- 柱状/面积：`yAxis.min = 0`；不要用 `min: 'dataMin'` 截断基线。
- 折线：允许按数据范围缩放，但要在副标题说明「纵轴按数据范围缩放」。
- 双 Y 轴：严禁随意拼凑双轴制造伪相关；允许经典帕累托图（左轴频次 + 右轴 0–100% 累计线）及强绑定双量纲（左右轴须与序列颜色编码绑定）。
- 分类轴：`boundaryGap: false` 只用于折线/面积；柱图保持默认 `true`。
- 时间轴：有序分类优先 `type: 'category'`；真正时间序列用 `type: 'time'` 并显式格式化。

### 3. 颜色与系列

- 颜色只取 CSS 语义变量：`--viz-focal`（焦点）、`--viz-context`（背景系列）、`--viz-positive`、`--viz-negative`、`--viz-alert`。
- 分类色按 Okabe-Ito 顺序扩展；同实体跨图必须同色，必要时用 `series_color_map`（Python 侧）或固定 HEX 常量。
- 系列数超过色板安全上限时：合并小类、改线型/点型、或改小倍图；不要循环复用颜色。
- 浅填深边：ECharts 用 `itemStyle.color` + `borderColor/borderWidth` 或 `areaStyle.opacity`；不要把填充透明度写成 1。

### 4. 图例、标签与 tooltip

### 5. 微看板卡片结构与分析信号层（解决单图空洞简陋）

- **顶部 3–4 格 KPI 摘要带**：使用 `.stat-strip` 与 `.stat-card`，必须在运行时由 JS 从数据数组动态计算指标（总额、均值、峰值、同比 Δ 等），并通过安全 DOM API（`document.getElementById().textContent`）写入，正负增量配合红绿颜色与箭头符号双编码；移动端（≤768px）自适应折叠为 2 列。
- **图内分析信号层**：
  - `markPoint`：自动圈出年内极值点或冠军标杆（`coord`、`type: 'max'` / `'min'`），配胶囊引线；
  - `markLine`：全域均值参考线、行业及格基准或帕累托 80% 治理截断线；
  - `markArea`：高亮关键业务时间窗口（如冲刺季、大促节点、政策冲击期）。
- **复合副视图**：折线图可配置双 Grid 联动展示月度同比增量脉冲柱；堆叠图叠加总量折线走势；条形图末端采用 `得分 (较均值 Δ)` 双编码，一图即是一份完整商业决策简报。

- legend 不遮数据：桌面放右上/图外；手机可横排居中，必要时缩短系列名。
- 直接标注优先于 legend：折线尾端 `endLabel`、条形端 `label`；但标签不得出界。
- 饼/环：≤6 类；小类合并「其他」；标签用引导线，中心放总量。
- tooltip：必须有单位；`valueFormatter` 返回带单位的字符串；时间序列用 `trigger:'axis'`。
- 长标签：优先横排条形图；必须旋转时保证不压轴标题，并给足 `grid.left/bottom`。

### 5. 性能

- >5,000 点：`large: true`、`progressive`、关闭 `showSymbol`；>50,000 点先在 Python 侧聚合。
- 避免在 `mousemove` 里重建整个 option；高频交互只更新局部数据。
- 多个图表实例共享 `ResizeObserver` 时加节流（100–160 ms），避免拖拽窗口时抖动。

## 二、D3 v7

### 1. 布局与响应式

```js
function draw() {
  const host = document.getElementById('chart');
  const width = host.clientWidth;
  const height = host.clientHeight;
  const mobile = width < 600;
  margin.left = mobile ? 44 : 58;
  d3.select(host).selectAll('*').remove();
  const svg = d3.select(host).append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('width', width).attr('height', height);
  // scales / axes / marks …
}
draw();
let timer = null;
window.addEventListener('resize', () => {
  clearTimeout(timer);
  timer = setTimeout(draw, 160);
});
```

- 每次重绘先清空容器，避免重复叠加 SVG。
- `viewBox` + 实际宽高同时设置，保证截图与缩放一致。
- 用容器 `clientWidth/clientHeight`，不要用 `window.innerWidth` 推算绘图区。
- 移动端减少标签数量：隔点显示、只显示枢纽、把图例移到图下方。

### 2. 数据连接与过渡

- 用 `selection.data(...).join('enter => …', 'update => …', 'exit => …')`，不要手写 `enter/append` 分支。
- 过渡前确保新旧数据键稳定（`key` 函数），否则元素会错位。
- 过渡时长 500–700 ms；不要给所有属性同时加长动画。
- 轴过渡与数据过渡分开处理：先更新比例尺，再 `transition().call(axis)`，最后更新 marks。

### 3. 力导向网络

- 初始位置按群组给中心，再用 `forceX/forceY` 拉回，避免首次渲染飞散。
- 节点大小编码权重时用面积（`r = sqrt(weight)`），不要直接线性。
- 标签：桌面显示重要节点，手机每群最多 1 个枢纽标签；其余用 `title` 或点击详情。
- 拖拽固定节点用 `d3.drag()`；释放后可选择继续模拟或 `fx=null`。
- `simulation.stop()` 后再截图；否则无头截图会拍到未稳定布局。模板等待 2.5 s 已覆盖。

### 4. 弦图 / 矩形树

- 弦图：矩阵行列顺序决定视觉分组；颜色按源渠道；手机改用底部水平图例，避免旋转标签裁切。
- 矩形树：层级 ≤3；小矩形标签按面积阈值隐藏；颜色只编码一级分组，不要每层换色。
- 所有图形加 `<title>` 或旁注，补充精确数值。

### 5. 可访问性与降级

- SVG 根节点加 `role="img"` 与 `aria-label`；动态图表提供一句话结论。
- 颜色不作为唯一编码：叠加线型、点型、直接标签或纹理。
- 动画尊重 `prefers-reduced-motion`；至少提供无动画的静态首帧。
- 不依赖 hover 才能读到的关键数值：核心结论必须在标题/标签/图注中可见。

## 三、共同禁区

| 禁区 | 替代 |
| :--- | :--- |
| 外部 CDN / Google Fonts | 本地 vendor + 系统字体栈 |
| 双 Y 轴 | 拆图、标准化或指数化 |
| 3D / 伪 3D | 2D 编码 + 直接标注 |
| 饼图 >6 类 | 合并小类、条形图 |
| 红绿唯一编码 | 色盲安全色 + 线型/标签 |
| 空图只有轴线 | 检查 `series[].data` 是否漏写 |
| 移动端旋转 45° 长标签 | 横排条形图或隔点显示 |
| `innerHTML` 拼用户输入 | `textContent` |

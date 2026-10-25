---
name: viz-web
description: 离线自包含的交互图表与单文件看板引擎。用于(1)ECharts 5 标准交互图：折线、面积、柱、条形、堆叠、环图、散点、气泡、热力、雷达、漏斗、仪表、箱线、桑基、矩形树；(2)D3 v7 非标拓扑：力导向网络、弦图、层级矩形树、折线过渡；(3)响应式多图联动看板与 KPI 卡页；(4)用无头 Chrome/Edge 精确截取 1280×800 桌面与 390×844 手机视口并做零外链、溢出与遮挡检查。不用于论文级静态矢量图/多面板统计图（用 viz-python）、信息图（用 viz-infographic）、截图逆向（用 viz-reverse）、需要后端、登录或数据库的完整 Web 应用。
---

# viz-web：交互图表、离线看板与响应式验收

交付物是**可直接双击打开的单文件 HTML**：ECharts/D3 从 `assets/vendor/` 本地加载，运行时零外部请求。目标不是「网页里放个图」，而是让图表在桌面与手机上都清楚、可读、可访问，并能被脚本稳定截图验收。

## 一、标准工作流（五步）

1. **选渲染器**：按下面的阶梯选 ECharts / D3 / 原生 SVG / Python 预聚合，不要用 D3 重写 ECharts 已覆盖的标准图。
2. **选模板并复制**：从 `templates/` 选最接近的一套，复制到工作区再改；不要从空 HTML 手搓。
3. **替换数据与文案**：只改模板顶部的数据常量、`title/subtitle`、分类与系列名、`SOURCE`；保留 `buildOption(width)`、响应式断点、`ResizeObserver`、`<figure>/aria` 与本地 vendor 路径。
4. **脚本检查**：`lint_html.py` 检查零外链、容器高度、viewport/charset/lang、`figure`/`aria`、内联脚本语法、`innerHTML/document.write`；`check_layout.py` 在真实视口里检查横向溢出与越界元素。
5. **渲染验收**：`capture_html.py` 用 CDP 精确截图桌面 1280×800 与手机 390×844；再目检中文、重叠、裁切、图例遮挡；必要时跑 `viz-audit/audit_export.py` 检查 HTML 外链与物理规格。

## 二、渲染器阶梯

| 规模/形态 | 选择 | 理由 |
| :--- | :--- | :--- |
| <1,000 图元、极简静态图 | 原生 SVG 或 HTML/CSS | 零依赖、可访问、易打印 |
| 1,000–50,000 点、标准统计图 | **ECharts 5** | 交互、tooltip、legend、响应式、aria 开箱即用 |
| 非标拓扑/自定义布局/过渡叙事 | **D3 v7** | 力导向、弦图、层级布局、精细动画 |
| >50,000 点或重计算 | Python 侧预聚合/分箱 | 避免浏览器卡顿；前端只画聚合结果 |
| 多图联动总览 | ECharts 看板模板 | 统一筛选、KPI、多图共享状态 |

判断顺序：**先问「标准图能否表达」→ 再问「是否必须自定义拓扑」→ 最后才考虑性能降采样**。不要为了炫技把标准柱图写成 D3。

## 三、模板目录

### ECharts 标准图（15 套）

| 模板 | 用途 | 关键约束 |
| :--- | :--- | :--- |
| `templates/echarts/line.html` | 时间趋势、同比对比 | 纵轴按数据范围缩放；尾端直接标注 |
| `templates/echarts/area.html` | 堆叠面积、渠道构成随时间 | 必须带 `data` 字段；零基线 |
| `templates/echarts/bar.html` | 分类比较 | 零基线；长标签自动旋转/横排 |
| `templates/echarts/hbar.html` | 排名、长标签 | 降序/升序明确；数值标签在条端 |
| `templates/echarts/stacked_bar.html` | 构成 + 总量 | 段数 ≤5；总量与构成同轴 |
| `templates/echarts/donut.html` | 占比（≤6 类） | 环心放总量；小类合并为「其他」 |
| `templates/echarts/scatter.html` | 双变量关系 | 白边散点；避免过绘 |
| `templates/echarts/bubble.html` | 三变量（x/y/大小） | 面积编码，不按半径线性放大 |
| `templates/echarts/heatmap.html` | 二维密度/矩阵 | 顺序色阶；色条图例 |
| `templates/echarts/radar.html` | 多维能力对比 | 指标同尺度；≤3 个对象 |
| `templates/echarts/funnel.html` | 转化漏斗 | 阶段有顺序；百分比口径明确 |
| `templates/echarts/gauge.html` | 单指标 KPI | 目标区间/阈值必须标注 |
| `templates/echarts/boxplot.html` | 分布比较 | 注明四分位与 1.5×IQR |
| `templates/echarts/sankey.html` | 流向/流量 | 节点层级清晰；流标签防重叠 |
| `templates/echarts/treemap.html` | 层级构成 | 面积编码；层级 ≤3 |

### D3 v7 定制骨架（4 套）

| 模板 | 用途 | 移动端处理 |
| :--- | :--- | :--- |
| `templates/d3/force_network.html` | 社群/节点关系、跨群桥接 | 每群只显示 1 个枢纽标签；可拖拽 |
| `templates/d3/chord.html` | 双向流量/互导矩阵 | 桌面弧形标签，手机底部两列水平图例 |
| `templates/d3/treemap.html` | 层级矩形树 | 手机隐藏过小矩形标签 |
| `templates/d3/line_transition.html` | 指标切换与过渡叙事 | y 域按当前数据缩放；手机隔点显示 x 标签 |

### 组合页

- `templates/dashboard/sales_dashboard.html`：12 列 CSS Grid、区域/季度筛选、4 KPI 卡、折线/环图/条形、区域明细表、移动端单列；筛选联动用 `textContent` 防注入。
- `templates/kpi/kpi_cards.html`：4 张 KPI 卡 + 内联 SVG sparkline；无 JS，适合静态汇报页。

## 四、模板硬契约

1. **零外链**：脚本只能引用 `../../assets/vendor/echarts.min.js` / `d3.min.js`；不得出现 `https://`、`//cdn`、Google Fonts、外部图片。
2. **显式高度**：图表容器必须设置 `height: calc(100vh - ...)` 或固定 `min-height`；否则 ECharts 会塌陷为 0。
3. **语义容器**：用 `<figure>` 包图与 `<figcaption>`；容器加 `role="img"` 与 `aria-label`，ECharts 再开 `aria.enabled`。
4. **响应式重建**：`buildOption(width)` 接收宽度，窄屏减少刻度、缩小字号、调整 legend/标签；用 `ResizeObserver` 或防抖 `resize` 重建。
5. **安全文本**：动态文本用 `textContent`，禁止 `innerHTML`；静态模板也不写 `document.write`。
6. **统计诚实**：柱/面积零基线；饼/环 ≤6 类；禁用双 Y 轴与 3D；误差/样本量/口径写进副标题或图注；演示数据必须标「合成」。

## 五、命令

```bash
# 单页 lint（0 blocking 才算通过）
uv run scripts/lint_html.py templates/echarts/line.html --json

# 批量 lint（21 套模板）
uv run scripts/lint_html.py templates/echarts/*.html templates/d3/*.html \
  templates/dashboard/*.html templates/kpi/*.html --json --out lint.json

# 真实视口溢出/越界检查（42 个组合）
uv run scripts/check_layout.py templates/echarts/*.html templates/d3/*.html \
  templates/dashboard/*.html templates/kpi/*.html --json --out layout.json

# 截图：CDP 精确视口（推荐）；自动回退 CLI
uv run scripts/capture_html.py templates/echarts/line.html \
  --outdir shots --json

# 指定桌面/手机视口
uv run scripts/capture_html.py templates/dashboard/sales_dashboard.html \
  --outdir shots --viewport desktop=1280x800 --viewport mobile=390x844 --json

# 同名模板（echarts/treemap 与 d3/treemap）批量截图时，脚本自动加父目录前缀；
# 也可显式指定 --stem 区分。
uv run scripts/capture_html.py templates/echarts/treemap.html --outdir shots \
  --stem echarts_treemap --json

# 长页面/信息图：按内容高度截整页（CDP 模式）
uv run scripts/capture_html.py \
  ../../examples/golden-runs/infographic-gallery/outputs/timeline__editorial.html \
  --outdir shots --viewport desktop=1280x800 --full-page --json
```

`capture_html.py` 优先使用 Chrome DevTools Protocol 的 `Emulation.setDeviceMetricsOverride`，避免 Windows headless 把移动布局视口钳制到约 500px；只有 CDP 不可用时才回退 CLI，并在 `warnings` 中说明。`--full-page` 会读取 `Page.getLayoutMetrics` 并按内容高度截整页，适合信息图/长看板；整页截图不校验收到的 PNG 高度等于视口高度。

## 六、响应式与可读性

- 断点：`600px`（单图手机）、`900px`（看板两列）、`1000px`（看板三列/图表并排）。
- 手机端必须检查：标题换行、legend 是否遮图、x 轴标签是否隔点/旋转、数值标签是否出界、表格是否横向溢出、页脚是否被裁。
- 长标签优先横排条形图，不强行旋转 45°；必须旋转时确保标签不压轴标题。
- 图表高度用 `calc(100vh - 头部/页脚高度)`，但设 `min-height`，避免横屏手机过矮。
- 看板桌面 1280×800 必须能完整看到页脚；手机允许纵向滚动，但不允许横向滚动。
- 颜色只走语义 CSS 变量（`--viz-focal/context/positive/negative/alert`），不逐图硬编码新主题色；同实体跨图同色。

## 七、交付前质检

1. `lint_html.py`：blocking 必须为 0；warning 逐条解释或修复。
2. `capture_html.py`：截图尺寸必须等于请求视口；检查 `png_size`。
3. 多模态目检：至少看桌面与手机各一张，重点看中文方块、文字重叠、图例遮挡、裁切、空图。
4. 自动溢出检查：`document.documentElement.scrollWidth > innerWidth` 或元素 `right > innerWidth` 即失败；看板还要检查表格与筛选器。
5. 接入 `viz-audit`：HTML 外链、`lang`、物理尺寸；交付说明写明 `visual_verified` 状态。

## 八、文件索引

```text
scripts/capture_html.py       # CDP/CLI 双模式截图，精确视口，PNG 尺寸校验
scripts/lint_html.py          # 零外链、容器高度、viewport/charset/lang、figure/aria、JS 语法
scripts/check_layout.py       # CDP 实际视口下的横向溢出、越界元素、视口一致性
assets/vendor/echarts.min.js  # ECharts 5.6.0（Apache-2.0）
assets/vendor/d3.min.js       # D3 v7.9.0（ISC）
templates/echarts/*.html      # 15 套标准图
templates/d3/*.html           # 4 套定制骨架
templates/dashboard/*.html    # 联动看板
templates/kpi/*.html          # KPI 卡页
references/echarts-d3-guardrails.md
references/responsive-dashboard-guide.md
```

## 九、边界

- 不写后端、登录、数据库、打包构建；交付是静态 HTML + 本地 vendor。
- 不用外部 CDN、地图 GeoJSON 在线瓦片、商业字体或需要授权的图片；地理图需用户自备合规 GeoJSON。
- 不把 Python 静态图直接塞进 HTML 假装交互；需要交互就读本 Skill，需要出版矢量图就转 `viz-python`。
- 不用截图冒充可交互成果；交互页必须保留真实 DOM/JS，截图只作验收证据。

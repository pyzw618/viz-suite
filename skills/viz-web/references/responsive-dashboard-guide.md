# 响应式看板规范

本文件约束 `viz-web` 的多图看板、KPI 卡页与手机端布局。目标是：**1280×800 一屏完整，390×844 可纵向滚动、绝不横向溢出**。

## 一、断点与网格

| 宽度 | 布局 | 图表 |
| :--- | :--- | :--- |
| ≥1000px | 12 列 Grid，KPI 4 列，图表 2–3 列 | 并排、高度 200–260px |
| 600–999px | 6 列 Grid，KPI 2 列，图表 1–2 列 | 两列或上下堆叠 |
| <600px | 单列，KPI 1–2 列，筛选器全宽 | 每图独占一行，高度 200–460px |

```css
.dashboard { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
@media (max-width: 900px) { .dashboard { grid-template-columns: repeat(6, 1fr); } }
@media (max-width: 600px) {
  .dashboard { grid-template-columns: 1fr; gap: 12px; }
  .kpi-grid { grid-template-columns: 1fr; }
}
```

注意：

- 用 `minmax(0, 1fr)` 而不是 `1fr`，否则长表格/长标签会撑破列宽。
- 不要在网格子项上写死 `width: 1200px`；需要最小宽度时用 `min-width: 0` + 横滚容器，而不是撑破页面。
- 看板根容器 `max-width: 1440px; margin: 0 auto; padding: 20px 24px;`；手机上 `padding: 12px`。

## 二、高度预算（1280×800 桌面）

一次截图 800px 高，必须能完整看到页脚。推荐预算：

| 区域 | 高度 |
| :--- | :--- |
| 标题 + 副标题 + 筛选器 | 90–110px |
| KPI 行 | 90–110px |
| 主图行（折线 + 环图） | 220–240px |
| 次图 + 表格行 | 180–220px |
| 页脚/来源 | 30–40px |
| 间距合计 | 60–80px |

模板 `sales_dashboard.html` 用：line/donut 220px、bar 200px、KPI 紧凑卡、移动端单列。修改图表高度后必须重新截图确认 footer 未被裁切。

## 三、移动端（390×844）

- 页面允许纵向滚动，**禁止横向滚动**：`body { overflow-x: hidden; }` 只能兜底，不能代替真正的宽度约束。
- 筛选器：桌面并排，手机全宽单列或 2 列；`<select>` 字号 ≥16px（避免 iOS 自动放大）。
- KPI：手机 1 列或 2 列；数字与单位同卡，说明文字最多 2 行。
- 表格：手机改用卡片列表，或允许表格容器 `overflow-x: auto`，但页面本身不溢出。
- 图表 legend：手机横排居中，必要时放图下方；系列名过长先缩写，不缩字号到 9px 以下。
- x 轴：分类多时隔点显示；标签仍拥挤就改横向条形图。
- 标题最多 2–3 行；不要把整段分析塞进 `<h1>`。

## 四、筛选与联动

```js
const state = {region: '全部区域', quarter: '2025Q2'};
function render() {
  const rows = RAW.filter(r => state.region === '全部区域' || r.region === state.region)
                  .filter(r => state.quarter === '全部区域' || r.quarter === state.quarter);
  updateKpis(rows);
  updateLine(rows);
  updateDonut(rows);
  updateBar(rows);
  updateTable(rows);
}
```

规则：

- **单一状态源**：所有图从同一个 `state` 与过滤后的 `rows` 推导，禁止每张图各自过滤。
- **空态**：筛选后无数据时显示「当前筛选无数据」，不要留空白图。
- **口径提示**：筛选变化后更新副标题或口径行（如「区域=华东｜季度=2025Q2｜n=...」）。
- **防注入**：名称、备注、表格单元格一律 `textContent`；不要拼接 `innerHTML`。
- **重绘节流**：一次筛选触发多图时，先算数据再逐图 `setOption`；窗口 resize 用 120–160ms 防抖。

## 五、KPI 卡

- 一张卡只放一个主指标；主数字最大，单位次之，说明最小。
- 同比/环比必须带方向与颜色语义：正向绿、负向红、持平灰；颜色不是唯一编码，加箭头/文字。
- 目标完成率要写清「完成率」分母；没有目标就不要画进度条。
- sparkline 只表达趋势，不标全部刻度；旁边给首尾值或变化率。
- 卡片高度一致：用 Grid `stretch` 或固定 `min-height`，不要因文案长度参差。

## 六、可访问性

- `<html lang="zh-CN">`；`<meta name="viewport" content="width=device-width, initial-scale=1">`。
- 每个图表有 `role="img"` + `aria-label`，ECharts 开 `aria.enabled`。
- 对比度：正文 ≥4.5:1，大字号 ≥3:1；焦点色与背景的对比度用 `viz-core` 的 WCAG 工具核对。
- 键盘：筛选器与按钮可 Tab 到达；不要只靠 hover 展示关键信息。
- 动效：提供 `prefers-reduced-motion` 分支，至少不做无限循环动画。

## 七、性能与截图验收

- 单页 ECharts 实例 ≤8 个；更多图用分页/切换，不要一次初始化几十个 canvas。
- 数据量 >5,000 点时先在 Python 侧聚合；>50,000 点不要直接塞前端。
- 截图用 `capture_html.py` 的 CDP 模式，请求 1280×800 与 390×844 两个视口；普通视口截图检查 `png_size` 是否等于请求值；长页面可加 `--full-page` 按内容高度截整页。
- 自动溢出检查：
  ```js
  document.documentElement.scrollWidth <= window.innerWidth + 1
  ```
  并逐个检查 `getBoundingClientRect().right <= innerWidth + 1`、`left >= -1`。
- 目检清单：标题换行、legend 遮挡、x 标签旋转/隔点、数值标签出界、表格横向溢出、页脚被裁、空图。
- 交付说明必须区分「脚本检查通过」与「已完成多模态目检」。

## 八、常见故障

| 现象 | 原因 | 修复 |
| :--- | :--- | :--- |
| 图表高度 0 / 白屏 | 容器没有显式高度 | 设 `height` 或 `min-height` |
| 手机出现横向滚动 | 固定宽度、长表格、负 margin | `minmax(0,1fr)`、`min-width:0`、表格容器横滚 |
| 桌面 1280 裁掉页脚 | 图表高度过大 | 按高度预算压缩图表 230→200px |
| legend 压住标题 | legend 与 header 同层 | 放图内右上或图下方；缩短系列名 |
| 筛选后图表不更新 | 只改 DOM 未重建 option | 统一 `render()` → `setOption(..., true)` |
| 手机截图内容被截断 | CLI 模式把视口钳制到 ~500px | 用 CDP 模式精确设置视口 |
| 表格文字溢出卡片 | 单元格无 `overflow-wrap` | `word-break: break-word` 或卡片化 |

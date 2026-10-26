---
name: viz-interactive
description: 离线自包含交互图表与响应式商业看板通道。基于本地 ECharts 5 与 D3 v7 模板交付零外链单文件 HTML（16 套标准交互图含帕累托、4 套 D3 定制拓扑、中国均权交互地图、12 列联动驾驶舱与 KPI 卡页），配套无头浏览器双视口截图与溢出体检。不用于期刊静态矢量图（用 viz-figure）、静态信息图（用 viz-diagram）或含后端数据库的完整 Web 应用。
---

# viz-interactive · 离线交互图表与响应式看板

`<SKILL>` 指本文件上一级的 `skills/` 包根目录（`../`），`<WORKSPACE>` 指当前任务工作区。交付物是**零外部请求、双击即开的单文件 HTML**（依赖从 `assets/vendor/` 本地引用或拷贝至工作区）。环境约定见 [宿主适配](../shared/references/host-adapter.md)。

## 一、模板选择与场景映射

1. **按复杂度选底座**（完整清单见 [选型决策树](../shared/references/decision-tree.md)）：
   - **标准交互统计图（优先）**：`templates/echarts/{line,area,bar,hbar,stacked_bar,donut,scatter,bubble,heatmap,radar,funnel,gauge,boxplot,sankey,treemap,pareto}.html`（16 套）。
   - **空间均权交互地图**：`templates/geo/china_grid_interactive.html`（中国 34 省级行政区均权网格 + 联动迷你走势）。
   - **非标关系与过渡拓扑**：`templates/d3/{force_network,chord,treemap,line_transition}.html`（4 套；不要用 D3 重写 ECharts 已覆盖的标准图）。
   - **多维筛选驾驶舱与指标卡**：`templates/dashboard/sales_dashboard.html`（12 列 CSS Grid 多图共享状态联动）、`templates/kpi/kpi_cards.html`（纯 SVG Sparkline 大数卡）。
2. **数据画像与场景令牌**：输入为表格文件时先跑 `<SKILL>/shared/scripts/profile_data.py`；按任务场景加载 `<SKILL>/shared/assets/scenes/{bi,story,geo}.json`（见 [场景增量](../shared/references/scene-deltas.md)），通过语义 CSS 变量（`--viz-focal/context/positive/negative/alert`）统一色彩，跨组件锁定同一实体颜色。

## 二、制作契约（复制到 `<WORKSPACE>` 修改）

- **零外链与安全 DOM**：仅引用本地 `echarts.min.js` / `d3.min.js`，严禁 `https://` CDN、在线字体或在线地图瓦片；动态文本一律用 `textContent`（禁 `innerHTML` / `document.write`）。
- **显式高度与响应式重建**：图表容器必须设显式高度或 `min-height` 防塌陷；保留 `buildOption(width)` 与 `ResizeObserver`，窄屏自动抽稀刻度、收拢图例、单列折叠（详见 [ECharts/D3 护栏](references/echarts-d3-guardrails.md) 与 [响应式看板指南](references/responsive-dashboard-guide.md)）。
- **微看板卡片结构**：单图优先升级为微看板卡片（顶部 3–4 格 KPI 卡由 JS 从数据动态计算并通过 `textContent` 写入；图内叠加 `markPoint` 峰谷气泡 / `markLine` 均值参考线 / `markArea` 重点区间；配合底部增量副图，杜绝单图空洞简陋感）。
- **无障碍与统计诚实**：`<figure>` 包裹图表并配 `role="img"`、`aria-label` 与 `tabular-nums` 等宽数字；柱/面积强制零基线，红黄绿状态须配符号/文字双编码。

## 三、四步自动化与多模态验收闭环

```bash
# 1. 静态合规检查（零外链、高度、viewport/lang、aria、JS 语法；blocking 须为 0）
uv run "<SKILL>/viz-interactive/scripts/lint_html.py" "<WORKSPACE>/outputs/dashboard.html" --json

# 2. 真实视口几何溢出检查（桌面 1280×800 与手机 390×844 横向溢出 issues 须为 0）
uv run "<SKILL>/viz-interactive/scripts/check_layout.py" "<WORKSPACE>/outputs/dashboard.html" --json

# 3. CDP 精确双视口截图 + 物理/外链综合审计
uv run "<SKILL>/viz-interactive/scripts/capture_html.py" "<WORKSPACE>/outputs/dashboard.html" \
  --outdir "<WORKSPACE>/shots" --viewport desktop=1280x800 --viewport mobile=390x844 --json
uv run "<SKILL>/shared/scripts/audit_export.py" "<WORKSPACE>/outputs/dashboard.html" "<WORKSPACE>/shots/"*.png --json
```

脚本全部通过后，必须用**宿主读图工具**实际打开 `desktop` 与 `mobile` 两张截图，确认无中文乱码、无图例压盖数据、桌面端完整露出页脚且手机端零横向截断。

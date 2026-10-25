# Web 模板双视口验收 · Gate 2 证据

对 `skills/viz-web/templates/` 全部 21 套模板做离线与响应式验收：

- 15 套 ECharts 标准图
- 4 套 D3 v7 定制骨架
- 1 套联动看板
- 1 套 KPI 卡页

## 结果

| 检查 | 结果 |
| :--- | :--- |
| `lint_html.py` | 21 文件、168 项检查全部通过；blocking 0 / warning 0 |
| `capture_html.py` | 42 次截图（21 模板 × 桌面/手机）全部 success；PNG 尺寸严格等于 1280×800 / 390×844 |
| `check_layout.py` | 42 个 page/viewport 组合，横向溢出与越界元素均为 0 |
| 多模态目检 | 中文正常、无空图、无图例遮挡、无标题/页脚裁切 |

`capture.json` 为截图记录；`lint.json` 为 lint 明细；`layout.json` 为 CDP 内 `documentElement.scrollWidth`、`body.scrollWidth` 与逐元素 `getBoundingClientRect()` 的检测结果。`contact-desktop.png` / `contact-mobile.png` 是 21 张缩略图接触表；`shots/` 保存全部 42 张原始截图（命名 `<template>_<viewport>.png`，同名模板自动带父目录前缀）。

## 关键修复

- **同名模板输出冲突**：`echarts/treemap.html` 与 `d3/treemap.html` 的 stem 都是 `treemap`。`capture_html.py` 现在在多文件且 stem 重名时自动加父目录前缀，输出 `echarts_treemap_*` / `d3_treemap_*`，避免互相覆盖。
- **移动视口钳制**：Windows headless 的 `--window-size=390,844` 实际布局约 500px。`capture_html.py` 改用 CDP `Emulation.setDeviceMetricsOverride`，实测 `innerWidth=390`、`innerHeight=844`。
- **ECharts 空图**：`area.html` 的 `series[].data` 漏写，只有轴线与 legend；已补 `data`，重截通过。
- **看板 1280×800 裁切**：折线/环图高度从 250 降到 220，条形图 230 降到 200，footer 完整可见。
- **手机端密度**：折线 y 轴按 20 的倍数取整、每 20 一档；条形/热力/雷达/弦图/力导向按 390px 重排，避免标签旋转裁切。

## 复现

```bash
cd skills/viz-web

uv run scripts/lint_html.py templates/echarts/*.html templates/d3/*.html \
  templates/dashboard/*.html templates/kpi/*.html --json --out lint.json

uv run scripts/capture_html.py templates/echarts/*.html templates/d3/*.html \
  templates/dashboard/*.html templates/kpi/*.html \
  --outdir shots --json --out capture.json

uv run scripts/check_layout.py templates/echarts/*.html templates/d3/*.html \
  templates/dashboard/*.html templates/kpi/*.html --json --out layout.json
```

`check_layout.py` 判定 `documentElement.scrollWidth <= innerWidth + 1`，并逐元素检查 `right <= innerWidth + 1` 与 `left >= -1`；同时核对实际布局视口是否等于请求宽度。

## 说明

- 截图是**验收证据**，不是交互交付物；真实交付仍是可双击打开的 HTML。
- 手机截图是视口首屏；长看板允许纵向滚动，但禁止横向滚动。首屏外的表格/图表不在 844px 内，这是预期行为。
- ECharts/D3 从 `assets/vendor/` 本地加载；lint 的 `offline` 检查覆盖 `<script>/<link>/<img>/<iframe>/<use>/<image>` 与 CSS `url()`/`@import`。
- 详细规范见 `skills/viz-web/SKILL.md`、`references/echarts-d3-guardrails.md`、`references/responsive-dashboard-guide.md`。

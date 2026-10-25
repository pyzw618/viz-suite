---
name: viz-infographic
description: 结构化信息图引擎。用于把长文/汇报/研究摘要蒸馏成 12 种布局（网格、横排、步骤、时间轴、金字塔、漏斗、四象限、左右对比、层级树、思维导图、循环、大数卡）× 4 种皮肤（报刊、极简、工程、暖色）的离线 HTML/SVG；内置 100 个本地 Lucide 图标，自动中文折行、卡片对齐与来源标注。不用于精确数值统计图（用 viz-python/viz-web）、截图逆向（用 viz-reverse）、UI 原型、PPT 版式生成、需要外部图片或 Emoji 当图标的信息图。
---

# viz-infographic：结构化信息图引擎

核心不是“把文字放进彩色框”，而是先把内容蒸馏成**一个主张 + 若干同级模块**，再选信息结构（布局）与视觉语气（皮肤），最后用确定性渲染器处理折行、对齐、图标与导出。

## 一、标准工作流（五步）

1. **蒸馏内容**：一图一核心主张；单模块 ≤7 个要点；标题短、副标题给口径；有数值必注来源。
2. **选布局**：先判断信息关系（并列/顺序/层级/转化/定位/循环），再选 12 种布局之一；不要用时间轴装并列清单。
3. **选皮肤**：`editorial` 深度/研究、`minimal` 董事会/产品一页纸、`technical` 管线/架构、`warm` 用户/团队/品牌。
4. **写紧凑 JSON**：顶层 `title/claim/source` + `modules`；特殊布局补 `hub/root/left_label/right_label/x_label/y_label`。
5. **渲染与验收**：`render_infographic.py` 输出 HTML+SVG；`lint_html.py` 零外链；`capture_html.py --full-page` 截图；`check_layout.py` 查溢出；`ViewImage` 目检折行、对齐、图标与来源。

## 二、12 种布局

| 布局 | 结构关系 | 模块数 | 必填字段 | 典型场景 |
| :--- | :--- | :---: | :--- | :--- |
| `list-grid` | 并列 | 2–12 | title, body, icon | 能力清单、要点矩阵 |
| `list-row` | 并列 | 2–7 | title, body, icon, value | 论据清单、发现列表 |
| `sequence-steps` | 顺序 | 3–6 | title, body | 流程、实施步骤 |
| `timeline` | 时间 | 3–8 | meta, title, body | 里程碑、阶段复盘 |
| `pyramid` | 层级 | 3–6 | title, body, value | 能力/优先级/价值层级 |
| `funnel` | 转化 | 3–6 | title, value, meta | 曝光→支付→复购 |
| `quadrant` | 二维定位 | 2–12 | title, x, y, size | 优先级矩阵、组合分析 |
| `compare-binary` | 对比 | 2–8 | title, body, side | 现状/目标、方案 A/B |
| `hierarchy-tree` | 层级 | 1 根 + 3–8 分支 | title, children | 体系拆解、分类树 |
| `mindmap` | 放射 | 1 中心 + 4–8 分支 | title, body | 概念拆解、议题地图 |
| `cycle` | 循环 | 3–8 | title, body | 闭环、飞轮、迭代 |
| `stat-cards` | 大数 | 2–6 | value, label, body, delta | 核心 KPI、关键数字 |

## 三、4 种皮肤

| 皮肤 | 语气 | 关键视觉 |
| :--- | :--- | :--- |
| `editorial` | 报刊社论、研究简报 | 暖纸底、衬线标题、红色焦点、细分隔线、方角 |
| `minimal` | 高留白、克制 | 近白底、细线、单一蓝点、无阴影、宽行距 |
| `technical` | 工程网格、技术复盘 | 蓝灰网格、等宽标签、方角卡片、左强调条 |
| `warm` | 柔和、亲和 | 奶油底、珊瑚/青绿、圆角、轻阴影、点状纹理 |

风格不能改变统计诚实与信息结构；只覆盖视觉令牌。

## 四、JSON 契约

```json
{
  "eyebrow": "2025 客户经营复盘",
  "title": "直播成为新增收入的第一引擎",
  "claim": "直播 6 月收入 286 万元，是 1 月的 4.2 倍；新增收入贡献 46%。",
  "subtitle": "2025 年 1–6 月｜渠道口径：确认收入",
  "icon": "trending-up",
  "layout": "stat-cards",
  "style": "editorial",
  "source": "数据来源：经营分析部 2025 年 6 月月报（合成）",
  "footnote": "口径：确认收入；目标=年度预算月均值。",
  "modules": [
    {"value": "286", "unit": "万元", "label": "直播收入", "title": "直播增长",
     "body": "6 月收入 286 万元，较 1 月增长 4.2 倍。", "icon": "trending-up",
     "delta": "+18.4%", "items": ["1 月 68 万元", "6 月 286 万元"]}
  ]
}
```

特殊布局：

- `hierarchy-tree`：`root: {title, children:[...]}`，或 `modules[0]` 自带 `children`。
- `mindmap` / `cycle`：`hub: {title, icon}`；`modules` 是分支。
- `compare-binary`：模块 `side: "left"|"right"`；或按顺序对半。
- `quadrant`：`x`,`y` 为 0–100；`size` 控制气泡。
- `timeline`：`meta` 为日期/阶段。
- `funnel` / `pyramid`：`value` + `meta`。

## 五、命令

```bash
# 查看布局、风格与图标库
uv run scripts/render_infographic.py --list --json

# 渲染 HTML + SVG
uv run scripts/render_infographic.py data.json --outdir outputs --json

# 覆盖布局/风格
uv run scripts/render_infographic.py data.json \
  --layout timeline --style technical --formats html,svg \
  --outdir outputs --stem timeline-tech --json

# 离线与结构检查
uv run ../viz-web/scripts/lint_html.py outputs/timeline-tech.html --json

# 整页截图（信息图可高于视口）+ 溢出检查
uv run ../viz-web/scripts/capture_html.py outputs/timeline-tech.html \
  --outdir shots --viewport desktop=1280x800 --full-page --json
uv run ../viz-web/scripts/check_layout.py outputs/timeline-tech.html \
  --viewport desktop=1280x800 --viewport mobile=390x844 --json
```

## 六、文本防溢出规则

- 标题 ≤90 字、核心主张 ≤160 字、模块标题 ≤60 字、模块正文 ≤240 字；超限自动截断并写 warning。
- 单模块要点 ≤7 个；超出截断并写 warning。
- HTML：`overflow-wrap:anywhere` + `min-width:0` + 响应式单列；特殊布局（金字塔/漏斗/四象限）使用固定几何与短标签。
- SVG：Python 侧按 CJK=1 em、Latin≈0.55 em 估算折行；`fit_text` 自动缩小字号，超出最大行数用省略号。
- 不得用固定 `height` + `overflow:hidden` 隐藏内容；必须让渲染器先截断并记录 warning。
- 有数值必须提供 `source`；缺失时图脚显示「数据来源：未提供」并 warning。

## 七、图标规则

- 只从 `assets/icons/index.json` 的 100 个 Lucide 图标中选；按语义选，不按形状选。
- 图标只作辅助，不替代标题；同一模块一个图标。
- 禁止 Emoji 充当图标；未知图标自动回退 `circle-dot` 并 warning。
- 图标 stroke 继承当前色；不内嵌外部图片。

## 八、交付前检查

- [ ] 一图一主张；单模块 ≤7 要点；有数值必注来源。
- [ ] 布局与信息关系匹配；没有用时间轴装并列清单。
- [ ] 12 布局 × 4 风格抽查：中文折行、卡片对齐、无重叠/裁切。
- [ ] `lint_html` blocking 0；HTML 零外链。
- [ ] `check_layout` 1280/390 无横向溢出。
- [ ] `ViewImage` 目检：标题、图标、正文、来源均可见。
- [ ] 导出 HTML/SVG；需要 PNG 时用 `capture_html.py --full-page`。

## 九、文件索引

```text
scripts/render_infographic.py   # 数据校验、折行、HTML 渲染、CLI
scripts/infographic_svg.py      # SVG 海报布局器
assets/layouts.json             # 12 布局元数据
assets/styles.json              # 4 皮肤令牌
assets/icons/*.svg              # 100 个 Lucide 图标（ISC）
assets/icons/index.json         # 图标语义索引
references/infographic-design-rules.md
```

## 十、边界

- 不生成精确统计图；需要坐标轴、误差棒、显著性时转 `viz-python`。
- 不生成 UI 原型、网页应用或 PPT 文件；需要幻灯片排版交宿主 `pptx`。
- 不复制外部图片、商标、商业模板；不内置 Emoji 图标。
- 不把长文整段塞进卡片；信息图是蒸馏，不是排版长文。

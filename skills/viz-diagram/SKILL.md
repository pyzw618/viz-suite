---
name: viz-diagram
description: 结构化信息图与逻辑架构图通道。将复盘主张、业务流程、技术管线、层级拆解或矩阵对比蒸馏为 12 种布局 × 6 种视觉皮肤的离线 HTML 与可编辑矢量 SVG，或直接调用 8 套独立矢量 SVG 架构 Master 模板（内置 100 个本地 Lucide 图标，自动中文折行与防溢出校验）。不用于精确坐标轴统计图（用 viz-figure）或筛选联动看板（用 viz-interactive）。
---

# viz-diagram · 结构化信息图与架构图

`<SKILL>` 指本文件上一级的 `skills/` 包根目录（`../`），`<WORKSPACE>` 指当前任务工作区。核心是先把复杂材料蒸馏为**一个核心主张 + 同级结构化模块**，再交由确定性渲染器输出双格式离线 HTML + 矢量 SVG。环境约定见 [宿主适配](../shared/references/host-adapter.md)。

## 一、布局、皮肤与 Master 架构选择

1. **按逻辑关系选 12 种布局**（字段细节见 `assets/layouts.json` 与 [信息图设计规则](references/infographic-design-rules.md)）：
   - **并列清单**：`list-grid`（2–12 卡片矩阵）、`list-row`（2–7 横条论据）
   - **时序与推进**：`sequence-steps`（3–6 实施步骤）、`timeline`（3–8 里程碑复盘）、`cycle`（3–8 闭环飞轮）
   - **层级与转化**：`pyramid`（3–6 价值/优先级层）、`hierarchy-tree`（1 根 + 3–8 分支树）、`funnel`（3–6 转化漏斗）
   - **对比、定位与大数**：`compare-binary`（左右方案对比）、`quadrant`（0–100 二维矩阵）、`mindmap`（中心放射拆解）、`stat-cards`（2–6 核心指标卡）
2. **按受众语气选 6 种皮肤**：`editorial`（报刊社论/研究简报）、`minimal`（高留白极简）、`technical`（工程网格）、`warm`（亲和团队/用户故事）、`mckinsey`（战略咨询/麦肯锡午夜蓝与发丝边框）、`academic_blueprint`（学术蓝图/极深蓝与等宽标注）。
3. **8 套独立企业级矢量 SVG 架构 Master**（见 `templates/svg-masters/index.json`）：
   - `layered_tech_stack`（分层技术中台）、`swimlane_pipeline`（跨部门泳道交付）、`mckinsey_scqa_pyramid`（SCQA战略金字塔）、`dual_flywheel_loop`（双飞轮增长闭环）、`value_chain_chevron`（波特价值链燕尾）、`medallion_lakehouse`（湖仓一体）、`agentic_rag_loop`（AI智能体RAG反思）、`competitive_2x2_radar`（竞品2x2与雷达）。

## 二、数据 JSON 与图标契约

- 在 `<WORKSPACE>/spec.json` 组织输入：顶层含 `eyebrow`、`title`（短标题）、`claim`、`layout`、`style`、`source` 与 `modules` 数组（支持微组件：`value`, `delta`, `progress` 0–100, `tags` 标签；支持 `zones` 阶段底框将多模块包裹入泳道容器，终结白框漂浮感）。
- **图标规范**：仅从 `assets/icons/index.json`（100 个本地 Lucide 线性图标）按语义选取，**严禁用 Emoji 充当图标**。

## 三、渲染与双端质检闭环

```bash
# 1. 渲染信息图或架构 Master 至任务工作区
uv run "<SKILL>/viz-diagram/scripts/render_infographic.py" "<WORKSPACE>/spec.json" --layout timeline --style mckinsey --outdir "<WORKSPACE>/outputs" --json
uv run "<SKILL>/viz-diagram/scripts/render_svg_master.py" mckinsey_scqa_pyramid --outdir "<WORKSPACE>/outputs" --stem scqa --json

# 2. SVG 几何审计 + 静态合规 + 双视口截图
uv run "<SKILL>/viz-diagram/scripts/check_svg_geometry.py" "<WORKSPACE>/outputs" --json
uv run "<SKILL>/viz-interactive/scripts/lint_html.py" "<WORKSPACE>/outputs/diagram.html" --json
uv run "<SKILL>/viz-interactive/scripts/check_layout.py" "<WORKSPACE>/outputs/diagram.html" --json
uv run "<SKILL>/shared/scripts/audit_export.py" "<WORKSPACE>/outputs/"*.svg "<WORKSPACE>/outputs/"*.html --json
```

脚本全部通过后，必须用**宿主读图工具**打开截图确认排版无遮挡截断后再交付。

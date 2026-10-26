---
name: viz-diagram
description: 结构化信息图与逻辑架构图通道。将复盘主张、业务流程、技术管线、层级拆解或矩阵对比蒸馏为 12 种布局 × 4 种视觉皮肤的离线 HTML 与可编辑矢量 SVG（内置 100 个本地 Lucide 图标，自动中文折行与防溢出校验）。不用于精确坐标轴统计图（用 viz-figure）或筛选联动看板（用 viz-interactive）。
---

# viz-diagram · 结构化信息图与架构图

`<SKILL>` 指本文件上一级的 `skills/` 包根目录（`../`），`<WORKSPACE>` 指当前任务工作区。核心是先把复杂材料蒸馏为**一个核心主张 + 同级结构化模块**，再交由确定性渲染器输出双格式离线 HTML + 矢量 SVG。环境约定见 [宿主适配](../shared/references/host-adapter.md)。

## 一、布局与皮肤匹配（严禁错配信息结构）

1. **按逻辑关系选 12 种布局**（字段细节见 `assets/layouts.json` 与 [信息图设计规则](references/infographic-design-rules.md)）：
   - **并列清单**：`list-grid`（2–12 卡片矩阵）、`list-row`（2–7 横条论据）
   - **时序与推进**：`sequence-steps`（3–6 实施步骤）、`timeline`（3–8 里程碑复盘）、`cycle`（3–8 闭环飞轮）
   - **层级与转化**：`pyramid`（3–6 价值/优先级层）、`hierarchy-tree`（1 根 + 3–8 分支树）、`funnel`（3–6 转化漏斗）
   - **对比、定位与大数**：`compare-binary`（左右方案对比）、`quadrant`（0–100 二维矩阵）、`mindmap`（中心放射拆解）、`stat-cards`（2–6 核心指标卡）
2. **按受众语气选 4 种皮肤**：`editorial`（报刊社论/研究简报）、`minimal`（高留白管理层一页纸）、`technical`（工程网格/技术管线）、`warm`（亲和团队/用户故事）。

## 二、数据 JSON 与图标契约

- 在 `<WORKSPACE>/spec.json` 组织输入：顶层含 `eyebrow`、`title`（结论型短标题）、`claim`、`subtitle`、`layout`、`style`、`source`（含任何数值时必填口径来源）与 `modules` 数组（单模块要点 ≤7 条，精炼短句不塞长段原文）。
- 特殊结构补充字段：`hierarchy-tree` 填 `root`；`mindmap`/`cycle` 填 `hub`；`compare-binary` 填 `side: "left"|"right"`；`quadrant` 填 `x, y, size`。
- **图标规范**：仅从 `assets/icons/index.json`（100 个本地 Lucide 线性图标）按语义选取，**严禁用 Emoji 充当图标**或引用外部网络图片。

## 三、渲染与双端质检闭环

```bash
# 1. 查看可用布局、皮肤与图标索引（按需）
uv run "<SKILL>/viz-diagram/scripts/render_infographic.py" --list --json

# 2. 渲染离线 HTML + 可编辑 SVG 至任务工作区
uv run "<SKILL>/viz-diagram/scripts/render_infographic.py" "<WORKSPACE>/spec.json" \
  --layout timeline --style technical --formats html,svg --outdir "<WORKSPACE>/outputs" --stem diagram --json

# 3. 零外链检查 + 双视口溢出检测 + 整页截图与 SVG 审计
uv run "<SKILL>/viz-interactive/scripts/lint_html.py" "<WORKSPACE>/outputs/diagram.html" --json
uv run "<SKILL>/viz-interactive/scripts/check_layout.py" "<WORKSPACE>/outputs/diagram.html" --json
uv run "<SKILL>/viz-interactive/scripts/capture_html.py" "<WORKSPACE>/outputs/diagram.html" \
  --outdir "<WORKSPACE>/shots" --viewport desktop=1280x800 --full-page --json
uv run "<SKILL>/shared/scripts/audit_export.py" "<WORKSPACE>/outputs/diagram.svg" "<WORKSPACE>/shots/"*.png --json
```

脚本全部通过（`blocking = 0`、无横向溢出）后，必须用**宿主读图工具**打开整页截图核查中文折行、卡片对齐、连线归属与底部来源，确认无遮挡截断后再交付。

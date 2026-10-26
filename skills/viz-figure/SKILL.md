---
name: viz-figure
description: 出版级统计与科学图表生成及图表逆向通道。支持从真实数据画像、选型适配 42 套复合/多面板 Python 黄金配方（PDF/SVG/300-600DPI PNG，内置 OFL 字体库，自动切换 academic/bi/story/geo 场景预设与碰撞自检），以及从 HTML/SVG/清晰位图做 SOURCE/B/C/X 级逆向数据提取与重绘。不用于交互网页看板（用 viz-interactive）或纯概念流程信息图（用 viz-diagram）。
---

# viz-figure · 统计与科学图表（含逆向工程）

`<SKILL>` 指本文件上一级的 `skills/` 包根目录（`../`），`<WORKSPACE>` 指当前任务工作区。共享资产与审计脚本位于 `<SKILL>/shared/`，本通道脚本与母版位于 `<SKILL>/viz-figure/`。环境与看图约定见 [宿主适配](../shared/references/host-adapter.md)。

## 一、正向统计绘图：画像 → 选型 → 三区适配 → 双重质检

1. **画像与选型**：先探查字段类型、缺失率与基数，再按 [选型决策树](../shared/references/decision-tree.md) 检索 `catalog/selection-index.jsonl`，并用宿主读图工具实际打开候选缩略图（`catalog/previews/<id>.jpg`）与保真卡（`catalog/cards/<id>.md`）：
   ```bash
   uv run "<SKILL>/shared/scripts/profile_data.py" "<WORKSPACE>/data.csv" --json
   uv run "<SKILL>/viz-figure/scripts/get_recipe.py" --id grouped_errorbar_bar --dest "<WORKSPACE>/viz-work" --force --json
   ```
2. **三区弹性适配（在 `<WORKSPACE>/viz-work/<id>.py` 上修改，绝不回写安装目录）**：
   - **数据管道区（自由改写）**：按业务语义自由改写过滤、聚合、透视、总额排序（如 `SORT_X="total_desc"`）与缺失计数；无数据支撑的条件层（如无显著性检验结果）干净移除，严禁生造数据或编造 p 值。
   - **画布与布局区（弹性伸缩）**：分类增多或标签较长时主动调优 `WIDTH_MM`、`ASPECT`、`GridSpec` 与参考注释；统一使用 `vs.add_header()` 与 `vs.adjust_layout()` 实现超长标题自动折行、图例动态避让及 `academic` 无标题顶部留白回收。
   - **微质感保护区（默认保留）**：保留 `vs.bootstrap()`、浅填深边、去顶右脊线与等宽数字刻度；通过 `--scene {academic,bi,story,geo}` 切换场景预设（见 [场景增量](../shared/references/scene-deltas.md) 与 [统计标注规范](references/stats-annotations.md)）。
3. **渲染与质检闭环**：
   ```bash
   uv run "<WORKSPACE>/viz-work/grouped_errorbar_bar.py" --scene story --outdir "<WORKSPACE>/outputs" --json
   uv run "<SKILL>/viz-figure/scripts/check_recipe_fidelity.py" --base "<SKILL>/viz-figure/recipes/grouped_errorbar_bar.py" --adapted "<WORKSPACE>/viz-work/grouped_errorbar_bar.py" --json
   uv run "<SKILL>/shared/scripts/audit_export.py" "<WORKSPACE>/outputs/"*.pdf "<WORKSPACE>/outputs/"*_300dpi.png --json
   ```
   - `check_recipe_fidelity.py` 输出非阻断审查线索（Review Hints，退出码恒为 `0`），合理的数据与布局适配无需回退。
   - `audit_export.py` 必须 `blocking = 0`（含 Agg Renderer 文本包围盒零重叠与 PDF 字体全嵌入），最后用宿主读图工具实际检视导出 PNG，对照 [反模式清单](../shared/references/anti-patterns.md) 确认视觉主次与可读性。

## 二、图表逆向提取与重绘（SOURCE / B / C / X）

当输入是外部 HTML/SVG 或已有图表截图需提取数据/换肤重绘时，先读取 [逆向管线](references/reverse-pipeline.md) 与 [证据分级规则](references/evidence-grading-rules.md)，严格按证据定级执行：
- **SOURCE 级**（本地 HTML/SVG/ECharts/Plotly 配置）：跑 `scripts/web_extract.py` 精确提取原始数组，不做像素猜测。
- **B 级**（≥800px 清晰 2D 柱/线/散点/饼/热力）：依次运行 `scripts/inspect_image.py` → 读 `text-crops/*.png` 写 `ticks.json` → `scripts/calibrate_and_extract.py`（轴拟合 $R^2 \ge 0.98$）→ `scripts/compare_render.py`（SSIM $\ge 0.85$）；需要换品牌色重绘时将提取的 `*_data.csv` 交回上方正向配方。
- **C / X 级诚实边界**：低清或复杂拓扑降为 **C 级**（仅给代码骨架与 `precision_claimed=false`）；3D 透视饼/柱、实拍扭曲、手绘一律判 **X 级拒绝反推数值**，仅提供 2D 重绘建议。严禁绕过登录/付费墙或篡改数据迎合 SSIM。

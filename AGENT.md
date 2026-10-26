# AGENT.md — viz-suite 仓库级协作与路由指引

`viz-suite` 是一套零外部 CDN 依赖、跨宿主即插即用的离线数据可视化 Skill 包。对外交付的核心技能包位于 [`skills/`](skills/SKILL.md)，采用 **“1 个极薄路由入口 + 3 个自闭环执行通道 + 共享场景预设”** 架构。

## 一、架构与入口路由

工作流一律从 [`skills/SKILL.md`](skills/SKILL.md) 开始，按**要表达的内容语义**（而非最终文件后缀）分派至唯一主通道，不预加载无关通道：

| 通道目录 | 适用任务语义 | 核心资产与确定性闭环 |
| :--- | :--- | :--- |
| [`skills/viz-figure/`](skills/viz-figure/SKILL.md) | 统计与科学图表（PDF/SVG/PNG）、期刊双栏多面板组图、空间分级设色；或从 HTML/SVG/截图逆向提取数据与重绘 | 42 套黄金配方 + 内置 OFL 静态字体库 + `viz_style.py` 流式避让 + `SOURCE/B/C/X` 逆向管线 + Renderer 碰撞自检 |
| [`skills/viz-interactive/`](skills/viz-interactive/SKILL.md) | 浏览器端筛选联动、Hover 明细、过渡叙事单文件交互图及响应式商业驾驶舱 | 本地 ECharts 5（16 套含帕累托）+ D3 v7（4 套）+ 中国均权交互地图 + 顶部 KPI 饰条 + `lint_html` / `check_layout` / CDP 双视口截图 |
| [`skills/viz-diagram/`](skills/viz-diagram/SKILL.md) | 流程步骤、时间轴、金字塔、四象限、层级树、飞轮闭环、大数卡等结构化观点/架构信息图 | 12 布局 × 6 皮肤（含麦肯锡/学术蓝图）+ 8 套独立矢量架构 Master + 100 个本地 Lucide 图标 + HTML/SVG 双端输出 |
| [`skills/shared/`](skills/shared/references/host-adapter.md) | 跨通道共享底座（不单独作为子 Skill 挂载） | `tokens.json`、`palettes.json`、`scenes/{academic,bi,story,geo}.json`、`profile_data.py`、`audit_export.py`、`resolve_runtime.py` |

## 二、路径锚点与工程铁律

1. **显式路径锚点**：`<SKILL>` 固定指 `skills/` 目录；`<WORKSPACE>` 指当前任务工作区。严禁使用脆弱的跨目录裸相对路径（如 `../viz-web/...`），一切中间脚本（`viz-work/`）、运行缓存（`.viz-suite/`）与交付产物（`outputs/`、`shots/`）必须落在 `<WORKSPACE>`。
2. **三区弹性适配（`viz-figure`）**：废除死板的“只改 `PARAMS`”束缚——**数据管道区**自由改写聚合/透视/总额排序、**画布与布局区**弹性伸缩尺寸与参考注释（统一走 `vs.add_header` 与 `vs.adjust_layout`）、**微质感保护区**默认保留浅填深边与去顶右脊线；`check_recipe_fidelity.py` 仅输出非阻断审查线索（Review Hints）。
3. **理性专业的统计与几何边界**：
   - 柱状图与面积图强制零基线；饼/环图 ≤ 6 类；严禁编造数据、样本量或显著性 p 值；缺失剔除如实披露 `rows_dropped`。
   - **区分伪 3D 与真三维**：严禁廉价伪 3D 柱/饼/透视环；允许真三维空间场、响应曲面与三维帕累托前沿。
   - **区分乱凑双轴与耦合双轴**：严禁随意拼凑双 Y 轴自由缩放制造伪相关；允许经典帕累托图（左轴量级 + 右轴 0–100% 累计线）及强耦合双量纲（左右轴须与对应序列颜色绑定）。
4. **双重质检闭环**：交付前必须先跑 `<SKILL>/shared/scripts/audit_export.py`（静态图确保 Renderer 文本包围盒零碰撞、字体全嵌入；HTML/信息图额外通过 `lint_html.py` 与 `check_layout.py`），再用**当前宿主的多模态读图工具**实际检视导出图像，如实报告 `visual_verified` 状态。

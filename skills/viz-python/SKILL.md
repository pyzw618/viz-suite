---
name: viz-python
description: Matplotlib/Seaborn 静态与出版级图表引擎。用于论文插图、科研多面板、统计分布图、矢量 PDF/高 DPI PNG 导出与可复现 Python 代码交付；提供「索引检索 + 预览看图选型 + 三区弹性适配 + Renderer 碰撞自检 + AST 审查线索」闭环。不用于交互网页图表/单文件看板（用 viz-web）、信息图（用 viz-infographic）、截图逆向（用 viz-reverse）、Excel 原生图表修改。
---

# viz-python：静态与出版级图表引擎

核心方法：**不闭门手搓，也不僵化死套模板**。先看候选配方的真实预览图，再读保真卡，按「三区弹性适配契约」改写数据管道与画布比例、保护微质感编码，渲染时自动执行流式页眉避让与 Renderer 文本包围盒碰撞自检，最后结合 AST 审查线索与多模态看图完成验收。

## 一、标准工作流（四步，不可跳步）

### 1. 检索 + 看预览图选型

```bash
uv run scripts/get_recipe.py --list --json
```

检索 `catalog/selection-index.jsonl`，按数据形态、意图、系列数、标签预算筛出 1–3 个候选。**必须使用当前宿主的看图工具实际查看 `catalog/previews/<id>.png`**，并阅读 `catalog/cards/<id>.md` 的「源码保真要点」。禁止只看配方名盲选。

### 2. 字体、场景与尺寸预计算

```bash
uv run scripts/detect_fonts.py --json
```

把字体环境与场景预设（`academic / bi / story / geo`）交给 `viz_style.resolve_theme(scene=...)` 与 `viz_style.bootstrap()`；`plan_size(WIDTH_MM, ASPECT, CITE_MM)` 反推 `figsize` 与字号。当激活 `academic` 场景时，运行时会自动切换学术色板、关闭图内大标题并回收顶部留白。

### 3. 拉取底稿并按「三区弹性适配契约」改写

```bash
uv run scripts/get_recipe.py --id <recipe_id> --dest ./viz-work --json
```

把配方脚本、`viz_style.py` 与 `.viz-suite/assets/` 拉到工作区，按以下三区边界进行结构适配（**不再限制仅修改 `PARAMS` 字面量**）：

1. **数据管道区（自由改写）**：根据真实 CSV/Excel 列结构改写清洗、聚合、业务排序（如按汇总额降序而非字母序）及二次衍生指标（占比 `%`、同比/组间差值 `Δ`）；**若真实数据不含底稿中的某个条件分组、基线或切分（如无 train/test 切分、无外部显著性 p 值），直接干净裁剪该条件图层并在交付说明中注明，严禁生造伪数据凑模板**。
2. **画布与版面区（弹性伸缩）**：根据分类数量、标签显示宽度（`max_label_units`）和场景预设（`--scene academic|bi|story|geo`）动态调整 `WIDTH_MM`、`ASPECT`、多面板 `GridSpec` 比例与边距；使用 `vs.add_header()` 与 `vs.adjust_layout()` 实现标题、副标题与轴外图例的自动折行与流式纵向避让。
3. **微质感编码区（风味保护）**：保留底稿核心视觉层次——同色系柔和填充与实线描边、多层透明置信色带、白边散点、误差棒、零基线、`n` 标注与直接标注逻辑。

> 多图任务由 `figure-manifest.json`（可声明 `"scene"`、`"palette"`、`"series_color_map"`）统一锁定跨图视觉一致性；显式 CLI 参数（`--scene`、`--palette`、`--layout`）优先级高于 manifest。

### 4. 渲染（内置碰撞自检）+ 非阻断保真线索 + 审图

```bash
uv run viz-work/<recipe>.py --data <csv> --scene <academic|bi|story|geo> --outdir outputs --json
uv run scripts/check_recipe_fidelity.py \
  --base recipes/<recipe>.py --adapted viz-work/<recipe>.py --json
```

- `vs.save_figure()` 保存前会自动调用 Agg Renderer 检测全图所有文本与图例像素包围盒（`check_text_collisions`），并将审计元数据写入 PNG 供 `viz-audit` 核验（命中重叠或贴边裁切直接报 `blocking`）；
- `check_recipe_fidelity.py` 默认处于**非阻断审查线索模式（Review Hints，退出码为 0）**：所有图层与参数差异仅作为审图核对线索，合理的业务数据管道与布局适配无需回退；但对移除 `bootstrap()`、引入禁用彩虹色阶等真实退化会发出 `warning`；
- 最后把 PNG 交给 `viz-audit` 与宿主看图工具做视觉验收；未看图时必须声明「未完成视觉验证」。

## 二、黄金配方库（28 套，全部实跑通过）

按 `catalog/selection-index.jsonl` 检索；每套必须同时具备 `recipes/<id>.py`、`catalog/cards/<id>.md`、`catalog/previews/<id>.png`。

| 家族 | 数量 | 代表配方 |
| :--- | :---: | :--- |
| 精致单图 | 8 | `grouped_errorbar_bar`、`stacked_bar_total_line`、`nested_ci_bands_line`、`stacked_area_events`、`donut_leader_labels`、`lollipop_rank_badges`、`parallel_coordinates`、`sankey_flow` |
| 同轴多层融合 | 12 | `raincloud_fusion`、`split_violin_box_sig`、`dumbbell_before_after`、`slope_rank_change`、`bump_rank_trajectory`、`waterfall_ablation`、`bland_altman`、`meta_funnel`、`volcano_fusion`、`pca_biplot`、`forest_interval_diamond`、`network_hull` |
| 共享轴多面板 | 8 | `marginal_scatter_kde`、`clustered_corr_dendro`、`method_rank_heatmap`、`shap_beeswarm_bars`、`km_survival_risk_table`、`calibration_histogram`、`pareto_cumulative`、`residual_violin_corr` |

> 依赖说明：`clustered_corr_dendro` 与 `method_rank_heatmap` 额外依赖 `scipy`（PEP 723 已声明）。
> **新增/修改配方必须同步更新脚本、保真卡、真实预览与索引条目，缺一不可。** 索引检索未命中时，先用 `viz_style.py` 的版式族与取色函数手写最小实现，再决定是否新增配方。

## 三、`viz_style.py` 能力速查

```python
import viz_style as vs

theme = vs.bootstrap(scene="academic")        # 场景预设(academic/bi/story/geo) + 字体 + EXTEND/manifest
pal = vs.palette(theme=theme)                 # 自动应用当前场景/manifest 色板
colors = pal.pick(4)                          # 最大感知色差序，不是原始前 4 色
# 系列数不得超过 pal.safe_k（色盲模拟下的安全上限）；超限请叠加线型/纹理或合并小类
# 版式族：clean_open / soft_grid / framed_journal / bold_edge / minimal_axis / panel_tint
vs.apply_style(ax, theme=theme)
# 浅填深边 / 白边散点 / 线宽
ax.barh(y, v, **vs.bar_kwargs(colors[0], theme=theme))
ax.scatter(x, y, **vs.marker_kwargs(colors[1], theme=theme))
# 色阶与合成底色文字对比度
seq = vs.sequential_cmap(colors[0])
div = vs.diverging_cmap(colors[0], theme=theme)
label_color = vs.contrast_text(fill=colors[0], background="#FFFFFF", alpha=0.18)
# 尺寸、流式页眉避让与碰撞自检导出
plan = vs.plan_size(width_mm=None, aspect=None, cite_mm=85, theme=theme)
fig, ax = vs.figure(plan["figsize"], theme=theme)
vs.add_header(fig, "事实型标题", "统计口径与单位", theme=theme)
vs.add_source(fig, "数据来源：...", theme=theme)
vs.adjust_layout(fig, left=0.10, right=0.97, top=0.80, bottom=0.15, theme=theme)
vs.save_figure(fig, "outputs", "fig-01", formats=("pdf", "png"), dpi=(300, 600), theme=theme)
layout_audit = vs.last_layout_audit()         # passed / collisions / clipped
```

## 四、版式与样式铁律

1. **浅填深边**：柱/箱/带用同色系 alpha 0.18–0.30 填充 + 同色实线描边；不要传 `alpha=1.0`。
2. **白边标记**：散点、折线节点统一 0.6pt 白边，防止糊团。
3. **零基线**：柱状/面积图强制零基线；分布图不强制。
4. **直接标注优先**：系列 ≤5 时优先尾端标注；多系列分组柱用无框图例。
5. **长标签横排**：由 `pick_orientation()` 判定；禁止 45° 斜排。
6. **网格弱化**：`soft_grid` 的横向虚线 alpha 0.35、线宽 0.6。
7. **物理尺寸可预测**：不随意使用 `tight_layout`/`bbox_inches="tight"`；用 `subplots_adjust` 控制边距。
8. **中文字体**：`font.family` 必须是有序回退列表；`bootstrap()` 已处理。

## 五、统计标注边界

- 误差棒必须定义（SD/SEM/95% CI），n 必须可见；
- n < 30 时正态近似 CI 仅作参考，脚本会警告；
- 显著性括号只画上游统计给出的 p 值/星号；**本技能不计算 p 值**；
- 不伪造数据、不补画不存在的显著性、不把相关写成因果。

详见 `references/stats-annotations.md`。

## 六、文件索引

| 路径 | 用途 |
| :--- | :--- |
| `scripts/viz_style.py` | 共享视觉运行时：版式族、取色、色阶、对比度、尺寸、导出 |
| `scripts/detect_fonts.py` | 扫描本机中英文字体并输出 rcParams |
| `scripts/get_recipe.py` | 按 ID 拉取底稿、共享库与资产 |
| `scripts/check_recipe_fidelity.py` | AST 比对底稿与适配脚本的图层/样式特征 |
| `recipes/*.py` | 黄金底稿（PEP 723，可直接 `uv run`） |
| `catalog/selection-index.jsonl` | 选型索引（数据形态、意图、系列上限、路径） |
| `catalog/cards/*.md` | 保真卡：槽位、源码保真要点、误用、验收清单 |
| `catalog/previews/*.png` | 真实渲染预览（选型时必须看） |
| `assets/styles/*.mplstyle` | 期刊/清爽样式表（SciencePlots MIT 提纯） |
| `references/matplotlib-seaborn-guardrails.md` | 现代语法与非废弃写法 |
| `references/stats-annotations.md` | 误差棒、显著性、直接标注规范 |

## 七、命令速查

```bash
uv run scripts/get_recipe.py --list --json
uv run scripts/get_recipe.py --id raincloud_fusion --dest ./viz-work --json
uv run scripts/detect_fonts.py --json
uv run viz-work/raincloud_fusion.py --data data/retention.csv --outdir outputs --json
uv run scripts/check_recipe_fidelity.py --base recipes/raincloud_fusion.py \
  --adapted viz-work/raincloud_fusion.py --json
```

## 八、交付前

- 产物：PDF（矢量）+ 300/600dpi PNG + 汇总 CSV + 复现脚本；
- 说明：数据口径、缺失剔除数、n、误差定义、默认假设、验证状态；
- 视觉验收：交给 `viz-audit`；未看图时必须声明「未完成视觉验证」；
- 需要嵌入报告/PPT 时，交给 `pdf`/`docx`/`pptx` Skill，不要在绘图脚本里硬塞排版。

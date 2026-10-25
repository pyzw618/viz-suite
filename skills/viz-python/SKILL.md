---
name: viz-python
description: Matplotlib/Seaborn 静态与出版级图表引擎。用于论文插图、科研多面板、统计分布图、矢量 PDF/高 DPI PNG 导出与可复现 Python 代码交付；提供「索引检索 + 预览看图选型 + 保真卡适配 + AST 样式核对」闭环。不用于交互网页图表/单文件看板（用 viz-web）、信息图（用 viz-infographic）、截图逆向（用 viz-reverse）、Excel 原生图表修改。
---

# viz-python：静态与出版级图表引擎

核心方法：**不闭门手搓，也不盲目套模板**。先看候选配方的真实预览图，再读保真卡，只改顶部 `PARAMS` 槽位，最后用 AST 比对防止样式被顺手删掉。

## 一、标准工作流（四步，不可跳步）

### 1. 检索 + 看预览图选型

```bash
uv run scripts/get_recipe.py --list --json
```

检索 `catalog/selection-index.jsonl`，按数据形态、意图、系列数、标签预算筛出 1–3 个候选。**必须用 `ViewImage` 实际查看 `catalog/previews/<id>.png`**，并阅读 `catalog/cards/<id>.md` 的「源码保真要点」。禁止只看配方名盲选。

### 2. 字体与尺寸预计算

```bash
uv run scripts/detect_fonts.py --json
```

把返回的 `rcParams` 交给 `viz_style.bootstrap()`；`plan_size(WIDTH_MM, ASPECT, CITE_MM)` 反推 `figsize` 与字号。目标引用宽度小于原生宽度时，字号会自动放大。

### 3. 拉取底稿并只改 PARAMS

```bash
uv run scripts/get_recipe.py --id <recipe_id> --dest ./viz-work --json
```

把配方脚本、`viz_style.py` 与 `.viz-suite/assets/` 拉到工作区。**只修改顶部 PARAMS 块与数据映射**：

- `DATA_PATH`、`GROUP_COL`、`SERIES_COL`、`VALUE_COL`、`ERROR_COL`；
- `TITLE`（写事实，不写未检验结论）、`SUBTITLE`（统计口径）、`SOURCE`；
- `WIDTH_MM`、`ASPECT`、`CITE_MM`、`PALETTE`、`LAYOUT`；
- 配方专属槽位（如 `AGG`、`ORIENTATION`、`SIG_PAIRS`）。

> 多图任务要由 `figure-manifest.json` 锁定尺寸/版式时，把 `WIDTH_MM` 与 `LAYOUT` 置为 `None`；显式 PARAMS 仍优先于 manifest。

**严禁**删改底稿中的浅填深边、多层透明带、白边散点、误差棒、箱体、零基线、n 标注与直接标注分支。需要结构性改动时，先说明理由，再新增分支，不要静默删除。

### 4. 渲染 + 保真核对 + 审图

```bash
uv run viz-work/<recipe>.py --data <csv> --outdir outputs --json
uv run scripts/check_recipe_fidelity.py \
  --base recipes/<recipe>.py --adapted viz-work/<recipe>.py --json
```

- 渲染成功得到 `pdf`、`svg`/`png`、汇总 CSV；
- `check_recipe_fidelity.py` 判定 `pass/review/fail`；`fail`（关键图层消失或样式丢失 >40%）必须修正；
- 最后把 PNG 交给 `viz-audit` 与 `ViewImage` 做视觉验收；脚本的 `verified` 只代表文件生成成功，**不代表审美与可读性已验收**。

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

theme = vs.bootstrap(vs.resolve_theme())      # 字体 + rcParams + EXTEND/manifest
pal = vs.palette("okabe_ito", theme=theme)
colors = pal.pick(4)                          # 最大感知色差序，不是原始前 4 色
# 系列数不得超过 pal.safe_k（色盲模拟下的安全上限）；超限请叠加线型/纹理或合并小类
# 版式族：clean_open / soft_grid / framed_journal / bold_edge / minimal_axis / panel_tint
vs.apply_style(ax, "soft_grid", theme=theme)
# 浅填深边 / 白边散点 / 线宽
ax.barh(y, v, **vs.bar_kwargs(colors[0], theme=theme))
ax.scatter(x, y, **vs.marker_kwargs(colors[1], theme=theme))
# 色阶
seq = vs.sequential_cmap(colors[0])
div = vs.diverging_cmap(colors[0], theme=theme)
# 合成底色上的黑白字
label_color = vs.contrast_text(fill=colors[0], background="#FFFFFF", alpha=0.18)
# 尺寸与导出
plan = vs.plan_size(width_mm=160, aspect=0.62, cite_mm=85, theme=theme)
fig, ax = vs.figure(plan["figsize"], theme=theme)
vs.save_figure(fig, "outputs", "fig-01", formats=("pdf", "png"), dpi=(300, 600), theme=theme)
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

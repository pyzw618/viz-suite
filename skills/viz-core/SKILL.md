---
name: viz-core
description: 数据可视化认知底座。用于(1)可视化前置规划：需求澄清、数据画像、图表选型、多图风格统一与设计令牌；(2)判断该用哪种图、是否该融合图层或多面板、长标签如何布局；(3)初始化 figure-manifest.json 锁定多图色板与尺寸。不用于纯数据分析/统计检验、纯架构图/流程图、以及具体渲染（请转 viz-python / viz-web / viz-infographic）或截图逆向（用 viz-reverse）。
---

# viz-core：访谈、画像、选型与设计规范

你是可视化任务的第一站。**先想清楚再画**：确认真实问题、数据形态、受众与交付介质，再给出 1 个首选方案 + 1–2 个备选方案 + 误用禁忌。

## 一、标准工作流

1. **分级澄清**：读取 `references/intake-guide.md`，按四档判定处理；最多追问 3 个问题，每题附默认推荐项。用户要求跳过时，立即按默认执行并记录假设。
2. **读取定制**：若存在 `.viz-suite/EXTEND.md`（项目）或 `~/.viz-suite/EXTEND.md`（用户），读取品牌色、字体与页脚；若启用了 `viz-scene-*`，同时读取其 `scene-delta.md` 的 12 槽位。优先级见 `references/typography-and-color.md`。
3. **数据画像**：对 CSV/TSV/XLSX 运行 `profile_data.py`，只把 <100 行摘要放进上下文，避免原始大表污染。
4. **选型**：结合 `references/chart-taxonomy.md` 与 `references/decision-tree.md`，先判断是否值得做**同轴图层融合**或**共享轴多面板**，再落到单图。
5. **多图台账**：单次任务 ≥3 张图时，在工作区写入 `figure-manifest.json`，锁定色板、版式族、物理宽度、系列语义色、字体栈与图号。
6. **交接**：把「首选方案 + 数据契约 + PARAMS 建议 + 物理尺寸」交给渲染引擎（静态图 → `viz-python`；交互图/看板 → `viz-web`；结构化信息图 → `viz-infographic`），并附上当前场景差分。

## 二、画像命令

```bash
uv run skills/viz-core/scripts/profile_data.py data.csv --json
uv run skills/viz-core/scripts/profile_data.py data.xlsx --sheet 明细 --json --out profile.json
```

输出字段关注：

- `rows / cols / missing_cells / duplicate_rows`；
- `label_budget.max_label_units` 与 `orientation_hint`：决定横排/竖排；
- `group_candidates / value_candidates / time_candidates`：可用列；
- `columns[].missing_rate / skew / outlier_share / top_values`；
- `chart_hints`：脚本给出的候选族，仅作参考，最终由你判断；
- `warnings`：缺失率 >30%、数值以文本存储、高基数文本、长标签等。

**禁止**把原始表整表粘进上下文；**禁止**在没有画像的情况下猜列类型。

### 不同任务的最小信息集

| 任务 | 必须知道 | 可以默认 |
| :--- | :--- | :--- |
| 单张比较图 | 分类列、数值列、比较目的 | 色板 Okabe-Ito、160mm 宽、soft_grid |
| 分组比较 + 不确定性 | 分类、系列、数值、误差定义 | 95% CI（n≥30）、n 标注、零基线 |
| 分布比较 | 分组列、原始观测、每组 n | 雨云图、高斯核、cut=0 |
| 时间趋势 | 时间列、指标、粒度 | 折线、尾端直接标注、事件竖线（如有） |
| 构成/占比 | 分类、数值、总和是否有意义 | ≤5 段堆叠条、排序 |
| 多图任务 | 图数、统一色板/尺寸/字体 | 写入 `figure-manifest.json` |
| 地理图 | 区域字段、GeoJSON、坐标系 | 分级设色、顺序色阶、注明投影 |

### `EXTEND.md` 可覆盖字段

```yaml
colors:      # 覆盖 9 大角色中的任意项，如 focal / context / positive / negative
typography:  # font_zh / font_en / font_serif_zh
brand:       # footer 等页脚文案
stack:       # preferred_web / preferred_python
```

只支持两层扁平 YAML 子集；复杂嵌套请改 `figure-manifest.json` 或显式参数。`EXTEND.md` 与 manifest 的优先级见 `references/typography-and-color.md` 第九节。

## 三、选型输出格式

```text
首选：分组误差棒柱图（grouped_errorbar_bar）
理由：1 个分类维 + 1 个数值维 + 1 个系列维；需要表达均值与 95% CI。
备选：雨云图（raincloud_fusion）——若审稿人要求展示原始分布。
禁忌：堆叠柱比较组间总量；误差棒重叠不等于显著。
数据契约：长表，列 = 渠道 / 季度 / 满意度；缺失 37 行需剔除。
尺寸：160mm 宽、0.62 比例；长标签 → 横排。
```

## 四、`figure-manifest.json` 骨架

```json
{
  "palette": "okabe_ito",
  "layout_family": "soft_grid",
  "width_mm": 160,
  "series_color_map": {"2024Q4": "#0072B2", "2025Q1": "#E69F00", "2025Q2": "#CC79A7"},
  "fonts": {"font_zh": ["Microsoft YaHei"], "font_en": ["Arial"]},
  "figures": [
    {"id": "fig-01", "title": "渠道满意度对比", "recipe": "grouped_errorbar_bar"},
    {"id": "fig-02", "title": "留存率分布", "recipe": "raincloud_fusion"},
    {"id": "fig-03", "title": "季度趋势", "recipe": "TBD"}
  ]
}
```

规则：同一业务实体跨图同色；同一图型不机械重复；互补视角优先；图号唯一。

## 五、设计令牌与色板

- `assets/tokens.json`：9 大色彩角色、字体栈、字号档位、6 套版式族、物理尺寸、统计诚实规则。
- `assets/palettes.json`：15 套宽松协议色板，含 `category_order`（最大感知色差序）、CVD 最小色差、白底对比度。
- **取色必须用 `category_order`**：只有 2–4 个分类时，不要直接取前 n 个原始色，而要用最大差异序。
- **分类数不得超过 `palette.safe_k`**（色盲模拟下安全区分的最大系列数）；超限必须叠加线型/纹理或合并小类。
- 顺序/发散色阶由 `viz_style.py` 自动派生；禁止 Jet/Rainbow。
- 详细规则见 `references/typography-and-color.md`。

## 六、四条硬规则

1. **统计诚实**：柱状/面积零基线；饼/环 ≤6 类；禁用双 Y 轴；不编造数据或显著性。
2. **标签预算**：最长标签 >12 显示单位且分类 >5 → 横向条形图；严禁 45° 斜排。
3. **尺寸反推**：先定目标引用宽度，再反推 `figsize` 与字号；上页字号 <6pt 必须放大。
4. **不重复出图**：已有基础草图时只做升级重绘或审计，不并行输出两张同义主图。

## 七、文件索引

| 文件 | 用途 |
| :--- | :--- |
| `scripts/profile_data.py` | 大表画像（PEP 723，pandas/numpy/openpyxl） |
| `assets/tokens.json` | 设计令牌与 6 套版式族 |
| `assets/palettes.json` | 色板、`category_order`、CVD 指标 |
| `references/intake-guide.md` | 四档澄清、问题库、默认假设写法 |
| `references/chart-taxonomy.md` | 意图→图种、融合与多面板、误用表 |
| `references/decision-tree.md` | 顺序决策树与快速映射 |
| `references/typography-and-color.md` | 色彩角色、色阶派生、字体、尺寸反推、EXTEND |
| `references/anti-patterns.md` | 分级反模式与交付前 10 秒自检 |

## 八、输出协议

脚本统一返回：

```json
{"status": "success|partial|error", "outputs": [], "rows_used": 0, "rows_dropped": 0,
 "verified": true, "warnings": [], "profile": {}}
```

`status=partial` 表示有警告但可用；`error` 必须把原因原样告知用户，不得静默回退。

## 九、交接给引擎时要说清楚

- 数据文件路径、工作表名、编码；
- 列映射（分类/系列/数值/误差）；
- 统计口径（均值±CI？中位数？缺失如何处理？）；
- 首选配方 ID 与备选；
- 目标物理尺寸、引用宽度、输出格式；
- 是否有 `EXTEND.md` / `figure-manifest.json`；
- 需要避免的误用。

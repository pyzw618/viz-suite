# Matplotlib / Seaborn 现代语法护栏

## 一、必须遵守

1. **对象式 API**：使用 `fig, ax = plt.subplots(...)`；不要依赖 `plt.gca()` 的隐式状态。
2. **先设字体再建图**：`vs.bootstrap()` 已设置 font.family 的有序回退列表。不要只写 `font.family=["sans-serif"]`——那样只会解析到第一个字体，中文会变方块。
3. **物理尺寸优先**：`figsize` 由 `plan_size()` 计算；`savefig` 不要加 `bbox_inches="tight"`，否则实际物理尺寸不可预测，`viz-audit` 的栏宽校验会失真。
4. **透明度用 RGBA 填充**：`vs.bar_kwargs()` 返回带 alpha 的 `color`。**不要再传 `alpha=1.0`**——`Patch.set_alpha` 会覆盖 facecolor 的 alpha，浅填深边会变成死板纯色。
5. **零基线**：柱状/面积图调用 `vs.ensure_zero_baseline(ax, "x"|"y")`；分布图不强制零基线。
6. **颜色**：从 `palette.pick(n)` 取色，不手写 HEX；连续色阶用 `vs.sequential_cmap()`，发散用 `vs.diverging_cmap()`。
7. **白边标记**：散点/折线节点用 `vs.marker_kwargs()`，避免密集点糊成色块。
8. **负号**：`axes.unicode_minus=False`，否则负号可能显示为方块。
9. **PDF 字体嵌入**：`pdf.fonttype=42`；SVG 保留文本（`svg.fonttype="none"`）便于编辑，但跨机查看需安装字体。
10. **导出**：用 `vs.save_figure()`，统一 `pdf/svg` + `300/600dpi PNG` 命名。

## 二、已废弃 / 常见错误写法

| 错误写法 | 现代写法 | 后果 |
| :--- | :--- | :--- |
| `plt.cm.get_cmap("viridis")` | `matplotlib.colormaps["viridis"]` | 3.9+ 废弃警告 |
| `sns.set()` / `sns.set_theme()` | `vs.bootstrap()` + `apply_style()` | 覆盖字体与版式，中文乱码 |
| `plt.style.use("seaborn")` | `apply_style(ax, "soft_grid")` | 旧版样式不兼容 |
| `ax.set_xticklabels(labels)` 未先 `set_xticks` | 先 `set_xticks` 再 `set_xticklabels` | 标签错位 |
| `bar(..., alpha=0.2, color=...)` | `bar(..., **vs.bar_kwargs(color))` | 边线也被整体透明化 |
| `savefig(..., bbox_inches="tight")` | 固定 `figsize` + `subplots_adjust` | 物理尺寸漂移 |
| `fig.text` 放在 `tight_layout` 之后 | 先布局再放文本，或统一用 `subplots_adjust` | 文本被裁切 |
| `violinplot(..., showextrema=True)` | 自绘半小提琴（`fill_betweenx`） | 默认小提琴是全宽且带无关极值线 |
| `boxplot` 默认 `manage_ticks=True` | `manage_ticks=False` + 自行设置刻度 | 刻度被箱线位置覆盖 |
| `plt.tight_layout()` 与手动 `subplots_adjust` 混用 | 只选一种 | 边距互相覆盖 |
| 用 `jet`/`rainbow` | 顺序/发散感知均匀色阶 | 误导梯度、色盲不友好 |

## 三、Seaborn 使用边界

- 可以用 `sns.kdeplot`、`sns.regplot`、`sns.heatmap` 做统计图层，但必须：
  - 在 `vs.bootstrap()` 之后调用，且不调用任何 `sns.set*`；
  - 颜色显式传入 `palette.pick(n)`；
  - 热力图 `annot=True` 时用 `vs.contrast_text()` 计算每个单元格的标签颜色（或关闭 annot，另绘文字）。
- 不要把 Seaborn 的默认主题、字体、网格带回图中。

## 四、中文排版检查

- 中文与拉丁混排时，`font.family` 列表按字形逐个回退：拉丁用 Arial/Inter，汉字自动落到 Microsoft YaHei/SimHei。
- 负号、破折号、百分号、`≥`/`≤` 需确认字体覆盖；`°`、`μ`、`±` 等符号建议用 DejaVu Sans 兜底。
- 长标签换行用 `\n`，不要依赖自动旋转；`viz_style.pick_orientation()` 判定横排。
- 导出后必须用 `audit_export.py` 与宿主读图工具检查 `□□□`、文字踩踏与裁切。

## 五、性能与稳定性

- 大表先在 pandas 侧聚合/分箱，不要把 10 万行原始点直接 scatter；
- 散点超过 5,000 点时降采样或改用二维密度；
- 热力图行列 >50 时关闭单元格标注；
- 固定随机种子（`np.random.default_rng(seed)`），保证 jitter 可复现。

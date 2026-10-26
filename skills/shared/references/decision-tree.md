# 选型决策树与全库模板映射（Decision Tree）

按顺序判断数据形态与表达意图，命中即停；选定后实际打开对应预览图（`<SKILL>/viz-figure/catalog/previews/<id>.jpg`）核对视觉特征。

## 第 0 步：先分流通道

- **单指标或纯观点/流程/层级/架构关系**（非精确坐标数据）→ 转 `viz-diagram`（12 种信息图布局）。
- **需要浏览器交互筛选、Hover 明细或响应式多图联动看板** → 转 `viz-interactive`（15 ECharts + 4 D3 + 看板/KPI）。
- **已有外部网页/SVG/清晰图表截图需提取数据或重绘** → 走 `viz-figure` 逆向管线（`SOURCE / B / C / X`）。
- **出版级静态统计图、多面板科学组图、商业复盘矢量图** → 走 `viz-figure` 正向 28 套黄金配方。

## 第 1 步：核心关系四问（`viz-figure` 选型）

1. **有连续时间或阶段序吗？**
   - 带不确定性包络 → `nested_ci_bands_line`
   - 构成随时间 + 关键事件节点 → `stacked_area_events`
   - 阶段构成 + 总量折线耦合 → `stacked_bar_total_line`
   - 两期名次升降 → `slope_rank_change`；多期名次轨迹 → `bump_rank_trajectory`
   - 随访生存率 + 在险人数 → `km_survival_risk_table`
2. **核心看原始分布还是聚合汇总？**
   - 分布 + 箱体 + 原始散点（每组 n ≥ 20，组 ≤ 6）→ `raincloud_fusion`
   - 成对分组对称分布 + 显著性括号 → `split_violin_box_sig`
   - 双变量散点回归 + 双侧边际核密度 → `marginal_scatter_kde`
   - 两测量方法一致性与偏差界限 → `bland_altman`
3. **聚合对比看大小、增减归因、构成还是流向？**
   - 分组均值 + 误差棒（CI/SD/SEM）→ `grouped_errorbar_bar`
   - 单维排行 + 徽章强调 → `lollipop_rank_badges`
   - 前后测/方案对比差值 Δ → `dumbbell_before_after`
   - 增减拆解 / 消融实验贡献 → `waterfall_ablation`
   - 二八关键少数（降序柱 + 累计曲线）→ `pareto_cumulative`
   - 少量分类占比（≤ 6 类）→ `donut_leader_labels`
   - 多级源-汇流量分配 → `sankey_flow`
4. **多维关系、效应量荟萃或机器学习诊断？**
   - 多指标效应量 + 汇总菱形 → `forest_interval_diamond`；发表偏倚漏斗 → `meta_funnel`
   - 差异倍数 × 显著性阈值 → `volcano_fusion`
   - 相关性聚类矩阵 → `clustered_corr_dendro`；多指标方法排名热力 → `method_rank_heatmap`
   - 多维权衡轮廓 → `parallel_coordinates`；PCA 降维载荷双标 → `pca_biplot`
   - 社群拓扑网络 → `network_hull`
   - 模型解释与诊断：特征贡献 `shap_beeswarm_bars`、概率校准 `calibration_histogram`、残差联合诊断 `residual_violin_corr`

---

## 全库快速映射表（28 统计配方 + 21 交互模板 + 12 信息图布局）

### A. `viz-figure` 静态统计与科学图表（28 套）

| 分析意图 | 配方 ID | 结构族 | 适用场景与核心编码 |
| :--- | :--- | :---: | :--- |
| 分组均值 + 误差棒 | `grouped_errorbar_bar` | single | 1 分类 + 可选系列 + CI/SD/SEM + 总体均值线；窄栏长标签自动转横向 |
| 单维排行徽章 | `lollipop_rank_badges` | single | ≤12 类排名对比，圆点徽章突出头部 |
| 前后测配对差值 | `dumbbell_before_after` | fusion | 两期/双状态点连线 + Δ 差值标注 |
| 两期排名变化 | `slope_rank_change` | fusion | 期初-期末名次斜率连线，焦点高亮 |
| 多期名次轨迹 | `bump_rank_trajectory` | single | ≥3 个时间节点排名演变凹凸图 |
| 增减归因 / 消融 | `waterfall_ablation` | single | 基线 → 正负增量阶梯 → 净结果柱 |
| 帕累托二八分析 | `pareto_cumulative` | multipanel | 降序贡献柱 + 右轴累计占比曲线（80% 阈值线） |
| 构成 + 总量同轴 | `stacked_bar_total_line` | single | 2–4 段堆叠柱 + 顶部总量折线（支持 `SORT_X="total_desc"`） |
| 时序构成 + 事件 | `stacked_area_events` | single | 堆叠面积趋势 + 关键事件竖线批注 |
| 少量分类占比 | `donut_leader_labels` | single | ≤6 类外置引线圆环图 + 环心汇总 |
| 多级流量分配 | `sankey_flow` | single | 自动分层桑基流向图 |
| 嵌套置信带趋势 | `nested_ci_bands_line` | single | 50%/80%/95% 三层渐变置信带折线 |
| 全信息分布对比 | `raincloud_fusion` | fusion | 半小提琴密度 + 窄箱线 + 白边抖动散点 |
| 对称分布 + 显著性 | `split_violin_box_sig` | fusion | 左右拼合小提琴 + 箱线 + 上游检验括号 |
| 散点回归 + 边际分布 | `marginal_scatter_kde` | multipanel | 主图回归散点/二维密度 + 顶/右核密度 |
| 方法一致性评估 | `bland_altman` | fusion | 均值-差值散点 + 偏倚线 + ±1.96 SD 一致性界限 |
| 效应量森林图 | `forest_interval_diamond` | fusion | 多研究/多渠道点估计 + 95% CI + 底部汇总菱形 |
| 发表偏倚漏斗图 | `meta_funnel` | fusion | 效应量 × 标准误三层伪置信漏斗 |
| 差异表达火山图 | `volcano_fusion` | fusion | log2FC × -log10(p) + 背景密度 + 双向防叠引线标注 |
| KM 生存曲线 + 风险表 | `km_survival_risk_table` | multipanel | Kaplan–Meier 阶梯删失曲线 + 对齐在险人数表 |
| 下三角聚类相关矩阵 | `clustered_corr_dendro` | multipanel | 相关系数热力 + 行列层次聚类树 |
| 多指标方法排名热力 | `method_rank_heatmap` | multipanel | 多基准数据集下的方法名次聚类热力矩阵 |
| 多维平行坐标 | `parallel_coordinates` | single | 多指标同向归一化权衡轮廓 |
| PCA 降维双标图 | `pca_biplot` | fusion | 样本主成分得分散点 + 特征载荷向量箭头 |
| 社区凸包网络图 | `network_hull` | fusion | 节点关系图 + 社区半透明凸包底衬 |
| SHAP 可解释性复合图 | `shap_beeswarm_bars` | multipanel | 左侧样本级蜂群色散点 + 右侧平均绝对贡献条 |
| 概率校准诊断图 | `calibration_histogram` | multipanel | 可靠性对角校准曲线 + 底部预测概率分布直方图 |
| 残差与相关性诊断 | `residual_violin_corr` | multipanel | 残差分布小提琴 + 解释变量相关矩阵联排 |

### B. `viz-interactive` 离线交互模板（21 套）

- **ECharts 标准交互（15 套，`templates/echarts/`）**：`line`、`area`、`bar`、`hbar`、`stacked_bar`、`donut`、`scatter`、`bubble`、`heatmap`、`radar`、`funnel`、`gauge`、`boxplot`、`sankey`、`treemap`。
- **D3 定制拓扑（4 套，`templates/d3/`）**：`force_network`（力导向社群）、`chord`（双向弦图）、`treemap`（层级矩形树）、`line_transition`（指标切换过渡）。
- **多图看板与大数页（2 套）**：`templates/dashboard/sales_dashboard.html`（12 列响应式联动驾驶舱）、`templates/kpi/kpi_cards.html`（4 KPI + 内联 Sparkline）。

### C. `viz-diagram` 结构化信息图（12 布局 × 4 皮肤）

- **12 布局**：并列 `list-grid` / `list-row`、顺序 `sequence-steps`、时间 `timeline`、层级 `pyramid` / `hierarchy-tree`、转化 `funnel`、定位 `quadrant`、对比 `compare-binary`、放射 `mindmap`、闭环 `cycle`、大数 `stat-cards`。
- **4 皮肤**：`editorial`（报刊社论）、`minimal`（极简留白）、`technical`（工程架构）、`warm`（亲和暖色）。

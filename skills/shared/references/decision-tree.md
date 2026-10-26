# 选型决策树与全库模板映射（Decision Tree）

按顺序判断数据形态与表达意图，命中即停；选定后实际打开对应预览图（`<SKILL>/viz-figure/catalog/previews/<id>.jpg`）核对视觉特征。

## 第 0 步：先分流通道

- **单指标或纯观点/流程/层级/架构关系**（非精确坐标数据）→ 转 `viz-diagram`（12 种信息图布局 + 6 种咨询/学术皮肤 + 8 套矢量架构 Master 模板）。
- **需要浏览器交互筛选、Hover 明细或响应式多图联动看板** → 转 `viz-interactive`（16 ECharts + 4 D3 + 1 Geo + 看板/KPI，共 23 套模板）。
- **已有外部网页/SVG/清晰图表截图需提取数据或重绘** → 走 `viz-figure` 逆向管线（`SOURCE / B / C / X`）。
- **出版级静态统计图、多面板科学组图、商业复盘矢量图** → 走 `viz-figure` 正向 42 套黄金配方。

## 第 1 步：核心关系四问（`viz-figure` 选型）

1. **有连续时间、事件序列或时序分解吗？**
   - 多序列趋势对比 + 末端直接标注（无图例折返）→ `multi_line_direct_label`
   - 带不确定性包络（P25–P75 / 95% CI）→ `nested_ci_bands_line`
   - 观察值趋势 + LOWESS 平滑 + 同期同比/环比脉冲分解条 → `trend_yoy_decomposed`
   - 构成随时间 + 关键事件节点 → `stacked_area_events`
   - 阶段构成 + 总量折线耦合 → `stacked_bar_total_line`
   - 政策冲击 / 因果推断事件研究（平行趋势检验 + 冲击竖线 + ATT 徽章）→ `event_study_did`
   - 两期名次升降 → `slope_rank_change`；多期名次轨迹 → `bump_rank_trajectory`
   - 随访生存率 + 在险人数 → `km_survival_risk_table`
2. **核心看原始分布、密度山脊还是相关/散点矩阵？**
   - 全信息单/多组分布（半小提琴 + 箱体 + 原始散点）→ `raincloud_fusion`
   - 多组平滑分布密度重叠（Joyplot 山脊图 + IQR 核 + 中位数点）→ `ridgeline_density`
   - 成对分组对称分布 + 显著性括号 → `split_violin_box_sig`
   - 双变量散点回归 + 双侧边际核密度 → `marginal_scatter_kde`
   - 两测量方法一致性与偏差界限 → `bland_altman`
   - 多维权衡轮廓 → `parallel_coordinates`；PCA 降维载荷双标 → `pca_biplot`
3. **聚合对比看大小、增减归因、构成、空间还是流向？**
   - 分组均值 + 误差棒（CI/SD/SEM）+ 标杆冠军标注 → `grouped_errorbar_bar`
   - 单维排行 + 徽章强调 → `lollipop_rank_badges`
   - 表图融合水平横向排行条 + 占比/变化率胶囊 → `hbar_delta_capsule`
   - 降序排行条形图 + 右下角死区内嵌宏观分类环形图 → `ranked_bar_inset_ring`
   - 全局概览排行条 + 2×2 分面细分群体小多面体联动 → `overview_small_multiples`
   - 前后测/方案对比差值 Δ → `dumbbell_before_after`
   - 增减拆解 / 消融实验贡献 → `waterfall_ablation`
   - 二八关键少数（降序柱 + 累计曲线）→ `pareto_cumulative`
   - 少量分类占比（≤ 6 类）外置引线圆环 → `donut_leader_labels`
   - 多级源-汇流量分配 → `sankey_flow`
   - 中国 34 省级行政区方形均权网格地图（防大省视觉压制 + 大区均值对比）→ `china_grid_cartogram`
   - 全球 177 国 Robinson 投影等面积感分级统计地图（免重型 GIS 依赖）→ `world_choropleth_robinson`
4. **多维关系、矩阵热力、效应量荟萃、模型诊断或响应曲面？**
   - 战略四象限矩阵（双均值十字准星 + 策略底色 + 面积权重气泡）→ `bubble_quadrant_matrix`
   - 队列/留存/时段精细热力矩阵（带顶侧/右侧边际均值柱条）→ `heatmap_annotated_grid`
   - 3D 响应连续曲面 + 2D 等高线投影联合分析（带极值标注钉）→ `response_surface_3d_contour`
   - 多指标效应量 + 汇总菱形（Lancet 级表图对齐）→ `forest_interval_diamond`；发表偏倚漏斗 → `meta_funnel`
   - 差异倍数 × 显著性阈值 → `volcano_fusion`
   - 相关性聚类矩阵 → `clustered_corr_dendro`；多指标方法排名热力 → `method_rank_heatmap`
   - 社群拓扑网络 → `network_hull`
   - 二分类模型综合诊断（ROC 置信带 + PR 曲线基线）→ `roc_pr_suite`
   - 多分类混淆矩阵 + 边际精确率与召回率分布柱 → `confusion_matrix_marginal`
   - 模型特征贡献解释（SHAP 蜂群散点 + 绝对贡献条 + Top3 累计贡献标注）→ `shap_beeswarm_bars`
   - 概率校准诊断图 → `calibration_histogram`；残差联合诊断 → `residual_violin_corr`

---

## 全库快速映射表（42 统计配方 + 23 交互模板 + 12 信息图布局 + 8 架构 Master）

### A. `viz-figure` 静态统计与科学图表（42 套）

| 分析意图 | 配方 ID | 结构族 | 适用场景与核心编码 |
| :--- | :--- | :---: | :--- |
| 分组均值 + 误差棒 | `grouped_errorbar_bar` | single | 1 分类 + 可选系列 + CI/SD/SEM + 总体均值线 + ★ 标杆组徽章 |
| 单维排行徽章 | `lollipop_rank_badges` | single | ≤12 类排名对比，圆点徽章突出头部 |
| 表图融合横向条 | `hbar_delta_capsule` | fusion | 水平排行条形图 + 右侧对齐数值、占比与 Δ 增长率胶囊药丸 |
| 死区内嵌环图条 | `ranked_bar_inset_ring` | fusion | 降序条形图 + 右下角天然死区内嵌宏观层级环形图（空间利用极致） |
| 全局与小多面体 | `overview_small_multiples` | multipanel | 左侧全局 Top 排行概览 + 右侧 2×2 分面细分子群小多面体 |
| 前后测配对差值 | `dumbbell_before_after` | fusion | 两期/双状态点连线 + Δ 差值标注 |
| 两期排名变化 | `slope_rank_change` | fusion | 期初-期末名次斜率连线，焦点高亮 |
| 多期名次轨迹 | `bump_rank_trajectory` | single | ≥3 个时间节点排名演变凹凸图 |
| 增减归因 / 消融 | `waterfall_ablation` | single | 基线 → 正负增量阶梯 → 净结果柱 |
| 帕累托二八分析 | `pareto_cumulative` | multipanel | 降序贡献柱 + 右轴累计占比曲线（80% 阈值线） |
| 构成 + 总量同轴 | `stacked_bar_total_line` | single | 2–4 段堆叠柱 + 顶部总量折线 + 柱内占比标签 + ★ 增速峰值 |
| 少量分类占比 | `donut_leader_labels` | single | ≤6 类外置引线圆环图 + 环心汇总 |
| 多级流量分配 | `sankey_flow` | single | 自动分层桑基流向图 |
| 多线末端直标 | `multi_line_direct_label` | single | 4–7 组时序曲线，末端贪心引线直接标注，带 P25–P75 灰色背景带 |
| 嵌套置信带趋势 | `nested_ci_bands_line` | single | 50%/80%/95% 三层渐变置信带折线 |
| 时序趋势与同比分解 | `trend_yoy_decomposed` | multipanel | 上图实际观测值与 LOWESS 平滑趋势，下图共享 X 轴同期同比脉冲柱 |
| 时序构成 + 事件 | `stacked_area_events` | single | 堆叠面积趋势 + 关键事件竖线批注 |
| 双重差分事件研究 | `event_study_did` | single | 政策冲击前后平行趋势检验 + 冲击竖线 + 95% CI 带 + ATT 均值徽章 |
| 全信息分布对比 | `raincloud_fusion` | fusion | 半小提琴密度 + 窄箱线 + 白边抖动散点 |
| 峰峦山脊核密度 | `ridgeline_density` | single | 垂直重叠山脊核密度 Joyplot + 羽毛渐变填色 + IQR 核心区与中位数点 |
| 对称分布 + 显著性 | `split_violin_box_sig` | fusion | 左右拼合小提琴 + 箱线 + 上游检验括号 |
| 散点回归 + 边际分布 | `marginal_scatter_kde` | multipanel | 主图回归散点/二维密度 + 顶/右核密度 |
| 战略四象限气泡 | `bubble_quadrant_matrix` | single | 双指标均值交叉十字准星 + 四象限战略底衬 + 气泡面积权重 |
| 方法一致性评估 | `bland_altman` | fusion | 均值-差值散点 + 偏倚线 + ±1.96 SD 一致性界限 |
| 效应量森林图 | `forest_interval_diamond` | fusion | 多研究/多渠道点估计 + 95% CI + Lancet 级表格对齐 + 底部汇总菱形 |
| 发表偏倚漏斗图 | `meta_funnel` | fusion | 效应量 × 标准误三层伪置信漏斗 |
| 差异表达火山图 | `volcano_fusion` | fusion | log2FC × -log10(p) + 背景密度 + 双向防叠引线标注 |
| KM 生存曲线 + 风险表 | `km_survival_risk_table` | multipanel | Kaplan–Meier 阶梯删失曲线 + 对齐在险人数表 |
| 边际柱带热力矩阵 | `heatmap_annotated_grid` | multipanel | 留存/队列热力色块 + 顶部列均值柱 + 右侧行均值柱 + 核心峰值框 |
| 下三角聚类相关矩阵 | `clustered_corr_dendro` | multipanel | 相关系数热力 + 行列层次聚类树 |
| 多指标方法排名热力 | `method_rank_heatmap` | multipanel | 多基准数据集下的方法名次聚类热力矩阵 |
| 3D 曲面与等高线投影 | `response_surface_3d_contour` | multipanel | 左侧 3D 连续响应曲面 $z=f(x,y)$ + 右侧 2D 等高线投影与最优极值钉 |
| 多维平行坐标 | `parallel_coordinates` | single | 多指标同向归一化权衡轮廓 |
| PCA 降维双标图 | `pca_biplot` | fusion | 样本主成分得分散点 + 特征载荷向量箭头 |
| 社区凸包网络图 | `network_hull` | fusion | 节点关系图 + 社区半透明凸包底衬 |
| ROC 与 PR 曲线诊断 | `roc_pr_suite` | multipanel | 左 ROC 曲线 + Bootstrap 羽毛置信带 + Youden-J 标杆；右 PR 曲线 + 基线 |
| 混淆矩阵与边际分布 | `confusion_matrix_marginal` | multipanel | $C\times C$ 混淆矩阵百分比 + 顶部精确率柱 + 右侧召回率柱 + Macro-F1 徽章 |
| SHAP 可解释性复合图 | `shap_beeswarm_bars` | multipanel | 左侧样本级蜂群色散点 + 右侧平均绝对贡献条 + Top3 累计贡献标注 |
| 概率校准诊断图 | `calibration_histogram` | multipanel | 可靠性对角校准曲线 + 底部预测概率分布直方图 |
| 残差与相关性诊断 | `residual_violin_corr` | multipanel | 残差分布小提琴 + 解释变量相关矩阵联排 |
| 中国省级均权网格地图 | `china_grid_cartogram` | multipanel | 34 省级行政区方形网格示意（防新疆西藏视觉压制）+ 7 大行政区均值对比柱 |
| 全球罗宾逊投影分级地图 | `world_choropleth_robinson` | multipanel | 纯 NumPy 罗宾逊投影全球 177 国分级色彩地图 + Top/Bottom 极值排行条 |

### B. `viz-interactive` 离线交互模板（23 套）

- **ECharts 标准交互（16 套，`templates/echarts/`）**：`line`、`area`、`bar`、`hbar`、`stacked_bar`、`donut`、`scatter`、`bubble`、`heatmap`、`radar`、`funnel`、`gauge`、`boxplot`、`sankey`、`treemap`、`pareto`（帕累托二八双轴交互）。
- **D3 定制拓扑（4 套，`templates/d3/`）**：`force_network`（力导向社群）、`chord`（双向弦图）、`treemap`（层级矩形树）、`line_transition`（指标切换过渡）。
- **空间均权交互（1 套，`templates/geo/`）**：`china_grid_interactive.html`（中国 34 省级行政区交互网格与区域联动）。
- **多图看板与大数页（2 套）**：`templates/dashboard/sales_dashboard.html`（12 列响应式联动驾驶舱）、`templates/kpi/kpi_cards.html`（4 KPI + 内联 Sparkline）。

### C. `viz-diagram` 结构化信息图（12 布局 × 6 皮肤 + 8 架构 Master）

- **12 布局**：并列 `list-grid` / `list-row`、顺序 `sequence-steps`、时间 `timeline`、层级 `pyramid` / `hierarchy-tree`、转化 `funnel`、定位 `quadrant`、对比 `compare-binary`、放射 `mindmap`、闭环 `cycle`、大数 `stat-cards`。
- **6 皮肤**：
  - `editorial`（报刊社论）：暖纸色、衬线标题、粗细分明网格；
  - `minimal`（高留白极简）：近白背景、克制蓝点、无阴影；
  - `technical`（工程网格）：蓝灰底色、等宽标签、架构底衬；
  - `warm`（柔和圆角）：奶油色、珊瑚青绿、轻柔阴影；
  - `mckinsey`（战略咨询）：深海蓝 `#00205B`、电光青 `#00A3E0`、金色批注、紧凑标题、严谨发丝边框；
  - `academic_blueprint`（学术蓝图）：蓝图深蓝 `#0B2545`、鼠尾草绿 `#134074`、浅蓝底 `#EEF4F8`、等宽标注。
- **8 套独立矢量 SVG 架构 Master 模版（`templates/svg-masters/`）**：
  - `layered_tech_stack.svg`：现代化分层技术中台架构（客户端/网关/服务/基础设施）
  - `swimlane_pipeline.svg`：跨部门泳道业务流程图（产品/研发/测试/运维）
  - `mckinsey_scqa_pyramid.svg`：麦肯锡金字塔原理 SCQA 战略推导图
  - `dual_flywheel_loop.svg`：双飞轮增长与网络效应商业闭环模型
  - `value_chain_chevron.svg`：波特价值链燕尾箭头端到端业务流
  - `medallion_lakehouse.svg`：现代数据栈湖仓一体 Medallion 架构（Bronze/Silver/Gold）
  - `agentic_rag_loop.svg`：自主 AI 智能体检索增强与反思闭环
  - `competitive_2x2_radar.svg`：竞品对标战略 2×2 矩阵与核心能力雷达图

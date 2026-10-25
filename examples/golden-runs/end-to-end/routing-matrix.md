# 路由矩阵

## 描述微调

- 10 个 SKILL.md 的 description 增加“不用于截图逆向（用 viz-reverse）”边界，避免与正向引擎混淆。
- viz-reverse description 增加“不用于正向绘图/看板/信息图（用对应引擎）”，并保留登录/付费墙/版权的负向边界。
- viz-audit 明确不用于逆向数据提取；场景模块明确不用于截图逆向。

## 正例（12 个任务）

| ID | 用户任务 | 主路由 | 场景 | 支撑 | 不应使用 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| R01 | 把三组前后测实验数据做成期刊双栏三面板图，均值 95% CI、趋势带、配对变化，注明 n/CI，不编造显著性。 | `viz-python` | `viz-scene-academic` | `viz-audit` | `viz-web`, `viz-infographic` |
| R02 | 用经营数据做可筛选月份/渠道的销售驾驶舱，KPI、实际 vs 目标、渠道构成、明细表，桌面和手机都验收。 | `viz-web` | `viz-scene-bi` | `viz-audit` | `viz-python`, `viz-infographic` |
| R03 | 把 2025 上半年复盘做成一页纸信息图，四个核心数字，报刊风格，带来源口径。 | `viz-infographic` | — | `viz-web`, `viz-audit` | `viz-python` |
| R04 | 这张别人的柱状图截图，反推数据后换成我们的品牌色重绘，保留数据但不要复制原图风格。 | `viz-reverse` | — | `viz-python`, `viz-audit` | `viz-web` |
| R05 | 这张图基线截断、彩虹色、标签旋转、没有来源；诊断并重绘一张可信排序横条图。 | `viz-audit` | — | `viz-python`, `viz-core` | `viz-reverse` |
| R06 | 从区域销售表完成统计摘要、图表和两页 PDF，并给 5 页 PPT 交接提纲。 | `viz-core` | — | `viz-python`, `viz-audit`, `host:pdf`, `host:pptx` | `viz-web` |
| R07 | 把 A/B 实验按渠道汇总成森林图，双栏、95% CI、n、汇总菱形，适合期刊投稿。 | `viz-python` | `viz-scene-academic` | `viz-audit` | `viz-web` |
| R08 | 用合成网格 GeoJSON 做区域分级设色，缺失区域斜纹，独立图例，标注 CRS/底图来源。 | `viz-python` | `viz-scene-geo` | `viz-audit` | `viz-web` |
| R09 | 把上半年渠道变化做成一页 16:9 高管汇报图：Action Title、单焦点色、灰色背景系列、直接标注。 | `viz-python` | `viz-scene-story` | `viz-audit` | `viz-web` |
| R10 | 把离线可视化管线做成技术风步骤信息图，输出 HTML/SVG，桌面与手机无溢出。 | `viz-infographic` | — | `viz-web`, `viz-audit` | `viz-python` |
| R11 | 从这个本地 ECharts 页面精确提取数据和配置，输出可复现 JS/data.csv，不要像素猜测。 | `viz-reverse` | — | `viz-audit` | `viz-python`, `viz-web` |
| R12 | 这张低清柱图和 3D 饼图能不能反推数据？给出证据等级、风险和替代。 | `viz-reverse` | — | `viz-audit` | `viz-python`, `viz-infographic` |

## 负例（最终形态优先）

| ID | 用户任务 | 应走 | 不应走 | 原因 |
| :--- | :--- | :--- | :--- | :--- |
| N01 | 把这篇论文的森林图改成能筛选月份和渠道的网页看板。 | `viz-web` | `viz-python`, `viz-scene-academic` | 最终交互形态是看板；学术场景差分不再适用。 |
| N02 | 用 ECharts 画一张要投期刊的双栏矢量图。 | `viz-python` | `viz-web`, `viz-infographic` | 期刊矢量/双栏优先于交互引擎。 |
| N03 | 给这张信息图加一个区域筛选器和 Hover 详情。 | `viz-web` | `viz-infographic` | 交互筛选是 Web 引擎职责；信息图只负责静态结构。 |
| N04 | 从这张 3D 饼图精确还原每个扇区的数值。 | `viz-reverse` | `viz-python`, `viz-infographic` | 3D 透视不可逆；viz-reverse 必须 X 级拒绝，而不是由正向引擎编数。 |

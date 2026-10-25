资料中涵盖的 **AI Agent 数据可视化 Skill 与系统** 呈现出高度专业化和场景细分化的生态格局。按应用领域、设计哲学和渲染引擎，可将这些 Skill 和系统划分为以下五大核心阵营：

---

### 一、 学术科研与论文绘图 Skill 阵营

#### 1. `yjz211/vivid-illustration-skill`（含 `vivid-figure-skill` & `vivid-architecture-diagram-skill`）
*   **核心特点**：采用“主入口 + 双通道”的解耦路由架构，将定量数据图与结构架构图严格隔离，避免规则冲突。强调真实数据源的代码级保真，严禁用插图代替数据证据。支持鲜艳与稳重等多种配色风格，兼顾论文发表与竞赛展示。
*   **包含场景**：科研论文写作、数学建模竞赛、实验对比报告、数据量值证据展示（如误差分布、收敛曲线、雨云图、三维曲面）以及系统/算法架构图绘制。
*   **包含素材/资产**：包含 **108–145 个可视化配方卡**、图表说明卡、多套预设配色方案、SVG 矢量架构模板、Python (Matplotlib/Seaborn) 绘图源码及可编辑 PPTX 交付产物。

#### 2. `Dsadd4/AgentFigureGallery`
*   **核心特点**：面向 Claude Code、Codex、Cursor 等 AI 编码 Agent 的即插即用型科研绘图 Skill。以 Nature 等顶级期刊的真实图表为基准，结合优质开源代码，通过“参考图引导（Reference-guided）”范式生成高质量图表。
*   **包含场景**：生物信息学、细胞生物学及物理/化学领域的顶级期刊论文插图绘制。
*   **包含素材/资产**：包含 **16,341 个视觉候选样本**（覆盖 10 种常见科研图表类型）、Nature/Science/Cell 风格参考包以及 Python/ggplot2 绘图参考源码。

#### 3. `dazhiyang/scientific-plotting-skill`
*   **核心特点**：专为生物医药与统计学论文打造的出版级图表 Skill，强制遵守顶级期刊严格的版面排版与视觉标准。
*   **包含场景**：生物医药统计分析展示、期刊论文矢量插图绘制。
*   **包含素材/资产**：限定 **85mm（单栏）** 与 **180mm（双栏）** 期刊标准版面尺寸，强制采用 Wong 色盲友好色板、Viridis 连续渐变色板及 Times 字体排版规则，输出矢量 PDF 及高 DPI PNG。

---

### 二、 商业咨询与战略汇报 Visual Skill 阵营

#### 1. `kgraph57/mckinsey-style-visualization-skill`
*   **核心特点**：将麦肯锡等咨询公司的 **金字塔原理（Pyramid Principle）** 与 **SCQA 结构** 深度注入规则中。要求“结论先行”并采用断言式标题（Action Titles）。采用零第三方依赖（仅基于 Python 3 标准库）的声明式 JSON Spec 驱动渲染引擎，环境免疫力极高。
*   **包含场景**：董事会汇报、战略规划（Where to play / How to win）、项目 PMO 状态审查、市场进入分析、客户销售提案及日本企业决策文书（稟議書、役員会资料等）。
*   **包含素材/资产**：包含 **22 种原生 SVG 矢量 Pattern**（如瀑布图、2x2 矩阵、漏斗图、甘特图等）与 13 种结构规范，**6 套预填完整故事线的大牌模板（Archetypes）**，支持导出单文件动画 HTML 幻灯片、A4 打印版 HTML 报告、演讲脚本文档以及 PPTX/Word/PDF。

#### 2. `antvis/Infographic` (`Infographic Syntax Creator`)
*   **核心特点**：由蚂蚁集团 AntV 团队推出的声明式信息图表引擎，语法专为 AI 提示生成优化。采用轻量级 Infographic DSL 语法，支持 **流式增量渲染**（大模型边生成文本，前端边实时绘制图形）。
*   **包含场景**：商业信息图表、知识可视化、咨询级结构拆解、高管汇报/演讲演示视觉呈现。
*   **包含素材/资产**：内置 **200+ 商业与咨询模板**（涵盖金字塔 `list-pyramid`、四象限 `compare-quadrant`、对比层级 `compare-hierarchy-row`、组织架构/脑图 `hierarchy-structure/mindmap`、序列阶梯 `sequence-stairs` 等 16 大设计族），支持多样主题风格（手绘、渐变、预设主题）以及矢量 SVG/PNG/HTML 导出。

---

### 三、 企业级图表语法与全域路由 Skill 阵营

#### 1. `antvis/chart-visualization-skills`（含 G2, G6, X6, GPT-Vis, T8 NTV）
*   **核心特点**：整合了 AntV 旗下 G2（统计图表）、G6（图可视化）、X6（图编辑器）、GPT-Vis（多端渲染）与 T8 NTV（叙事文本）全套图形语法生态。引入 **向量与全文检索（zvec+HNSW+RRF 融合）** 机制，能根据自然语言意图精准自动匹配加载最合适的子 Skill。
*   **包含场景**：企业级日常报表、动态数据仪表盘、网络关系图、流程图/DAG/ER 编辑器、数据解读叙事报告。
*   **包含素材/资产**：覆盖 26+ 种统计图表类型，10+ 种 G6 布局算法（Force, Dagre, Mindmap, Fishbone 等），X6 编辑器 11 个官方插件，矢量 SVG、JavaScript/React/Vue 渲染代码及 JSON 配置。

#### 2. `OpenAI / data-visualization`（收录于 `agent-skills-library`）
*   **核心特点**：作为整个可视化体系的 **隐式调度器（Implicit Orchestrator）**，拥有 9 步路由分发工作流。建立严格的技术栈优先梯队（声明式语法 > D3/SVG > Canvas2D > WebGL/3D），并强制执行色彩账本（Color-role ledger）控制。
*   **包含场景**：全域 Web 数据可视化、统计分析、地理空间地图、甘特图、网络拓扑、三维/粒子数据渲染、Scrollytelling 滚动叙事、无障碍（a11y）审阅。
*   **包含素材/资产**：内置 Vega-Lite/Vega 声明式规范、D3/SVG 渲染模板、Canvas2D/WebGL 渲染管线、地理地图衬底库以及各类设计契约模板（如 `chart-brief`、`visual-design-contract`）。

---

### 四、 软件架构、系统设计与技术图表 Skill 阵营

#### 1. `Agents365-ai/drawio-skill`
*   **核心特点**：能将自然语言、代码库、IaC 配置及数据库 Schema 直接转换为可二次编辑的 `.drawio` 架构模型。支持多视图投影、增量同步（不破坏手动布局）与自检自动修复（通过读取渲染 PNG 自动纠正重叠与边缘碰撞）。
*   **包含场景**：微服务架构、云原生/IaC 部署拓扑（AWS/Azure/GCP/K8s）、网络拓扑、UML 类图/时序图、C4 模型（支持点击下钻）、ML/深度学习网络（标注 Tensor shape）、BPMN/SysML 及代码库可视化。
*   **包含素材/资产**：内置 **10,000+ 官方矢量形状**，**321 个 AI/LLM 品牌矢量 Logo**（OpenAI, Claude, Gemini, DeepSeek 等）与 18 个数据存储品牌 Logo，11 种图表预设类型，支持导出原生 `.drawio`、交互式 HTML、PPTX、动画数据流 SVG、Mermaid 等。

#### 2. `cathrynlavery/diagram-design`
*   **核心特点**：极简编辑主义（Editorial style）图表 Skill，主打“高画质删除法”——无阴影、1px 细线、4px 坐标网格，保留唯一 Accent 调和色。支持一键吸取用户网站品牌颜色与字体（Onboarding）。
*   **包含场景**：软件系统架构、IT 现况与现代化演进（Architecture delta）、决策流程图、状态机、ER 模型、四象限图、轴测拆解图（Exploded axonometric）及平面轴测图（Axonometric plan）。
*   **包含素材/资产**：包含 **45 种图表类型**（每种含 minimal light、minimal dark、full-editorial 3 种变体），9 种语义行为模式，支持直接将 draw.io、Mermaid、Excalidraw 重绘为统一品牌风格，输出无依赖单文件 HTML+SVG。

#### 3. `bybit-exchange/svg-diagram`
*   **核心特点**：专注于纯 SVG 矢量图表生成的严谨设计 Skill，特别优化了 CJK（中日韩）字体排版与防碰撞矩阵算法，支持通过全局平移矩阵（Transform matrix）纠正边距与对齐。
*   **包含场景**：系统架构图、数据流图、流程图、序列表、网络拓扑图。
*   **包含素材/资产**：提供完整的矢量 SVG 代码生成规约、防重叠矩阵计算规则、CJK 字体回退表及标尺对齐模板。

#### 4. `nicobailon/visual-explainer`
*   **核心特点**：将复杂终端输出或代码变更转化为美观、交互式的 HTML 页面或 Slide，摆脱 ASCII 字符与终端表格折行问题。
*   **包含场景**：系统架构解释、代码 Diff 评审（`/diff-review`）、需求与计划审计（`/plan-review`）、数据表格与项目复盘。
*   **包含素材/资产**：内置 **11 种主题配色**（Dracula, Nord, One Dark, Catppuccin, Gruvbox 等），手绘风动画图表组件，无依赖 HTML 页面生成器及 PPTX 导出工具。

---

### 五、 极简主义、无障碍与低代码/协同设计 Skill 阵营

#### 1. `gnurio/tufte-vdqi-plugin`
*   **核心特点**：贯彻 Edward Tufte 的《定量信息视觉显示》（VDQI）原则，以“最大化数据-墨水比（Data-Ink Ratio）”和“剥离图表垃圾（Chartjunk）”为核心，自动计算谎言因子（Lie Factor）并用区间框（Range-frame）代替传统坐标轴。
*   **包含场景**：极简定量数据展示、学术数据质检、高数据密度图表渲染。
*   **包含素材/资产**：包含 Tufte 评分引擎、谎言因子校验器、区间框散点图/折线图生成器，直接输出纯净 SVG。

#### 2. `xability/maidr-skill`
*   **核心特点**：专为无障碍（a11y）设计的视觉 Skill，基于 MAIDR 框架，将视觉图表无缝转化为视障人士可感知的多模态交互形式。
*   **包含场景**：公共数据发布、无障碍网页与报表制作、全人群数据交互。
*   **包含素材/资产**：绑定 `maidr.js` / `py-maidr` 引擎，提供 **方向键键盘导航**、**屏幕阅读器文本**、**音效化**（Sonification，用音高代表数值趋势）、**电子盲文（Braille）展示** 及 **AI 视觉场景描述**。

#### 3. `nexu-io/open-design`
*   **核心特点**：开源的本地优先（Local-first）AI 协同设计与 Agent 工作台，整合了 19 个功能 Skill 与 71+ 品牌级设计系统。拥有五维自审机制（Critique）和反 AI 杂乱检查清单。
*   **包含场景**：Web/移动端原型（iPhone/Pixel 框架）、SaaS Landing Page、数据仪表盘（Dashboard）、杂志级 PPT、社交媒体 Carousel、HyperFrames 动态视频/Motion Graphics。
*   **包含素材/资产**：**71+ 设计系统**、15 套 HTML Deck 模板（含 Guizang PPT）、93 个开箱即用 Prompt 模板、5 种视觉流派、HeyGen 开源 HyperFrames 动态视频框架，支持导出 HTML, PDF, PPTX, MP4。

#### 4. 低代码与工作流插件（Dify 生态：`dify_echarts` & `smart_excel_kit`）
*   **`dify_echarts`**：在 Dify 工作流中将统计数据直接解析转换为 Apache ECharts JSON 配置并渲染展示，适用于业务报表与数据自动化 Pipeline。
*   **`smart_excel_kit`**：本地优先的智能 Excel 处理插件，利用 LLM 分析 Excel/CSV 列数据、生成销售/雷达/散点图表，并批量解析图像 URL 输出处理后的 Excel 文件。

---


为方便快速跳转学习，以下汇总了报告中涵盖的主要开源 Skill 与系统的项目链接列表：

---

### 1. 学术科研与论文绘图阵营
*   **`yjz211/vivid-illustration-skill`**：[GitHub 仓库链接](https://github.com/yjz211/vivid-illustration-skill)
*   **`Dsadd4/AgentFigureGallery`**：[GitHub 仓库链接](https://github.com/Dsadd4/AgentFigureGallery)
*   **`dazhiyang/scientific-plotting-skill`**：[GitHub 仓库链接](https://github.com/dazhiyang/scientific-plotting-skill)

### 2. 商业咨询与战略汇报阵营
*   **`kgraph57/mckinsey-style-visualization-skill`**：[GitHub 仓库链接](https://github.com/kgraph57/mckinsey-style-visualization-skill)
*   **`antvis/Infographic`**：[GitHub 仓库链接](https://github.com/antvis/Infographic)

### 3. 企业级图表语法与全域路由阵营
*   **`antvis/chart-visualization-skills`**：[GitHub 仓库链接](https://github.com/antvis/chart-visualization-skills)
*   **`OpenAI / data-visualization`**：[Agent Skills Library 目录链接](https://github.com/agent-skills-library/original-skills/tree/main/x-openai-data-visualization-ae23089)

### 4. 软件架构与技术图表阵营
*   **`Agents365-ai/drawio-skill`**：[GitHub 仓库链接](https://github.com/Agents365-ai/drawio-skill)
*   **`cathrynlavery/diagram-design`**：[GitHub 仓库链接](https://github.com/cathrynlavery/diagram-design)
*   **`bybit-exchange/svg-diagram`**：[GitHub 仓库链接](https://github.com/bybit-exchange/svg-diagram)
*   **`nicobailon/visual-explainer`**：[GitHub 仓库链接](https://github.com/nicobailon/visual-explainer)

### 5. 极简主义、无障碍与协同设计阵营
*   **`gnurio/tufte-vdqi-plugin`**：[GitHub 仓库链接](https://github.com/gnurio/tufte-vdqi-plugin)
*   **`xability/maidr-skill`**：[GitHub 仓库链接](https://github.com/xability/maidr-skill)
*   **`nexu-io/open-design`**：[GitHub 仓库链接](https://github.com/nexu-io/open-design)
*   **`canjian215215/dify_echarts`**：[GitHub 仓库链接](https://github.com/canjian215215/dify_echarts)
*   **`sawyer-shi/dify-plugins-smart_excel_kit`**：[GitHub 仓库链接](https://github.com/sawyer-shi/dify-plugins-smart_excel_kit)

---

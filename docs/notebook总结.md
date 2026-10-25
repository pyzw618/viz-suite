# AI Agent 数据可视化 Skill 与开源生态全景调研报告

## 1. 绪论：大模型时代 AI Agent 数据可视化的范式转移与生态版图

在生成式人工智能与大语言模型（LLM）加速演进的浪潮中，数据可视化正经历一场深刻的范式转移。传统的“人类开发者手动编写指令式代码（如 D3.js、Matplotlib 或 Highcharts）”开发模式，正在快速向“Agent 声明式生成配置与 MCP（Model Context Protocol）工具调用”的新范式演进。大模型本身具备强大的文本推理与结构化数据处理能力，但在直接输出高维视觉图形时存在天然的“语义-渲染”断层。数据可视化 Skill 与工具链作为中间桥梁，能够将 Agent 抽象的文本逻辑与数据推理结果，精准转化为高维、直观、可交互且符合合规标准的视觉表达。

从系统架构的视角审视，当前 AI Agent 数据可视化 Skill 生态已呈现出多元化发展与高度分工的格局，主要可归纳为以下**五大核心阵营**：

1. **学术科研与论文绘图阵营**：专注于高精度数学建模、实验数据可复现性（Jupyter Notebook 工具链）以及将位图逆向重构为可编辑矢量图（SVG）。
2. **商业咨询与战略汇报阵营**：专注于金融级 Excel 表格建模、零错误公式重算、CRM 业务指标分析与金融账户 API 直连。
3. **企业级图表语法与全域路由阵营**：基于标准化声明式 JSON 语法、服务端渲染（SSR）与 MCP 协议，实现全域图表自动推荐、Schema 校验与单次工具调用渲染。
4. **图像合成、模型路由与自动化评测阵营**：涵盖多模态图像生成、动态 AI 模型成本/延迟路由，以及 Agent 可视化能力 Benchmark 评测基准打包。
5. **极简、无障碍与协同设计阵营**：聚焦 WCAG 2.1 AA 无障碍标准、声化（Sonification）多模态交互，以及基于矢量图结构图（CSG）的双向约束协同重构。

在 Agent 的交互与架构设计中，数据生成与渲染模式的选择直接决定了系统的稳定性、上下文 Token 消耗以及最终的用户体验：

| 对比维度 | 纯代码生成模式（如 D3.js / Matplotlib） | 声明式 JSON / MCP 渲染模式（如 Highcharts MCP / SVG） |
| --- | --- | --- |
| LLM 语义报错率 | 高（包含大量复杂的方法链操纵、DOM/SVG 语法操纵与手动坐标缩放计算，指令表面积大，易产生语法幻觉） | 极低（基于严格 Schema 约束的纯声明式 JSON 或结构化 SVG Token，语义明确，消除代码拼接错误） |
| 执行与上下文成本 | 高（必须配备沙盒代码执行环境；生成大量命令式代码会迅速挤占 LLM 上下文窗口；需多步骤交互与环境配置） | 极低（Agent 只需单次工具调用或输出纯 JSON 配置，服务端实时返回渲染图，上下文占用小，执行零摩擦） |
| 感知与无障碍体验 | 参差不齐（完全依赖开发者手动编写 ARIA 属性与键盘事件处理，Agent 难以自主校验对比度与 DOM 结构，无障碍保障弱） | 优异（原生集成 WCAG 2.1 AA 标准，自动构建离屏 HTML 数据表、键盘焦点环与数据声化表达，无障碍开箱即用） |

这种技术路径的显著差异，促使声明式 JSON 接口、MCP 工具调用以及基于强化学习的矢量逆向技术，成为了当代 AI Agent 架构师构建可视化能力时的核心选择。在这一全景图下，学术科研与论文绘图领域对数据精度和图形保真度的严苛要求，构成了可视化 Skill 生态中最具技术挑战性的前沿。

## 2. 学术科研与论文绘图阵营 (Academic Research & Paper Plotting)

学术论文与科研建模对数据可视化有着极高的门槛要求，包括图形的绝对数据保真度、数学语义的准确表达、实验环境的可复现性，以及严苛的出版级学术合规性。AI Agent 通过集成专项 Skill 与逆向工程 MLLM 模型，能够将繁重的绘图代码编写、数据清洗及图表矢量化重构过程全面自动化。

### 2.1 yjz211/vivid-illustration-skill：科研与数学建模图表 Skill

- **能力模块定位**：专门针对科研与数学建模数据图规划、生成、修改及合规性检查的 Agent 技能模块（yjz211/vivid-illustration-skill，GitHub: yjz211/vivid-illustration-skill）。
- **输入/输出契约与资源储备**：输入为原始统计数据或自然语言绘图需求，输出为符合学术出版规范的结构化图表代码与图形配置。内部储备了 145 个专业配方（Recipes）、3 套高维组合模板，以及配套的学术级统计配色方案。
- **执行与合规安全 Profile**：能够在 Agent 推理链中对数据的统计语义（Statistical Semantics）进行自动判读，校验色盲友好度（Color-blind safe）与出版分辨率合规性，有效避免数据视觉误导，确保生成的图件直接满足学术期刊的审稿标准。

### 2.2 DetachHead/rebased：可复现性能实验与 Jupyter Notebook 工具链

- **能力模块定位**：专注于为 AI Agent 提供自动化构建与维护可复现性能实验的 Jupyter Notebook 技能模块（DetachHead/rebased，GitHub: DetachHead/rebased）。
- **输入/输出契约与资源储备**：依托极速 Python 环境配置工具 uv 与 nb.py 自动化 CLI 工具，为 Agent 提供对 Notebook 单元格（Cells）进行增删改查、自动化代码执行、Patch 补丁应用与动态状态更新的接口。
- **执行与合规安全 Profile**：构建完全隔离且可复现的实验沙盒，解决大模型在代码执行过程中的环境依赖冲突问题，实现性能测试数据流从记录、分析到可视化呈现的全干预自动化。

### 2.3 Chart2SVG：位图转可编辑 SVG 图表逆向工程 MLLM 系统

- **架构解构与模型基座**：基于 Qwen3-VL 架构构建的多模态大语言模型（提供 4B 与 8B 参数版本，开源仓库：JinningCui/Chart2SVG），旨在将静态位图（PNG/JPG）逆向重构为语义化、结构化且可编辑的矢量 SVG 图表。
- **115 个 SVG 语法专项 Token 词表**：为了消除传统 LLM 生成原生 XML 字符串时的语法幻觉与 Token 膨胀，系统在词表中扩展了 115 个 SVG 语法专项 Token（划分为结构容器 $\mathcal{V}_{struct}$、图形图元 $\mathcal{V}_{prim}$、视觉通道属性 $\mathcal{V}_{attr}$、几何指令 $\mathcal{V}_{geom}$ 4 大类），将矢量生成重构为高效率的语法单元预测。
- **Beagle+ 数据集血统与预处理**：针对原始 Web 采集 SVG 存在结构冗余与工具依赖的问题，研发团队基于 Beagle 数据集（涵盖 41K 个 SVG 可视化，覆盖 24 种图表类型，并特别剔除了长尾无序的 D3 子集）以及从 ECharts 官方画廊爬取的 276 个样本，经过规范化与结构蒸馏（统一 viewBox、样式属性化、路径相对化、去冗余），过滤掉超过 8,192 Token 长度限制的稠密图表，最终构建出包含 33,000 个高保真规范图表 Pair 的 **Beagle+ 数据集**（HuggingFace 托管：syslocker/Beagle_Plus）。
- **渲染感知 GRPO 强化学习 (Reinforcement Learning)**：在 SFT 阶段之后，模型采用组相对策略优化（GRPO）进行 post-training 强化学习，构建了结合代码规范与视觉渲染双重反馈的奖励机制：
  1. **代码级奖励（$R_{\text{code}}$）**：包含语法可执行性校验 $R_{\text{valid}}$ 与序列长度惩罚 $\mathcal{P}_{\text{len}}$，公式为 $R_{\text{code}}(S_i) = R_{\text{valid}}(S_i) - \lambda_{\text{len}} \mathcal{P}_{\text{len}}(S_i)$，严格惩罚不可渲染代码与重复冗余生成。
  2. **视觉级奖励（$R_{\text{vis}}$）**：融合前景 IoU（采用 $5 \times 5$ 结构元素膨胀 dilate 以容忍亚像素级的渲染位移）、峰值信噪比 PSNR（通过 40 dB 上限进行归一化）以及结构相似性 SSIM（采用绝对交叉协方差 $|\sigma_{xy}|$ 以避免早期训练产生负向惩罚）。综合奖励计算公式为：

     $$R(S_i, I) = \lambda_{\text{code}} R_{\text{code}}(S_i) + \lambda_{\text{vis}} R_{\text{vis}}(\tilde{I}_i, I)$$

- **图表结构图 (CSG) 支撑**：重构生成的 SVG 可无缝转化为图表结构图（Chart Structure Graph, CSG），支撑语言驱动的图表双向约束编辑与数据重构。

| 评估维度 | vivid-illustration | DetachHead/rebased | Chart2SVG MLLM 系统 |
| --- | --- | --- | --- |
| 数据精度 (Data Precision) | 高（基于原始数据） | 极高（真实实验数据流） | 中高（基于视觉矢量重构） |
| 格式可编辑性 (Editability) | 中（取决于代码/模板） | 高（支持 Notebook Patch） | 极高（输出 CSG 与原生 SVG） |
| 科研出版合规性 (Research Compliance) | 极高（内置 145 配方） | 极高（环境双重复现，uv 驱动） | 高（精准还原论文矢量原貌） |

从追求绝对数学精度与出版规范的科研绘图场景延伸，企业商业决策对零错误计算、财务格式标准以及与数据库的实时对接提出了更为严格的工程化要求。

## 3. 商业咨询与战略汇报阵营 (Business Consulting & Strategic Reporting)

在商业咨询与企业战略汇报中，数据分析的严密性与财务模型的合规性至关重要。幻觉导致的数值错误或格式不符合财务规范（如缺乏标准的颜色编码 Color-coding），都会直接破坏决策的有效性。AI Agent 通过集成金融级表格处理矩阵与 CRM/数据库直连 Skill，构建起高度可靠的企业级数据决策管道。

### 3.1 金融级与企业表格建模 Skill 矩阵 (Financial & Enterprise Table Processing Architecture)

在 LLM 的推理循环中，如果直接让模型生成或修改电子表格的数值与公式，由于 LLM 缺乏精确的数值重算引擎，极易产生“数值幻觉”或破坏已有的动态公式链。为此，企业级表格建模 Skill 矩阵采用了“LLM 逻辑推理 + 底层 openpyxl/pandas 执行引擎”的解耦架构，通过代码级操纵确保计算的零错误。

| Skill 标识与资源链接 | 核心架构与功能特性 |
| --- | --- |
| Prat011/awesome-llm-skills (xlsx)<br>https://tool.lu/ko_KR/skill/s/aAf | 提供严格遵循财务模型规范的 Excel 创建与编辑能力，支持 Color-coding（硬编码数字/公式/跨表引用区分颜色）、数字格式化与公式重算，确保零计算错误。 |
| MemTensor/memmy-agent (xlsx)<br>https://tool.lu/ko_KR/skill/s/ora | 专注于 Excel 工作簿的验证与渲染，完整保留宏（Macros）、格式与元数据，提供严苛的质量检查与 CSV/TSV 转换管道，防止单元格样式损毁。 |
| See-Sol-Lab/DeepSeekGUI (office-xlsx)<br>https://tool.lu/ko_KR/skill/s/oSk | 基于 openpyxl/pandas 实现单元格级操纵，支持自动更新并重新计算 Excel 内部缓存值，保障商业报表公式链的完整性。 |
| sdyckjq-lab/llm-wiki-skill (xlsx)<br>https://tool.lu/ko_KR/skill/s/hy3 | 覆盖跨格式数据清洗、规范化与财务报表生成，内置自动公式校验逻辑，防止手动修改破坏汇总逻辑。 |

- **架构设计意义**：该矩阵通过 Python 底层库拦截所有表格写入操作，在保留现存模板样式、图表绑定、透视表及 VBA 宏元数据的同时，强制执行财务模型的标准校验。这种设计阻断了 LLM 输出错误计算结果的路径，使得 Agent 能够安全地处理企业核心财务报表。

### 3.2 DeskcommCRM (melgarafael/DeskcommCRM)：业务指标与 CRM 分析 Skill

- **能力模块定位**：指导 AI Agent 以专业数据分析师视角直接评估 CRM 绩效的数据库分析 Skill（DeskcommCRM，GitHub: melgarafael/DeskcommCRM）。
- **输入/输出契约与资源储备**：具备直接查询 Supabase 后端数据库的能力，内置 CRM 数据分析指标模型（如转化率 Conversion、营销漏斗 Funnel、获客成本 CAC 等）与安全的 SQL 聚合查询规范。
- **执行与安全 Profile**：Agent 拦截自然语言业务提问，将其转化为只读的 Supabase SQL 聚合指令，以零数据泄露风险的方式实时返回营销漏斗与业务绩效图表的数据源。

### 3.3 MuseAI-Skills (win4r/MuseAI-Skills)：金融账户数据接入与分析 Skill

- **能力模块定位**：支持 Agent 连接 Plaid API 并直接提取多源金融账户数据的集成 Skill（MuseAI-Skills，GitHub: win4r/MuseAI-Skills）。
- **输入/输出契约与底层模组**：输入为 Plaid 鉴权 Token，输出为结构化的资产负债与收支数据。系统明确依赖并集成了三套核心底层数据库映射模组：
  1. `plaid`：负责对接 Plaid 接口并安全拉取账户元数据、实时余额与流水；
  2. `muse_db`：负责将金融数据结构化写入本地/云端数据库，构建经常性收支（Recurring Income/Expenses）模型；
  3. `function_health`：负责对金融数据管道的运行状态与 API 契约进行监控与异常诊断。
- **应用场景**：为企业或个人 Agent 自动化生成资产负债表、现金流趋势图及投资组合分析图表提供精准的数据底层。

单点的商业报表与数据库查询最终需要收拢至统一的渲染大厅，这促使企业引入声明式的标准化图表语法与全域 Agent 路由机制。

## 4. 企业级图表语法与全域路由阵营 (Enterprise Chart Grammar & Full-Domain Routing)

大型企业在部署 AI Agent 可视化能力时，最忌讳 Agent 随意生成散乱、不可控的胶水代码（Glue Code）。企业需要统一的声明式 JSON 配置接口、可靠的服务端无头渲染（SSR）能力，以及基于 MCP（Model Context Protocol）协议的标准化工具集，以实现在对话流与自动化报告管道中的全域可视化路由。

### 4.1 Highcharts MCP 架构与 AI 原生渲染机制

作为企业级可视化的标杆，Highcharts 率先推出了官方 MCP 双服务端架构，彻底重构了大模型交互与渲染的流程：

```text
+-------------------------------------+   +-----------------------------------+
| @anthropic/highcharts-docs-server   |   | @anthropic/highcharts-mcp-server  |
| (动态 Schema RAG 文档库)            |   | (服务端无头渲染引擎)              |
+-------------------------------------+   +-----------------------------------+
| - search_docs                       |   | - render_chart                    |
| - validate_config                   |   |   (基于 Node.js / Puppeteer)      |
| - recommend_chart                   |   |   (单次工具调用返回高清 PNG)      |
| - search_snippets                   |   |                                   |
+-------------------------------------+   +-----------------------------------+
```

1. **Schema RAG 模式 (@anthropic/highcharts-docs-server)**：传统 Prompt 工程需要将数千 Token 的配置文档硬编码进 System Prompt，占用大量上下文。在 Highcharts MCP 架构中，文档服务器作为 Agent 的动态工具存在，Agent 在生成图表前可按需调用 `search_docs`、`recommend_chart` 或 `validate_config`，对待生成的 JSON 配置进行实时 Schema 校验与修正，极大地降低了生成幻觉。
2. **无头渲染与单次工具调用 (@anthropic/highcharts-mcp-server)**：Agent 完成 JSON 配置构造后，直接调用 `render_chart` 工具。服务端运行基于 Node.js 与 Puppeteer 的 Highcharts Export Server，以无头方式完成图表绘制并直接返回高清 PNG 图像。这使图表生成简化为**单次工具调用（Single Tool Call）**，免去了浏览器端运行环境与客户端代码拷贝的摩擦。
3. **40+ 深度图表类型支持**：全面覆盖瀑布图（Waterfall）、漏斗图（Funnel）、桑基图（Sankey）、甘特图（Gantt）、树状图（Treemap）及热力图等复杂企业级图表类型。

### 4.2 图表库横向对比与选型评估

在大模型生成场景下，图表库的选型维度发生了根本性变化，配置格式的 LLM 友好度、MCP 原生支持以及 WCAG 无障碍合规度成为了核心指标：

| 对比维度 | Highcharts | Chart.js | D3.js | Plotly |
| --- | --- | --- | --- | --- |
| MCP 服务端支持 | 原生提供（官方双 MCP Server） | 无 | 无 | 无 |
| 配置接口格式 | 纯声明式 JSON | JS 对象（含函数句柄） | 过程式/命令式代码 | JSON + 回调函数 |
| 服务端渲染 (SSR) | 官方 Export Server (Puppeteer) | 仅社区简易方案 | 需手动搭建 SVG DOM | 依赖付费 Orca 服务 |
| WCAG 2.1 AA 合规度 | 原生内置 (92%) | 极低 (45%) | 纯手动开发 (30%) | 部分支持 (71%) |
| 图表类型覆盖 | 40+ 种（含高级金融/甘特图） | 8 种核心类型 | 无限（需从零绘制） | 30+ 种 |
| LLM 生成语义报错率 | 低 (Low) | 中 (Medium) | 极高 (High) | 中 (Medium) |
| 开源与商业许可 | 非商业免费；商业需付费授权 | MIT 许可（开源免费） | BSD 许可（开源免费） | MIT 许可（开源免费） |

**Highcharts 的 AI 时代架构优势**：凭借纯 JSON 配置格式、官方 MCP 服务端（将图表生成简化为单次 API 调用）、开箱即用的 92% WCAG 无障碍合规度以及 40+ 图表类型，Highcharts 在降低 LLM 报错率与提升 Agent 交互体验方面展现出显著优势。

### 4.3 企业级数据集成与结构化提取 Skill

- **datavane/tis (TIS 数据集成平台 Skill)**：
  - **架构特性**：TIS 数据集成平台 Agent Skill（datavane/tis），支持管理 20+ 种异构数据源，具备基于 DataX 的批量数据同步与基于 Flink CDC 的实时增量数据同步控制能力。
  - **应用场景**：为企业级大屏 Dashboard 与实时分析 Agent 提供稳定的底层数据流管道与执行监控。
- **yifanfeng97/Hyper-Extract (结构化数据提取与图表设计 Skill)**：
  - **架构特性**：用于设计 YAML 数据提取模板的 Skill（yifanfeng97/Hyper-Extract）。显式支持 `model`、`list`、`set` 三种数据记录类型。
  - **底层子模块储备**：内置三大核心子模块：
    1. `record-designer`：负责定义提取字段与标识符规则；
    2. `graph-designer`：负责建立抽取数据与图形映射关系的显示规则；
    3. `hyper-extract`：负责执行无损数据抽取与去重。为 Agent 从非结构化文本中提炼结构化图表数据源提供了标准化契约。

在结构化图表之外，某些业务场景需要非结构化的生成式图像、动态模型路由机制以及对 Agent 生成能力的评估，这引出了多模态合成与路由阵营。

## 5. 图像合成、模型路由与自动化评测阵营 (Image Synthesis, Model Routing & Evaluation)

一个完整的 Agent 可视化系统，除了处理精确的结构化图表外，还需要具备生成概念插图、根据成本和延迟动态选择后端 LLM/MLLM，以及对生成的图表结果进行自动评测的能力。

### 5.1 SwarmClaw (swarmclawai/swarmclaw)：多模态图像生成与画廊 Skill

- **能力模块定位**：集成 OpenAI Images API 的 Agent 多模态视觉生成技能模块（SwarmClaw，GitHub: swarmclawai/swarmclaw）。
- **输入/输出契约与资产储备**：输入为 Prompt 文本，内部通过 openai-image-gen 技能模组调用 GPT Image 或 DALL-E 接口。支持批量生成、随机提示词采样（Random Prompt Sampling），并能自动将多张生成图片打包输出为响应式的**HTML 视觉画廊（HTML Gallery Output）**。
- **执行 Profile**：为 Agent 提供了超越传统图表的生成式概念插图与视觉素材集中展示能力。

### 5.2 Maggy (alinaqi/maggy)：AI 模型选型矩阵与 API 权衡 Skill

- **能力模块定位**：专为可视化 Agent 设计的动态模型路由与成本/延迟权衡 Skill（Maggy，GitHub: alinaqi/maggy）。
- **输入/输出契约与资产储备**：内部集成 ai-models 技能模组，提供覆盖主流 AI 模型（如 Claude 3.5/3.7、OpenAI GPT-4o/o3 等）的性能权衡矩阵（Selection Matrix）、API 调用示例与实时价格/延迟数据库。
- **执行 Profile**：当 Agent 接收到可视化渲染任务时，Maggy 模块能够根据任务复杂度（如简单柱状图 vs 复杂网状图），动态路由至性价比最高的大模型，实现成本与渲染质量的最佳平衡。

### 5.3 WBench (meituan-longcat/WBench)：模型结果评测与排行榜打包 Skill

- **能力模块定位**：用于将 Agent 或大模型的可视化生成结果打包并提交至 WBench 排行榜的自动化评测 Skill（WBench，GitHub: meituan-longcat/WBench）。
- **资产储备与 CLI 工具链**：显式集成并提供三套核心 CLI 工具脚本：
  1. `wbench-submit`：负责将评测结果标准化打包并提交至官方排行榜或 HuggingFace 数据集；
  2. `wbench-evaluate`：负责运行自评估算法，针对图表生成质量进行评分；
  3. `wbench-generate`：负责自动化生成评测所需的 meta.json、turns.json 元数据配置文件及视频演示包（Video Packages）。
- **执行 Profile**：为 Agent 可视化能力的持续迭代提供了自动化 Benchmark 测试与基准测量管道。

将视角转向人类最终的使用体验，数据可视化的合规性（WCAG 无障碍标准）与可交互重构能力，构成了极简与无障碍协同阵营的核心价值。

## 6. 极简、无障碍与协同设计阵营 (Minimalist, Accessible & Collaborative Design)

数据可视化中的无障碍设计（WCAG 2.1 AA 标准）不仅是法律与道德的刚性要求（如美国 ADA、Section 508 法案），也是提升全人群数据交互体验的关键。在纯文本 Prompt 模式下，LLM 无法自主校验渲染色彩的对比度，也无法对离屏 DOM 进行键盘导航测试。因此，AI 系统的无障碍性必须深度依赖底层图表库的原生无障碍架构，以及基于矢量图结构图（CSG）的协同重构机制。

### 6.1 Highcharts 无障碍架构 (WCAG 2.1 AA) 与多模态交互

依靠 Prompt 调优（例如要求 Agent“生成一张无障碍图表”）在生产环境中极不可靠。Highcharts 在库层实现了开箱即用的 92% WCAG 2.1 AA 无障碍合规支持，深度嵌入了多项无障碍技术标准：

1. **离屏 HTML 数据表自动生成**：屏幕阅读器模块（Screen Reader Module）会在后台自动为图表数据生成隐藏但语义完整的离屏 HTML 结构化表格（  ），使视障用户使用的辅助技术（如 NVDA、JAWS）能够无缝读取数据内容。
2. **键盘 Tab 键与焦点环导航**：无需鼠标，用户可完全通过键盘 Tab 键与方向键，在图表的数据点、数据系列（Series）、图例及坐标轴之间进行焦点切换，并辅以高亮的可见焦点环（Visible Focus Rings）。
3. **语义化 ARIA 标签与 Landmark Roles**：渲染器会自动注入 `role="img"`、`role="region"` 以及动态计算的 `aria-label` 描述（如：“柱状图：2024 年四季度区域营收，包含 3 个数据点，最小值 98M，最大值 142M”）。
4. **数据声化 (Sonification) 多模态表达**：Highcharts 能够将图表的数据趋势与数值起伏，转化为不同音高与频率的声音信号（Sound Patterns）。视障用户只需聆听声音频率的变化，即可直观感知曲线的波动趋势，实现了真正意义上的多模态数据感知。

### 6.2 图表结构图 (CSG) 与矢量图表重构生态

在矢量图表的二次重构与语言驱动协同修改方面，Chart2SVG 以及前沿研究（DIVI、Mystique、DataWink）提出了基于**图表结构图（Chart Structure Graph, CSG）**的技术架构。

传统的直写 SVG 字符串修改模式（Direct SVG String Editing）极易遭遇严重的破坏性失效（Failure Modes）：例如当 Agent 增加数据文本字号时，会导致文本与相邻柱体严重重叠；当扩大柱体宽度时，会导致图形超出 Canvas 画布边缘而被截断。CSG 通过将底层 SVG 元素升维为包含语义属性的图节点，并建立两类核心约束边，解决了这一难题：

```text
+--------------------------------------+---------------------------------------+
|                        Chart Structure Graph (CSG)                         |
+--------------------------------------+---------------------------------------+
| 数据约束 (Data Constraints)          | 空间约束 (Spatial Constraints)        |
| - Axis Scaling (坐标轴缩放)          | - Element Alignment (元素对齐)        |
| - Value Proportionality (数值比例)   | - Group Spacing (组内间距)            |
| - Category Consistency (类别一致)    | - Overlap Prevention (防重叠)         |
+--------------------------------------+---------------------------------------+
```

1. **数据约束 (Data Constraints)**：
   - **Axis Scaling**：约束数据值域与坐标系的映射。当数据范围改变时，自动重新计算坐标轴刻度与所有依附图元的相对位置。
   - **Value Proportionality**：强制保证图元几何属性（如矩形高度、扇形弧度）与底层数值保持严格的数学等比例关系。
   - **Category Consistency**：绑定同一数据类别的视觉通道（如颜色、填充纹理）。修改图例颜色会自动同步更新所有关联的数据 Mark。
2. **空间约束 (Spatial Constraints)**：
   - **Element Alignment & Group Spacing**：维持刻度线、网格与图元之间的绝对对齐与均匀间距。
   - **Bidirectional Constraint Propagation（双向约束传播机制）**：CSG 具备局部与全局双向协同更新能力。当用户发出“将香蕉数据柱的宽度扩大 50%”的指令时，局部图元尺寸的增加引发空间需求膨胀，该需求会**向上传播**，触发坐标轴间距扩展与 Canvas 画布整体扩容（彻底消除边缘截断失效）；反之，当全局 Canvas 尺寸受限时，约束会**向下传播**，等比例压缩图元间距与字号（彻底消除文本重叠失效），保障了协同修改中的视觉严谨性。

综合上述五大阵营的技术特性与应用场景，报告最后将为企业架构师提供技术选型指南，并展望未来的技术演进趋势。

## 7. AI Agent 数据可视化 Skill 的选型指南与演进趋势

### 7.1 选型决策矩阵

企业架构师与开发者在为 AI Agent 构建数据可视化能力时，应根据具体的业务场景需求、部署门槛及许可协议进行 Skill 的组合选型：

| 业务场景需求 | 推荐 Skill / 系统组合 | 部署与执行门槛 | 许可协议 / 开源状态 |
| --- | --- | --- | --- |
| 学术论文绘图与可复现实验 | yjz211/vivid-illustration-skill + DetachHead/rebased + Chart2SVG | 中高（需配置 Python/CLI 环境及 Qwen3-VL 权重） | GitHub 开源协议 / CC BY 4.0 |
| 金融建模与零错误商业报表 | Prat011/awesome-llm-skills + MemTensor/memmy-agent + See-Sol-Lab/DeepSeekGUI | 低（依托 Python openpyxl/pandas 执行引擎） | GitHub 开源协议 |
| CRM 营销与金融资产分析 | melgarafael/DeskcommCRM + win4r/MuseAI-Skills | 中（需配置 Supabase 数据库与 Plaid API Key） | GitHub 开源协议 |
| 企业级对话流图表与 Dashboard | Highcharts MCP (@anthropic/highcharts-mcp-server) + datavane/tis + Hyper-Extract | 低至中（基于 Node.js/MCP 环境与数据管道） | Highcharts 商业授权（非商业免费）；组件开源 |
| 多模态生图与 Agent 评测 | swarmclawai/swarmclaw + alinaqi/maggy + meituan-longcat/WBench | 低（需准备 OpenAI Key 与评测脚本） | GitHub 开源协议 |

### 7.2 未来演进趋势

1. **从“命令式代码生成”全面转向“MCP 原生服务与矢量图结构图（CSG）双轨驱动”**：
   让 LLM 直接撰写 D3/Matplotlib 代码的模式，正因高报错率和沙盒执行成本而被淘汰。未来的主流架构将演进为：在实时对话交互场景下，Agent 通过 **MCP 协议**直接调用服务端无头渲染引擎生成高高清图表；在二次编辑与 complex 复杂图表重构场景下，基于 **CSG 图结构**进行语义化的节点与双向约束联动修改。
2. **强无障碍（WCAG 2.1 AA）与多模态声化（Sonification）成为 Agent 输出的标配**：
   企业级应用与公共服务对无障碍合规性的要求日益趋严。由于 LLM 无法通过纯文本校验对比度和键盘事件，未来的可视化 Skill 将全面依赖像 Highcharts 这样在库层自动生成离屏 HTML 替代数据表、绑定 ARIA 角色以及支持声音频率表达的底层渲染引擎。
3. **基于 RL（如 GRPO）的视觉渲染感知微调将成为图表基础模型训练的标准范式**：
   仅仅依靠 SFT 优化 Token 级别的文本似然度，无法消除渲染后的几何错位与语法报错。以 Chart2SVG 为代表的“SFT + 渲染感知 GRPO 强化学习”范式——利用前景 IoU、SSIM 和 PSNR 作为视觉奖励，反向指导多模态大模型生成精准的矢量代码——将成为下一代图表生成与逆向工程模型训练的标准路径。

# THIRD_PARTY_NOTICES

本项目（viz-suite）严格遵守开源许可规范，仅打包宽松协议资产与独立编写的代码。以下列出第三方来源、协议与使用范围；运行时 Python 依赖不随仓库分发，由 PEP 723 在 `uv run` 时解析，遵循各自开源协议。

---

## 一、内置静态开源字体资产 (`skills/shared/assets/fonts/`)

本项目内置 9 款经过官方检验的静态 TrueType (`.ttf`) 字体文件，全部遵循 **SIL Open Font License 1.1 (OFL 1.1)**。支持自由分发、商用与矢量 PDF (Type 42) 嵌入。

| 字体名称 | 权属人 / 上游项目 | 文件名 | 协议 | 用途说明 |
| :--- | :--- | :--- | :--- | :--- |
| Inter (Regular, Medium, Bold) | Rasmus Andersson / The Inter Project (https://rsms.me/inter/) | `Inter-Regular.ttf`, `Inter-Medium.ttf`, `Inter-Bold.ttf` | SIL OFL 1.1 | 现代无衬线正文、坐标轴与信息图标签基准 |
| IBM Plex Serif (Regular, Bold) | IBM Corp. (https://github.com/IBM/plex) | `IBMPlexSerif-Regular.ttf`, `IBMPlexSerif-Bold.ttf` | SIL OFL 1.1 | 权威学术报刊衬线大标题与引文强调 |
| JetBrains Mono (Regular, Bold) | JetBrains s.r.o. (https://www.jetbrains.com/lp/mono/) | `JetBrainsMono-Regular.ttf`, `JetBrainsMono-Bold.ttf` | SIL OFL 1.1 | 表格数值对齐、等宽代码与统计量指标展示 |
| Noto Sans SC (Regular, Bold) | Google LLC (https://fonts.google.com/noto/specimen/Noto+Sans+SC) | `NotoSansSC-Regular.ttf`, `NotoSansSC-Bold.ttf` | SIL OFL 1.1 | 跨平台中文无衬线印刷级正文与图例 |

### SIL Open Font License 1.1 简要说明
字体软件按 SIL Open Font License Version 1.1 授权分发。允许自由使用、研究、复制、合并、嵌入、修改与重新分发。本项目未单独销售字体本身，亦未在修改版中使用保留字体名称。

---

## 二、地理底图与拓扑网格资产 (`skills/shared/assets/geo/`)

| 资产文件 | 来源与规格 | 协议 | 用途说明 |
| :--- | :--- | :--- | :--- |
| `china_prov_tile_grid.json` | viz-suite 规范化原创拓扑（12 列 × 9 行） | CC0 1.0 (Public Domain) | 34 省级行政区均权方形示意网格（非精确国界线，规避大省面积视觉偏倚与测绘合规风险） |
| `ne_110m_countries.geojson` | Natural Earth 110m (https://www.naturalearthdata.com/) | CC0 1.0 (Public Domain) | 全球 177 国陆地轮廓矢量底图，纯 NumPy 罗宾逊投影映射 |
| `us_states_hexgrid.geojson` | NPR / US Census Bureau 开放数据 | 0BSD / CC0 | 美国 50 州蜂窝均权六边形网格 |
| `us_states_tile_grid.json` | 开放数据社区贡献 | CC0 1.0 | 美国 50 州方形均权网格 |

---

## 三、期刊版式规范与调色板基准

| 组件 | 来源 | 协议 | 使用位置 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| 期刊版式出版标准 | Nature, Science, Cell Press, PNAS, Lancet, IEEE, ACM 及 `scientific-agent-skills` | MIT / 公开规范 | `skills/viz-figure/assets/publisher_profiles.json` | 各顶刊单栏/双栏最大尺寸、DPI、字号阶梯与色盲友好要求 |
| SciencePlots 样式参数 | https://github.com/garrettj403/SciencePlots | MIT | `skills/shared/assets/tokens.json` | 提纯 `science` / `nature` / `ieee` 参数，移除专有字体硬编码 |
| Paul Tol's Colour Schemes | Paul Tol, SRON (https://personal.sron.nl/~pault/) | CC0 1.0 / 公共领域 | `skills/shared/assets/palettes.json` | `tol_bright`, `tol_muted`, `tol_light`, `tol_vibrant` CVD 色盲安全色板 |
| Crameri Scientific Colour Maps | Fabio Crameri (https://www.fabiocrameri.ch/colourmaps/) | MIT / CC0 | `skills/shared/assets/palettes.json` | `crameri_batlow`, `crameri_roma` 连续/发散感知均匀色标 |
| MetBrewer 色彩库 | https://github.com/BlakeRMills/MetBrewer | CC0 1.0 | `skills/shared/assets/palettes.json` | `met_hiroshige`, `met_klimt` 艺术级配色与色盲安全指标 |
| ColorBrewer 2.0 | https://colorbrewer2.org | Apache-2.0 | `skills/shared/assets/palettes.json` | `Dark2`, `Set2`, `Paired` 经典色板 |
| Okabe-Ito 色板 | Okabe & Ito (2008), *Color Universal Design* | 公开学术标准 | `skills/shared/assets/palettes.json` | 色盲安全分类色板 |
| 自研色板与主题令牌 | viz-suite 原创 | MIT | `skills/shared/assets/tokens.json` | `academic_muted`、`business_clean`、`bi_ibcs`、`editorial_warm`、`mckinsey`、`academic_blueprint` 与全色系 CIEDE2000 色差排序 |

---

## 四、前端库与图标资产

| 组件 | 来源 | 协议 | 使用位置 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| Apache ECharts 5.6.0 | https://echarts.apache.org | Apache-2.0 | `skills/viz-interactive/assets/vendor/echarts.min.js` | 本地压缩发行版；许可全文见 `LICENSE-echarts.txt`，版权声明见 `NOTICE-echarts.txt` |
| D3.js v7.9.0 | https://d3js.org | ISC | `skills/viz-interactive/assets/vendor/d3.min.js` | 本地压缩发行版；许可全文见 `LICENSE-d3.txt` |
| Lucide Icons 1.61.0 | https://lucide.dev | ISC | `skills/viz-diagram/assets/icons/*.svg` | 精选 100 个语义图标；许可全文见 `LICENSE.txt` |

---

## 五、运行时 Python 依赖（不随仓库分发）

| 依赖 | 协议 | 用途 |
| :--- | :--- | :--- |
| matplotlib | PSF-based / BSD-compatible | 核心绘图底座、版式注入、排版体检 |
| numpy | BSD-3-Clause | 罗宾逊投影映射、统计核密度、数据变换 |
| pandas | BSD-3-Clause | 数据剖析、长宽表转换、排序计算 |
| openpyxl | MIT | Excel 报表解析 |
| Pillow | HPND / MIT-CMU | 缩略图高质量压制、尺寸审计 |
| pypdf | BSD-3-Clause | 矢量 PDF 字体嵌入 (Type 42) 深度体检 |
| defusedxml | PSF-2.0 | 安全 XML 解析 |
| opencv-python-headless | Apache-2.0 | 图像特征检验（逆向管线） |
| scikit-image | BSD-3-Clause | 图像像素级保真比对 |
| scipy | BSD-3-Clause | 空间计算与科学统计推断 |

这些依赖由各脚本顶部 PEP 723 声明，由 `uv` 在沙箱环境中按需解析，源码不随仓库打包分发。

---

## 六、清洁室独立研发声明（Clean-Room Implementation）

1. **零直接代码复制**：本项目绝对未复制参考仓库 `vivid-figures-skill` / `vivid-illustration-skill`（受 Personal Non-Commercial 协议保护）或 `ggsci` / `maidr-skill`（受 GPL-3 传染性协议保护）的任何 `.py` 源代码、私有色板 HEX、Markdown 原文或图片。
2. **抽象架构吸收**：仅吸收属于通用行业实践的方法论（如多层文本防重叠、二八法则、网格均权示意、Saga/Medallion 架构图示），并采用宽松开源协议底座全新独立重构。
3. **配方自研生成**：全库 42 套配方、23 套交互模板、12 套信息图布局与 8 套矢量架构 Master 均由本项目脚本实跑生成并经过全流程自动化测试验证。

# THIRD_PARTY_NOTICES

本项目（viz-suite）仅打包宽松协议资产与独立编写的代码。以下列出第三方来源、协议与使用范围；运行时 Python 依赖不随仓库分发，由 PEP 723 在 `uv run` 时解析，遵循各自协议。

## 一、内置资产

| 组件 | 来源 | 协议 | 使用位置 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| SciencePlots（样式参数） | https://github.com/garrettj403/SciencePlots | MIT | `skills/viz-python/assets/styles/*.mplstyle` | 提纯 `science` / `nature` / `ieee` 参数，移除 LaTeX 依赖、专有字体硬编码与 `savefig.bbox=tight` |
| MetBrewer（色彩值） | https://github.com/BlakeRMills/MetBrewer | CC0 1.0 | `skills/viz-core/assets/palettes.json` | 仅使用 HEX 色值与上游 `colorblind` 标记 |
| ColorBrewer 2.0（色板） | https://colorbrewer2.org | Apache-2.0 | `skills/viz-core/assets/palettes.json` | Dark2 / Set2 / Paired 色板 |
| Okabe-Ito 色板 | Okabe & Ito (2008), *Color Universal Design* | 公开学术标准 | `skills/viz-core/assets/palettes.json` | 色盲安全分类色板；本项目未复制任何代码文件 |
| 自研色板与令牌 | viz-suite 原创 | MIT | `skills/viz-core/assets/*` | `academic_muted`、`business_clean`、`bi_ibcs`、`editorial_warm`、`gray_print` 与全部 `category_order` / CVD 指标 |
| Apache ECharts 5.6.0 | https://echarts.apache.org | Apache-2.0 | `skills/viz-web/assets/vendor/echarts.min.js` | 本地压缩发行版；全文见同目录 `LICENSE-echarts.txt`，版权声明见 `NOTICE-echarts.txt` |
| D3.js v7.9.0 | https://d3js.org | ISC | `skills/viz-web/assets/vendor/d3.min.js` | 本地压缩发行版；全文见同目录 `LICENSE-d3.txt` |
| Lucide Icons 1.61.0 | https://lucide.dev | ISC | `skills/viz-infographic/assets/icons/*.svg` | 精选 100 个语义图标；全文见同目录 `LICENSE.txt` |

### SciencePlots MIT 许可全文

```text
MIT License

Copyright (c) 2018 John Garrett

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### MetBrewer CC0 1.0

MetBrewer 的全部色板以 CC0 1.0 Universal 释出，可自由复制、修改与商用；本项目仅提取色值，并对取色顺序与色盲指标做了独立计算。来源致谢：Blake R. Mills, MetBrewer。

### ColorBrewer 2.0

ColorBrewer 色板由 Cynthia Brewer 设计，按 Apache License 2.0 使用；本项目仅使用公开色值，未复制其源代码。

### Okabe-Ito

引用：Okabe, M., & Ito, K. (2008). Color universal design (CUD): How to make figures and presentations that are friendly to colorblind people. 本项目使用其公开推荐的 7 色序列（不含黑色）。

### Apache ECharts 5.6.0

Apache ECharts 由 Apache Software Foundation 以 Apache License 2.0 发布。本项目内置其官方压缩发行版 `echarts.min.js`，未修改源码；完整许可全文见 `skills/viz-web/assets/vendor/LICENSE-echarts.txt`，版权与 NOTICE 见 `skills/viz-web/assets/vendor/NOTICE-echarts.txt`。上游项目：https://echarts.apache.org。

### D3.js v7.9.0

D3.js 由 Mike Bostock 以 ISC 许可发布。本项目内置其官方压缩发行版 `d3.min.js`，未修改源码；完整许可全文见 `skills/viz-web/assets/vendor/LICENSE-d3.txt`。上游项目：https://d3js.org。

### Lucide Icons 1.61.0

Lucide Icons 以 ISC 许可发布。本项目精选 100 个语义图标（本地 SVG），仅改了展示尺寸与颜色继承，未修改路径数据；完整许可全文见 `skills/viz-infographic/assets/icons/LICENSE.txt`。上游项目：https://lucide.dev。

## 二、运行时 Python 依赖（不随仓库分发）

| 依赖 | 协议 | 使用脚本 |
| :--- | :--- | :--- |
| matplotlib | PSF-based / BSD-compatible | `viz_style.py`、`detect_fonts.py`、配方 |
| numpy | BSD-3-Clause | 画像、配方、体检 |
| pandas | BSD-3-Clause | `profile_data.py`、配方 |
| openpyxl | MIT | `profile_data.py` |
| Pillow | HPND / MIT-CMU | `audit_export.py` |
| pypdf | BSD-3-Clause | `audit_export.py` |
| defusedxml | PSF-2.0 | `audit_export.py`、`web_extract.py` |
| opencv-python-headless | Apache-2.0 | `inspect_image.py`、`calibrate_and_extract.py` |
| scikit-image | BSD-3-Clause | `compare_render.py` |
| scipy | BSD-3-Clause | `calibrate_and_extract.py` |

这些依赖通过各脚本顶部 PEP 723 注释声明，由 `uv` 在运行时安装；分发本项目不包含其源码。

## 三、清洁室声明（Clean-Room）

- 本项目**未复制** `vivid-figures-skill` / `vivid-illustration-skill` 的任何 `.py` 源文件、私有色板 HEX、Markdown 原文、HTML 快照或预览图片。
- 吸收的仅为不受著作权排他保护的方法论与通用数学逻辑：`selection-index.jsonl` + 预览实图选型 + 源码保真卡工作流、基于标准库 `ast` 的保真比对、最大色差取色序、连续/发散色阶插值、WCAG 合成亮度对比公式、受约束版式旋钮与引用尺寸反推。
- 28 套配方全部基于宽松协议开源基座与自有合成数据独立编写，预览图由本项目脚本实跑生成。
- HTML 模板、看板、KPI 卡页、`capture_html.py` 的 CDP 客户端、`lint_html.py`、`check_layout.py`、`render_infographic.py`、4 个场景差分规范与 `viz-reverse` 管线均为本项目独立编写；仅内置上游 ECharts/D3/Lucide 发行版与运行时 Python 依赖。
- `ggsci`（GPL-3）、`maidr-skill`（GPL-3）未复制任何代码或色值定义。
- 咨询公司模板与 FT 海报仅提炼公开分类学与版式原则，未复制原图、商标或版式文件。

## 四、明确未打包的资产

- 商业专有字体（仅引用系统已安装字体名）；
- 中国及其他敏感地区行政区划边界 GeoJSON（由用户自备合规数据）；
- 任何需要登录、付费或授权的内容；
- 宿主内置默认 Skill 文件（本仓库不修改）。

## 五、后续阶段占位

后续阶段如引入新的第三方资产，将在本文件补充来源、协议与许可全文。

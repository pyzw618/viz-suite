# viz-suite · 本地专业数据可视化 Agent

基于**顶层系统提示词 + 自建 Skill 集群**的本地数据可视化能力包。零外部包管理器、零构建发布基建、离线自包含；语义归模型，计算归脚本。

> 当前交付状态、门禁结果与已知边界见 [`当前进度.md`](当前进度.md)。

## 当前交付

- **Stage 0（全局底座）**：`skills/` 目录骨架、`AGENT.md`、`viz-core/assets/palettes.json`（15 套色板 + 色盲校验 + 最大差异取色序）、`tokens.json`。
- **Stage 1（正向 MVP）**：
  - `viz-core`：需求澄清、数据画像、选型决策树、设计令牌；
  - `viz-python`：共享视觉运行时 + 字体探测 + 配方拉取 + AST 保真核对；
  - `viz-audit`：物理尺寸/DPI/白边、PDF 字体嵌入、WCAG、色盲色差、HTML 外链。
- **Stage 2（配方库与 Web 引擎）**：
  - `viz-python`：28 套黄金配方（8 单图 + 12 多层融合 + 8 多面板），每套含脚本、保真卡、真实预览与索引条目；
  - `viz-web`：15 类 ECharts 5 模板、4 类 D3 v7 骨架、响应式联动看板与 KPI 卡页；本地 vendor、CDP 精确截图、HTML lint 与真实视口布局检查；
  - 品牌换肤与多图锁定的金标验证：`examples/golden-runs/brand-lock/`。
- **Stage 3（信息图与场景差分）**：
  - `viz-infographic`：12 种布局 × 4 种皮肤、100 个本地 Lucide 图标、HTML/SVG 双通道与中文折行；
  - `viz-scene-academic` / `-bi` / `-story` / `-geo`：4 个独立 12 槽位场景差分 Skill；
  - 信息图 48 组合验收：`examples/golden-runs/infographic-gallery/`；
  - Gate 3 场景差异：`examples/golden-runs/scene-gate3/`（同一份数据的学术/商业/叙事三套产物）。
- **Stage 4（逆向工程）**：
  - `viz-reverse`：源码/DOM（ECharts/Chart.js/Plotly/SVG）A 级提取、五类清晰图 B 级轴标定反推、低清 C 级降级、3D 透视 X 级拒绝；
  - `compare_render.py`：SSIM / CIEDE2000 ΔE / IoU / diff.png 往返核验；
  - Gate 4 基准：`examples/golden-runs/reverse-benchmark/`（5 类图 MAPE 中位 0.23%、最低 SSIM 0.949）。
- **Stage 5（全局联调）**：
  - 12 个端到端任务：`examples/golden-runs/end-to-end/`（科研多面板、销售看板、信息图、逆向换色、丑图修复、PDF/PPT 交接、森林图、地理地图、故事图、技术信息图、源码提取、低清/3D 降级）；
  - `run_suite.py`：12/12 任务产物齐全，10/10 Skill 全覆盖；`routing-matrix.json` 12 正例 + 4 负例。
- **Gate 1 金标案例**：`examples/golden-runs/dirty-csv-walkthrough/`（脏 CSV 全链路跑通）。
- **Gate 2 Web 验收证据**：`examples/golden-runs/web-templates/`（21 套模板 × 2 视口截图、lint 与布局检查报告）。

## 目录

```text
AGENT.md                     # 顶层系统提示词（交给宿主）
THIRD_PARTY_NOTICES.md       # 开源资产协议与清洁室声明
skills/
├── README.md                # 集群状态与冒烟测试
├── viz-core/                # 认知层
├── viz-python/              # 静态/出版级引擎（28 套配方）
├── viz-web/                 # 交互图表与单文件看板引擎
├── viz-infographic/         # 信息图引擎（12 布局 × 4 风格）
├── viz-scene-*/             # 4 个场景差分（academic / bi / story / geo）
├── viz-audit/               # 质检层
└── viz-reverse/             # 源码/DOM 与像素级逆向
examples/
├── fixtures/                # 脏数据夹具
└── golden-runs/             # 金标运行记录（Stage 1–5）
docs/
└── host-probe-checklist.md  # Stage 0 宿主探针（真人执行）
PLAN.md                      # 总体架构与路线图
```

## 快速开始

前置：Python ≥3.10、`uv`、中文字体（Microsoft YaHei / SimHei / Noto Sans CJK SC）。

```bash
# 字体探测
uv run skills/viz-python/scripts/detect_fonts.py --json

# 画像脏数据
uv run skills/viz-core/scripts/profile_data.py examples/fixtures/客服满意度_原始脏数据.csv --json

# 一键复现金标案例
cd examples/golden-runs/dirty-csv-walkthrough/work
uv run grouped_errorbar_bar.py --json > ../render.json
cd ../../../..

# Web 模板：lint + 双视口截图
uv run skills/viz-web/scripts/lint_html.py skills/viz-web/templates/echarts/line.html --json
uv run skills/viz-web/scripts/capture_html.py skills/viz-web/templates/echarts/line.html \
  --outdir shots --json

# 信息图：12 布局 × 4 风格
uv run skills/viz-infographic/scripts/render_infographic.py --list --json
uv run skills/viz-infographic/scripts/render_infographic.py \
  examples/fixtures/infographic_sample.json --layout stat-cards --style editorial \
  --outdir outputs --json

# 逆向：源码级 / 像素级 / 往返比对
uv run skills/viz-reverse/scripts/web_extract.py page.html --outdir rev --json
uv run skills/viz-reverse/scripts/inspect_image.py chart.png --chart-type bar \
  --outdir rev/inspect --json
uv run skills/viz-reverse/scripts/compare_render.py original.png reproduction.png \
  --outdir rev/compare --json
```

Gate 3 场景差异见 `examples/golden-runs/scene-gate3/README.md`；Gate 4 逆向基准见 `examples/golden-runs/reverse-benchmark/README.md`。

完整命令见 `skills/README.md`、各金标案例 README 与 `skills/viz-web/SKILL.md`。

## 设计要点

1. **纯 Skill + 系统提示词**：模块启用靠宿主原生勾选，职责路由靠 `AGENT.md` + 各 `SKILL.md` 的 description 边界；无 `skill.json` / `build.py` / `install.py`。
2. **确定性脚本**：所有脚本 PEP 723 声明依赖、`--json` 协议输出、Windows UTF-8 兼容；不静默丢数据。
3. **底稿填空**：正向绘图用「设计 Token + 黄金底稿 + PARAMS 槽位」，只改槽位、不手搓、不删样式；AST 比对防丢失。
4. **诚实交付**：零基线、误差定义、n 标注、证据分级、未完成视觉验证必须声明；不编造数据或显著性。
5. **离线自包含**：运行时不请求网络；字体、色板、样式、ECharts/D3/Lucide 全部本地。
6. **双视口验收**：Web 图表用 CDP 精确截取 1280×800 与 390×844，lint 零外链、零溢出；截图尺寸正确不等于视觉验收通过，仍须多模态目检。
7. **信息图双通道**：同一份 JSON 同时输出响应式 HTML 与 1200×1600 SVG；中文折行/截断由渲染器负责，禁止 Emoji 充当图标。
8. **逆向证据分级**：SOURCE > B > C > X；低清降级、3D/透视拒绝；SSIM 不达标只改样式，不改数据。

## 后续

Stage 0–5 全部完成：10 个自包含 Skill + 顶层 `AGENT.md` + 各阶段金标样例。`参考/` 为开发参考素材，不属于交付 Skill；后续可在不改变契约的前提下追加真实业务样例。

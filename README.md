# viz-suite · 本地专业数据可视化 Skill 集群

基于 **“1 个极薄路由入口 + 3 个自闭环执行通道 + 共享场景底座”** 的全离线数据可视化能力包。零外部 CDN、PEP 723 内联依赖声明，语义归模型、计算归脚本。

> 深度审查报告见 [`docs/skill_cluster_evaluation.md`](docs/skill_cluster_evaluation.md)；分阶段演进与验收日志见 [`docs/阶段优化记录.md`](docs/阶段优化记录.md)。

## 一、核心架构（Stage P1 重构后）

```text
AGENT.md                         # 仓库级协作与路由概览
THIRD_PARTY_NOTICES.md           # 开源资产协议与清洁室声明
skills/
├── SKILL.md                     # 根薄路由入口 (viz-suite, ≤40 行, 定义 <SKILL>/<WORKSPACE> 与语义分流)
├── README.md                    # 挂载指南与快速冒烟命令
├── shared/                      # 跨通道共享底座（令牌、色板、4 场景 JSON、数据画像、物理与碰撞审计）
│   ├── assets/scenes/           # academic.json / bi.json / story.json / geo.json
│   ├── references/              # host-adapter / decision-tree (61 项映射) / scene-deltas / anti-patterns
│   └── scripts/                 # resolve_runtime.py / profile_data.py / audit_export.py
├── viz-figure/                  # 通道 1：出版级统计与科学图表（28 黄金配方 + 轻量 JPG 缩略图）+ 逆向提取 (SOURCE/B/C/X)
├── viz-interactive/             # 通道 2：离线交互图表与响应式看板（15 ECharts + 4 D3 + 驾驶舱/KPI + CDP 双视口验收）
└── viz-diagram/                 # 通道 3：结构化信息图与逻辑架构图（12 布局 × 4 皮肤 + 100 本地 Lucide 图标 + HTML/SVG）
examples/
├── fixtures/                    # 测试夹具与脏数据样本
└── golden-runs/                 # 回归金标（dirty-csv / brand-lock / web-templates / infographic / reverse / end-to-end）
docs/
├── skill_cluster_evaluation.md  # 集群深度审查与对标改进方案
└── 阶段优化记录.md               # P0 → P1 → P2 阶段改造与验收记录
```

## 二、快速开始

前置：Python ≥ 3.10、`uv`、本机可用中文字体（Microsoft YaHei / Noto Sans CJK SC / SimHei 等）。

```bash
# 1. 环境与路径锚点探测
uv run skills/shared/scripts/resolve_runtime.py --no-write --json

# 2. 字体与数据画像
uv run skills/viz-figure/scripts/detect_fonts.py --json
uv run skills/shared/scripts/profile_data.py examples/fixtures/客服满意度_原始脏数据.csv --json

# 3. 统计与科学图（拉取配方 → 场景化渲染 → Renderer 碰撞与物理审计）
uv run skills/viz-figure/scripts/get_recipe.py --id grouped_errorbar_bar --dest ./viz-work --force --json
uv run viz-work/grouped_errorbar_bar.py --scene academic --outdir outputs --json
uv run skills/shared/scripts/audit_export.py outputs/*.pdf outputs/*_300dpi.png --json

# 4. 离线交互图与看板（静态 lint + 双视口截图）
uv run skills/viz-interactive/scripts/lint_html.py skills/viz-interactive/templates/echarts/line.html --json
uv run skills/viz-interactive/scripts/capture_html.py skills/viz-interactive/templates/echarts/line.html --outdir shots --json

# 5. 结构化信息图（12 布局 × 4 皮肤，HTML + SVG）
uv run skills/viz-diagram/scripts/render_infographic.py \
  examples/fixtures/infographic_sample.json --layout stat-cards --style editorial --outdir outputs --json

# 6. 图表逆向工程（SOURCE 级源码提取 / B 级标定反推 / SSIM 往返核验）
uv run skills/viz-figure/scripts/web_extract.py page.html --outdir rev --json
uv run skills/viz-figure/scripts/inspect_image.py chart.png --chart-type bar --outdir rev/inspect --json
uv run skills/viz-figure/scripts/compare_render.py original.png reproduction.png --outdir rev/compare --json

# 7. 端到端 12 任务回归套件
uv run examples/golden-runs/end-to-end/run_suite.py
```

## 三、核心设计准则

1. **薄路由与通道自闭环**：根入口与 3 个通道 `SKILL.md` 均控制在 25–45 行以内，零重复规训；数据画像、场景切换与成图审计全部内聚到通道标准流，杜绝多 Skill 漏召回与上下文稀释。
2. **三区弹性适配**：统计配方划分**数据管道自由改写区 / 画布布局弹性伸缩区 / 微质感保护区**，配合 `check_recipe_fidelity.py` 非阻断审查线索（Review Hints），兼顾真实业务数据自由度与出版级审美底线。
3. **像素级碰撞硬门禁**：`viz_style.py` 在渲染期执行流式标题折行、图例动态避让、窄栏长标签横排自适应与 Agg Renderer 文本包围盒碰撞自检，并将结果嵌入 PNG 元数据供 `audit_export.py` 强制核验。
4. **宿主解耦与诚实边界**：统一 `<SKILL>` / `<WORKSPACE>` 路径锚点与宿主无关看图复核约定；严禁编造数据或 p 值，对低清图降级（C 级）、对伪 3D 透视图拒绝数值反推（X 级）。

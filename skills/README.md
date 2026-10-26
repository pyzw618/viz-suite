# viz-suite Skills

本目录是**开发态即运行态**的数据可视化 Skill 包：零外部 CDN、PEP 723 内联依赖声明，跨 Antigravity / Claude Code / Codex / Cursor 即插即用。

## 一、架构拓扑（1 薄路由 + 3 自闭环通道 + 共享底座）

| 路径 | 角色 | 行数 / 资产规模 | 宿主接入方式 |
| :--- | :--- | :--- | :--- |
| [`SKILL.md`](SKILL.md) | 根薄路由（`viz-suite`） | ≤40 行；定义 `<SKILL>` / `<WORKSPACE>` 锚点与语义分流 | 整包挂载本目录时作为唯一入口 |
| [`viz-figure/`](viz-figure/SKILL.md) | 通道 1：统计与科学图表 + 逆向 | ≤50 行 `SKILL.md`；28 黄金配方 + 轻量 JPG 缩略图 + `SOURCE/B/C/X` 逆向脚本 | 可由根入口分派，也可在 `skills/*` 扫描器中独立挂载 |
| [`viz-interactive/`](viz-interactive/SKILL.md) | 通道 2：离线交互图表与商业看板 | ≤50 行 `SKILL.md`；15 ECharts + 4 D3 + 看板/KPI + CDP 截图与溢出检查 | 可由根入口分派，也可独立挂载 |
| [`viz-diagram/`](viz-diagram/SKILL.md) | 通道 3：结构化信息图与架构图 | ≤50 行 `SKILL.md`；12 布局 × 4 皮肤 + 100 本地 Lucide 图标 + HTML/SVG | 可由根入口分派，也可独立挂载 |
| `shared/` | 跨通道共享底座（无 `SKILL.md`） | `tokens.json`、`palettes.json`、`scenes/{academic,bi,story,geo}.json`、`profile_data.py`、`audit_export.py`、`resolve_runtime.py` | 由各通道按 `<SKILL>/shared/...` 直接调用，避免碎片化漏召回 |

## 二、快速冒烟测试（在仓库根目录执行）

```bash
# 1. 环境与路径锚点解析
uv run skills/shared/scripts/resolve_runtime.py --no-write --json

# 2. 字体与数据画像
uv run skills/viz-figure/scripts/detect_fonts.py --json
uv run skills/shared/scripts/profile_data.py examples/fixtures/客服满意度_原始脏数据.csv --json

# 3. 检索并拉取统计图配方（自动附带 tokens / palettes / scenes/*.json）
uv run skills/viz-figure/scripts/get_recipe.py --list --json
uv run skills/viz-figure/scripts/get_recipe.py --id grouped_errorbar_bar --dest ./viz-work --force --json

# 4. 场景化渲染 + 非阻断保真提示 + Renderer 碰撞/物理审计
uv run viz-work/grouped_errorbar_bar.py --scene academic --outdir outputs --json
uv run skills/viz-figure/scripts/check_recipe_fidelity.py \
  --base skills/viz-figure/recipes/grouped_errorbar_bar.py \
  --adapted viz-work/grouped_errorbar_bar.py --json
uv run skills/shared/scripts/audit_export.py outputs/*.pdf outputs/*_300dpi.png --json

# 5. 交互模板批量静态检查与视口布局检查
uv run skills/viz-interactive/scripts/lint_html.py \
  skills/viz-interactive/templates/echarts/*.html skills/viz-interactive/templates/d3/*.html \
  skills/viz-interactive/templates/dashboard/*.html skills/viz-interactive/templates/kpi/*.html --json

# 6. 结构化信息图双格式渲染
uv run skills/viz-diagram/scripts/render_infographic.py --list --json

# 7. 端到端 12 任务回归套件
uv run examples/golden-runs/end-to-end/run_suite.py
```

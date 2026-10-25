# viz-suite Skills

本目录是**开发态即运行态**的 Skill 集群：无需 `build.py` / `install.py`。宿主把本目录下的 10 个模块目录加入技能搜索路径（或在界面中勾选）即可；10 个目录均含 `SKILL.md`，全部可被宿主加载。顶层系统提示词见仓库根目录 `AGENT.md`。

## 当前状态

| Skill | 分层 | 状态 | 可加载 |
| :--- | :--- | :--- | :---: |
| `viz-core` | L0 认知层 | Stage 1 已交付 | ✅ |
| `viz-python` | L1 引擎层 | Stage 2 已交付（28 套配方） | ✅ |
| `viz-web` | L1 引擎层 | Stage 2 已交付（15 ECharts + 4 D3 + 看板/KPI） | ✅ |
| `viz-audit` | L3 质检层 | Stage 1 已交付 | ✅ |
| `viz-infographic` | L1 引擎层 | Stage 3 已交付（12 布局 × 4 风格 + 100 图标） | ✅ |
| `viz-scene-academic` | L2 场景层 | Stage 3 已交付 | ✅ |
| `viz-scene-bi` | L2 场景层 | Stage 3 已交付 | ✅ |
| `viz-scene-story` | L2 场景层 | Stage 3 已交付 | ✅ |
| `viz-scene-geo` | L2 场景层 | Stage 3 已交付 | ✅ |
| `viz-reverse` | L3 逆向层 | Stage 4 已交付（SOURCE/B/C/X + SSIM 闭环） | ✅ |

> 10 个 Skill 全部交付；`viz-reverse` 的重依赖（OpenCV/scikit-image）由 PEP 723 在运行时解析。

## 依赖与前置

- Python ≥ 3.10；推荐 `uv`（脚本以 PEP 723 内联声明依赖）。
- 中文字体：Microsoft YaHei / SimHei / Noto Sans CJK SC 之一（运行 `detect_fonts.py` 自检）。
- Stage 2–4：Web/信息图截图需要本机 Chrome/Edge；逆向需要 OpenCV/scikit-image（PEP 723 自动安装）。

## 冒烟测试（Stage 1–5 门禁）

```bash
# 1. 字体
uv run skills/viz-python/scripts/detect_fonts.py --json

# 2. 数据画像
uv run skills/viz-core/scripts/profile_data.py examples/fixtures/客服满意度_原始脏数据.csv --json

# 3. 列举配方
uv run skills/viz-python/scripts/get_recipe.py --list --json

# 4. 拉取底稿到工作区
uv run skills/viz-python/scripts/get_recipe.py --id grouped_errorbar_bar --dest ./viz-work --json

# 5. 渲染
uv run viz-work/grouped_errorbar_bar.py --data examples/fixtures/客服满意度_原始脏数据.csv --outdir outputs --json

# 6. AST 保真核对
uv run skills/viz-python/scripts/check_recipe_fidelity.py \
  --base skills/viz-python/recipes/grouped_errorbar_bar.py \
  --adapted viz-work/grouped_errorbar_bar.py --json

# 7. 成图体检
uv run skills/viz-audit/scripts/audit_export.py outputs/*.pdf outputs/*_300dpi.png \
  --target-width-mm 160 --fg "#1F2937" --bg "#FFFFFF" \
  --palette "#0072B2,#E69F00,#CC79A7" --json

# 8. Web 模板离线/结构检查（21 套批量）
uv run skills/viz-web/scripts/lint_html.py \
  skills/viz-web/templates/echarts/*.html skills/viz-web/templates/d3/*.html \
  skills/viz-web/templates/dashboard/*.html skills/viz-web/templates/kpi/*.html \
  --json --out lint.json

# 9. CDP 双视口截图
uv run skills/viz-web/scripts/capture_html.py \
  skills/viz-web/templates/dashboard/sales_dashboard.html \
  --outdir shots --viewport desktop=1280x800 --viewport mobile=390x844 --json

# 10. 布局溢出检查（42 个 page/viewport）
uv run skills/viz-web/scripts/check_layout.py \
  skills/viz-web/templates/echarts/*.html skills/viz-web/templates/d3/*.html \
  skills/viz-web/templates/dashboard/*.html skills/viz-web/templates/kpi/*.html \
  --json --out layout.json

# 11. 信息图：12 布局 × 4 风格
uv run skills/viz-infographic/scripts/render_infographic.py --list --json
uv run skills/viz-infographic/scripts/render_infographic.py \
  examples/fixtures/infographic_sample.json --layout timeline --style warm \
  --outdir outputs --json

# 12. 场景差分 Gate 3（同一份数据三套产物）
cd examples/golden-runs/scene-gate3/academic/work
uv run --python 3.12 forest_interval_diamond.py --json > ../render.json
cd ../../bi && uv run --python 3.12 build_dashboard.py
cd ../story/work && uv run --python 3.12 stacked_bar_total_line.py --json > ../render.json

# 13. 品牌换肤 + 多图锁色金标
cd ../../../brand-lock/work
uv run --python 3.12 theme_probe.py

# 14. Gate 4 逆向基准
cd ../../reverse-benchmark
python run_benchmark.py --python /path/to/python

# 15. Stage 5 端到端套件（12 任务 / 10 Skill 覆盖）
cd ../end-to-end
python run_suite.py
```

## 目录契约

```text
skills/<id>/SKILL.md          # 必须；描述触发条件、工作流、硬规则、文件索引
skills/<id>/scripts/          # 确定性脚本（PEP 723，--json 协议）
skills/<id>/assets/           # 离线静态资产（色板、令牌、样式、图标、vendor）
skills/<id>/references/       # 按需读取的长文档
skills/<id>/recipes|catalog/  # 仅 viz-python：黄金底稿、索引、保真卡、预览
```

## 设计约束

- 零外部 CDN；运行时零网络请求。
- 语义归模型，计算归脚本；脚本统一 `--json` 返回 `status/outputs/rows_used/rows_dropped/verified/warnings`。
- 取色必须走 `category_order`；版式必须走 6 套安全族；导出必须可预测物理尺寸。
- 不修改宿主默认 Skill；不打包受限字体、GeoJSON 或商业模板。

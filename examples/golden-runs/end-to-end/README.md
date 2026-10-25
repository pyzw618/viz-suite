# Stage 5 · 全局联调与端到端金标

12 个覆盖全场景的端到端任务，全部使用同一套 Skill 集群，不依赖任何外部网络或隐式环境。每个任务有 `task.json`、README、真实输入/输出与验证记录。

## 覆盖

| # | 任务 | 主路由 | 场景 | 关键产物 |
| :--- | :--- | :--- | :--- | :--- |
| 01 | 科研多面板组图 | `viz-python` | academic | 183 mm PDF/SVG/PNG + 图注 |
| 02 | 销售联动看板 | `viz-web` | bi | 1280/390 截图 + HTML + CSV |
| 03 | 复盘一页纸信息图 | `viz-infographic` | — | HTML/SVG + 整页截图 |
| 04 | 截图逆向换品牌色 | `viz-reverse` → `viz-python` | — | 反推 CSV/spec + 品牌图 |
| 05 | 问题丑图诊断修复 | `viz-audit` → `viz-python` | — | before/after + 对比 audit |
| 06 | 分析→统计→绘图→PDF/PPT | `viz-core` → `viz-python` | — | 2 页 PDF + CSV + handoff |
| 07 | 科研森林图 | `viz-python` | academic | 183 mm 森林图 + CI/n |
| 08 | 区域经营地图 | `viz-python` | geo | 分级设色 + 缺失斜纹 + CRS |
| 09 | 高管汇报 16:9 故事图 | `viz-python` | story | 254×142.9 mm 图 |
| 10 | 技术管线信息图 | `viz-infographic` | — | technical HTML/SVG |
| 11 | 源码级精确提取 | `viz-reverse` | — | SOURCE 数据/配置/JS |
| 12 | 低清/3D 逆向降级 | `viz-reverse` | — | C 级降级 + X 级拒绝 |

## 校验结果

`run_suite.py` 读取 12 个 `task.json`，检查输入/输出与路由矩阵：

```json
{
  "status": "success",
  "tasks": 12,
  "passed": 12,
  "missing": [],
  "skill_coverage": [
    "viz-audit", "viz-core", "viz-infographic", "viz-python",
    "viz-reverse", "viz-scene-academic", "viz-scene-bi",
    "viz-scene-geo", "viz-scene-story", "viz-web"
  ],
  "missing_skills": [],
  "routing": {"cases": 12, "negative_cases": 4, "task_routes_consistent": true}
}
```

- 详细记录：`results.json`
- 总览接触表：`contact.png`
- 路由测试：`routing-matrix.json` / `routing-matrix.md`（12 个正例 + 4 个负例）

## 路由打磨

- 10 个 `SKILL.md` 的 description 都增加了“**不用于截图逆向（用 viz-reverse）**”边界；
- `viz-reverse` 增加“不用于正向绘图/看板/信息图”，保留登录/付费墙/版权负向边界；
- `viz-audit` 明确不用于逆向数据提取；
- 12 个正例 + 4 个负例验证“最终形态优先于输入形态”：
  - 论文图改看板 → `viz-web`；
  - ECharts 画投稿 PDF → `viz-python`；
  - 信息图加筛选 → `viz-web`；
  - 3D 饼精确反推 → `viz-reverse` 的 X 级拒绝。

## 复现

```bash
cd examples/golden-runs/end-to-end
python run_suite.py
```

单个任务：

```bash
# 01
cd tasks/01-academic-multipanel/work && python make_figure.py
# 03
cd tasks/03-retro-infographic && \
  uv run ../../../../../skills/viz-infographic/scripts/render_infographic.py \
  input/retro.json --outdir outputs --stem retro --json
# 04
cd tasks/04-reverse-rebrand && \
  python ../../../../../skills/viz-reverse/scripts/inspect_image.py input/source.png \
  --chart-type bar --outdir work/inspect --json
# 06
cd tasks/06-analysis-to-pdf/work && python make_report.py
# 08
cd tasks/08-geo-grid-map/work && python make_map.py
```

其余任务的复现命令见各自 `README.md` 的 `task.json` 字段。

## 说明

- 02/07/09 复用 Stage 3 Gate 3 的同一份数据与产物，作为跨阶段回归；11/12 复用 Stage 4 Gate 4 的逆向夹具。
- 01/03/04/05/06/08/10 是本阶段新增的端到端产物，输入为合成演示数据，不含真实业务信息。
- 06 的 PPT 只交付 `handoff.md` 提纲与素材，不伪造已生成的 `.pptx`；PDF 由 matplotlib PdfPages 生成。
- 08 使用合成网格 GeoJSON，不是真实行政区边界；图中明确标注 local synthetic Cartesian、无投影/底图来源。
- 所有任务均不依赖外部 CDN、外部图片或隐式环境。

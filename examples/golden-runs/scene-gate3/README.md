# Gate 3 · 同一份经营实验数据的三种专业场景

验证 PLAN Stage 3 门禁：同一份数据，分别勾选 `viz-scene-academic`、`viz-scene-bi`、`viz-scene-story` 时，版式、标题、配色与导出规格呈现鲜明且准确的专业差异。

## 同一份数据

原始数据：`examples/fixtures/经营实验_渠道月度.csv`（24 行，2025 年 1–6 月 × 4 渠道，合成演示）。

| 场景 | 使用的列 | 派生 |
| :--- | :--- | :--- |
| academic | `A样本量/A转化数/B样本量/B转化数` | `data/ab_by_channel.csv`：各渠道 B−A 转化率差与 95% CI |
| bi | `收入_万元/目标_万元/新客数/满意度` | `bi/summary.csv`：月份/渠道/总体汇总 |
| story | `收入_万元` | `story/data/channel_month_long.csv`：月份 × 渠道长表 |

## 三套产物

| 场景 | 产物 | 规格 | 关键视觉 |
| :--- | :--- | :--- | :--- |
| academic | `academic/outputs/fig-ab-conversion.*` | 183 mm 双栏；PDF + SVG + 300/600 DPI PNG；6–8 pt；无大标题 | 森林图、95% CI、n、汇总菱形、L 型轴、无背景网格 |
| bi | `bi/index.html` + `bi/summary.csv` + `bi/shots/*` | 1280×800 与 390×844；离线 HTML；12 列栅格 | KPI 驾驶舱、IBCS 实际/目标、红黄绿阈值、As-of、筛选联动 |
| story | `story/outputs/story-revenue-shift.*` | 254×142.9 mm（16:9）；SVG + 300/600 DPI PNG | Action Title、单焦点蓝 + 冷灰、直接标注、来源/假设 |

总览：`contact.png`。机器可读的三场景配置：`scene-config.json`。

## 12 槽位对照

| 槽位 | academic | bi | story |
| :--- | :--- | :--- | :--- |
| 1 标题 | 图内无大标题；`a` 面板标号；图注独立 | “6 月收入 876 万元，目标完成率 104%”+ As-of/口径 | Action Title：“直播从 12% 升至 33%，贡献了上半年新增收入的三分之二” |
| 2 画布 | 183 mm 双栏（单栏 89 mm 规则见 scene-delta） | 12 列响应式；1280×800 / 390 单列 | 16:9（254×142.9 mm），兼容 4:5 |
| 3 色彩 | Okabe-Ito；色盲/灰度安全；无彩虹 | 实际蓝实心、目标灰虚线/空框；红黄绿阈值 | 单一焦点蓝 `#0072B2`；其余渠道冷灰 `#CBD5E1` |
| 4 字体 | 6–8 pt；Arial/宋体栈；0.5–1.5 pt 线宽 | 正文 12–14 px；KPI 大数 23 px；等宽数字 | 正文 11.5 pt≈15 px；标题 17 pt≈23 px；来源 10.5 pt |
| 5 轴/网格 | L 型轴、刻度朝外、无背景网格 | 弱虚线水平网格 + 目标线；零基线 | 弱化轴线；零基线；直接标注 |
| 6 批注 | n、95% CI、汇总效应；门店 CI 跨 0 明示 | 环比箭头、完成率、达标/临界/未达 | 6 月直播 286 万元（占比 32.6%）；总量直接标注 |
| 7 图种 | 森林图（点区间 + 汇总菱形） | KPI + 折线 + 环图 + 条形 + 明细表 | 高亮堆叠柱 + 总量线 |
| 8 交互 | 无；纯静态印刷级 | 月份/渠道筛选联动；Hover | 无；静态高清图 |
| 9 交付 | PDF + SVG + 300/600 PNG + 数据 CSV + 图注 | HTML + 汇总 CSV + 双视口截图 | SVG + 300/600 PNG + 数据 CSV |
| 10 来源 | 实验 n、95% CI、合成数据、图注 | As-of 2025-06-30、确认收入、目标口径 | 左下角来源 + 推演假设（增量=6 月−1 月） |
| 11 无障碍 | 灰度/色盲可辨；CI 不靠颜色 | 涨跌箭头+颜色双重编码；键盘可达 | 高对比；焦点色+直接标签；最小字号 ≥14 px |
| 12 禁令 | 无编造 p 值、无 Jet/Rainbow | 无满屏仪表盘/发光边框 | 无“哑巴图表”、无夸大差异 |

## 验证结果

- **academic**：`render.json` success；4 个渠道 + 汇总；`audit.json` 4 文件 / 23 项检查，blocking 0 / warning 0；目检通过。
- **bi**：`build_dashboard.py` 写入 24 行；`lint_html.py` 8 项检查 0 warning；`check_layout.py` 2 视口 0 issue；`audit_export.py` HTML 1 项检查 0 warning；筛选测试：1 月总收入 550 万元、1 月直播 68 万元；无 JS 错误。
- **story**：`render.json` success；254 mm / 16:9；`audit.json` 3 文件 / 17 项检查，blocking 0 / warning 0；目检通过。
- **同一数据**：三套产物均由上述 24 行派生；没有为场景差异替换数据。

## 复现

```bash
# academic
cd examples/golden-runs/scene-gate3/academic/work
uv run --python 3.12 forest_interval_diamond.py --json > ../render.json

# bi
cd ../../bi
uv run --python 3.12 build_dashboard.py

# story
cd ../story/work
uv run --python 3.12 stacked_bar_total_line.py --json > ../render.json

# BI 验收
cd ../..
uv run ../../../skills/viz-web/scripts/lint_html.py bi/index.html --json
uv run ../../../skills/viz-web/scripts/capture_html.py bi/index.html \
  --outdir bi/shots --viewport desktop=1280x800 --viewport mobile=390x844 --json
uv run ../../../skills/viz-web/scripts/check_layout.py bi/index.html \
  --viewport desktop=1280x800 --viewport mobile=390x844 --json
```

## 说明与限制

- `academic` 使用双栏 183 mm；单栏 85–89 mm 规则已写入 `scene-delta.md`。CI 为正态近似，图注已声明。
- `bi` 是离线单文件，ECharts 从 `bi/assets/vendor/` 本地加载；汇总 CSV 与页面同源。
- `story` 的“新增收入三分之二”= 直播增量 218 万 ÷ 总收入增量 326 万；假设与来源已在图内标注。
- `viz-scene-geo` 已交付 12 槽位规范，但 Gate 3 只要求 academic / bi / story 三场景；地理图需用户自备合规 GeoJSON。
- 本目录不包含任何真实业务数据；所有数字为合成演示。

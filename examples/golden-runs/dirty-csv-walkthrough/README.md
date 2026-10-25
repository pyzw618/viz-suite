# 金标案例：脏 CSV → 横向分组误差棒图

本目录是 Stage 1 Gate 1 的真实跑通记录：一份含缺失、重复、超长中文标签与文本化数值的脏 CSV，走完「画像 → 选型 → 看预览 → 拉底稿 → 改 PARAMS → 渲染 → AST 保真核对 → 脚本体检 → 多模态目检」全链路。

## 1. 输入

`../../fixtures/客服满意度_原始脏数据.csv`（UTF-8 BOM，372 行）

| 问题 | 数量 | 处置 |
| :--- | :---: | :--- |
| 全空行 | 3 | 剔除 |
| 完全重复记录 | 8 | `DROP_DUPLICATES=True` 剔除（调研口径） |
| 满意度评分缺失 | 36（含 3 行全空行） | 剔除，图注 n 为有效样本 |
| 响应时长以文本存储（含 `1,205`） | 1 行 | 本图未使用该列；画像已警告需清洗 |
| 超长中文标签 | 最长 36 个显示单位 | 自动切换横向条形图 |
| 高基数受访者编号 | 361 个唯一值 | 不作图，画像已警告 |

## 2. 画像结论

`profile.json` 关键字段：

- `rows_used=369`、`rows_dropped=3`（全空行）、`duplicate_rows=8`；
- `label_budget.max_label_units=36`、`orientation_hint=horizontal`；
- `group_candidates = [调研渠道, 城市, 季度]`，`value_candidates = [满意度评分, 响应时长_分钟]`；
- `group_sizes`：调研渠道 6 组，每组 60–63 行；拆分到「渠道 × 季度」后有效样本约 16–20；
- `季度` 被识别为有序分类（`period=quarter`，`ordered_values=[2024Q4, 2025Q1, 2025Q2]`），不会误判为连续时间戳；
- `chart_hints = [bar_grouped_horizontal, scatter, heatmap_or_grouped]`；
- 警告：8 行重复、响应时长文本存储、备注缺失 54%、长标签。

**选型**：`grouped_errorbar_bar`（首选）。理由：1 分类维（6 渠道）+ 1 系列维（3 季度）+ 1 数值维（满意度），需要同时表达均值与不确定性；长标签 → 横排。
**备选**：`raincloud_fusion`——若审稿人要求展示每个渠道的评分分布而非均值。
**禁忌**：堆叠柱比较组间总量；误差棒重叠不等于显著。

## 3. 底稿适配（仅改 PARAMS）

`work/grouped_errorbar_bar.py` 相对黄金底稿的改动：

```python
DATA_PATH = "../../../fixtures/客服满意度_原始脏数据.csv"
DROP_DUPLICATES = True
GROUP_COL = "调研渠道"
SERIES_COL = "季度"
VALUE_COL = "满意度评分"
TITLE = "门店与企业微信渠道满意度领先，社媒与小程序渠道垫底"
SUBTITLE = "按季度分组｜误差棒为 95% 置信区间｜已剔除重复与缺失"
VALUE_LABEL = "满意度评分（1–5 分）"
SOURCE = "数据来源：客服满意度调研脏数据（含缺失、重复与超长标签）｜演示用例"
ASPECT = 0.72          # 6 组 × 3 系列，增加高度保证条宽
OUTDIR = "../outputs"
STEM = "fig-01-channel-satisfaction"
```

绘制逻辑（浅填深边、误差棒、零基线、n 标注、总体均值线、长标签左边距）**未改动**。

## 4. 复现命令

```bash
cd examples/golden-runs/dirty-csv-walkthrough/work
uv run grouped_errorbar_bar.py --json > ../render.json

cd ../../../..   # 回到仓库根
uv run skills/viz-python/scripts/check_recipe_fidelity.py \
  --base skills/viz-python/recipes/grouped_errorbar_bar.py \
  --adapted examples/golden-runs/dirty-csv-walkthrough/work/grouped_errorbar_bar.py \
  --json > examples/golden-runs/dirty-csv-walkthrough/fidelity.json

uv run skills/viz-audit/scripts/audit_export.py \
  examples/golden-runs/dirty-csv-walkthrough/outputs/fig-01-channel-satisfaction.pdf \
  examples/golden-runs/dirty-csv-walkthrough/outputs/fig-01-channel-satisfaction_300dpi.png \
  --target-width-mm 160 --min-dpi 300 --fg "#1F2937" --bg "#FFFFFF" \
  --palette "#0072B2,#E69F00,#CC79A7" --json \
  --out examples/golden-runs/dirty-csv-walkthrough/audit.json
```

## 5. 运行结果

`render.json`：

- `status=success`，`verified=true`，`visual_verified=false`（脚本只验证文件生成）；
- `rows_used=326`，`rows_dropped=46`（3 全空行 + 8 重复 + 35 缺失评分）；
- `orientation=horizontal`，`160 × 115.2 mm`；
- 警告：18 个「渠道 × 季度」组合 n=16–20（<30），正态近似 CI 仅供参考；
- 产物：PDF、300/600dpi PNG、`fig-01-channel-satisfaction_data.csv`。

`fidelity.json`：

- `verdict=pass`，样式参数 33 → 33，无图层丢失，无样式值改动。

`audit.json`：

- `blocking=0`、`warning=0`（12 项检查全部通过）；
- PDF 首页 159.99mm，3 个字体全部嵌入，内容流约 381 个矢量绘制操作（未栅格化）；
- PNG 300dpi，159.94×115.1mm；
- 色板最小色差：正常 ΔE=41.1，protanopia 12.2，deuteranopia 25.2，tritanopia 10.9（阈值 10）。

## 6. 多模态目检记录

已用 `ViewImage` 实际查看 `outputs/fig-01-channel-satisfaction_300dpi.png`：

- [x] 中文无方块，长渠道名完整显示且未旋转；
- [x] 标题/副标题/来源均在画布内，无裁切；
- [x] 图例位于坐标区上方右侧，不遮挡数据；
- [x] X 轴从 0 开始（零基线）；
- [x] 每个渠道下第二行显示有效 n；
- [x] 总体均值虚线 3.51 与标签清晰；
- [x] 三个季度色（蓝/橙/粉）区分明显；
- [x] 误差棒帽可见，条宽在 115mm 高度下可读。

**残余风险**：18 个单元格 n=16–20，误差棒较宽；若用于正式报告，建议合并季度或补充样本。已在交付说明中声明。

## 7. 交付说明（可复用模板）

```text
产物：outputs/fig-01-channel-satisfaction.pdf / _300dpi.png / _600dpi.png / _data.csv
核心结论：企业微信与线下门店渠道满意度领先，社交平台与微信小程序渠道垫底。
数据口径：剔除 3 行全空行、8 行完全重复、35 行缺失评分；有效 n=326；误差棒为 95% CI（正态近似）。
默认假设：重复记录视为重复采集；季度按分类序列处理；满意度评分 1–5 分。
验证状态：viz-audit 脚本通过（blocking 0 / warning 0）；多模态目检已完成。
未解决项：18 个渠道×季度组合 n=16–20，CI 偏宽，已在图注与说明中提示。
```

## 8. 目录

```text
dirty-csv-walkthrough/
├── README.md              # 本文件
├── profile.json           # 画像结果
├── render.json            # 渲染协议输出
├── fidelity.json          # AST 保真核对
├── audit.json             # 物理/色彩体检
├── work/                  # 适配后的脚本 + viz_style + .viz-suite/assets
└── outputs/               # PDF、300/600dpi PNG、汇总 CSV
```

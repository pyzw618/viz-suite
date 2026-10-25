# 品牌换肤与多图风格锁定 · 金标运行

验证 PLAN Stage 2 的第 3 项：`EXTEND.md` 品牌换肤与 `figure-manifest.json` 多图风格锁定。
本目录是一次可复现的 4 图任务，所有数据为合成演示数据。

## 结论

| 检查 | 结果 | 证据 |
| :--- | :--- | :--- |
| 主题令牌 12 项断言 | 12/12 通过 | `theme-probe.json` |
| 4 套配方渲染 | 4/4 success，物理宽度均 150 mm | `render-fig-0*.json` |
| 导出体检（PDF/PNG） | 8 文件、48 项检查，blocking 0 / warning 0 | `audit.json` |
| 多模态目检 | 4 图中文正常、无文字重叠、无裁切 | `outputs/*_300dpi.png` |

四图接触表：`contact.png`。

## 配置

`figure-manifest.json`（任务级锁定）：

- `palette`: `okabe_ito`
- `layout_family`: `soft_grid`
- `width_mm`: `150`
- `series_color_map`: `2024Q4 → #0072B2`、`2025Q1 → #E69F00`、`2025Q2 → #CC79A7`
- `fonts` / `footer` 故意写入与品牌规范不同的值，用于验证覆盖顺序

`.viz-suite/EXTEND.md`（项目品牌覆盖）：

- 焦点色 `#0F62FE`、正文色 `#0B2545`、网格 `#DCE7F3`、画布 `#FAFCFF`
- 字体强制为 `Microsoft YaHei / PingFang SC / Noto Sans CJK SC`
- 页脚为「数据来源：商业分析部｜内部资料」
- 故意覆盖 manifest 的 `fonts` 与 `footer`

## 优先级实测

优先级按 `viz_style.resolve_theme()` 实现：

```text
显式 overrides > 项目 .viz-suite/EXTEND.md > 用户 EXTEND.md > figure-manifest.json > tokens
```

`theme-probe.json` 中的关键断言：

- `extend_beats_manifest_footer`: 实际为 EXTEND 页脚，manifest 页脚被覆盖；
- `extend_beats_manifest_fonts`: 实际为 `Microsoft YaHei`，manifest 的 `SimHei` 被覆盖；
- `palette_locked` / `layout_locked` / `width_locked`: manifest 的色板、版式族、150 mm 生效；
- `series_color_map_locked`: 三个季度系列拿到锁定的 HEX；
- `font_stack_usable`: 实际 `font.family` 为 Arial → Microsoft YaHei → DejaVu Sans，拉丁与中文均可回退。

## 四张图

| 图 | 配方 | 验证点 |
| :--- | :--- | :--- |
| `outputs/fig-01-rank.*` | `lollipop_rank_badges` | EXTEND 焦点色 `#0F62FE` 用于前三名徽章；页脚左右分区 |
| `outputs/fig-02-satisfaction.*` | `grouped_errorbar_bar` | 季度系列严格使用 manifest 锁色；误差棒、零基线不变 |
| `outputs/fig-03-rank-change.*` | `slope_rank_change` | 同一 `soft_grid` 版式族、150 mm 宽度与品牌字体 |
| `outputs/fig-04-revenue-mix.*` | `stacked_bar_total_line` | 与 fig-02 相同的三个季度实体跨图同色 |

`fig-02` 与 `fig-04` 的季度系列都取 `series_color_map`，以此证明「同一业务实体跨图同色」不是靠手工复制色值。

## 复现

```bash
cd examples/golden-runs/brand-lock/work
uv run --python 3.12 theme_probe.py

uv run lollipop_rank_badges.py --outdir ../outputs --stem fig-01-rank --json
uv run grouped_errorbar_bar.py --outdir ../outputs --stem fig-02-satisfaction --json
uv run slope_rank_change.py --outdir ../outputs --stem fig-03-rank-change --json
uv run stacked_bar_total_line.py --outdir ../outputs --stem fig-04-revenue-mix --json

cd ..
uv run ../../../skills/viz-audit/scripts/audit_export.py \
  outputs/*.pdf outputs/*_300dpi.png --target-width-mm 150 \
  --fg "#0B2545" --bg "#FFFFFF" --palette "#0072B2,#E69F00,#CC79A7" \
  --json --out audit.json
```

## 适配说明

- 四份底稿的 `WIDTH_MM` 与 `LAYOUT` 被置为 `None`，让 manifest 接管；底稿的默认值为 160 mm 与各自版式族，显式 PARAMS 仍优先。
- `fig-04` 使用 `data/quarterly_channel_revenue.csv`（合成），其余三图使用配方内置演示数据。
- `fig-02` 有 13 行缺失值被剔除（`rows_used=707`，`rows_dropped=13`），JSON 已如实记录。
- 品牌页脚与数据来源分列左右；品牌页脚不会覆盖数据出处。
- `work/viz_style.py`、四份配方与 `.viz-suite/assets/` 是为离线复现保留的快照；共享库更新后可重新 `get_recipe.py --force` 拉取。

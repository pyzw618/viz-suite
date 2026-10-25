# 字体、色彩与版式规范（Typography & Color）

本文件解释 `assets/tokens.json`、`assets/palettes.json` 与 `viz-python/scripts/viz_style.py` 的用法。**不要临场编造色值或字号。**

## 一、9 大色彩角色

| 角色 | 默认值 | 用途 | 约束 |
| :--- | :--- | :--- | :--- |
| `focal` | `#0072B2` | 焦点主色 | 每张图只有一个主视觉主角 |
| `context` | `#CBD5E1` | 背景对比序列 | 非重点系列统一置灰 |
| `positive` | `#198038` | 正向/达标 | 必须与 `negative` 双编码（颜色 + 符号） |
| `negative` | `#DA1E28` | 负向/异常 | 不要用于普通分类系列 |
| `alert` | `#D97706` | 阈值告警 | 配合文字说明阈值 |
| `grid` | `#E2E8F0` | 弱网格 | 与白底对比度 ≤15% |
| `background` | `#FFFFFF` | 画布 | 深色主题由 EXTEND 覆盖 |
| `text` | `#1F2937` | 主文本 | 正文对比度 ≥4.5:1 |
| `muted_text` | `#6B7280` | 来源注记 | 最小字号 7.5pt |

场景色板映射：`academic → okabe_ito`、`bi → bi_ibcs`、`story → editorial_warm`、`geo → met_egypt`。

## 二、色板与 `category_order`

`palettes.json` 内置 15 套宽松协议色板（Okabe-Ito、MetBrewer CC0、ColorBrewer、自研低饱和主题）。

每套色板除原始和谐顺序外，还维护 **`category_order`（最大感知色差优先索引）**：

1. 以设计主色 `colors[0]` 为种子；
2. 每次贪心选择与已选颜色 **最小 CIEDE2000 距离最大** 的下一个颜色；
3. 与白底 WCAG 对比度 <1.6 的颜色（如亮黄）降级到序列末尾，避免成为主系列。

因此 **只有 2–4 个分类时不要直接取 `colors[:n]`**，必须用 `palette.pick(n)` 或读取 `category_order`。

`min_delta_e` 字段给出正常视觉与三种色觉异常模拟下的全色板最小色差；`computed_colorblind_safe` 为 `deuteranopia ≥10 且 protanopia ≥10` 的自动判定。该判定是工程近似，不是临床结论。

**`safe_k`**：按 `category_order` 取前 k 色时，在 protanopia 与 deuteranopia 下仍保持两两 ΔE ≥10 的最大 k。**分类数不得超过 `palette.safe_k`**；超过时必须叠加线型/纹理，或改用更大色板/合并小类。`palette.pick_safe(n)` 会在超限时警告。

选择规则：

- 分类数 ≤ `min(8, palette.safe_k)`：优先 `colorblind_safe` 色板；
- 分类数 > `safe_k`：叠加线型/纹理，或改小多图；
- 灰度打印：`gray_print`，并叠加线型/纹理；
- 前后对比：`cb_paired`（浅/深成对）；
- 不确定时默认 `okabe_ito`（safe_k=7）。

## 三、色阶自动派生

**顺序色阶（Sequential）**：

```python
cmap = vs.sequential_cmap(base="#0072B2")
```

浅端 = 90% 画布白 + 10% 主题首色，平滑插值至主题首色。默认 256 级。

**发散色阶（Diverging）**：

```python
cmap = vs.diverging_cmap(base="#D55E00")   # 另一极自动取色板中最远颜色
```

- 另一极 = 当前色板中与 `base` 的 CIEDE2000 距离最大的颜色；
- 奇数 LUT（257 级），中点精确锁定 `#FFFFFF`；
- 禁止 Jet / Rainbow / 伪彩色。

**合成底色自适应文字**：

```python
label = vs.contrast_text(fill="#0072B2", background="#FFFFFF", alpha=0.18)
# 先按 fill×alpha + background×(1-alpha) 合成真实 RGB，再比较深灰 #2D2D2D 与纯白 #FFFFFF 的 WCAG 对比度
```

用于热力图单元格、半透明色块、地图分级色块上的标签。**禁止深底黑字或浅底白字。**

## 四、对比度阈值

| 对象 | 最低对比度 | 检查方式 |
| :--- | :--- | :--- |
| 正文/轴标签 | 4.5:1 | `vs.contrast_ratio(fg, bg)` |
| 大字号标题（≥18pt） | 3:1 | 同上 |
| 图形元素/色块边界 | 3:1 | 与相邻填充色比较 |
| 网格线 | ≤15% 视觉强度 | 低 alpha + 浅灰 |
| 色盲模拟最小色差 | ΔE ≥10 | `audit_export.py --palette` |

## 五、字体栈与字号

- 中文：`Microsoft YaHei → PingFang SC → Noto Sans CJK SC → Source Han Sans SC → SimHei`
- 英文：`Inter → Arial → Helvetica → Segoe UI → DejaVu Sans`
- `matplotlib` 的 `font.sans-serif` 会按字符回退：拉丁字符用英文字体，汉字自动落到中文字体。
- 运行 `uv run detect_fonts.py --json` 获取本机真实可用栈；**禁止硬编码未探测的字体**。
- `axes.unicode_minus = False`，避免负号显示为方块。
- `pdf.fonttype = 42`，保证 PDF 字体嵌入；`svg.fonttype = "none"` 保留可编辑文本。

字号档位（pt，作用于 160mm 画布）：

| 元素 | 默认 | small | large |
| :--- | :---: | :---: | :---: |
| 标题 | 13.0 | 11.7 | 14.6 |
| 副标题 | 10.5 | 9.5 | 11.8 |
| 轴标题 | 10.0 | 9.0 | 11.2 |
| 刻度 | 9.0 | 8.1 | 10.1 |
| 图例 | 9.0 | 8.1 | 10.1 |
| 批注 | 8.5 | 7.7 | 9.5 |
| 来源 | 7.5 | 6.8 | 8.4 |

上页最小可读字号 6.0pt；投影场景最小 14px（由场景模块覆盖）。

## 六、引用尺寸反推

公式：

```text
上页实际字号 = 代码字号 × 目标引用宽度 ÷ 原生画布宽度
```

若图会从 160mm 缩到 85mm 排版，代码字号 10pt 上页只剩 5.3pt——不可读。`plan_size` 自动放大：

```python
plan = vs.plan_size(width_mm=160, cite_mm=85, aspect=0.62)
fig, ax = vs.figure(plan["figsize"])
# plan["font_scale"] 已并入 bootstrap(font_scale=...)
```

常用物理宽度：单栏 89mm、双栏 183mm、A4 正文 160mm、16:9 投影 338.7×190.5mm。

## 七、6 套安全版式族与 6 个旋钮

| 版式族 | 特征 | 适用 |
| :--- | :--- | :--- |
| `clean_open` | 左下轴、刻度朝外、无网格 | 通用极简 |
| `soft_grid` | 左下轴 + 横向虚线网格 | 需要读数的比较图 |
| `framed_journal` | 四面框、刻度朝内、无网格 | 期刊投稿 |
| `bold_edge` | 加重轴线与刻度 | 投影/远距阅读 |
| `minimal_axis` | 仅底轴 | 坡度图、哑铃图、直接标注 |
| `panel_tint` | 浅灰蓝面板底 | 分区叙事 |

只开放 6 个旋钮：`border(open/journal)`、`grid(none/y/both)`、`line_width(thin/regular/bold)`、`font_size(small/regular/large)`、`legend_frame(false/true)`、`canvas(white/soft_tint)`。`open` 模式会显式关闭上/右刻度点，保证任意组合自洽。

## 八、微质感默认值

- 柱体/箱体：**同色系浅色半透明填充（alpha 0.18–0.30）+ 同色深色实线描边**；
- 散点/折线节点：细白边（0.6pt），防止重叠糊团；
- 不确定区间：多层递减透明度色带（0.08/0.12/0.18）；
- 均值线：`#6B7280` 虚线 0.9pt；
- 批注框：白底、`#D1D5DB` 细边、圆角；
- 直接标注优先于图例（系列 ≤5）。

`viz_style.bar_kwargs()` / `marker_kwargs()` / `line_kwargs()` 已封装这些默认值。

## 九、`EXTEND.md` 覆盖

`viz_style.resolve_theme()` 的覆盖优先级：

```text
用户当前指令 > 项目 .viz-suite/EXTEND.md > 用户 ~/.viz-suite/EXTEND.md
> figure-manifest.json > 激活的 viz-scene-* > 引擎默认版式族 > viz-core 基线
```

示例：

```yaml
colors:
  focal: "#0F62FE"
  context: "#CBD5E1"
typography:
  font_zh: "HarmonyOS Sans SC, Microsoft YaHei, sans-serif"
  font_en: "Inter, Arial, sans-serif"
brand:
  footer: "数据来源：商业分析部 | 内部资料"
stack:
  preferred_web: "echarts"
```

解析器支持两层扁平 YAML 子集（不含嵌套列表与多行字符串），零额外依赖。

## 十、多图台账 `figure-manifest.json`

≥3 张图时，在工作区根目录锁定：

```json
{
  "palette": "okabe_ito",
  "layout_family": "soft_grid",
  "width_mm": 160,
  "series_color_map": {"2024Q4": "#0072B2", "2025Q1": "#E69F00", "2025Q2": "#CC79A7"},
  "fonts": {"font_zh": ["Microsoft YaHei"]},
  "figures": [
    {"id": "fig-01", "title": "渠道满意度对比", "recipe": "grouped_errorbar_bar"},
    {"id": "fig-02", "title": "留存率分布", "recipe": "raincloud_fusion"}
  ]
}
```

`series_color_map` 确保同一业务实体跨图同色；`figures[].id` 提供唯一图号序列。

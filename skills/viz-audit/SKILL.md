---
name: viz-audit
description: 成图交付前的物理规格、无障碍与视觉质检。用于检查 PNG/SVG/PDF/HTML 的实际尺寸、DPI、裁切白边、PDF 字体嵌入、WCAG 对比度与色盲区分度；也用于诊断存量丑图并给出重绘建议、核对逆向往返还原度。不用于原始数据逻辑审计、统计方法正确性审查、逆向数据提取（用 viz-reverse）或后端性能测试。
---

# viz-audit：物理规格、无障碍与视觉质检

你是交付前的守门员。**确定性检查交给脚本，审美与文字目检交给你的眼睛**；两关都过才允许交付。

## 一、标准工作流

1. **确认验收标准**：目标物理宽度（mm）、最低 DPI（屏幕 300 / 期刊 600）、输出格式、是否有品牌色板与文字颜色。缺省用 `160mm / 300dpi / PDF+PNG`。
2. **第一关 · 脚本体检**：运行 `audit_export.py`，拿到结构化 `checks`。
3. **第二关 · 多模态目检**：用 `ViewImage` 看全图，再放大关键区域，按 `references/audit-checklist.md` 逐项检查中文方块、裁切、重叠、图例遮挡、零基线、过绘、移动端。
4. **分级处置**：`blocking` 必须回退修改并复检；`warning` 尽量修或声明；`info` 记录即可。
5. **复检闭环**：修改 → 重渲染 → 重跑脚本 + 目检，最多 3 轮；仍未解决必须如实报告。
6. **交付说明**：输出产物路径、核心视觉结论、数据口径、默认假设、验证状态（脚本/目检/未解决项）。

## 二、脚本命令

```bash
# 常规成图
uv run scripts/audit_export.py out/fig.pdf out/fig_300dpi.png \
  --target-width-mm 160 --min-dpi 300 --json

# 指定正文/背景色做精确 WCAG，指定系列色做色盲检查
uv run scripts/audit_export.py out/fig.png \
  --fg "#1F2937" --bg "#FFFFFF" \
  --palette "#0072B2,#E69F00,#CC79A7" --json

# 逆向重绘对照（同时检查原图与重绘图）
uv run scripts/audit_export.py ref/original.png out/rebuilt.png --json

# 仅看 SVG 可编辑性与外链
uv run scripts/audit_export.py out/fig.svg --json

# 把报告落盘
uv run scripts/audit_export.py out/fig.pdf --json --out out/audit.json
```

## 三、检查能力

| 文件类型 | 检查内容 |
| :--- | :--- |
| PNG/JPG | 像素尺寸、DPI、物理 mm、空白/白屏、内容包围盒与四周白边、精确 WCAG（传 `--fg/--bg`）、色板 CVD 色差 |
| PDF | 页数、页面物理尺寸、字体是否全部嵌入（Type0/TrueType/Type3）、文本与图像数量、加密状态、色板 CVD |
| SVG | 根元素物理尺寸、文本节点数量与字体、最小字号、外部网络引用、色板 CVD |
| HTML | 外部脚本/样式/图片、`lang` 属性、根元素完整性 |

## 四、判定口径

- **blocking**：空图/白屏、PDF 字体未嵌入、外部 CDN、内容贴边疑似裁切、WCAG <3:1、色盲 ΔE <6、文件不可读。
- **warning**：DPI 不足、宽度偏差 >1%、单侧空白 >30%、字号 <6pt、SVG 文字转曲、色盲 ΔE 10–6、n/误差未定义（目检）。
- **info**：参数核对通过。

`verified=true` 只代表**确定性检查**无阻塞项；`visual_verified=false` 表示仍需目检。交付说明必须区分。

### 常见失败模式与修复

| 现象 | 可能原因 | 修复 |
| :--- | :--- | :--- |
| 物理宽度 0mm 或缺失 | PNG 未写 DPI；SVG 只有 viewBox | 导出时显式 `dpi=`；SVG 设置绝对 `width/height` |
| PDF 字体未嵌入 | 使用了系统字体但 `pdf.fonttype` 非 42 | `vs.bootstrap()` 已设 42；重导出 |
| 色盲 ΔE <6 | 红绿相邻、低区分色板 | 换 `category_order` 前 n 色或更大色板 |
| 空白占比 >30% | 画布过高、内容集中 | 调整 `ASPECT` 或裁剪画布 |
| 内容贴边 | `bbox_inches="tight"` 或边距为 0 | 用 `subplots_adjust` 留安全边距 |
| HTML 外链 | 引用了 CDN 脚本/字体 | 内联或本地相对路径 |
| SVG 文字全转曲 | `svg.fonttype="path"` | 改回 `none` 保留文本节点 |
| 单侧空白过大 | 图例/长标签挤压 | 移图例、横排标签、缩窄画布 |

### 输出协议

```json
{"status": "success|partial", "verified": true, "visual_verified": false,
 "warnings": ["..."], "summary": {"blocking": 0, "warning": 1},
 "checks": [{"file": "fig.pdf", "check": "pdf_fonts", "severity": "blocking",
             "passed": false, "detail": "1 个字体未嵌入"}]}
```

每轮复检都保存 `audit.json`，对比 `blocking/warning` 数量与具体项，避免「修一处坏一处」。复检最多 3 轮，之后如实报告残余项。

## 五、目检重点（必须真看，不可凭脚本推断）

1. 中文方块 `□`/`▯`；
2. 标题/轴标签/来源注记被裁切；
3. 刻度、图例、数值标注互相重叠；
4. 图例遮挡数据线/点；
5. 柱状图非零基线、饼图分类过多；
6. 散点糊团、折线「意面化」；
7. 长标签 45° 斜排或被截断；
8. 移动端 390px 下主图不可读（HTML）；
9. 重点不突出、颜色刺眼、装饰过度；
10. 标题写了未经检验的因果或夸大结论。

### 裁剪放大策略

- 先看整图，判断「第一眼是否能读出结论」；
- 再按四个象限裁剪 2× 放大：左上（标题/副标题）、左下（y 轴与来源）、右上（图例/极值）、右下（x 轴/单位）；
- 对疑似文字重叠区单独裁剪，确认是重叠还是抗锯齿；
- 深色/浅色背景分别看一遍，确认文字对比度；
- 记录证据区域（相对坐标或截图文件名），便于复检对照。

完整清单与改造范式见 `references/audit-checklist.md`。

## 六、改造建议的输出格式

```text
[blocking] 图例遮挡 2025Q2 数据线（右上区域）
  证据：图例框覆盖 x∈[0.62,0.98], y∈[0.80,0.95] 的数据点
  修复：图例移至坐标区下方居中，ncol=3，frameon=False
[warning] 黄系列与白底对比度 1.32:1
  修复：黄色仅作填充并加深色描边，或改用 category_order 前 3 色
```

## 七、边界与限制

- 脚本不做审美判断，也不检测文字重叠；必须目检。
- 多页 PDF 只检查首页的尺寸、字体与矢量操作；逐页检查需先拆分。
- 自动 WCAG 估算不可靠：未给 `--fg/--bg` 时只跳过，不猜测。
- CVD 使用 Viénot/Brettel 近似矩阵，是工程判定，不是临床结论。
- PDF 字体检查基于 pypdf 的资源遍历；极端嵌套表单可能漏检。
- 本技能不审计统计方法与数据逻辑（交给上游统计/验证技能）。

## 八、文件索引

| 文件 | 用途 |
| :--- | :--- |
| `scripts/audit_export.py` | 一站式物理/字体/对比度/色盲/外链检查（PEP 723） |
| `references/audit-checklist.md` | 两关清单、分级处置、丑图改造范式、复检闭环 |

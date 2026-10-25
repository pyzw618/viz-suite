# 信息图 12 布局 × 4 风格 · Stage 3 证据

验证 `viz-infographic`：12 种信息结构 × 4 种视觉皮肤 = **48 种组合**，每种都输出离线 HTML 与 SVG。

## 结果

| 检查 | 结果 |
| :--- | :--- |
| 组合渲染 | 48/48 success；96 个 HTML/SVG 文件 |
| HTML lint | 48 文件、384 项检查；blocking 0 / warning 0 |
| 布局溢出 | 48 HTML × 2 视口 = 96 组合；issues 0 / missing 0 |
| SVG 体检 | 48 文件、144 项检查；blocking 0 / warning 0 |
| 图标 | 100 个本地 Lucide SVG（ISC）；无 Emoji 图标；未知图标回退并 warning |
| 目检 | 4 张按风格接触表 + 12 布局；中文折行、卡片对齐、无重叠/裁切 |

## 组合与样例

| 布局 | 使用样例 | 适合的关系 |
| :--- | :--- | :--- |
| `list-grid` | `specs/sample.json` | 并列要点 |
| `list-row` | `specs/sample.json` | 逐行论据 |
| `sequence-steps` | `specs/sequence.json` | 有先后顺序的步骤 |
| `timeline` | `specs/timeline.json` | 时间里程碑 |
| `pyramid` | `specs/pyramid.json` | 层级/优先级 |
| `funnel` | `specs/funnel.json` | 转化/流失 |
| `quadrant` | `specs/sample.json` | 二维定位 |
| `compare-binary` | `specs/sample.json` | 方案/现状对比 |
| `hierarchy-tree` | `specs/sample.json` | 分类体系 |
| `mindmap` | `specs/sample.json` | 概念放射 |
| `cycle` | `specs/sample.json` | 闭环/迭代 |
| `stat-cards` | `specs/sample.json` | 核心大数 |

48 个输出命名：`outputs/<layout>__<style>.html` 与 `.svg`。

## 皮肤对照

- `editorial`：暖纸底、衬线标题、红色焦点、细分隔线、方角。
- `minimal`：近白底、细线、单一蓝点、高留白、无阴影。
- `technical`：蓝灰网格、等宽标签、方角卡片、左强调条。
- `warm`：奶油底、珊瑚/青绿、圆角、轻阴影、点状纹理。

总览接触表：

- `contact-editorial.png`：12 布局 × 报刊
- `contact-minimal.png`：12 布局 × 极简
- `contact-technical.png`：12 布局 × 工程
- `contact-warm.png`：12 布局 × 暖色
- `contact-mobile.png`：12 布局 × 390 px 手机

## 复现

```bash
cd skills/viz-infographic

for l in list-grid list-row sequence-steps timeline pyramid funnel quadrant compare-binary hierarchy-tree mindmap cycle stat-cards; do
  for s in editorial minimal technical warm; do
    uv run scripts/render_infographic.py \
      ../../examples/golden-runs/infographic-gallery/specs/sample.json \
      --layout "$l" --style "$s" --formats html,svg \
      --outdir ../../examples/golden-runs/infographic-gallery/outputs \
      --stem "${l}__${s}" --json
  done
done

uv run ../viz-web/scripts/lint_html.py ../../examples/golden-runs/infographic-gallery/outputs/*.html --json
uv run ../viz-web/scripts/check_layout.py ../../examples/golden-runs/infographic-gallery/outputs/*.html \
  --viewport desktop=1280x800 --viewport mobile=390x844 --json
uv run ../viz-audit/scripts/audit_export.py ../../examples/golden-runs/infographic-gallery/outputs/*.svg --json
```

> 复现脚本用 `specs/sample.json` 对所有布局做组合验证；要得到更贴合语义的展示图，按上表替换为 `sequence/timeline/pyramid/funnel` 样例。

## 证据文件

- `lint.json`：48 HTML 的 384 项检查。
- `layout.json`：96 个 page/viewport 的溢出与越界检测。
- `audit.json`：48 SVG 的 144 项体检。
- `capture-mobile.json`：手机整页截图记录；桌面 48 组合的缩略总览见 4 张 `contact-*.png`。
- `shots/`：12 布局（editorial）+ 3 个额外皮肤代表图。
- `shots-mobile/`：12 布局手机整页截图。

## 说明

- 所有样例均为合成演示数据；不包含真实业务信息。
- 文本预算：标题 ≤90 字、模块正文 ≤240 字、单模块 ≤7 要点；超限截断并写 warning。
- HTML 用 `figure` + `figcaption` + `aria-label`；SVG 为 1200×1600 海报，Python 侧折行。
- 未知图标会回退 `circle-dot` 并写 warning；本套 48 组合无 warning。
- 需要 PNG 时用 `viz-web/capture_html.py --full-page`，不要用低分辨率截图冒充交付。

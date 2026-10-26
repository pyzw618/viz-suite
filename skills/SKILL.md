---
name: viz-suite
description: 全场景离线数据可视化与图表工程总入口。按表达语义分流至统计与科学图表（viz-figure，含图表逆向）、离线交互看板（viz-interactive）或结构化信息图（viz-diagram），支持四类场景预设（academic/bi/story/geo）与多图锁色规划。
---

# viz-suite · 数据可视化总入口

本入口仅负责识别表达意图并分派通道。确认目标通道后，**只读取所选通道的 `SKILL.md` 及本次任务必需的按需参考**，不预加载无关通道。

| 任务语义与交付目标 | 读取的通道 Skill |
| :--- | :--- |
| 真实数据统计图、期刊/汇报静态矢量图、多面板科学组图、空间分级设色图；或从已有网页/SVG/截图逆向提取数据与重绘 | [统计与逆向 · viz-figure](viz-figure/SKILL.md) |
| 需要浏览器筛选联动、Hover 明细、过渡动画的单文件交互图（ECharts/D3）或响应式商业 KPI 驾驶舱 | [交互与看板 · viz-interactive](viz-interactive/SKILL.md) |
| 流程步骤、时间轴、金字塔、四象限、层级树、闭环飞轮、核心大数卡等结构化观点/架构信息图（HTML + SVG） | [信息与架构图 · viz-diagram](viz-diagram/SKILL.md) |

**分流铁律**：按**内容语义**而非文件扩展名分派——数值证据即使交付 SVG/PDF 仍走 `viz-figure`；交互筛选即使数据源于科研实验仍走 `viz-interactive`；纯逻辑架构即使含少量数字仍走 `viz-diagram`。需求缺口会实质改变图种时，最多合并追问 3 个关键问题（受众场景、核心问题、输出规格），详见 [需求澄清](shared/references/intake-guide.md)。

## 路径锚点与场景预设

- `<SKILL>` 始终指本文件所在的 `skills/` 包根目录；三个子通道位于 `<SKILL>/viz-{figure,interactive,diagram}/`，共享令牌、选型与质检脚本位于 `<SKILL>/shared/`。
- `<WORKSPACE>` 指当前任务工作区；源码副本（`viz-work/`）、运行配置（`.viz-suite/`）与导出产物（`outputs/`、`shots/`）一律写入 `<WORKSPACE>`，详见 [执行环境与宿主适配](shared/references/host-adapter.md)。
- 四个场景预设（`academic` 学术出版 / `bi` 商业看板 / `story` 16:9 叙事 / `geo` 空间地理）存放在 `<SKILL>/shared/assets/scenes/*.json`，由代码通过 `--scene` 或 `figure-manifest.json` 直接加载，语义速查见 [场景增量规范](shared/references/scene-deltas.md)。

## 多图套图与混合任务

同一报告或论文含 ≥2 张图时，先在 `<WORKSPACE>/figure-manifest.json` 登记全局 `scene`、`palette`、`series_color_map`（锁定同一实体跨图同色）与分图清单，再按每张图的通道分别执行并用 `<SKILL>/shared/scripts/audit_export.py` + 宿主多模态读图工具逐图核验。单图任务无需启动整套规划。

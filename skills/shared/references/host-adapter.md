# 执行环境与宿主适配（Host Adapter）

本说明统一 `viz-suite` 在不同 Agent 宿主（Antigravity、Claude Code、Codex、Cursor 等）下的路径锚点、运行命令与看图复核方式。

## 1. 路径锚点约定

- `<SKILL>`：始终指 `viz-suite` 包根目录（即 `skills/SKILL.md` 所在目录；从任一子通道 `viz-figure/`、`viz-interactive/`、`viz-diagram/` 出发均为 `../`）。
- `<WORKSPACE>`：当前用户任务工作区目录。工作区内的临时源码（`viz-work/`）、运行缓存（`.viz-suite/`）与交付产物（`outputs/`、`shots/`）均相对于 `<WORKSPACE>` 解析，**绝不写回 `<SKILL>` 安装目录**。

首次在陌生工作区执行时，可运行环境探针固化路径与可用工具：

```bash
uv run "<SKILL>/shared/scripts/resolve_runtime.py" --workspace "<WORKSPACE>" --json
```

若宿主持有 `uv`，优先使用 `uv run <script.py>`（各脚本顶部均内联 PEP 723 依赖声明）；若无 `uv`，使用同一 Python 3.10+ 环境直接运行 `python <script.py>`。

## 2. 项目级配置优先级

所有通道统一遵循以下覆盖链（高到低）：
`CLI 显式参数 > <WORKSPACE>/.viz-suite/EXTEND.md > ~/.viz-suite/EXTEND.md > <WORKSPACE>/figure-manifest.json > 场景预设 (scenes/*.json) > tokens.json 默认值`。

多图或跨通道任务在 `<WORKSPACE>/figure-manifest.json` 中统一维护 `scene`、`palette`、`series_color_map`（锁定同一业务实体的跨图颜色）与图件清单。

## 3. 宿主无关的视觉复核规则

- **不绑定单一工具名**：打开候选预览图（`<SKILL>/viz-figure/catalog/previews/*.jpg`）与最终导出图（`*_300dpi.png`、`shots/*.png`）时，调用**当前宿主提供的多模态读图工具**（例如 `read_file`、`Read`、`view_file` 或宿主内置图像查看器），不要假设某个固定工具名必然存在。
- **双重质检闭环**：
  1. **确定性脚本门禁**：静态图与 PDF/SVG 跑 `<SKILL>/shared/scripts/audit_export.py`（含 Agg Renderer 文本包围盒碰撞自检、DPI、字体嵌入、色盲 ΔE）；Web/信息图额外跑 `<SKILL>/viz-interactive/scripts/lint_html.py` 与 `check_layout.py`。
  2. **多模态真图审校**：脚本返回 `verified=true` 仅证明物理与几何盒合规；交付前必须用宿主读图工具实际打开渲染 PNG，确认中文无乱码方块、视觉主次分明、注释连线无穿刺遮挡后，方可标记视觉复核完成。

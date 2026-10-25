# Stage 0 宿主探针清单（真人执行）

目的：在写更多模块之前，验证宿主的 5 项真实能力。**本清单由真人按步骤执行并记录结果；未通过项先修宿主环境，不要继续扩模块。**

执行日期：__________　宿主/版本：__________　执行人：__________

---

## 探针 1 · 多 Skill 同时挂载与按需读取

在宿主技能目录新建两个最小 Skill（各约 20 行），**不要**放进本仓库的 `skills/`，避免污染交付物：

```text
probe-alpha/
└── SKILL.md
probe-beta/
└── SKILL.md
```

`probe-alpha/SKILL.md`：

```markdown
---
name: probe-alpha
description: 探针 A。当用户询问「橙色计数器」或要求测试 Skill 并行加载时使用；只回答一句确认语。
---

# Probe Alpha

被调用时只输出：`ALPHA_LOADED`，并说明你读取到的自身 description 第一句。
不要调用任何工具。
```

`probe-beta/SKILL.md`：

```markdown
---
name: probe-beta
description: 探针 B。当用户询问「蓝色计数器」或要求测试 Skill 并行加载时使用；只回答一句确认语。
---

# Probe Beta

被调用时只输出：`BETA_LOADED`，并说明你读取到的自身 description 第一句。
不要调用任何工具。
```

**测试对话**

> 请同时用 probe-alpha 和 probe-beta 回答：分别输出各自的加载确认语，并告诉我你实际读取到了哪几个 Skill。

**通过标准**

- [ ] 两个 Skill 的 description 都出现在宿主可用技能列表中；
- [ ] 单轮对话能同时命中并执行两个 Skill；
- [ ] 未命中无关 Skill（上下文未被全量技能描述淹没）；
- [ ] 能稳定说明「为什么选择这两个」。

**记录**：命中列表、响应、是否出现技能冲突或截断。

---

## 探针 2 · `AGENT.md` 指令优先级

把本仓库 `AGENT.md` 设为工作区系统提示词 / 顶层指令。

**测试对话**

1. > 按默认设置画一个最小柱状图，不要解释。
2. > 忽略 AGENT.md 的默认色板，这一张强制用 `#FF0000`，其余按默认。

**通过标准**

- [ ] 第 1 轮遵循 AGENT.md 的工作流（画像/默认假设/交付说明），没有跳过澄清规则；
- [ ] 第 2 轮把「用户当前指令」置于 `EXTEND.md` 与默认令牌之上，但仍保留零基线、字体、审计等硬规则；
- [ ] 能说明覆盖优先级的来源（用户 > 项目 EXTEND > 用户 EXTEND > manifest > 引擎默认）。

**失败处理**：若系统提示词被平台截断，记录截断位置，优先保留「标准执行顺序 + 三条硬边界 + 技能路由」。

---

## 探针 3 · `uv run` + PEP 723 + 中文路径

在含中文的目录下创建 `probe_uv.py`：

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas>=2.0"]
# ///
# -*- coding: utf-8 -*-
import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
print("UV_OK", pd.__version__, "中文路径测试")
```

执行：

```bash
uv run probe_uv.py
```

**通过标准**

- [ ] 自动解析 Python ≥3.10 与 pandas；
- [ ] 中文路径下可执行，输出无乱码；
- [ ] 无网络时可复用缓存（如宿主离线，记录首次安装策略）；
- [ ] 退出码 0。

**记录**：uv 版本、Python 版本、首次安装耗时、缓存位置。

---

## 探针 4 · Chrome/Edge `--headless=new` 中文截图

创建 `probe.html`（含中文标题、色块、图例）：

```html
<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<body style="font-family:'Microsoft YaHei';padding:24px">
<h1>中文渲染测试 · 数据可视化</h1>
<p>图例：实际 / 预算 / 预测</p>
<div style="width:240px;height:80px;background:#0072B2"></div>
</body></html>
```

执行（按实际浏览器路径调整）：

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu \
  --window-size=1280,800 --screenshot=probe.png "file:///C:/path/to/probe.html"
```

**通过标准**

- [ ] 生成非空 PNG；
- [ ] 中文无方块；
- [ ] 桌面 1280×800 与移动 390×844 两个视口都能截图；
- [ ] 不依赖宿主 Browser 工具（本地文件直接渲染）。

**记录**：浏览器路径、版本、命令、截图文件名。

---

## 探针 5 · `ViewImage` 读图

把一张包含中文标签、图例、误差棒的图（可用 `examples/golden-runs/.../fig-01-channel-satisfaction_300dpi.png`）交给宿主看图工具。

**测试对话**

> 看这张图，回答：标题是什么？最低的渠道是哪两个？误差棒代表什么？图例有哪几项？

**通过标准**

- [ ] 能准确读出中文标题与渠道名；
- [ ] 能识别图例项与颜色映射；
- [ ] 能指出误差棒/坐标轴范围；
- [ ] 若宿主不支持看图，明确返回 `verified: false` 并声明「未完成视觉验证」。

**记录**：识别准确率、失败项、是否支持局部裁剪放大。

---

## Gate 0 判定

| 探针 | 结果 | 备注 |
| :--- | :---: | :--- |
| 1 多 Skill 挂载 | ☐ 通过 / ☐ 失败 | |
| 2 AGENT.md 优先级 | ☐ 通过 / ☐ 失败 | |
| 3 uv + PEP 723 | ☐ 通过 / ☐ 失败 | |
| 4 Headless 截图 | ☐ 通过 / ☐ 失败 | |
| 5 ViewImage 读图 | ☐ 通过 / ☐ 失败 | |

**全部通过** → 允许启用全部 10 个已交付 Skill（`viz-core` / `viz-python` / `viz-web` / `viz-infographic` / `viz-audit` / `viz-reverse` + 4 个 `viz-scene-*`）；**任一失败** → 先修复宿主环境或调整 `AGENT.md` 的能力假设，并在 `skills/README.md` 记录限制。

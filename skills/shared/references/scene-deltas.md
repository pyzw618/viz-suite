# 四大场景预设与增量规范（Scene Deltas）

场景预设已内化为机器可读配置 `<SKILL>/shared/assets/scenes/{academic,bi,story,geo}.json`，并在 `viz_style.resolve_theme(scene=...)` 及各配方 `--scene` 参数中自动生效。以下为四场景语义要点速查：

| 维度 | `academic`（学术出版） | `bi`（商业看板 / IBCS） | `story`（高管叙事汇报） | `geo`（空间地理分析） |
| :--- | :--- | :--- | :--- | :--- |
| **标题范式** | **图内无大标题**（`in_canvas_title=false`）；左上标 `a, b, c`，结论入外部图注 | `对象 + 指标 + 时间窗 + 状态`；顶栏固定 As-of 日期与口径 | **Action Title** 直书事实结论（≤2 行）；副标题仅放口径单位 | `区域 + 标准化指标 + 时间切片`；副标题写分箱方法 |
| **默认尺寸** | 单栏 `89mm` / 双栏 `183mm`（上页缩印后字号 ≥6pt） | Web `1280×800` & `390×844`；静态宽 `160mm` | `254×142.9mm`（16:9 宽屏，投影最小字 ≥14px） | `180mm`（地图严格 `aspect='equal'` 等比） |
| **色彩策略** | `okabe_ito` 色盲安全 + 线型/点型灰度双编码；禁 `jet` | 实际=主色实心，目标=中性灰虚线/空框；红黄绿配符号文字 | `economist_editorial`；**单焦点色高亮**，背景系列冷灰 | 5–7 档顺序/发散色阶；**无数据区浅灰斜纹（hatch）** |
| **必配标注** | 样本量 `n`、误差口径（SD/SEM/95% CI）、真实检验名（禁编造 p 值） | YoY/MoM 箭头+数值、目标完成率公式 | 关键拐点事件气泡、倍数/百分点差距箭头、左下角来源假设 | **投影/CRS 坐标系、底图来源许可**、分箱档位 |
| **核心红线** | 严禁编造显著性、截断柱基线、掺入商业话术 | 严禁炫光大屏装饰框、横向溢出、混排不同时间口径 | 严禁哑巴指标标题、相关性写成因果、满图多色平均用力 | **严禁绝对总量直接着色面积**（须转密度/人均/比率）、严禁未审边界 |

## 调用方式

- **Python 统计图（`viz-figure`）**：运行脚本时加 `--scene academic|bi|story|geo`，或在工作区 `figure-manifest.json` 写入 `"scene": "academic"`，或在代码中调用 `vs.resolve_theme(scene="academic")`。
- **交互图表与看板（`viz-interactive`）**：读取 `<SKILL>/shared/assets/scenes/bi.json`（或 `story.json`）中的语义色、字号底线与视口契约，写入 HTML 顶部 CSS 变量。
- **信息图（`viz-diagram`）**：通过 `--style {editorial,minimal,technical,warm}` 映射对应叙事语气。

# EXTEND.md 示例（团队品牌覆盖）

把本文件复制为项目根目录 `.viz-suite/EXTEND.md`（项目级）或 `~/.viz-suite/EXTEND.md`（用户级）。
`viz_style.resolve_theme()` 会自动读取并合并；优先级：项目 > 用户 > manifest > tokens。

```yaml
colors:
  focal: "#0F62FE"          # 覆盖焦点主色
  context: "#CBD5E1"        # 非重点系列置灰色
  positive: "#198038"
  negative: "#DA1E28"

typography:
  font_zh: "HarmonyOS Sans SC, Microsoft YaHei, sans-serif"
  font_en: "Inter, Arial, sans-serif"

brand:
  footer: "数据来源：商业分析部 | 内部资料"

stack:
  preferred_web: "echarts"
  preferred_python: "matplotlib"
```

注意：

- 只支持两层扁平 YAML 子集（不含嵌套列表/多行字符串）；
- 字体必须是本机已安装字体，先用 `detect_fonts.py` 探测；
- `brand.footer` 渲染在图底部右侧，数据来源保留在左侧，二者不互相覆盖；
- 覆盖只影响语义令牌，不改变统计诚实规则（零基线、误差定义、n 标注等）；
- 复杂多图锁色请用 `figure-manifest.json` 的 `series_color_map`；
- 多图锁尺寸/版式时，把配方的 `WIDTH_MM` / `LAYOUT` 置为 `None`，让 manifest 接管；显式 PARAMS 仍优先。

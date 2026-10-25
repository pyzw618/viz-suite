# 逆向基准 · Gate 4 证据

验证 `viz-reverse`：

- 5 类清晰图（柱/折线/散点/饼/热力）反推数据误差中位数 ≤5%；
- 往返重绘 SSIM ≥0.85；
- 低清图触发 C 级降级；
- 3D 透视饼图触发 X 级拒绝；
- 源码级 ECharts / Chart.js / Plotly / SVG 精确提取（误差 0）。

## 结果

| 图种 | 证据 | 行数 | 反推误差中位数 | SSIM | ΔE 均值 | 布局 IoU |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 柱状 `bar.png` | B | 5 | 0.192% | 0.9488 | 1.504 | 1.000 |
| 折线 `line.png` | B | 12 | 0.223% | 0.9960 | 0.084 | 1.000 |
| 散点 `scatter.png` | B | 20 | 0.230% | 0.9991 | 0.014 | 1.000 |
| 饼图 `pie.png` | B | 5 | 0.863% | 0.9834 | 0.252 | 0.9946 |
| 热力 `heatmap.png` | B | 30 | 0.423% | 0.9962 | 0.199 | 0.9918 |

**Gate 4**

```json
{
  "clean_median_error_pct": 0.23,
  "max_median_error_pct": 0.863,
  "min_ssim": 0.9488,
  "error_pass": true,
  "ssim_pass": true,
  "lowres_pass": true,
  "three_d_pass": true,
  "pass": true
}
```

## 低清与 3D

- `bar_lowres.png`（400px）：`inspect_image` → `evidence_hint=C`；`calibrate_and_extract` → `status=partial`，刻度未检出时使用均匀位置近似，`precision_claimed=false`，明确“不承诺 5% 误差”。
- `pie_3d.png`（椭圆 aspect≈1.99）：`inspect_image` → `evidence_hint=X`；`calibrate_and_extract` → `status=partial`、`refused=true`，只输出 `2d-suggestion.md`，不输出数值 CSV。

## 源码级夹具

| 文件 | 通道 | 结果 | 精确误差 |
| :--- | :--- | :--- | :---: |
| `web/echarts_source.html` | 内嵌 ECharts option | 5 行，SOURCE | 0.0% |
| `web/chartjs_source.html` | `window.__CHART_CONFIG__` | 12 行，SOURCE | 0.0% |
| `web/plotly_source.html` | `window.__PLOTLY_DATA__` | 5 行，SOURCE | 0.0% |
| `web/bar_source.svg` | SVG `data-*` 元数据 | 5 行，SOURCE | 0.0% |
| `web/generic_c.html` | 无可读配置 | C 级骨架，`TODO` | — |

每个源码夹具同时生成 `*_browser-extract.js`，供 Browser 工具在已授权页面执行只读 `getOption()/config`。

## 复现

```bash
cd examples/golden-runs/reverse-benchmark

# 1. 生成基准图（可选，仓库已包含）
python generate_benchmark.py

# 2. 跑全管线（环境需 cv2/scikit-image/defusedxml/matplotlib）
python run_benchmark.py --python /path/to/python

# 3. 单独跑一张
python ../../../skills/viz-reverse/scripts/inspect_image.py \
  images/bar.png --chart-type bar --outdir rev/inspect --json
python ../../../skills/viz-reverse/scripts/calibrate_and_extract.py \
  images/bar.png --measurements rev/inspect/measurements.json \
  --ticks ticks/bar.json --chart-type bar \
  --outdir rev --stem bar --render --json
python ../../../skills/viz-reverse/scripts/compare_render.py \
  images/bar.png rev/reproduction.png --outdir rev/compare --json
```

## 文件

- `images/`：5 类清晰图 + `bar_lowres.png` + `pie_3d.png`。
- `ticks/`：VLM/人工读出的刻度、标题、系列颜色；**不含反推数据**。
- `ground-truth/`：只用于误差打分，不参与反推。
- `reverse-output/`：`measurements.json`、`*_data.csv`、`reverse-spec.json`、`reproduction.py/png`、`diff.png`、`results.json`。
- `contact.png`：原图 / 复现 / diff 对照。

## 说明

- 所有图与数据为合成演示，不含真实业务信息。
- 轴标定 R² 均 ≥0.999；柱/线/散点/饼/热力的误差来自抗锯齿与像素量化，不是调参。
- SSIM 用灰度结构；ΔE 为 CIEDE2000；IoU 为内容 bbox/像素。SSIM <0.85 时最多 3 轮，只修样式/轴/布局，**不得修改反推数据或加偏移**。
- 3D 饼图的 `pie_3d.png` 是透视压缩 + 阴影模拟，用于验证 X 级拒绝；不是可反推的真实 3D 数据。

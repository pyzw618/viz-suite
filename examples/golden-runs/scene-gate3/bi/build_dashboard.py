# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
# -*- coding: utf-8 -*-
"""生成 Gate 3 的 BI 驾驶舱（离线单文件 HTML，数据来自同一份 CSV）。"""
import csv
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # examples/golden-runs/scene-gate3 -> examples
DATA = ROOT / "fixtures" / "经营实验_渠道月度.csv"
VENDOR = HERE.parent.parent.parent.parent / "skills" / "viz-web" / "assets" / "vendor" / "echarts.min.js"
OUT = HERE / "index.html"
ASSETS = HERE / "assets" / "vendor"


def load_rows():
    with DATA.open(encoding="utf-8-sig") as fh:
        rows = []
        for r in csv.DictReader(fh):
            rows.append({
                "m": r["月份"], "c": r["渠道"],
                "rev": float(r["收入_万元"]), "target": float(r["目标_万元"]),
                "new": int(r["新客数"]), "sat": float(r["满意度"]),
            })
        return rows


TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>6 月经营驾驶舱 · IBCS</title>
<style>
:root{--bg:#F4F7FA;--surface:#FFFFFF;--text:#1F2937;--muted:#667085;--grid:#E4E7EC;
  --actual:#0072B2;--target:#667085;--positive:#198038;--negative:#DA1E28;--alert:#D97706;
  --tint:#EAF2F8}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--text);
  font-family:Inter,"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",Arial,sans-serif}
body{padding:16px 20px 18px;overflow-x:hidden}
.top{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:12px}
h1{font-size:21px;line-height:1.25;margin:0 0 4px;font-weight:700;letter-spacing:-.01em}
.tags{font-size:12px;color:var(--muted);margin:0}
.tags span{display:inline-block;margin-right:10px}
.filters{display:flex;gap:10px;flex-wrap:wrap}
label{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--muted)}
select{font:inherit;font-size:13px;padding:6px 10px;border:1px solid var(--grid);border-radius:6px;
  background:var(--surface);color:var(--text);min-width:110px}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:12px}
.kpi{background:var(--surface);border:1px solid var(--grid);border-radius:8px;padding:10px 14px;min-width:0}
.kpi .label{font-size:11px;color:var(--muted);letter-spacing:.04em}
.kpi .value{font-size:23px;line-height:1.15;font-weight:700;margin:3px 0 2px;font-variant-numeric:tabular-nums}
.kpi .sub{font-size:11px;color:var(--muted);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.kpi .sub.up,.kpi .sub.good,.kpi .sub .up{color:var(--positive);font-weight:700}
.kpi .sub.down,.kpi .sub.bad,.kpi .sub .down{color:var(--negative);font-weight:700}
.kpi .sub.warn,td.warn{color:var(--alert);font-weight:700}
td.good{color:var(--positive);font-weight:700}td.bad{color:var(--negative);font-weight:700}
td.up{color:var(--positive);font-weight:700}td.down{color:var(--negative);font-weight:700}
.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:10px}
.card{background:var(--surface);border:1px solid var(--grid);border-radius:8px;padding:10px 12px 8px;margin:0;min-width:0}
.card figcaption{font-size:13px;font-weight:700;margin-bottom:2px}
.card .hint{font-size:10px;color:var(--muted);margin:0 0 3px}
.chart{width:100%;min-width:0}
.span-8{grid-column:span 8}.span-4{grid-column:span 4}.span-6{grid-column:span 6}
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:11.5px;font-variant-numeric:tabular-nums}
th,td{padding:5px 4px;border-bottom:1px solid var(--grid);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:600}
footer{margin-top:10px;font-size:10.5px;color:var(--muted);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
@media (max-width:1000px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
  .span-8,.span-4,.span-6{grid-column:span 12}}
@media (max-width:600px){body{padding:12px}h1{font-size:18px}.filters{width:100%}
  .filters label{flex:1}select{width:100%}.kpi .value{font-size:20px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<header class="top">
  <div>
    <h1 id="page-title">6 月经营驾驶舱：收入 876 万元，目标完成率 104%</h1>
    <p class="tags"><span>As of 2025-06-30</span><span>口径：确认收入</span><span>单位：万元</span><span>数据：合成演示</span></p>
  </div>
  <div class="filters">
    <label>月份<select id="month"></select></label>
    <label>渠道<select id="channel"><option value="全部">全部渠道</option><option>直播</option><option>电商</option><option>门店</option><option>私域</option></select></label>
  </div>
</header>

<section class="kpis" aria-label="核心 KPI">
  <article class="kpi"><div class="label">收入</div><div class="value" id="rev-value">—</div><div class="sub" id="rev-sub"></div></article>
  <article class="kpi"><div class="label">目标完成率</div><div class="value" id="rate-value">—</div><div class="sub" id="rate-sub"></div></article>
  <article class="kpi"><div class="label">新客数</div><div class="value" id="new-value">—</div><div class="sub" id="new-sub"></div></article>
  <article class="kpi"><div class="label">满意度</div><div class="value" id="sat-value">—</div><div class="sub" id="sat-sub"></div></article>
</section>

<section class="grid">
  <figure class="card span-8">
    <figcaption>收入趋势：实际 vs 目标</figcaption>
    <p class="hint">实线=实际，虚线=目标；单位：万元；纵轴从 0 起</p>
    <div id="line" class="chart" role="img" aria-label="2025 年 1 至 6 月收入实际与目标折线图" style="height:220px"></div>
  </figure>
  <figure class="card span-4">
    <figcaption>渠道构成</figcaption>
    <p class="hint">当月收入占比；≤4 类</p>
    <div id="donut" class="chart" role="img" aria-label="当月各渠道收入占比圆环图" style="height:220px"></div>
  </figure>
  <figure class="card span-6">
    <figcaption>渠道收入：实际 vs 目标</figcaption>
    <p class="hint">实心=实际，空框虚线=目标；按目标完成率标色</p>
    <div id="bar" class="chart" role="img" aria-label="当月各渠道实际收入与目标收入对比条形图" style="height:200px"></div>
  </figure>
  <figure class="card span-6">
    <figcaption>渠道明细</figcaption>
    <p class="hint">完成率=实际÷目标；Δ=环比</p>
    <div class="table-wrap">
      <table aria-label="渠道经营明细">
        <thead><tr><th>渠道</th><th>收入</th><th>目标</th><th>完成率</th><th>环比</th><th>新客</th><th>满意度</th></tr></thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </figure>
</section>
<footer><span>数据来源：经营分析部 2025 年 6 月月报（合成演示数据）</span><span>零外部网络请求｜ECharts 5｜离线自包含</span></footer>

<script src="assets/vendor/echarts.min.js"></script>
<script>
const RAW = __DATA__;
const css = getComputedStyle(document.documentElement);
const C = k => css.getPropertyValue(k).trim();
const COLORS = [C('--actual'), '#E69F00', '#CC79A7', '#009E73'];
const CHANNELS = ['直播', '电商', '门店', '私域'];
const MONTHS = ['2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06'];
const LABELS = MONTHS.map(m => Number(m.slice(5)) + '月');
const state = {month: '2025-06', channel: '全部'};
const charts = {line: echarts.init(document.getElementById('line')), donut: echarts.init(document.getElementById('donut')), bar: echarts.init(document.getElementById('bar'))};

function rows(month, channel) {
  return RAW.filter(r => r.m === month && (channel === '全部' || r.c === channel));
}
function sum(list, key) { return list.reduce((a, r) => a + r[key], 0); }
function prevMonth(month) { const i = MONTHS.indexOf(month); return i > 0 ? MONTHS[i - 1] : null; }
function pct(a, b) { return b ? a / b * 100 : 0; }
function fmt(v, d = 0) { return Number(v).toLocaleString('zh-CN', {maximumFractionDigits: d}); }
function statusText(rate) { return rate >= 100 ? '达标' : rate >= 95 ? '临界' : '未达'; }
function statusClass(rate) { return rate >= 100 ? 'good' : rate >= 95 ? 'warn' : 'bad'; }
function setText(id, text) { document.getElementById(id).textContent = text; }
function setSub(id, text, cls) {
  const el = document.getElementById(id);
  el.textContent = text;
  el.className = 'sub' + (cls ? ' ' + cls : '');
}

function updateKpis() {
  const cur = rows(state.month, state.channel);
  const pm = prevMonth(state.month);
  const prev = pm ? rows(pm, state.channel) : [];
  const rev = sum(cur, 'rev'), target = sum(cur, 'target');
  const rate = pct(rev, target);
  const revDelta = prev.length ? pct(rev - sum(prev, 'rev'), sum(prev, 'rev')) : null;
  setText('rev-value', fmt(rev, 0) + ' 万元');
  setSub('rev-sub', (revDelta === null ? '无上月对比' : `${revDelta >= 0 ? '↑' : '↓'} ${Math.abs(revDelta).toFixed(1)}% 环比`) + ' · ' + statusText(rate),
    revDelta !== null && revDelta < 0 ? 'down' : statusClass(rate));
  setText('rate-value', rate.toFixed(1) + '%');
  setSub('rate-sub', `目标 ${fmt(target, 0)} 万元 · ${statusText(rate)}`, statusClass(rate));
  const newCur = sum(cur, 'new'), newPrev = prev.length ? sum(prev, 'new') : 0;
  const nDelta = newPrev ? pct(newCur - newPrev, newPrev) : null;
  setText('new-value', fmt(newCur) + ' 人');
  setText('new-sub', nDelta === null ? '无上月对比' : `${nDelta >= 0 ? '↑' : '↓'} ${Math.abs(nDelta).toFixed(1)}% 环比`);
  document.getElementById('new-sub').className = 'sub ' + (nDelta !== null && nDelta < 0 ? 'down' : 'up');
  const sat = cur.length ? sum(cur, 'sat') / cur.length : 0;
  setText('sat-value', sat.toFixed(2) + ' 分');
  setText('sat-sub', sat >= 4.3 ? '高于 4.3 服务基线' : '低于 4.3 服务基线');
  document.getElementById('page-title').textContent =
    `${Number(state.month.slice(5))} 月经营驾驶舱：收入 ${fmt(rev, 0)} 万元，目标完成率 ${rate.toFixed(0)}%`;
}

function renderLine() {
  const totals = MONTHS.map(m => rows(m, state.channel));
  charts.line.setOption({
    animationDuration: 300, backgroundColor: 'transparent',
    color: [C('--actual'), C('--target')],
    tooltip: {trigger: 'axis', valueFormatter: v => fmt(v, 0) + ' 万元'},
    legend: {data: ['实际', '目标'], right: 0, top: 0, textStyle: {color: C('--text'), fontSize: 11}},
    grid: {left: 48, right: 14, top: 32, bottom: 26},
    xAxis: {type: 'category', data: LABELS, axisTick: {show: false}, axisLine: {lineStyle: {color: C('--grid')}},
      axisLabel: {color: C('--muted'), fontSize: 10}},
    yAxis: {type: 'value', min: 0, splitNumber: 4, axisLabel: {color: C('--muted'), fontSize: 10},
      splitLine: {lineStyle: {color: C('--grid'), type: 'dashed', opacity: .55}}},
    series: [
      {name: '实际', type: 'line', data: totals.map(t => sum(t, 'rev')), symbol: 'circle', symbolSize: 5,
       lineStyle: {width: 2.2, color: C('--actual')}, itemStyle: {color: C('--actual'), borderColor: '#fff', borderWidth: 1}},
      {name: '目标', type: 'line', data: totals.map(t => sum(t, 'target')), symbol: 'none',
       lineStyle: {width: 1.5, type: 'dashed', color: C('--target')}}
    ]
  }, true);
}

function renderDonut() {
  const cur = rows(state.month, '全部');
  const data = CHANNELS.map((c, i) => ({name: c, value: sum(cur.filter(r => r.c === c), 'rev'),
    itemStyle: {color: COLORS[i], opacity: state.channel === '全部' || state.channel === c ? 1 : .35}}));
  const total = sum(cur, 'rev');
  charts.donut.setOption({
    animationDuration: 300, backgroundColor: 'transparent',
    tooltip: {trigger: 'item', valueFormatter: v => fmt(v, 0) + ' 万元'},
    legend: {bottom: 0, left: 'center', textStyle: {color: C('--text'), fontSize: 10}},
    graphic: [{type: 'text', left: 'center', top: '40%', style: {text: fmt(total, 0), fill: C('--text'),
      font: '700 20px "Microsoft YaHei"', textAlign: 'center'}},
      {type: 'text', left: 'center', top: '56%', style: {text: '万元', fill: C('--muted'),
        font: '11px "Microsoft YaHei"', textAlign: 'center'}}],
    series: [{type: 'pie', radius: ['46%', '68%'], center: ['50%', '43%'], avoidLabelOverlap: true,
      label: {show: false}, labelLine: {show: false}, data}]
  }, true);
}

function renderBar() {
  const cur = rows(state.month, '全部');
  const actual = CHANNELS.map(c => sum(cur.filter(r => r.c === c), 'rev'));
  const target = CHANNELS.map(c => sum(cur.filter(r => r.c === c), 'target'));
  charts.bar.setOption({
    animationDuration: 300, backgroundColor: 'transparent',
    tooltip: {trigger: 'axis', axisPointer: {type: 'shadow'}, valueFormatter: v => fmt(v, 0) + ' 万元'},
    legend: {data: ['实际', '目标'], right: 0, top: 0, textStyle: {color: C('--text'), fontSize: 11}},
    grid: {left: 46, right: 14, top: 32, bottom: 28},
    xAxis: {type: 'category', data: CHANNELS, axisTick: {show: false}, axisLine: {lineStyle: {color: C('--grid')}},
      axisLabel: {color: state.channel === '全部' ? C('--muted') : C('--text'), fontSize: 11,
        fontWeight: state.channel === '全部' ? 400 : 700}},
    yAxis: {type: 'value', min: 0, splitNumber: 4, axisLabel: {color: C('--muted'), fontSize: 10},
      splitLine: {lineStyle: {color: C('--grid'), type: 'dashed', opacity: .55}}},
    series: [
      {name: '实际', type: 'bar', data: actual.map((v, i) => ({value: v,
        itemStyle: {color: COLORS[i], opacity: state.channel === '全部' || state.channel === CHANNELS[i] ? 1 : .35}})),
       barWidth: 22, label: {show: true, position: 'top', color: C('--muted'), fontSize: 10}},
      {name: '目标', type: 'bar', data: target, barWidth: 22, barGap: '20%',
       itemStyle: {color: 'transparent', borderColor: C('--target'), borderWidth: 1.3, borderType: 'dashed'},
       label: {show: false}}
    ]
  }, true);
}

function renderTable() {
  const cur = rows(state.month, '全部');
  const pm = prevMonth(state.month);
  const body = document.getElementById('rows');
  body.replaceChildren();
  for (const c of CHANNELS) {
    const r = cur.find(x => x.c === c);
    const prev = pm ? rows(pm, c)[0] : null;
    const rate = pct(r.rev, r.target);
    const delta = prev ? pct(r.rev - prev.rev, prev.rev) : null;
    const tr = document.createElement('tr');
    const cells = [c, fmt(r.rev, 0), fmt(r.target, 0), rate.toFixed(0) + '% ' + statusText(rate),
      delta === null ? '—' : (delta >= 0 ? '↑ ' : '↓ ') + Math.abs(delta).toFixed(1) + '%',
      fmt(r.new), r.sat.toFixed(1)];
    cells.forEach((v, i) => {
      const td = document.createElement('td'); td.textContent = v;
      if (i === 3) td.className = statusClass(rate);
      if (i === 4 && delta !== null) td.className = delta >= 0 ? 'up' : 'down';
      tr.appendChild(td);
    });
    body.appendChild(tr);
  }
}

function render() {
  updateKpis(); renderLine(); renderDonut(); renderBar(); renderTable();
}

const monthSel = document.getElementById('month');
for (const m of MONTHS) { const o = document.createElement('option'); o.value = m; o.textContent = Number(m.slice(5)) + '月'; monthSel.appendChild(o); }
monthSel.value = state.month;
monthSel.addEventListener('change', e => { state.month = e.target.value; render(); });
document.getElementById('channel').addEventListener('change', e => { state.channel = e.target.value; render(); });
let timer = null;
window.addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(() => Object.values(charts).forEach(c => c.resize()), 120); });
render();
</script>
</body>
</html>
"""


def write_summary(rows) -> Path:
    months = sorted({r["m"] for r in rows})
    channels = ["直播", "电商", "门店", "私域"]
    out = []
    for m in months:
        part = [r for r in rows if r["m"] == m]
        rev, target = sum(r["rev"] for r in part), sum(r["target"] for r in part)
        out.append(["月份", m, f"{rev:.1f}", f"{target:.1f}", f"{rev / target * 100:.1f}%",
                    sum(r["new"] for r in part), f"{sum(r['sat'] for r in part) / len(part):.2f}"])
    for c in channels:
        part = [r for r in rows if r["c"] == c]
        rev, target = sum(r["rev"] for r in part), sum(r["target"] for r in part)
        out.append(["渠道", c, f"{rev:.1f}", f"{target:.1f}", f"{rev / target * 100:.1f}%",
                    sum(r["new"] for r in part), f"{sum(r['sat'] for r in part) / len(part):.2f}"])
    rev, target = sum(r["rev"] for r in rows), sum(r["target"] for r in rows)
    out.append(["总体", "2025-01..06", f"{rev:.1f}", f"{target:.1f}", f"{rev / target * 100:.1f}%",
                sum(r["new"] for r in rows), f"{sum(r['sat'] for r in rows) / len(rows):.2f}"])
    path = HERE / "summary.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["范围", "键", "收入_万元", "目标_万元", "目标完成率", "新客数", "满意度"])
        w.writerows(out)
    return path


def main() -> int:
    rows = load_rows()
    summary = write_summary(rows)
    ASSETS.mkdir(parents=True, exist_ok=True)
    if VENDOR.is_file():
        shutil.copy2(VENDOR, ASSETS / "echarts.min.js")
    html = TEMPLATE.replace("__DATA__", json.dumps(rows, ensure_ascii=False, indent=0))
    OUT.write_text(html, encoding="utf-8")
    print(json.dumps({"status": "success", "output": str(OUT), "summary": str(summary),
                      "rows": len(rows), "vendor": str(ASSETS / "echarts.min.js")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

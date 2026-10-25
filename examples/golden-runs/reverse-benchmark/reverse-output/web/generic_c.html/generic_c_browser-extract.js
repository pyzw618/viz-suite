// viz-reverse · read-only browser extraction snippet
// Run only on pages you are authorized to inspect. It does not click, login, or bypass paywalls.
(async () => {
  const out = {source: 'browser', format: 'auto'};
  try {
    if (window.echarts) {
      const el = document.querySelector('[data-echarts], .echarts, #chart') || document.body;
      const inst = echarts.getInstanceByDom(el);
      if (inst) out.echarts = inst.getOption();
    }
    if (window.Chart) {
      const canvas = document.querySelector('canvas');
      if (canvas) out.chartjs = Chart.getChart(canvas)?.config;
    }
    if (window.Plotly) {
      const gd = document.querySelector('.plotly-graph-div, [data-plotly]');
      if (gd && gd.data) { out.plotlyData = gd.data; out.plotlyLayout = gd.layout; }
    }
  } catch (e) { out.error = String(e); }
  console.log(JSON.stringify(out));
})();

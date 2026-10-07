(function () {
  "use strict";

  var instances = {};
  var lastData = null;

  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function clock(iso) {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function mount(id, empty, config) {
    var canvas = document.getElementById(id);
    if (!canvas) return;
    if (instances[id]) { instances[id].destroy(); delete instances[id]; }

    var missing = typeof Chart === "undefined";
    var note = canvas.parentElement.querySelector(".chart-empty");
    canvas.hidden = empty || missing;
    if (note) {
      note.hidden = !(empty || missing);
      note.textContent = missing ? "Chart library not found (app/static/vendor/chart.umd.min.js)." : "No data yet.";
    }
    if (empty || missing) return;
    instances[id] = new Chart(canvas, config);
  }

  function scales() {
    var text = css("--text"), grid = css("--border");
    return {
      x: { ticks: { color: text, maxRotation: 45, minRotation: 0 }, grid: { color: grid } },
      y: { beginAtZero: true, ticks: { color: text }, grid: { color: grid } },
    };
  }

  function legend(position) { return { position: position, labels: { color: css("--text") } }; }

  function lineConfig(labels, datasets, yScale) {
    var s = scales();
    Object.assign(s.y, yScale || {});
    return {
      type: "line",
      data: { labels: labels, datasets: datasets },
      options: { responsive: true, maintainAspectRatio: false, scales: s, plugins: { legend: legend("top") } },
    };
  }

  function render(data) {
    lastData = data;
    var c1 = css("--chart-1"), c2 = css("--chart-2"), c3 = css("--chart-3"), c4 = css("--chart-4");
    var a = data.activity, ch = data.charts;

    var counts = [a.port_scans.count, a.audits.count, a.integrity_baselines.count, a.network_logs.count];
    mount("chart-activity", counts.every(function (n) { return n === 0; }), {
      type: "doughnut",
      data: {
        labels: ["Port scans", "System audits", "Integrity baselines", "Network samples"],
        datasets: [{ data: counts, backgroundColor: [c1, c2, c3, c4], borderColor: css("--surface"), borderWidth: 2 }],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: legend("bottom") } },
    });

    mount("chart-network", ch.network.labels.length === 0, lineConfig(
      ch.network.labels.map(clock),
      [
        { label: "Upload (KB/s)", data: ch.network.upload, borderColor: c1, backgroundColor: c1, tension: 0.3 },
        { label: "Download (KB/s)", data: ch.network.download, borderColor: c2, backgroundColor: c2, tension: 0.3 },
      ]
    ));

    var barScales = scales();
    barScales.y.ticks.precision = 0;
    mount("chart-ports", ch.port_scans.labels.length === 0, {
      type: "bar",
      data: { labels: ch.port_scans.labels, datasets: [{ label: "Open ports", data: ch.port_scans.open, backgroundColor: c3, borderRadius: 4 }] },
      options: { responsive: true, maintainAspectRatio: false, scales: barScales, plugins: { legend: { display: false } } },
    });

    mount("chart-cpu", ch.cpu.labels.length === 0, lineConfig(
      ch.cpu.labels.map(clock),
      [{ label: "CPU usage (%)", data: ch.cpu.values, borderColor: c4, backgroundColor: c4, tension: 0.3 }],
      { max: 100 }
    ));
  }

  document.addEventListener("themechange", function () { if (lastData) render(lastData); });

  window.TK = Object.assign(window.TK || {}, { charts: { render: render } });
})();
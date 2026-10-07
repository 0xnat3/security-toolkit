(function () {
  "use strict";

  var tabs = Array.from(document.querySelectorAll("[data-panel]"));
  var panels = Array.from(document.querySelectorAll(".panel"));
  if (!tabs.length) return;

  var h = TK.h;
  var errorBox = document.getElementById("overview-error");
  var recentBox = document.getElementById("recent-activity");

  function setStats(a) {
    var values = {
      port_scans: a.port_scans.count,
      audits: a.audits.count,
      baselines: a.integrity_baselines.count,
      network: a.network_logs.count,
    };
    Object.entries(values).forEach(function (pair) {
      var el = document.querySelector('[data-stat="' + pair[0] + '"]');
      if (el) el.textContent = String(pair[1]);
    });
  }

  function renderRecent(data) {
    var r = data.recent, items = [];
    if (r.port_scan) {
      items.push({
        at: r.port_scan.created_at, icon: "🔍", title: "Port scan of " + r.port_scan.host,
        detail: [TK.plural(r.port_scan.open_count, "open port"), "ports " + r.port_scan.start_port + "–" + r.port_scan.end_port],
      });
    }
    if (r.audit) {
      items.push({
        at: r.audit.created_at, icon: "📋", title: "System audit",
        detail: [r.audit.os, "CPU " + r.audit.cpu_percent + "%", "RAM " + r.audit.ram_percent + "%"],
      });
    }
    if (r.baseline) {
      items.push({
        at: r.baseline.created_at, icon: "📁", title: "Baseline of " + r.baseline.directory,
        detail: [TK.plural(r.baseline.file_count, "file"), r.baseline.algorithm],
      });
    }
    items.sort(function (a, b) { return Date.parse(b.at) - Date.parse(a.at); });

    TK.clear(recentBox);
    if (!items.length) {
      recentBox.append(h("p", { class: "muted" }, "No activity yet. Open a tool tab to run a scan, audit or baseline."));
      return;
    }
    recentBox.append(h("ul", { class: "activity" }, items.map(function (item) {
      return h("li", null,
        h("span", { class: "activity-icon", "aria-hidden": "true" }, item.icon),
        h("div", null,
          h("strong", null, item.title),
          h("div", { class: "muted small" }, item.detail.concat(TK.time(item.at)).join(" · "))));
    })));
  }

  async function loadOverview() {
    try {
      var data = await TK.api.get("/api/dashboard");
      TK.clear(errorBox);
      setStats(data.activity);
      renderRecent(data);
      TK.charts.render(data);
    } catch (err) {
      TK.clear(errorBox);
      errorBox.append(TK.notice("danger", err.message));
    }
  }

  function show(name, updateHash) {
    if (!panels.some(function (p) { return p.id === "panel-" + name; })) name = "overview";
    tabs.forEach(function (t) { t.setAttribute("aria-selected", String(t.dataset.panel === name)); });
    panels.forEach(function (p) { p.hidden = p.id !== "panel-" + name; });
    if (updateHash) window.history.replaceState(null, "", "#" + name);
    document.dispatchEvent(new CustomEvent("panelchange", { detail: name }));
    if (name === "overview") loadOverview();
  }

  tabs.forEach(function (t) { t.addEventListener("click", function () { show(t.dataset.panel, true); }); });
  window.addEventListener("hashchange", function () { show(window.location.hash.slice(1), false); });
  show(window.location.hash.slice(1) || "overview", false);
})();
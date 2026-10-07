(function () {
  "use strict";

  var root = document.getElementById("history-table");
  if (!root) return;

  var h = TK.h;
  var search = document.getElementById("history-search");
  var range = document.getElementById("history-range");
  var messageBox = document.getElementById("history-message");
  var exportCsv = document.getElementById("export-csv");
  var exportPdf = document.getElementById("export-pdf");
  var tabs = Array.from(document.querySelectorAll("[data-tab]"));
  var DAY = 86400000;

  var TABS = {
    port_scans: [
      ["Host", function (r) { return r.host; }],
      ["Address", function (r) { return r.ip; }],
      ["Ports", function (r) { return r.start_port + "–" + r.end_port; }],
      ["Open", function (r) { return String(r.open_count); }],
      ["When", function (r) { return TK.time(r.created_at); }],
    ],
    audits: [
      ["System", function (r) { return r.os || "Unknown"; }],
      ["CPU", function (r) { return r.cpu_percent + "%"; }],
      ["RAM", function (r) { return r.ram_percent + "%"; }],
      ["When", function (r) { return TK.time(r.created_at); }],
    ],
    integrity_baselines: [
      ["Folder", function (r) { return r.directory; }],
      ["Algorithm", function (r) { return r.algorithm.toUpperCase(); }],
      ["Files", function (r) { return String(r.file_count); }],
      ["When", function (r) { return TK.time(r.created_at); }],
    ],
    network_logs: [
      ["Upload", function (r) { return r.upload_kb_s + " KB/s"; }],
      ["Download", function (r) { return r.download_kb_s + " KB/s"; }],
      ["When", function (r) { return TK.time(r.created_at); }],
    ],
  };

  var data = {};
  var tab = "port_scans";

  function cutoff() {
    if (range.value === "today") { var d = new Date(); d.setHours(0, 0, 0, 0); return d.getTime(); }
    if (range.value === "week") return Date.now() - 7 * DAY;
    if (range.value === "month") return Date.now() - 30 * DAY;
    return 0;
  }

  function updateExportLinks() {
    // The tab names match the report names the server accepts.
    exportCsv.href = "/export/" + tab + "/csv";
    exportPdf.href = "/export/" + tab + "/pdf";
  }

  function render() {
    var cols = TABS[tab];
    var all = data[tab] || [];
    var q = search.value.trim().toLowerCase();
    var since = cutoff();

    var rows = all.filter(function (r) { return Date.parse(r.created_at) >= since; }).filter(function (r) {
      return !q || cols.map(function (c) { return c[1](r); }).join(" ").toLowerCase().indexOf(q) !== -1;
    });

    TK.clear(root);
    if (!rows.length) {
      root.append(h("p", { class: "empty" }, all.length ? "No entries match your filters." : "Nothing here yet."));
      return;
    }
    root.append(h("table", { class: "data" },
      h("thead", null, h("tr", null, cols.map(function (c) { return h("th", null, c[0]); }))),
      h("tbody", null, rows.map(function (r) {
        return h("tr", null, cols.map(function (c) { return h("td", null, c[1](r)); }));
      }))));
  }

  async function load() {
    try {
      data = await TK.api.get("/api/history");
      render();
    } catch (err) {
      TK.clear(messageBox);
      messageBox.append(TK.notice("danger", err.message));
    }
  }

  tabs.forEach(function (t) {
    t.addEventListener("click", function () {
      tab = t.dataset.tab;
      tabs.forEach(function (x) { x.setAttribute("aria-selected", String(x === t)); });
      updateExportLinks();
      render();
    });
  });
  search.addEventListener("input", render);
  range.addEventListener("change", render);

  document.getElementById("clear-history").addEventListener("click", async function () {
    var ok = window.confirm(
      "Delete ALL of your history: port scans, audits, network samples and integrity baselines?\n\n" +
      "Deleting baselines means you will need to create new ones before checking for changes. This cannot be undone.");
    if (!ok) return;
    TK.clear(messageBox);
    try {
      var result = await TK.api.del("/api/history");
      messageBox.append(TK.notice("success", "Deleted " + TK.plural(result.deleted, "entry") + "."));
      await load();
    } catch (err) {
      messageBox.append(TK.notice("danger", err.message));
    }
  });

  updateExportLinks();
  load();
})();
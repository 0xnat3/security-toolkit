(function () {
  "use strict";

  var form = document.getElementById("port-form");
  var out = document.getElementById("port-result");
  if (!form || !out) return;

  var h = TK.h;
  var button = form.querySelector("button[type=submit]");

  function render(d) {
    TK.clear(out);
    out.append(h("p", { class: "summary" },
      d.host + " (" + d.ip + ") · ports " + d.start_port + "–" + d.end_port + " · " +
      TK.plural(d.open_count, "open port") + " · " + TK.time(d.created_at)));

    if (!d.results.length) {
      out.append(TK.notice("info", "No open ports found in that range."));
      return;
    }

    var flagged = d.results.filter(function (r) { return r.risk; }).length;
    if (flagged) {
      out.append(TK.notice("warning", TK.plural(flagged, "open port") + " with security notes. See the Notes column."));
    }

    // Banners come from whatever is listening on the target: untrusted, shown as plain text only.
    out.append(h("div", { class: "table-wrap" }, h("table", { class: "data" },
      h("thead", null, h("tr", null, h("th", null, "Port"), h("th", null, "Service"), h("th", null, "Banner"), h("th", null, "Notes"))),
      h("tbody", null, d.results.map(function (r) {
        return h("tr", null,
          h("td", { class: "mono" }, r.port),
          h("td", null, r.service),
          h("td", { class: "mono banner" }, r.banner || "—"),
          h("td", r.risk ? { class: "warn-text" } : null, r.risk ? "⚠ " + r.risk : "—"));
      })))));
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    TK.clearErrors(form);
    TK.clear(out);
    TK.busy(button, true, "Scanning…");
    var f = form.elements;
    try {
      render(await TK.api.post("/api/port-scan", {
        host: f.host.value.trim(),
        start_port: Number(f.start_port.value),
        end_port: Number(f.end_port.value),
        timeout: Number(f.timeout.value),
      }));
    } catch (err) {
      if (!TK.showFieldErrors(form, err.fields)) out.append(TK.notice("danger", err.message));
    } finally {
      TK.busy(button, false);
    }
  });
})();
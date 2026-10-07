(function () {
  "use strict";

  var button = document.getElementById("audit-run");
  var out = document.getElementById("audit-result");
  if (!button || !out) return;

  var h = TK.h;

  function meter(percent) {
    return h("progress", { max: 100, value: percent, class: percent >= 80 ? "hot" : "" });
  }

  function card(title, big, lines, percent) {
    return h("div", { class: "info-card" },
      h("h3", null, title),
      h("div", { class: "big" }, big),
      lines.map(function (line) { return h("div", { class: "muted small" }, line); }),
      percent === undefined ? null : meter(percent));
  }

  function render(d) {
    TK.clear(out);
    out.append(
      h("div", { class: "info-grid" },
        card("Operating system", d.os + " " + d.release, []),
        card("Processor", d.cpu_percent + "% in use", [d.cpu, TK.plural(d.cpu_cores, "logical core")], d.cpu_percent),
        card("Memory", d.ram_percent + "% in use", ["of " + d.ram_gb + " GB"], d.ram_percent),
        card("Uptime", d.uptime, ["Booted " + d.boot_time])),
      h("p", { class: "muted small" }, "Audit taken " + TK.time(d.created_at)));
  }

  button.addEventListener("click", async function () {
    TK.clear(out);
    TK.busy(button, true, "Auditing…");
    try {
      render(await TK.api.post("/api/system/audit"));
    } catch (err) {
      out.append(TK.notice("danger", err.message));
    } finally {
      TK.busy(button, false);
    }
  });
})();
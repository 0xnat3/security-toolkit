(function () {
  "use strict";

  var form = document.getElementById("integrity-form");
  var out = document.getElementById("integrity-result");
  if (!form || !out) return;

  var h = TK.h;
  var buttons = Array.from(form.querySelectorAll("button[data-action]"));

  function skippedNote(count) {
    return count ? TK.notice("warning", TK.plural(count, "file") + " could not be read (locked or no permission) and were skipped.") : null;
  }

  function section(title, count, paths) {
    if (!count) return null;
    return [
      h("h3", null, title + " (" + count + ")"),
      h("ul", { class: "filelist" }, paths.map(function (p) { return h("li", null, h("code", null, p)); })),
    ];
  }

    function renderBaseline(d) {
    TK.clear(out);
    out.append(
      d.file_count
        ? TK.notice("success", "Baseline saved: " + TK.plural(d.file_count, "file") + " in " + d.directory + " (" + d.algorithm + ") at " + TK.time(d.created_at) + ".")
        : TK.notice("warning", "Baseline saved, but " + d.directory + " contains no files, so there is nothing to monitor yet. Add files and create the baseline again."),
      skippedNote(d.skipped_count));
  }

  function renderCheck(d) {
    TK.clear(out);
    out.append(h("p", { class: "summary" },
      d.directory + " (" + d.algorithm + ") compared with the baseline from " + TK.time(d.baseline_created_at)));

    var c = d.counts;
    if (!c.added && !c.removed && !c.modified) {
      out.append(TK.notice("success", "No changes detected."));
    } else {
      out.append(h("p", { class: "summary" }, d.summary),
        section("Modified", c.modified, d.modified),
        section("Removed", c.removed, d.removed),
        section("Added", c.added, d.added));
    }
    if (d.truncated) out.append(TK.notice("info", "Lists show the first 500 entries per category. The counts are exact."));
    out.append(skippedNote(d.skipped_count));
  }

  async function run(action, button) {
    TK.clearErrors(form);
    TK.clear(out);
    buttons.forEach(function (b) { b.disabled = true; });
    TK.busy(button, true, action === "baseline" ? "Hashing…" : "Checking…");
    var f = form.elements;
    var directory = f.directory.value.trim();

    try {
      if (action === "baseline") {
        renderBaseline(await TK.api.post("/api/integrity/baseline", { directory: directory, algorithm: f.algorithm.value }));
      } else {
        var body = directory ? { directory: directory, algorithm: f.algorithm.value } : {};
        renderCheck(await TK.api.post("/api/integrity/check", body));
      }
    } catch (err) {
      if (!TK.showFieldErrors(form, err.fields)) out.append(TK.notice("danger", err.message));
    } finally {
      TK.busy(button, false);
      buttons.forEach(function (b) { b.disabled = false; });
    }
  }

  buttons.forEach(function (b) { b.addEventListener("click", function () { run(b.dataset.action, b); }); });
  form.addEventListener("submit", function (e) { e.preventDefault(); }); // Enter must not trigger an action
})();
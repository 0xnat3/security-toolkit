(function () {
  "use strict";

  var out = document.getElementById("net-result");
  var sampleBtn = document.getElementById("net-sample");
  var autoBtn = document.getElementById("net-auto");
  if (!out || !sampleBtn || !autoBtn) return;

  var h = TK.h;
  var KEEP = 10, EVERY_MS = 5000;
  var samples = [], total = 0, timer = null, inFlight = false;

  function average(key) {
    return samples.reduce(function (sum, s) { return sum + s[key]; }, 0) / samples.length;
  }
  function kb(n) { return n.toFixed(2) + " KB/s"; }

  function card(title, big, sub) {
    return h("div", { class: "info-card" },
      h("h3", null, title),
      h("div", { class: "big" }, big),
      sub ? h("div", { class: "muted small" }, sub) : null);
  }

  function render(latest) {
    TK.clear(out);
    out.append(h("div", { class: "info-grid" },
      card("Upload", kb(latest.upload_kb_s)),
      card("Download", kb(latest.download_kb_s)),
      card("Average of last " + samples.length, "↑ " + kb(average("upload_kb_s")), "↓ " + kb(average("download_kb_s"))),
      card("Samples this session", String(total), "Updated " + TK.time(latest.created_at))));
  }

  function setAuto(on) {
    if (on && !timer) { timer = setInterval(sample, EVERY_MS); sample(); }
    if (!on && timer) { clearInterval(timer); timer = null; }
    autoBtn.setAttribute("aria-pressed", String(Boolean(timer)));
    autoBtn.textContent = "Auto-refresh: " + (timer ? "on" : "off");
  }

  async function sample() {
    if (inFlight) return;
    inFlight = true;
    sampleBtn.disabled = true;
    try {
      var data = await TK.api.post("/api/network/sample");
      samples.push(data);
      if (samples.length > KEEP) samples.shift();
      total += 1;
      render(data);
    } catch (err) {
      setAuto(false);
      TK.clear(out);
      out.append(TK.notice("danger", err.message));
    } finally {
      inFlight = false;
      sampleBtn.disabled = false;
    }
  }

  sampleBtn.addEventListener("click", sample);
  autoBtn.addEventListener("click", function () { setAuto(!timer); });
  document.addEventListener("panelchange", function (e) { if (e.detail !== "network") setAuto(false); });
  document.addEventListener("visibilitychange", function () { if (document.hidden) setAuto(false); });
})();
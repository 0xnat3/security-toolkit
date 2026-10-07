(function () {
  var KEY = "theme"; // "light" | "dark" | "auto"
  var root = document.documentElement;

  function stored() {
    try { return localStorage.getItem(KEY) || "auto"; } catch (e) { return "auto"; }
  }
  function resolve(pref) {
    if (pref === "light" || pref === "dark") return pref;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
    function apply(pref) {
    root.setAttribute("data-theme", resolve(pref));
    document.dispatchEvent(new Event("themechange"));
  }

  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
      if (stored() === "auto") apply("auto");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.querySelector("[data-theme-toggle]");
    if (btn) {
      btn.addEventListener("click", function () {
        window.setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
      });
    }
  });
})();
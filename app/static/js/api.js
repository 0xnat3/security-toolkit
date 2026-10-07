(function () {
  "use strict";

  var csrfMeta = document.querySelector('meta[name="csrf-token"]');
  var csrfToken = csrfMeta ? csrfMeta.content : "";

  function ApiError(message, status, fields) {
    var err = new Error(message);
    err.name = "ApiError";
    err.status = status;
    err.fields = fields || null;
    return err;
  }

  async function request(method, url, body) {
    var options = {
      method: method,
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-CSRFToken": csrfToken },
    };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }

    var response;
    try {
      response = await fetch(url, options);
    } catch (e) {
      throw ApiError("Could not reach the server. Is it still running?", 0);
    }

    if (response.status === 401) {
      window.location.assign("/login?next=" + encodeURIComponent(window.location.pathname));
      throw ApiError("Your session has expired. Redirecting to sign in…", 401);
    }

    var data = null;
    try { data = await response.json(); } catch (e) { /* not JSON */ }

    if (!response.ok) {
      var message = (data && (data.error || data.message)) || "Request failed (" + response.status + ").";
      if (response.status === 429) message = "Too many requests. Wait a minute and try again.";
      throw ApiError(message, response.status, data && data.fields);
    }
    return data;
  }

  // Build DOM safely: strings become text nodes, so server data can never inject HTML.
  function h(tag, attrs) {
    var el = document.createElement(tag);
    Object.entries(attrs || {}).forEach(function (pair) {
      var key = pair[0], value = pair[1];
      if (value === null || value === undefined || value === false) return;
      if (key === "class") el.className = value;
      else if (key.indexOf("on") === 0 && typeof value === "function") el.addEventListener(key.slice(2), value);
      else el.setAttribute(key, value === true ? "" : String(value));
    });
    Array.prototype.slice.call(arguments, 2).flat().forEach(function (child) {
      if (child === null || child === undefined || child === false) return;
      el.append(child instanceof Node ? child : document.createTextNode(String(child)));
    });
    return el;
  }

  function clear(el) { el.replaceChildren(); }

  function notice(kind, message) {
    return h("div", { class: "alert alert-" + kind, role: kind === "danger" ? "alert" : "status" }, message);
  }

  function busy(button, isBusy, label) {
    if (isBusy) {
      button.dataset.label = button.textContent;
      button.textContent = label || "Working…";
      button.disabled = true;
    } else {
      if (button.dataset.label) button.textContent = button.dataset.label;
      button.disabled = false;
    }
  }

  function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }

  function time(iso) {
    var d = new Date(iso);
    return isNaN(d) ? String(iso || "") : d.toLocaleString([], { dateStyle: "medium", timeStyle: "medium" });
  }

  function clearErrors(form) {
    form.querySelectorAll(".field-error").forEach(function (el) { el.remove(); });
  }

  function showFieldErrors(form, fields) {
    var shown = 0;
    Object.entries(fields || {}).forEach(function (pair) {
      var input = form.elements.namedItem(pair[0]);
      var wrap = input && input.closest ? input.closest(".field") : null;
      if (!wrap) return;
      pair[1].forEach(function (message) {
        wrap.append(h("small", { class: "field-error" }, message));
        shown++;
      });
    });
    return shown;
  }

  window.TK = Object.assign(window.TK || {}, {
    api: {
      get: function (url) { return request("GET", url); },
      post: function (url, body) { return request("POST", url, body === undefined ? {} : body); },
      del: function (url) { return request("DELETE", url); },
    },
    h: h, clear: clear, notice: notice, busy: busy, plural: plural, time: time,
    clearErrors: clearErrors, showFieldErrors: showFieldErrors,
  });
})();
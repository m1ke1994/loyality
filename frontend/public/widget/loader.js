(function () {
  var script = document.currentScript;
  if (!script) return;
  var tenant = script.getAttribute("data-tenant") || "demo";
  var host = script.getAttribute("data-host") || "http://localhost:5173";
  var mode = script.getAttribute("data-mode") || "iframe";

  function createIframe() {
    var iframe = document.createElement("iframe");
    iframe.src = host + "/t/" + tenant + "/widget";
    iframe.style.width = "360px";
    iframe.style.height = "520px";
    iframe.style.border = "1px solid #ddd";
    iframe.style.borderRadius = "16px";
    iframe.style.boxShadow = "0 10px 30px rgba(0,0,0,0.15)";
    iframe.style.background = "#fff";
    return iframe;
  }

  if (mode === "modal") {
    var button = document.createElement("button");
    button.textContent = "Open Loyalty";
    button.style.padding = "10px 16px";
    button.style.borderRadius = "12px";
    button.style.border = "none";
    button.style.background = "#2d6a4f";
    button.style.color = "#fff";
    button.style.cursor = "pointer";

    var overlay = document.createElement("div");
    overlay.style.position = "fixed";
    overlay.style.inset = "0";
    overlay.style.background = "rgba(0,0,0,0.45)";
    overlay.style.display = "none";
    overlay.style.alignItems = "center";
    overlay.style.justifyContent = "center";
    overlay.style.zIndex = "9999";

    var modal = document.createElement("div");
    modal.style.position = "relative";
    modal.appendChild(createIframe());

    var close = document.createElement("button");
    close.textContent = "Close";
    close.style.position = "absolute";
    close.style.top = "-12px";
    close.style.right = "-12px";
    close.style.padding = "6px 10px";
    close.style.borderRadius = "999px";
    close.style.border = "none";
    close.style.background = "#111";
    close.style.color = "#fff";
    close.style.cursor = "pointer";

    close.addEventListener("click", function () {
      overlay.style.display = "none";
    });

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) overlay.style.display = "none";
    });

    modal.appendChild(close);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    button.addEventListener("click", function () {
      overlay.style.display = "flex";
    });

    script.parentNode.insertBefore(button, script);
  } else {
    var iframe = createIframe();
    script.parentNode.insertBefore(iframe, script);
  }
})();

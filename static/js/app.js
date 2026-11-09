(function () {
  "use strict";

  function lockForm(form) {
    form.dataset.submitting = "true";
    form.querySelectorAll("button[type='submit']").forEach(function (button) {
      var spinner = document.createElement("span");
      spinner.className = "spinner-border spinner-border-sm me-2";
      spinner.setAttribute("aria-hidden", "true");
      button.dataset.originalHtml = button.innerHTML;
      button.replaceChildren(spinner, document.createTextNode(button.dataset.loadingText || "Please wait..."));
      button.disabled = true;
    });
  }

  function unlockForm(form) {
    delete form.dataset.submitting;
    form.querySelectorAll("button[type='submit']").forEach(function (button) {
      if (button.dataset.originalHtml !== undefined) {
        button.innerHTML = button.dataset.originalHtml;
        delete button.dataset.originalHtml;
      }
      button.disabled = false;
    });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.matches("form[data-prevent-double-submit]")) {
      return;
    }
    if (form.dataset.submitting === "true") {
      event.preventDefault();
      return;
    }
    form.dataset.submitting = "true";
    // Wait one tick so the browser has started the submission before the button is disabled.
    setTimeout(function () {
      lockForm(form);
    }, 0);
  });

  // Returning with the Back button can restore a page with locked buttons; unlock them.
  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) {
      return;
    }
    document.querySelectorAll("form[data-submitting='true']").forEach(unlockForm);
  });
  
  // Light/dark theme toggle. The initial theme is applied earlier by theme.js.
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    var root = document.documentElement;
    toggle.setAttribute("aria-pressed", String(root.getAttribute("data-bs-theme") === "dark"));
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      toggle.setAttribute("aria-pressed", String(next === "dark"));
      try {
        localStorage.setItem("theme", next);
      } catch (error) {
        /* storage blocked: the choice just won't be remembered */
      }
    });
  }
})();
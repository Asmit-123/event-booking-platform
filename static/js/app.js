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

    function renderToggleState(isDark) {
      toggle.setAttribute("aria-pressed", String(isDark));
      var sunSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="me-1" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2"></path><path d="M12 20v2"></path><path d="m4.93 4.93 1.41 1.41"></path><path d="m17.66 17.66 1.41 1.41"></path><path d="M2 12h2"></path><path d="M20 12h2"></path><path d="m6.34 17.66-1.41 1.41"></path><path d="m19.07 4.93-1.41 1.41"></path></svg>';
      var moonSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="me-1" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path></svg>';
      toggle.innerHTML = (isDark ? sunSvg : moonSvg) + (isDark ? 'Light mode' : 'Dark mode');
    }

    renderToggleState(root.getAttribute("data-bs-theme") === "dark");

    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      renderToggleState(next === "dark");
      try {
        localStorage.setItem("theme", next);
      } catch (error) {
        /* storage blocked: the choice just won't be remembered */
      }
    });
  }
})();

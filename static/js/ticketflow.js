// TicketFlow UI helpers.
// Progressive enhancement only: every form still posts to the server and
// every rule (permissions, validation, state machine) stays server-side.
// Bootstrap's bundle already handles dropdowns, the off-canvas sidebar
// and dismissible alerts.
(function () {
    "use strict";

    // Show/hide password fields (login, password reset, user creation).
    document.querySelectorAll("[data-toggle-password]").forEach(function (button) {
        var input = document.getElementById(button.getAttribute("data-toggle-password"));
        if (!input) {
            return;
        }
        var icon = button.querySelector(".tf-icon");
        button.addEventListener("click", function () {
            var show = input.type === "password";
            input.type = show ? "text" : "password";
            button.setAttribute("aria-pressed", show ? "true" : "false");
            button.setAttribute("aria-label", show ? "Ocultar contraseña" : "Mostrar contraseña");
            if (icon) {
                icon.textContent = show ? "visibility_off" : "visibility";
            }
        });
    });

    // Confirmation before destructive POST forms (delete user/area/category).
    // The server still validates and may refuse the deletion.
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (!window.confirm(form.getAttribute("data-confirm"))) {
                event.preventDefault();
            }
        });
    });

    // New ticket: preview the destination area from the selected category.
    // Category options are rendered as "Área / Categoría" (Category.__str__);
    // the real area is always derived server-side from the category.
    var previewWrapper = document.querySelector("[data-area-preview]");
    var categorySelect = previewWrapper ? previewWrapper.querySelector("select") : null;
    if (categorySelect) {
        var target = document.getElementById(previewWrapper.getAttribute("data-area-preview"));
        var targetText = target ? target.querySelector("[data-area-name]") : null;
        var update = function () {
            if (!target || !targetText) {
                return;
            }
            var option = categorySelect.options[categorySelect.selectedIndex];
            if (!option || !option.value) {
                target.hidden = true;
                return;
            }
            var label = option.text;
            var separator = label.indexOf(" / ");
            targetText.textContent = separator > -1 ? label.slice(0, separator) : label;
            target.hidden = false;
        };
        categorySelect.addEventListener("change", update);
        update();
    }

    // Keyboard shortcut: "/" or Ctrl/Cmd+K focuses the global ticket search.
    var search = document.getElementById("tf-global-search");
    if (search) {
        document.addEventListener("keydown", function (event) {
            var tag = (event.target.tagName || "").toLowerCase();
            var typing = tag === "input" || tag === "textarea" || tag === "select" || event.target.isContentEditable;
            if ((event.key === "k" && (event.ctrlKey || event.metaKey)) || (event.key === "/" && !typing)) {
                event.preventDefault();
                search.focus();
            }
        });
    }
})();

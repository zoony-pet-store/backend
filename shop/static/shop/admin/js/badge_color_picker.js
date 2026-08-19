(function () {
    function normalizeHex(value) {
        const trimmed = (value || "").trim();

        if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) {
            return trimmed.toUpperCase();
        }

        if (/^[0-9a-fA-F]{6}$/.test(trimmed)) {
            return `#${trimmed.toUpperCase()}`;
        }

        return null;
    }

    function hexToRgb(hex) {
        const normalized = normalizeHex(hex);

        if (!normalized) {
            return null;
        }

        return {
            r: parseInt(normalized.slice(1, 3), 16),
            g: parseInt(normalized.slice(3, 5), 16),
            b: parseInt(normalized.slice(5, 7), 16),
        };
    }

    function getRelativeLuminance(hex) {
        const rgb = hexToRgb(hex);

        if (!rgb) {
            return null;
        }

        const values = [rgb.r, rgb.g, rgb.b].map(function (value) {
            const channel = value / 255;

            if (channel <= 0.03928) {
                return channel / 12.92;
            }

            return Math.pow((channel + 0.055) / 1.055, 2.4);
        });

        return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722;
    }

    function getContrastRatio(color, background) {
        const colorLuminance = getRelativeLuminance(color);
        const backgroundLuminance = getRelativeLuminance(background);

        if (colorLuminance === null || backgroundLuminance === null) {
            return null;
        }

        const lighter = Math.max(colorLuminance, backgroundLuminance);
        const darker = Math.min(colorLuminance, backgroundLuminance);

        return (lighter + 0.05) / (darker + 0.05);
    }

    function getContrastLevel(ratio) {
        if (ratio === null || ratio < 3) {
            return "bad";
        }

        if (ratio < 4.5) {
            return "warn";
        }

        return "good";
    }

    function dispatchFieldEvents(field) {
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function initializePicker(wrapper) {
        const textInput = wrapper.querySelector("[data-hex-color-text]");
        const pickerInput = wrapper.querySelector("[data-hex-color-picker]");
        let errorElement = wrapper.querySelector(".hex-color-picker__error");

        if (!textInput || !pickerInput || wrapper.dataset.hexColorPickerReady) {
            return;
        }

        wrapper.dataset.hexColorPickerReady = "true";

        if (!errorElement) {
            errorElement = document.createElement("span");
            errorElement.className = "hex-color-picker__error";
            errorElement.textContent = "Use HEX format, e.g. #A29696.";
            wrapper.insertAdjacentElement("afterend", errorElement);
        }

        function updateValidity() {
            const isValid = Boolean(normalizeHex(textInput.value));

            wrapper.classList.toggle("hex-color-picker--invalid", !isValid);
            errorElement.classList.toggle("hex-color-picker__error--visible", !isValid);
            textInput.setAttribute("aria-invalid", isValid ? "false" : "true");
        }

        const initialHex = normalizeHex(textInput.value) || pickerInput.value;
        pickerInput.value = initialHex;
        textInput.value = initialHex;
        updateValidity();

        pickerInput.addEventListener("input", function () {
            textInput.value = pickerInput.value.toUpperCase();
            updateValidity();
            dispatchFieldEvents(textInput);
        });

        textInput.addEventListener("input", function () {
            const hex = normalizeHex(textInput.value);

            if (hex) {
                pickerInput.value = hex;
            }

            updateValidity();
        });

        textInput.addEventListener("change", function () {
            const hex = normalizeHex(textInput.value);

            if (hex) {
                textInput.value = hex;
                pickerInput.value = hex;
            }

            updateValidity();
        });
    }

    function createBadgePreview() {
        const panel = document.createElement("div");
        panel.className = "badge-color-preview";
        panel.innerHTML = [
            '<div class="badge-color-preview__header">Badge preview</div>',
            '<div class="badge-color-preview__content">',
            '<span class="badge-color-preview__badge">Badge</span>',
            '<span class="badge-color-preview__contrast"></span>',
            "</div>",
        ].join("");

        return panel;
    }

    function initializeBadgeEnhancements() {
        const labelInput = document.querySelector("#id_label");
        const colorInput = document.querySelector("#id_color");
        const backgroundInput = document.querySelector("#id_background_color");
        const backgroundWrapper = backgroundInput?.closest(".hex-color-picker");

        if (!colorInput || !backgroundInput || !backgroundWrapper) {
            return;
        }

        let preview = document.querySelector(".badge-color-preview");

        if (!preview) {
            preview = createBadgePreview();
            backgroundWrapper.insertAdjacentElement("afterend", preview);
        }

        const badge = preview.querySelector(".badge-color-preview__badge");
        const contrast = preview.querySelector(".badge-color-preview__contrast");

        function updatePreview() {
            const color = normalizeHex(colorInput.value);
            const background = normalizeHex(backgroundInput.value);
            const label = (labelInput?.value || "Badge").trim() || "Badge";

            badge.textContent = label;

            if (color && background) {
                badge.style.color = color;
                badge.style.backgroundColor = background;
            }

            const ratio = getContrastRatio(color, background);
            const level = getContrastLevel(ratio);

            contrast.className = `badge-color-preview__contrast badge-color-preview__contrast--${level}`;
            contrast.textContent = ratio
                ? `contrast ${ratio.toFixed(1)}:1`
                : "invalid colors";
        }

        [labelInput, colorInput, backgroundInput].forEach(function (field) {
            if (!field || field.dataset.badgePreviewReady) {
                return;
            }

            field.dataset.badgePreviewReady = "true";
            field.addEventListener("input", updatePreview);
            field.addEventListener("change", updatePreview);
        });

        updatePreview();
    }

    function initializePickers() {
        document.querySelectorAll(".hex-color-picker").forEach(initializePicker);
    }

    document.addEventListener("DOMContentLoaded", function () {
        initializePickers();
        initializeBadgeEnhancements();
    });
})();

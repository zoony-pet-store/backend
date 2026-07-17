(function () {
    const MAX_INIT_ATTEMPTS = 20;
    const INIT_RETRY_DELAY_MS = 100;

    function getSelect2JQuery() {
        const candidates = [
            window.django?.jQuery,
            window.jQuery,
        ];

        return (
            candidates.find(
                (candidate) =>
                    typeof candidate === "function" &&
                    typeof candidate.fn?.select2 === "function"
            ) || null
        );
    }

    function renderMediaAsset(option) {
        if (!option.id) {
            return option.text;
        }

        const optionElement = option.element;
        const imageUrl = optionElement?.dataset?.imageUrl;
        const source = optionElement?.dataset?.source || "";

        if (!imageUrl) {
            return option.text;
        }

        const wrapper = document.createElement("div");
        wrapper.className = "media-asset-option";

        const image = document.createElement("img");
        image.src = imageUrl;
        image.alt = option.text || "";
        image.className = "media-asset-option__image";
        image.loading = "lazy";

        const textWrapper = document.createElement("div");
        textWrapper.className = "media-asset-option__text";

        const title = document.createElement("span");
        title.textContent = option.text || "";

        textWrapper.appendChild(title);

        if (source) {
            const sourceElement = document.createElement("small");
            sourceElement.textContent = source;
            textWrapper.appendChild(sourceElement);
        }

        wrapper.appendChild(image);
        wrapper.appendChild(textWrapper);

        return wrapper;
    }

    function initializeMediaAssetSelects(attempt = 0) {
        const $ = getSelect2JQuery();

        if (!$) {
            if (attempt < MAX_INIT_ATTEMPTS) {
                window.setTimeout(
                    () => initializeMediaAssetSelects(attempt + 1),
                    INIT_RETRY_DELAY_MS
                );
                return;
            }

            console.error(
                "[media asset select] jQuery with Select2 is not available."
            );
            return;
        }

        const selects = $("select.media-asset-select");

        selects.each(function () {
            const select = $(this);

            if (select.hasClass("select2-hidden-accessible")) {
                select.select2("destroy");
            }

            select.select2({
                theme: select.data("theme") || "admin-autocomplete",
                width: "100%",
                allowClear: !select.prop("required"),
                placeholder: select.data("placeholder") || "",
                templateResult: renderMediaAsset,
                templateSelection: renderMediaAsset,
            });
        });
    }

    function boot() {
        /*
         * Unfold first performs its regular Select2 initialization.
         * We then reinitialize only our media select with custom templates.
         */
        window.setTimeout(() => {
            initializeMediaAssetSelects();
        }, INIT_RETRY_DELAY_MS);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();

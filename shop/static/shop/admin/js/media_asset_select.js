(function ($) {
    function renderMediaAsset(option) {
        if (!option.id) {
            return option.text;
        }

        const element = option.element;
        const imageUrl = element?.dataset?.imageUrl;
        const source = element?.dataset?.source || "";

        if (!imageUrl) {
            return option.text;
        }

        const wrapper = document.createElement("div");
        wrapper.className = "media-asset-option";

        const image = document.createElement("img");
        image.src = imageUrl;
        image.alt = option.text;
        image.className = "media-asset-option__image";

        const textWrapper = document.createElement("div");
        textWrapper.className = "media-asset-option__text";

        const title = document.createElement("span");
        title.textContent = option.text;

        const sourceElement = document.createElement("small");
        sourceElement.textContent = source;

        textWrapper.appendChild(title);
        textWrapper.appendChild(sourceElement);

        wrapper.appendChild(image);
        wrapper.appendChild(textWrapper);

        return $(wrapper);
    }

    function initializeMediaAssetSelects(root) {
        $(root)
            .find("select.media-asset-select")
            .each(function () {
                const select = $(this);

                /*
                 * Unfold may have already initialized this element.
                 * Destroy the existing Select2 instance so that we can
                 * initialize it again with our custom render functions.
                 */
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

    $(function () {
        /*
         * Delay initialization until Unfold has completed
         * its standard Select2 initialization.
         */
        window.setTimeout(function () {
            initializeMediaAssetSelects(document);
        }, 0);
    });
})(django.jQuery);

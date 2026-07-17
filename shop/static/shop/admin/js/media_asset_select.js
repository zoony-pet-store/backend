(function () {
    const MAX_INIT_ATTEMPTS = 20;
    const INIT_RETRY_DELAY_MS = 100;

    let formsetHandlerRegistered = false;

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

    function normalizeRoot(root) {
        if (!root) {
            return document;
        }

        /*
         * Django's jQuery formset event may pass the newly added row
         * as a jQuery object rather than a native DOM element.
         */
        if (root.jquery && typeof root.get === "function") {
            return root.get(0) || document;
        }

        return root;
    }

    function getMediaSelects($, root) {
        const rootElement = normalizeRoot(root);

        if (rootElement === document) {
            return $("select.media-asset-select");
        }

        const rootQuery = $(rootElement);

        let selects = rootQuery.find("select.media-asset-select");

        /*
         * The supplied root can itself be the select,
         * not only a container containing the select.
         */
        if (rootQuery.is("select.media-asset-select")) {
            selects = selects.add(rootQuery);
        }

        return selects;
    }

    function registerFormsetHandler($) {
        if (formsetHandlerRegistered) {
            return;
        }

        formsetHandlerRegistered = true;

        /*
         * Django Admin sends this event whenever a new inline row
         * is added with "Add another ...".
         */
        $(document).on(
            "formset:added.mediaAssetSelect",
            function (event, addedRow) {
                window.setTimeout(
                    () => initializeMediaAssetSelects(addedRow),
                    INIT_RETRY_DELAY_MS
                );
            }
        );
    }

    function initializeMediaAssetSelects(root = document, attempt = 0) {
        const $ = getSelect2JQuery();

        if (!$) {
            if (attempt < MAX_INIT_ATTEMPTS) {
                window.setTimeout(
                    () =>
                        initializeMediaAssetSelects(
                            root,
                            attempt + 1
                        ),
                    INIT_RETRY_DELAY_MS
                );

                return;
            }

            console.error(
                "[media asset select] jQuery with Select2 is not available."
            );

            return;
        }

        registerFormsetHandler($);

        const selects = getMediaSelects($, root);

        selects.each(function () {
            const select = $(this);

            /*
             * Do not repeatedly reinitialize a picker that was
             * already initialized by this script.
             */
            if (select.data("mediaAssetPreviewInitialized")) {
                return;
            }

            /*
             * Unfold may already have initialized standard Select2.
             * Remove it before applying our custom templates.
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

            select.data("mediaAssetPreviewInitialized", true);
        });
    }

    function boot() {
        /*
         * Allow Unfold to complete its standard Select2 setup,
         * then replace only media asset selects.
         */
        window.setTimeout(
            () => initializeMediaAssetSelects(document),
            INIT_RETRY_DELAY_MS
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            boot,
            { once: true }
        );
    } else {
        boot();
    }
})();

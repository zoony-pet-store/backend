(() => {
    "use strict";

    const EDITOR_ID = "id_content_blocks_jsonform";
    const TYPE_FIELD_PATTERN = /^rjf§\d+§type$/;

    const BLOCK_TYPES = [
        {
            value: "text",
            label: "Text",
        },
        {
            value: "key_value",
            label: "Key / Value",
        },
        {
            value: "table",
            label: "Table",
        },
    ];

    let refreshScheduled = false;

    function setText(element, value) {
        if (element && element.textContent !== value) {
            element.textContent = value;
        }
    }

    function getDirectGroupTitle(group) {
        if (!group) {
            return "";
        }

        const titleElement = group.querySelector(
            [
                ":scope > .rjf-form-group-title",
                ":scope > .rjf-form-group-inner > .rjf-form-group-title",
            ].join(", ")
        );

        if (!titleElement) {
            return "";
        }

        const titleClone = titleElement.cloneNode(true);

        titleClone.querySelectorAll("button").forEach((button) => {
            button.remove();
        });

        return titleClone.textContent.trim();
    }

    function findGroupByTitle(block, expectedTitle) {
        return (
            Array.from(
                block.querySelectorAll(".rjf-form-group")
            ).find((group) => {
                return getDirectGroupTitle(group) === expectedTitle;
            }) || null
        );
    }

    function getSectionContainer(group) {
        if (!group) {
            return null;
        }

        const parent = group.parentElement;

        if (
            parent &&
            parent.classList.contains("rjf-form-group-wrapper")
        ) {
            return parent;
        }

        return group;
    }

    function findNamedElement(container, expectedName) {
        return (
            Array.from(container.querySelectorAll("[name]")).find(
                (element) => element.name === expectedName
            ) || null
        );
    }

    function setSectionVisible(section, visible) {
        if (!section) {
            return;
        }

        section.hidden = !visible;
        section.classList.toggle(
            "content-block-section--hidden",
            !visible
        );
    }

    function createBlockHeader(block, prefix) {
        let header = block.querySelector(
            ":scope > .content-block-card__header"
        );

        if (!header) {
            header = document.createElement("div");
            header.className = "content-block-card__header";

            const title = document.createElement("strong");
            title.className = "content-block-card__title";

            const metadata = document.createElement("span");
            metadata.className = "content-block-card__metadata";

            header.append(title, metadata);
            block.prepend(header);
        }

        const titleInput = findNamedElement(
            block,
            `${prefix}§title`
        );
        const keyInput = findNamedElement(
            block,
            `${prefix}§key`
        );

        const title =
            titleInput?.value.trim() || "Untitled content block";
        const key = keyInput?.value.trim() || "No key";

        setText(
            header.querySelector(".content-block-card__title"),
            title
        );

        setText(
            header.querySelector(".content-block-card__metadata"),
            key
        );
    }

    function updateTypeSwitcher(select, switcher) {
        const selectedType = select.value;

        switcher
            .querySelectorAll(".content-block-type-switcher__button")
            .forEach((button) => {
                const isActive =
                    button.dataset.blockType === selectedType;

                button.classList.toggle(
                    "content-block-type-switcher__button--active",
                    isActive
                );

                button.setAttribute(
                    "aria-pressed",
                    String(isActive)
                );
            });
    }

    function createTypeSwitcher(select) {
        const formRow = select.closest(".rjf-form-row");

        if (!formRow) {
            return;
        }

        let switcher = formRow.querySelector(
            ".content-block-type-switcher"
        );

        if (!switcher) {
            switcher = document.createElement("div");
            switcher.className = "content-block-type-switcher";
            switcher.setAttribute("role", "group");
            switcher.setAttribute(
                "aria-label",
                "Content block type"
            );

            BLOCK_TYPES.forEach(({ value, label }) => {
                const button = document.createElement("button");

                button.type = "button";
                button.className =
                    "content-block-type-switcher__button";
                button.dataset.blockType = value;
                button.textContent = label;
                button.setAttribute("aria-pressed", "false");

                button.addEventListener("click", () => {
                    if (select.value === value) {
                        return;
                    }

                    select.value = value;

                    select.dispatchEvent(
                        new Event("input", {
                            bubbles: true,
                        })
                    );

                    select.dispatchEvent(
                        new Event("change", {
                            bubbles: true,
                        })
                    );

                    updateTypeSwitcher(select, switcher);
                    scheduleRefresh();
                });

                switcher.append(button);
            });

            const nativeInputGroup = select.closest(
                ".rjf-input-group"
            );

            if (nativeInputGroup) {
                nativeInputGroup.classList.add(
                    "content-block-type-select--native"
                );

                nativeInputGroup.insertAdjacentElement(
                    "afterend",
                    switcher
                );
            }

            select.addEventListener("change", () => {
                updateTypeSwitcher(select, switcher);
                scheduleRefresh();
            });
        }

        updateTypeSwitcher(select, switcher);
    }

    function renameGroupAddButton(group, label) {
        if (!group) {
            return;
        }

        const button = Array.from(
            group.querySelectorAll(".rjf-add-button")
        ).find((candidate) => {
            return candidate.closest(".rjf-form-group") === group;
        });

        if (!button) {
            return;
        }

        setText(button, label);
        button.title = label.replace(/^\+\s*/, "");
    }

    function enhanceKeyValueRows(group, prefix) {
        if (!group) {
            return;
        }

        group.classList.add("content-block-key-value");

        const rowWrappers = new Set();
        const itemPrefix = `${prefix}§content§items§`;

        group.querySelectorAll("[name]").forEach((element) => {
            if (!element.name.startsWith(itemPrefix)) {
                return;
            }

            const rowWrapper = element.closest(
                ".rjf-form-group-wrapper"
            );

            if (rowWrapper) {
                rowWrappers.add(rowWrapper);
            }
        });

        rowWrappers.forEach((rowWrapper) => {
            rowWrapper.classList.add(
                "content-block-key-value__row"
            );
        });

        renameGroupAddButton(group, "+ Add key/value");
    }

    function enhanceTableGroup(group, buttonLabel) {
        if (!group) {
            return;
        }

        group.classList.add("content-block-table-section");
        renameGroupAddButton(group, buttonLabel);
    }

    function enhanceBlock(typeSelect) {
        const prefix = typeSelect.name.replace(/§type$/, "");

        const block = typeSelect.closest(
            ".rjf-form-group-wrapper"
        );

        if (!block) {
            return;
        }

        block.classList.add("content-block-card");

        createBlockHeader(block, prefix);
        createTypeSwitcher(typeSelect);

        const textInput = findNamedElement(
            block,
            `${prefix}§content§text`
        );

        const textSection = textInput?.closest(
            ".rjf-form-row"
        );

        const keyValueGroup = findGroupByTitle(
            block,
            "Key / Value items"
        );

        const columnsGroup = findGroupByTitle(
            block,
            "Table columns"
        );

        const rowsGroup = findGroupByTitle(
            block,
            "Table rows"
        );

        const keyValueSection =
            getSectionContainer(keyValueGroup);

        const columnsSection =
            getSectionContainer(columnsGroup);

        const rowsSection =
            getSectionContainer(rowsGroup);

        enhanceKeyValueRows(keyValueGroup, prefix);
        enhanceTableGroup(columnsGroup, "+ Add column");
        enhanceTableGroup(rowsGroup, "+ Add row");

        const selectedType = typeSelect.value;

        setSectionVisible(
            textSection,
            selectedType === "text"
        );

        setSectionVisible(
            keyValueSection,
            selectedType === "key_value"
        );

        setSectionVisible(
            columnsSection,
            selectedType === "table"
        );

        setSectionVisible(
            rowsSection,
            selectedType === "table"
        );
    }

    function enhanceRootGroup(root) {
        const rootGroup = root.querySelector(
            [
                ":scope > .rjf-form-wrapper",
                "> fieldset",
                "> .rjf-form-group-wrapper",
                "> .rjf-form-group",
            ].join(" ")
        );

        if (!rootGroup) {
            return;
        }

        const rootTitle = rootGroup.querySelector(
            ":scope > .rjf-form-group-title"
        );

        if (rootTitle) {
            rootTitle.classList.add(
                "content-blocks-editor__root-title"
            );
        }

        const rootAddButton = Array.from(
            rootGroup.querySelectorAll(".rjf-add-button")
        ).find((button) => {
            return button.closest(".rjf-form-group") === rootGroup;
        });

        if (rootAddButton) {
            setText(rootAddButton, "+ Add content block");
            rootAddButton.title = "Add content block";
            rootAddButton.classList.add(
                "content-blocks-editor__add-block"
            );
        }
    }

    function enhanceEditor() {
        const root = document.getElementById(EDITOR_ID);

        if (!root) {
            return;
        }

        root.classList.add("content-blocks-editor");

        const unfoldSection = root.closest(".max-w-4xl");

        if (unfoldSection) {
            unfoldSection.classList.add(
                "content-blocks-admin-section"
            );
        }

        enhanceRootGroup(root);

        root.querySelectorAll("select[name]").forEach((select) => {
            if (TYPE_FIELD_PATTERN.test(select.name)) {
                enhanceBlock(select);
            }
        });
    }

    function scheduleRefresh() {
        if (refreshScheduled) {
            return;
        }

        refreshScheduled = true;

        window.requestAnimationFrame(() => {
            refreshScheduled = false;
            enhanceEditor();
        });
    }

    function initialize() {
        enhanceEditor();

        const root = document.getElementById(EDITOR_ID);

        if (!root) {
            return;
        }

        root.addEventListener("input", scheduleRefresh);
        root.addEventListener("change", scheduleRefresh);

        const observer = new MutationObserver(scheduleRefresh);

        observer.observe(root, {
            childList: true,
            subtree: true,
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            {
                once: true,
            }
        );
    } else {
        initialize();
    }
})();

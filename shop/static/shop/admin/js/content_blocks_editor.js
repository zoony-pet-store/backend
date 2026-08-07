(() => {
    "use strict";

    const EDITOR_ID = "id_content_blocks_jsonform";
    const TYPE_SELECTOR = 'select[name$="§type"]';
    const BLOCK_TYPES = [
        { value: "text", label: "Text" },
        { value: "key_value", label: "Key / Value" },
        { value: "table", label: "Table" },
    ];

    let observer = null;
    let refreshScheduled = false;
    let bootAttempt = 0;
    let bootTimer = null;

    function setText(element, value) {
        if (element && element.textContent !== value) {
            element.textContent = value;
        }
    }

    function findNamedElement(container, name) {
        return (
            Array.from(container.querySelectorAll("[name]")).find(
                (element) => element.name === name
            ) || null
        );
    }

    function getDirectGroupTitleElement(group) {
        return group?.querySelector(
            ":scope > .rjf-form-group-title, " +
                ":scope > .rjf-form-group-inner > .rjf-form-group-title"
        );
    }

    function getDirectGroupTitle(group) {
        const titleElement = getDirectGroupTitleElement(group);

        if (!titleElement) {
            return "";
        }

        const clone = titleElement.cloneNode(true);

        clone.querySelectorAll("button").forEach((button) => {
            button.remove();
        });

        return clone.textContent.trim();
    }

    function findGroupByTitle(container, title) {
        return (
            Array.from(
                container.querySelectorAll(".rjf-form-group")
            ).find(
                (group) => getDirectGroupTitle(group) === title
            ) || null
        );
    }

    function getSectionContainer(group) {
        if (!group) {
            return null;
        }

        return group.parentElement?.classList.contains(
            "rjf-form-group-wrapper"
        )
            ? group.parentElement
            : group;
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

    function setNativeSelectValue(select, value) {
        const descriptor = Object.getOwnPropertyDescriptor(
            HTMLSelectElement.prototype,
            "value"
        );

        if (descriptor?.set) {
            descriptor.set.call(select, value);
        } else {
            select.value = value;
        }

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
    }

    function getBlockTypeLabel(value) {
        return (
            BLOCK_TYPES.find(
                (item) => item.value === value
            )?.label || "Select type"
        );
    }

    function createBlockHeader(
        block,
        prefix,
        typeSelect
    ) {
        let header = block.querySelector(
            ":scope > .content-block-card__header"
        );

        if (!header) {
            header = document.createElement("div");
            header.className =
                "content-block-card__header";

            header.innerHTML = `
                <div class="content-block-card__heading">
                    <strong class="content-block-card__title"></strong>
                    <span class="content-block-card__metadata"></span>
                </div>
                <span class="content-block-card__type"></span>
            `;

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

        setText(
            header.querySelector(
                ".content-block-card__title"
            ),
            titleInput?.value.trim() ||
                "Untitled content block"
        );

        setText(
            header.querySelector(
                ".content-block-card__metadata"
            ),
            keyInput?.value.trim() || "No key"
        );

        setText(
            header.querySelector(
                ".content-block-card__type"
            ),
            getBlockTypeLabel(typeSelect.value)
        );
    }

    function updateTypeSwitcher(
        select,
        switcher
    ) {
        switcher
            .querySelectorAll(
                ".content-block-type-switcher__button"
            )
            .forEach((button) => {
                const active =
                    button.dataset.blockType ===
                    select.value;

                button.classList.toggle(
                    "content-block-type-switcher__button--active",
                    active
                );

                button.setAttribute(
                    "aria-pressed",
                    String(active)
                );
            });
    }

    function createTypeSwitcher(select) {
        const formRow = select.closest(
            ".rjf-form-row"
        );

        if (!formRow) {
            return;
        }

        let switcher = formRow.querySelector(
            ".content-block-type-switcher"
        );

        if (!switcher) {
            switcher =
                document.createElement("div");

            switcher.className =
                "content-block-type-switcher";

            switcher.setAttribute(
                "role",
                "group"
            );

            switcher.setAttribute(
                "aria-label",
                "Content block type"
            );

            BLOCK_TYPES.forEach(
                ({ value, label }) => {
                    const button =
                        document.createElement(
                            "button"
                        );

                    button.type = "button";
                    button.className =
                        "content-block-type-switcher__button";
                    button.dataset.blockType = value;
                    button.textContent = label;

                    button.setAttribute(
                        "aria-pressed",
                        "false"
                    );

                    button.addEventListener(
                        "click",
                        () => {
                            if (
                                select.value === value
                            ) {
                                return;
                            }

                            setNativeSelectValue(
                                select,
                                value
                            );

                            updateTypeSwitcher(
                                select,
                                switcher
                            );

                            scheduleRefresh();
                        }
                    );

                    switcher.append(button);
                }
            );

            const inputGroup = select.closest(
                ".rjf-input-group"
            );

            if (inputGroup) {
                inputGroup.classList.add(
                    "content-block-type-select--native"
                );

                inputGroup.insertAdjacentElement(
                    "afterend",
                    switcher
                );
            }
        }

        if (
            select.dataset
                .contentBlockTypeBound !== "true"
        ) {
            select.dataset.contentBlockTypeBound =
                "true";

            select.addEventListener(
                "change",
                () => {
                    updateTypeSwitcher(
                        select,
                        switcher
                    );

                    scheduleRefresh();
                }
            );
        }

        updateTypeSwitcher(select, switcher);
    }

    function renameGroupAddButton(
        group,
        label
    ) {
        if (!group) {
            return;
        }

        const button = Array.from(
            group.querySelectorAll(
                ".rjf-add-button"
            )
        ).find(
            (candidate) =>
                candidate.closest(
                    ".rjf-form-group"
                ) === group
        );

        if (button) {
            setText(button, label);

            button.title = label.replace(
                /^\+\s*/,
                ""
            );
        }
    }

    function enhanceKeyValueRows(
        group,
        prefix
    ) {
        if (!group) {
            return;
        }

        group.classList.add(
            "content-block-key-value"
        );

        const itemPrefix =
            `${prefix}§content§items§`;

        const wrappers = new Set();

        group
            .querySelectorAll("[name]")
            .forEach((element) => {
                if (
                    !element.name.startsWith(
                        itemPrefix
                    )
                ) {
                    return;
                }

                const wrapper =
                    element.closest(
                        ".rjf-form-group-wrapper"
                    );

                if (wrapper) {
                    wrappers.add(wrapper);
                }
            });

        wrappers.forEach((wrapper) => {
            wrapper.classList.add(
                "content-block-key-value__row"
            );
        });

        renameGroupAddButton(
            group,
            "+ Add key/value"
        );
    }

    function enhanceTableGroup(
        group,
        label
    ) {
        if (!group) {
            return;
        }

        group.classList.add(
            "content-block-table-section"
        );

        renameGroupAddButton(
            group,
            label
        );
    }

    function enhanceBlock(typeSelect) {
        const prefix =
            typeSelect.name.replace(
                /§type$/,
                ""
            );

        const block = typeSelect.closest(
            ".rjf-form-group-wrapper"
        );

        if (!block) {
            return;
        }

        block.classList.add(
            "content-block-card"
        );

        createBlockHeader(
            block,
            prefix,
            typeSelect
        );

        createTypeSwitcher(typeSelect);

        const contentGroup =
            findGroupByTitle(
                block,
                "Content"
            );

        const keyValueGroup =
            findGroupByTitle(
                block,
                "Key / Value items"
            );

        const columnsGroup =
            findGroupByTitle(
                block,
                "Table columns"
            );

        const rowsGroup =
            findGroupByTitle(
                block,
                "Table rows"
            );

        contentGroup?.classList.add(
            "content-block-content"
        );

        enhanceKeyValueRows(
            keyValueGroup,
            prefix
        );

        enhanceTableGroup(
            columnsGroup,
            "+ Add column"
        );

        enhanceTableGroup(
            rowsGroup,
            "+ Add row"
        );

        const textInput =
            findNamedElement(
                block,
                `${prefix}§content§text`
            );

        setSectionVisible(
            textInput?.closest(
                ".rjf-form-row"
            ) || null,
            typeSelect.value === "text"
        );

        setSectionVisible(
            getSectionContainer(
                keyValueGroup
            ),
            typeSelect.value ===
                "key_value"
        );

        setSectionVisible(
            getSectionContainer(
                columnsGroup
            ),
            typeSelect.value === "table"
        );

        setSectionVisible(
            getSectionContainer(
                rowsGroup
            ),
            typeSelect.value === "table"
        );
    }

    function enhanceRootGroup(root) {
        const rootGroup =
            root.querySelector(
                ".rjf-form-wrapper > fieldset > " +
                    ".rjf-form-group-wrapper > " +
                    ".rjf-form-group"
            );

        if (!rootGroup) {
            return;
        }

        rootGroup.classList.add(
            "content-blocks-editor__root-group"
        );

        getDirectGroupTitleElement(
            rootGroup
        )?.classList.add(
            "content-blocks-editor__root-title"
        );

        const addButton = Array.from(
            rootGroup.querySelectorAll(
                ".rjf-add-button"
            )
        ).find(
            (button) =>
                button.closest(
                    ".rjf-form-group"
                ) === rootGroup
        );

        if (addButton) {
            setText(
                addButton,
                "+ Add content block"
            );

            addButton.title =
                "Add content block";

            addButton.classList.add(
                "content-blocks-editor__add-block"
            );
        }
    }

    function enhanceEditor() {
        const root =
            document.getElementById(
                EDITOR_ID
            );

        if (!root) {
            return false;
        }

        root.classList.add(
            "content-blocks-editor"
        );

        root.closest(
            ".field-row"
        )?.classList.add(
            "content-blocks-admin-field"
        );

        enhanceRootGroup(root);

        root.querySelectorAll(
            TYPE_SELECTOR
        ).forEach(enhanceBlock);

        root.dataset.contentBlocksEditorBooted =
            "true";

        return (
            root.querySelectorAll(
                TYPE_SELECTOR
            ).length > 0
        );
    }

    function scheduleRefresh() {
        if (refreshScheduled) {
            return;
        }

        refreshScheduled = true;

        window.requestAnimationFrame(() => {
            refreshScheduled = false;

            try {
                enhanceEditor();
            } catch (error) {
                console.error(
                    "Content blocks editor refresh failed:",
                    error
                );
            }
        });
    }

    function bindEditorEvents(root) {
        if (
            root.dataset
                .contentBlocksEventsBound ===
            "true"
        ) {
            return;
        }

        root.dataset.contentBlocksEventsBound =
            "true";

        root.addEventListener(
            "input",
            scheduleRefresh
        );

        root.addEventListener(
            "change",
            scheduleRefresh
        );

        observer = new MutationObserver(
            scheduleRefresh
        );

        observer.observe(root, {
            childList: true,
            subtree: true,
        });
    }

    function bootContentBlocksEditor() {
        const root =
            document.getElementById(
                EDITOR_ID
            );

        if (!root) {
            return false;
        }

        bindEditorEvents(root);

        try {
            return enhanceEditor();
        } catch (error) {
            console.error(
                "Content blocks editor initialization failed:",
                error
            );

            return false;
        }
    }

    function retryBoot() {
        const ready =
            bootContentBlocksEditor();

        if (
            ready ||
            bootAttempt >= 100
        ) {
            return;
        }

        bootAttempt += 1;

        window.clearTimeout(
            bootTimer
        );

        bootTimer =
            window.setTimeout(
                retryBoot,
                100
            );
    }

    window.bootContentBlocksEditor =
        bootContentBlocksEditor;

    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            retryBoot,
            {
                once: true,
            }
        );
    } else {
        retryBoot();
    }

    window.addEventListener(
        "load",
        retryBoot,
        {
            once: true,
        }
    );
})();

(function () {
  function initCategoryTreeSelect(widget) {
    if (widget.dataset.initialized === "true") {
      return;
    }

    widget.dataset.initialized = "true";

    const input = document.getElementById(widget.dataset.inputId);
    const button = widget.querySelector(".category-tree-select__button");
    const valueLabel = widget.querySelector(".category-tree-select__value");
    const panel = widget.querySelector(".category-tree-select__panel");
    const groupsContainer = widget.querySelector(".category-tree-select__groups");
    const placeholder = widget.dataset.placeholder || "Select category";
    const treeScript = document.getElementById(widget.dataset.treeScriptId);
    const tree = JSON.parse(treeScript ? treeScript.textContent : "[]");
    const selectGroups = widget.dataset.selectGroups === "true";
    const animalTypeInput = widget.dataset.animalTypeInputId
      ? document.getElementById(widget.dataset.animalTypeInputId)
      : null;

    document.body.appendChild(panel);

    function positionPanel() {
      const rect = button.getBoundingClientRect();
      const viewportMargin = 12;
      const panelGap = 6;
      const preferredHeight = Math.min(window.innerHeight * 0.7, 640);
      const availableBelow = window.innerHeight - rect.bottom - viewportMargin;
      const availableAbove = rect.top - viewportMargin;
      let maxHeight = Math.min(preferredHeight, availableBelow);
      let top = rect.bottom + panelGap;

      if (maxHeight < 260 && availableAbove > availableBelow) {
        maxHeight = Math.min(preferredHeight, availableAbove);
        top = Math.max(viewportMargin, rect.top - panelGap - maxHeight);
      }

      if (maxHeight < 180) {
        top = viewportMargin;
        maxHeight = window.innerHeight - viewportMargin * 2;
      }

      panel.style.left = rect.left + "px";
      panel.style.top = top + "px";
      panel.style.width = rect.width + "px";
      panel.style.maxHeight = maxHeight + "px";
    }

    function closePanel() {
      panel.hidden = true;
      button.setAttribute("aria-expanded", "false");
    }

    function toggleChildren(toggle, children) {
      const isHidden = children.hidden;

      children.hidden = !isHidden;
      toggle.textContent = isHidden ? "▾" : "▸";

      if (isHidden) {
        window.setTimeout(function () {
          positionPanel();
          children.scrollIntoView({ block: "nearest" });
        }, 0);
      }
    }

    function clearSelectedOptions() {
      panel.querySelectorAll(
        ".category-tree-select__option--selected, .category-tree-select__group-title--selected"
      ).forEach(function (selectedOption) {
        selectedOption.classList.remove(
          "category-tree-select__option--selected",
          "category-tree-select__group-title--selected"
        );
      });
    }

    function setAnimalType(animalTypeId) {
      if (!animalTypeInput) {
        return;
      }

      animalTypeInput.value = animalTypeId || "";
      animalTypeInput.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function createNode(node, depth, groupName) {
      const item = document.createElement("div");
      const row = document.createElement("div");
      const toggle = document.createElement("button");
      const option = document.createElement("button");
      const hasChildren = node.children.length > 0;
      const expanded = Boolean(node.expanded);

      item.className = "category-tree-select__node";
      row.className = "category-tree-select__row";
      row.style.setProperty("--category-tree-depth", depth);

      toggle.type = "button";
      toggle.className = "category-tree-select__toggle";
      toggle.textContent = hasChildren ? (expanded ? "▾" : "▸") : "";
      toggle.setAttribute("aria-label", hasChildren ? "Toggle subcategories" : "Select category");

      if (!hasChildren) {
        toggle.classList.add("category-tree-select__toggle--placeholder");
      }

      option.type = "button";
      option.className = "category-tree-select__option";
      option.textContent = (hasChildren ? "📁 " : "🏷️ ") + node.name;

      if (hasChildren) {
        row.classList.add("category-tree-select__row--toggleable");
        option.classList.add("category-tree-select__option--folder");
      }

      if (node.selected) {
        option.classList.add("category-tree-select__option--selected");
      }

      row.appendChild(toggle);
      row.appendChild(option);
      item.appendChild(row);

      const children = document.createElement("div");
      children.className = "category-tree-select__children";
      children.hidden = !expanded;

      node.children.forEach(function (child) {
        children.appendChild(createNode(child, depth + 1, groupName));
      });

      item.appendChild(children);

      function selectNode() {
        if (!node.selectable) {
          if (hasChildren) {
            toggleChildren(toggle, children);
          }

          return;
        }

        input.value = node.id;
        setAnimalType(node.animal_type_id);
        valueLabel.textContent = groupName + " / " + node.path;
        closePanel();

        clearSelectedOptions();
        option.classList.add("category-tree-select__option--selected");
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }

      toggle.addEventListener("click", function (event) {
        event.stopPropagation();

        if (hasChildren) {
          toggleChildren(toggle, children);
        }
      });

      option.addEventListener("click", function (event) {
        event.stopPropagation();
        selectNode();
      });

      return item;
    }

    tree.forEach(function (group) {
      const groupElement = document.createElement("div");
      const groupTitle = document.createElement("button");
      const groupChildren = document.createElement("div");
      const groupToggle = document.createElement("span");
      const groupLabel = document.createElement("span");

      groupElement.className = "category-tree-select__group";
      groupChildren.className = "category-tree-select__group-children";
      groupChildren.hidden = !group.expanded;
      groupTitle.type = "button";
      groupTitle.className = "category-tree-select__group-title";
      groupToggle.className = "category-tree-select__group-toggle";
      groupToggle.textContent = group.expanded ? "▾" : "▸";
      groupLabel.className = "category-tree-select__group-label";
      groupLabel.textContent = "⭐ " + group.name;
      groupTitle.appendChild(groupToggle);
      groupTitle.appendChild(groupLabel);
      groupElement.appendChild(groupTitle);

      if (group.selected) {
        groupTitle.classList.add("category-tree-select__group-title--selected");
      }

      group.children.forEach(function (node) {
        groupChildren.appendChild(createNode(node, 0, group.name));
      });

      function toggleGroup() {
        const isHidden = groupChildren.hidden;

        groupChildren.hidden = !isHidden;
        groupToggle.textContent = isHidden ? "▾" : "▸";

        if (isHidden) {
          window.setTimeout(function () {
            positionPanel();
            groupChildren.scrollIntoView({ block: "nearest" });
          }, 0);
        }
      }

      function selectGroup() {
        if (!selectGroups) {
          toggleGroup();
          return;
        }

        input.value = "";
        setAnimalType(group.id);
        valueLabel.textContent = group.name;
        closePanel();

        clearSelectedOptions();
        groupTitle.classList.add("category-tree-select__group-title--selected");
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }

      groupToggle.addEventListener("click", function (event) {
        event.stopPropagation();
        toggleGroup();
      });

      groupTitle.addEventListener("click", function () {
        selectGroup();
      });

      groupElement.appendChild(groupChildren);
      groupsContainer.appendChild(groupElement);
    });

    if (!input.value && !valueLabel.textContent.trim()) {
      valueLabel.textContent = placeholder;
    }

    button.addEventListener("click", function () {
      const isHidden = panel.hidden;
      panel.hidden = !isHidden;
      button.setAttribute("aria-expanded", isHidden ? "true" : "false");

      if (isHidden) {
        positionPanel();
      }
    });

    window.addEventListener("resize", function () {
      if (!panel.hidden) {
        positionPanel();
      }
    });

    window.addEventListener(
      "scroll",
      function () {
        if (!panel.hidden) {
          positionPanel();
        }
      },
      true
    );

    document.addEventListener("click", function (event) {
      if (!widget.contains(event.target) && !panel.contains(event.target)) {
        closePanel();
      }
    });
  }

  function initAllCategoryTreeSelects() {
    document.querySelectorAll(".category-tree-select").forEach(initCategoryTreeSelect);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAllCategoryTreeSelects);
  } else {
    initAllCategoryTreeSelects();
  }
})();

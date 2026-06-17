(function () {
  const SELECT_TYPE = "select";
  const NUMERIC_TYPE = "numeric";

  function escapeAttributeValue(value) {
    return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }

  function getFieldByName(name) {
    return document.querySelector(`[name="${escapeAttributeValue(name)}"]`);
  }

  function getFieldPrefix(attributeSelect) {
    if (!attributeSelect || !attributeSelect.name) {
      return "";
    }

    return attributeSelect.name.replace(/-attribute$/, "");
  }

  function getRelatedField(attributeSelect, fieldName) {
    const prefix = getFieldPrefix(attributeSelect);

    if (!prefix) {
      return null;
    }

    return getFieldByName(`${prefix}-${fieldName}`);
  }

  function getNearestCommonAncestor(firstElement, secondElement) {
    if (!firstElement || !secondElement) {
      return null;
    }

    let current = firstElement;
    let steps = 0;

    while (current && steps < 10) {
      if (current.contains(secondElement)) {
        return current;
      }

      current = current.parentElement;
      steps += 1;
    }

    return null;
  }

  function getFieldContainer(fieldElement) {
    if (!fieldElement) {
      return null;
    }

    const label = fieldElement.id
      ? document.querySelector(`label[for="${fieldElement.id}"]`)
      : null;

    const commonAncestor = getNearestCommonAncestor(label, fieldElement);

    if (commonAncestor) {
      return commonAncestor;
    }

    return (
      fieldElement.closest(".form-row") ||
      fieldElement.closest("[class*='form-row']") ||
      fieldElement.closest("tr") ||
      fieldElement.closest("td") ||
      fieldElement.closest("div")
    );
  }

  function setVisible(element, isVisible) {
    if (!element) {
      return;
    }

    element.style.display = isVisible ? "" : "none";
  }

  function clearField(fieldElement) {
    if (!fieldElement) {
      return;
    }

    fieldElement.value = "";
    fieldElement.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function filterValueOptions(valueField, attributeId) {
    if (!valueField || valueField.tagName !== "SELECT") {
      return;
    }

    Array.from(valueField.options).forEach((option) => {
      if (!option.value) {
        option.hidden = false;
        option.disabled = false;
        return;
      }

      const optionAttributeId = option.dataset.attributeId;
      const isAllowed = !attributeId || optionAttributeId === attributeId;

      option.hidden = !isAllowed;
      option.disabled = !isAllowed;

      if (!isAllowed && option.selected) {
        valueField.value = "";
      }
    });
  }

  function filterUnitOptions(unitField, availableUnitsCsv) {
    if (!unitField || unitField.tagName !== "SELECT") {
      return;
    }

    const availableUnits = availableUnitsCsv
      ? availableUnitsCsv.split(",").filter(Boolean)
      : [];

    Array.from(unitField.options).forEach((option) => {
      if (!option.value) {
        option.hidden = false;
        option.disabled = false;
        return;
      }

      const isAllowed =
        availableUnits.length === 0 || availableUnits.includes(option.value);

      option.hidden = !isAllowed;
      option.disabled = !isAllowed;

      if (!isAllowed && option.selected) {
        unitField.value = "";
      }
    });
  }

  function syncAttributeSelect(attributeSelect) {
    if (!attributeSelect || attributeSelect.tagName !== "SELECT") {
      return;
    }

    const selectedOption = attributeSelect.options[attributeSelect.selectedIndex];

    const attributeId = attributeSelect.value;
    const attributeType = selectedOption
      ? selectedOption.dataset.attributeType
      : "";
    const availableUnits = selectedOption
      ? selectedOption.dataset.availableUnits
      : "";

    const valueField = getRelatedField(attributeSelect, "value");
    const valueNumericField = getRelatedField(attributeSelect, "value_numeric");
    const unitField = getRelatedField(attributeSelect, "unit");

    const valueContainer = getFieldContainer(valueField);
    const valueNumericContainer = getFieldContainer(valueNumericField);
    const unitContainer = getFieldContainer(unitField);

    filterValueOptions(valueField, attributeId);
    filterUnitOptions(unitField, availableUnits);

    if (!attributeId) {
      setVisible(valueContainer, false);
      setVisible(valueNumericContainer, false);
      setVisible(unitContainer, false);

      clearField(valueField);
      clearField(valueNumericField);
      clearField(unitField);

      return;
    }

    if (attributeType === NUMERIC_TYPE) {
      setVisible(valueContainer, false);
      setVisible(valueNumericContainer, true);
      setVisible(unitContainer, true);

      clearField(valueField);

      return;
    }

    if (attributeType === SELECT_TYPE) {
      setVisible(valueContainer, true);
      setVisible(valueNumericContainer, false);
      setVisible(unitContainer, false);

      clearField(valueNumericField);
      clearField(unitField);

      return;
    }

    setVisible(valueContainer, true);
    setVisible(valueNumericContainer, true);
    setVisible(unitContainer, true);
  }

  function syncAllRows() {
    document
      .querySelectorAll('select[name$="-attribute"]')
      .forEach((attributeSelect) => {
        syncAttributeSelect(attributeSelect);
      });
  }

  function boot() {
    syncAllRows();
    setTimeout(syncAllRows, 100);
    setTimeout(syncAllRows, 300);
    setTimeout(syncAllRows, 800);
    setTimeout(syncAllRows, 1500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.addEventListener("load", syncAllRows);

  document.addEventListener("change", function (event) {
    if (event.target.matches('select[name$="-attribute"]')) {
      syncAttributeSelect(event.target);
    }
  });

  document.addEventListener("formset:added", function () {
    syncAllRows();
    setTimeout(syncAllRows, 100);
    setTimeout(syncAllRows, 300);
  });

  window.syncVariantAttributeInlines = syncAllRows;
})();

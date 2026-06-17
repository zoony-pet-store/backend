(function () {
  const SELECT_TYPE = "select";
  const NUMERIC_TYPE = "numeric";

  function getRow(element) {
    if (!element) {
      return null;
    }

    return (
      element.closest(".dynamic-variant_attributes") ||
      element.closest("[class*='dynamic-']") ||
      element.closest("tr.form-row") ||
      element.closest("tr") ||
      element.closest(".form-row")
    );
  }

  function getFieldElement(row, fieldName) {
    if (!row) {
      return null;
    }

    return row.querySelector(
      `select[name$="-${fieldName}"], input[name$="-${fieldName}"]`
    );
  }

  function getFieldContainer(row, fieldName) {
    if (!row) {
      return null;
    }

    const fieldElement = getFieldElement(row, fieldName);

    return (
      row.querySelector(`.field-${fieldName}`) ||
      row.querySelector(`[class*="field-${fieldName}"]`) ||
      row.querySelector(`[data-field-name="${fieldName}"]`) ||
      (fieldElement ? fieldElement.closest(".form-row") : null) ||
      (fieldElement ? fieldElement.closest("div") : null)
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

  function filterValueOptions(row, attributeId) {
    const valueSelect = getFieldElement(row, "value");

    if (!valueSelect || valueSelect.tagName !== "SELECT") {
      return;
    }

    Array.from(valueSelect.options).forEach((option) => {
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
        valueSelect.value = "";
      }
    });
  }

  function filterUnitOptions(row, availableUnitsCsv) {
    const unitField = getFieldElement(row, "unit");

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

  function syncRow(row) {
    if (!row) {
      return;
    }

    const attributeSelect = getFieldElement(row, "attribute");

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

    const valueContainer = getFieldContainer(row, "value");
    const valueNumericContainer = getFieldContainer(row, "value_numeric");
    const unitContainer = getFieldContainer(row, "unit");

    const valueField = getFieldElement(row, "value");
    const valueNumericField = getFieldElement(row, "value_numeric");
    const unitField = getFieldElement(row, "unit");

    filterValueOptions(row, attributeId);
    filterUnitOptions(row, availableUnits);

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
        syncRow(getRow(attributeSelect));
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
      syncRow(getRow(event.target));
    }
  });

  document.addEventListener("formset:added", function () {
    syncAllRows();
    setTimeout(syncAllRows, 100);
    setTimeout(syncAllRows, 300);
  });

  window.syncVariantAttributeInlines = syncAllRows;
})();

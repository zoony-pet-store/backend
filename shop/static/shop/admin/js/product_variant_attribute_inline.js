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
      (fieldElement
        ? fieldElement.closest(".form-row, .field, td, div")
        : null)
    );
  }

  function setVisible(element, isVisible) {
    if (!element) {
      return;
    }

    element.style.display = isVisible ? "" : "none";
  }

  function clearSelect(selectElement) {
    if (!selectElement) {
      return;
    }

    selectElement.value = "";

    selectElement.dispatchEvent(
      new Event("change", {
        bubbles: true,
      })
    );
  }

  function clearInput(inputElement) {
    if (!inputElement) {
      return;
    }

    inputElement.value = "";
  }

  function filterValueOptions(row, attributeId) {
    const valueSelect = getFieldElement(row, "value");

    if (!valueSelect) {
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
    const unitSelect = getFieldElement(row, "unit");

    if (!unitSelect) {
      return;
    }

    const availableUnits = availableUnitsCsv
      ? availableUnitsCsv.split(",").filter(Boolean)
      : [];

    Array.from(unitSelect.options).forEach((option) => {
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
        unitSelect.value = "";
      }
    });
  }

  function syncRow(row) {
    if (!row) {
      return;
    }

    const attributeSelect = getFieldElement(row, "attribute");

    if (!attributeSelect) {
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

    const valueSelect = getFieldElement(row, "value");
    const valueNumericInput = getFieldElement(row, "value_numeric");
    const unitSelect = getFieldElement(row, "unit");

    filterValueOptions(row, attributeId);
    filterUnitOptions(row, availableUnits);

    if (!attributeId) {
      setVisible(valueContainer, false);
      setVisible(valueNumericContainer, false);
      setVisible(unitContainer, false);

      clearSelect(valueSelect);
      clearInput(valueNumericInput);
      clearSelect(unitSelect);

      return;
    }

    if (attributeType === NUMERIC_TYPE) {
      setVisible(valueContainer, false);
      setVisible(valueNumericContainer, true);
      setVisible(unitContainer, true);

      clearSelect(valueSelect);

      return;
    }

    if (attributeType === SELECT_TYPE) {
      setVisible(valueContainer, true);
      setVisible(valueNumericContainer, false);
      setVisible(unitContainer, false);

      clearInput(valueNumericInput);
      clearSelect(unitSelect);

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

  document.addEventListener("DOMContentLoaded", function () {
    syncAllRows();
    setTimeout(syncAllRows, 300);
  });

  document.addEventListener("change", function (event) {
    if (event.target.matches('select[name$="-attribute"]')) {
      syncRow(getRow(event.target));
    }
  });

  document.addEventListener("formset:added", function () {
    syncAllRows();
    setTimeout(syncAllRows, 100);
  });
})();

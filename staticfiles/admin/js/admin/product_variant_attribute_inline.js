(function () {
  const SELECT_TYPE = "select";
  const NUMERIC_TYPE = "numeric";

  function getRow(element) {
    return (
      element.closest("tr.form-row") ||
      element.closest(".form-row") ||
      element.closest("[class*='dynamic-']")
    );
  }

  function getFieldContainer(row, fieldName) {
    if (!row) {
      return null;
    }

    return (
      row.querySelector(`.field-${fieldName}`) ||
      row.querySelector(`[class*="field-${fieldName}"]`)
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
  }

  function clearInput(inputElement) {
    if (!inputElement) {
      return;
    }

    inputElement.value = "";
  }

  function filterValueOptions(row, attributeId) {
    const valueSelect = row.querySelector('select[name$="-value"]');

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
    const unitSelect = row.querySelector('select[name$="-unit"]');

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

    const attributeSelect = row.querySelector('select[name$="-attribute"]');

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

    const valueSelect = row.querySelector('select[name$="-value"]');
    const valueNumericInput = row.querySelector('input[name$="-value_numeric"]');
    const unitSelect = row.querySelector('select[name$="-unit"]');

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

  document.addEventListener("DOMContentLoaded", syncAllRows);

  document.addEventListener("change", function (event) {
    if (event.target.matches('select[name$="-attribute"]')) {
      syncRow(getRow(event.target));
    }
  });

  document.addEventListener("formset:added", function (event) {
    syncRow(event.target);
  });
})();

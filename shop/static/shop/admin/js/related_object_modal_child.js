(function () {
  const params = new URLSearchParams(window.location.search);

  if (
    params.get("_modal") !== "1"
    || window.parent === window
  ) {
    return;
  }

  function postToParent(payload) {
    window.parent.postMessage(
      payload,
      window.location.origin
    );
  }

  function initModalChildForm() {
    const form = document.querySelector(
      'form[method="post"]'
    );

    if (!form) {
      return;
    }

    if (!form.querySelector('input[name="_modal"]')) {
      const modalInput = document.createElement("input");

      modalInput.type = "hidden";
      modalInput.name = "_modal";
      modalInput.value = "1";

      form.appendChild(modalInput);
    }

    [
      "_addanother",
      "_continue",
      "_saveasnew",
    ].forEach(function (name) {
      document
        .querySelectorAll(`[name="${name}"]`)
        .forEach(function (control) {
          control.hidden = true;
        });
    });

    let dirty = Boolean(
      document.querySelector(
        ".errornote, .errorlist, [aria-invalid='true']"
      )
    );

    function markDirty() {
      if (dirty) {
        return;
      }

      dirty = true;

      postToParent({
        type: "admin-related-object-dirty",
        dirty: true,
      });
    }

    form.addEventListener("input", markDirty, true);
    form.addEventListener("change", markDirty, true);

    postToParent({
      type: "admin-related-object-dirty",
      dirty: dirty,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initModalChildForm
    );
  } else {
    initModalChildForm();
  }
})();

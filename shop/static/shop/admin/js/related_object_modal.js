(function () {
  const SAVED_MESSAGE_KEY =
    "admin-related-object-saved-message";

  function initRelatedObjectModal() {
    const modal = document.getElementById(
      "related-object-modal"
    );

    if (!modal) {
      return;
    }

    const iframe = modal.querySelector(
      "[data-related-modal-iframe]"
    );
    const loader = modal.querySelector(
      "[data-related-modal-loader]"
    );
    const closeButton = modal.querySelector(
      "[data-related-modal-close]"
    );
    const title = document.getElementById(
      "related-object-modal-title"
    );
    const productForm = document.querySelector(
      "#product_form"
    );

    const notice = document.querySelector(
      "[data-related-modal-notice]"
    );
    const noticeText = document.querySelector(
      "[data-related-modal-notice-text]"
    );
    const refreshButton = document.querySelector(
      "[data-related-modal-refresh]"
    );
    const dismissButton = document.querySelector(
      "[data-related-modal-notice-dismiss]"
    );

    if (!iframe || !loader || !closeButton || !title) {
      return;
    }

    let iframeDirty = false;
    let productFormDirty = Boolean(
      productForm
      && productForm.querySelector(
        ".errornote, .errorlist, [aria-invalid='true']"
      )
    );
    let lastTrigger = null;

    function storeSavedMessage(message) {
      try {
        window.sessionStorage.setItem(
          SAVED_MESSAGE_KEY,
          message
        );
      } catch (error) {
        console.warn(
          "Unable to store the modal success message.",
          error
        );
      }
    }

    function consumeSavedMessage() {
      try {
        const message = window.sessionStorage.getItem(
          SAVED_MESSAGE_KEY
        );

        if (message) {
          window.sessionStorage.removeItem(
            SAVED_MESSAGE_KEY
          );
        }

        return message;
      } catch (error) {
        console.warn(
          "Unable to read the modal success message.",
          error
        );
        return null;
      }
    }

    function showNotice(message, options) {
      if (!notice || !noticeText) {
        return;
      }

      const showRefresh = Boolean(
        options && options.showRefresh
      );

      noticeText.textContent = message;
      notice.hidden = false;

      if (refreshButton) {
        refreshButton.hidden = !showRefresh;
      }
    }

    function hideNotice() {
      if (!notice) {
        return;
      }

      notice.hidden = true;

      if (noticeText) {
        noticeText.textContent = "";
      }
    }

    function resetIframe() {
      iframe.src = "about:blank";
      iframe.hidden = true;
      iframe.setAttribute("aria-busy", "true");

      loader.hidden = false;
      iframeDirty = false;
    }

    function openModal(trigger) {
      const modalUrl =
        trigger.dataset.modalUrl || trigger.href;
      const fallbackUrl = trigger.href || modalUrl;
      const modalTitle =
        trigger.dataset.modalTitle
        || "Edit related object";

      if (!modalUrl) {
        return;
      }

      if (typeof modal.showModal !== "function") {
        window.location.assign(fallbackUrl);
        return;
      }

      hideNotice();

      lastTrigger = trigger;
      iframeDirty = false;

      title.textContent = modalTitle;

      loader.hidden = false;
      iframe.hidden = true;
      iframe.setAttribute("aria-busy", "true");
      iframe.src = modalUrl;

      if (!modal.open) {
        modal.showModal();
      }
    }

    function closeModal(options) {
      const force = Boolean(
        options && options.force
      );

      if (
        !force
        && iframeDirty
        && !window.confirm(
          "Discard unsaved changes in the modal form?"
        )
      ) {
        return;
      }

      if (modal.open) {
        modal.close();
      }

      resetIframe();

      if (
        lastTrigger
        && lastTrigger.isConnected
        && typeof lastTrigger.focus === "function"
      ) {
        lastTrigger.focus();
      }

      lastTrigger = null;
    }

    function refreshPage() {
      if (
        productFormDirty
        && !window.confirm(
          "Refreshing will discard unsaved product "
          + "changes. Continue?"
        )
      ) {
        return;
      }

      window.location.reload();
    }

    function isBackdropClick(event) {
      if (event.target !== modal) {
        return false;
      }

      const rect = modal.getBoundingClientRect();

      return (
        event.clientX < rect.left
        || event.clientX > rect.right
        || event.clientY < rect.top
        || event.clientY > rect.bottom
      );
    }

    document.addEventListener("click", function (event) {
      if (
        event.defaultPrevented
        || event.button !== 0
        || event.ctrlKey
        || event.metaKey
        || event.shiftKey
        || event.altKey
      ) {
        return;
      }

      if (!(event.target instanceof Element)) {
        return;
      }

      const trigger = event.target.closest(
        ".js-related-object-modal"
      );

      if (!trigger) {
        return;
      }

      event.preventDefault();
      openModal(trigger);
    });

    iframe.addEventListener("load", function () {
      if (
        !iframe.src
        || iframe.src === "about:blank"
      ) {
        return;
      }

      loader.hidden = true;
      iframe.hidden = false;
      iframe.setAttribute("aria-busy", "false");
    });

    closeButton.addEventListener("click", function () {
      closeModal();
    });

    modal.addEventListener("cancel", function (event) {
      event.preventDefault();
      closeModal();
    });

    modal.addEventListener("click", function (event) {
      if (isBackdropClick(event)) {
        closeModal();
      }
    });

    window.addEventListener("message", function (event) {
      if (event.origin !== window.location.origin) {
        return;
      }

      if (event.source !== iframe.contentWindow) {
        return;
      }

      if (
        !event.data
        || typeof event.data !== "object"
      ) {
        return;
      }

      if (
        event.data.type
        === "admin-related-object-dirty"
      ) {
        iframeDirty = Boolean(event.data.dirty);
        return;
      }

      if (
        event.data.type
        !== "admin-related-object-saved"
      ) {
        return;
      }

      iframeDirty = false;
      closeModal({ force: true });

      document.dispatchEvent(
        new CustomEvent(
          "admin-related-object-saved",
          {
            detail: event.data,
          }
        )
      );

      const message =
        event.data.message
        || "Variant saved successfully.";

      if (!productFormDirty) {
        storeSavedMessage(message);
        window.location.reload();
        return;
      }

      showNotice(
        message
        + " Save the product or refresh the page "
        + "to update the variants list.",
        {
          showRefresh: true,
        }
      );
    });

    if (productForm) {
      window.setTimeout(function () {
        function markProductFormDirty() {
          productFormDirty = true;
        }

        productForm.addEventListener(
          "input",
          markProductFormDirty,
          true
        );
        productForm.addEventListener(
          "change",
          markProductFormDirty,
          true
        );
      }, 0);
    }

    if (refreshButton) {
      refreshButton.addEventListener(
        "click",
        refreshPage
      );
    }

    if (dismissButton) {
      dismissButton.addEventListener(
        "click",
        hideNotice
      );
    }

    const savedMessage = consumeSavedMessage();

    if (savedMessage) {
      showNotice(
        savedMessage,
        {
          showRefresh: false,
        }
      );
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initRelatedObjectModal
    );
  } else {
    initRelatedObjectModal();
  }
})();

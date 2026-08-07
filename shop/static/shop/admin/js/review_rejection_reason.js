(function () {
  function resizeTextarea(textarea) {
    const maxRows = Number(textarea.dataset.maxRows || 7);
    const minRows = Number(textarea.getAttribute("rows") || 2);
    const styles = window.getComputedStyle(textarea);
    const lineHeight = parseFloat(styles.lineHeight);
    const paddingTop = parseFloat(styles.paddingTop);
    const paddingBottom = parseFloat(styles.paddingBottom);
    const borderTop = parseFloat(styles.borderTopWidth);
    const borderBottom = parseFloat(styles.borderBottomWidth);
    const minHeight = lineHeight * minRows + paddingTop + paddingBottom + borderTop + borderBottom;
    const maxHeight = lineHeight * maxRows + paddingTop + paddingBottom + borderTop + borderBottom;

    textarea.style.height = "auto";
    textarea.style.height = `${Math.max(minHeight, Math.min(textarea.scrollHeight, maxHeight))}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  }

  function initRejectionReasonTextarea() {
    document.querySelectorAll("textarea.review-rejection-reason-autogrow").forEach((textarea) => {
      resizeTextarea(textarea);
      textarea.addEventListener("input", () => resizeTextarea(textarea));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initRejectionReasonTextarea);
  } else {
    initRejectionReasonTextarea();
  }
})();

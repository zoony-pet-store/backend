(function () {
  const payloadNode = document.getElementById(
    "related-object-modal-payload"
  );

  if (!payloadNode || window.parent === window) {
    return;
  }

  let payload;

  try {
    payload = JSON.parse(payloadNode.textContent);
  } catch (error) {
    console.error(
      "Unable to parse related object modal payload.",
      error
    );
    return;
  }

  window.parent.postMessage(
    payload,
    window.location.origin
  );
})();

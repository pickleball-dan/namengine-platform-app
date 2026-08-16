(function () {
  document.addEventListener("click", async (event) => {
    const trigger = event.target.closest("[data-share-list]");
    if (!trigger) return;

    event.preventDefault();

    const shareUrl = new URL(trigger.dataset.shareUrl || trigger.getAttribute("href") || window.location.href, window.location.origin).href;
    const sharePayload = {
      title: trigger.dataset.shareTitle || document.title || "NamEngine list",
      text: trigger.dataset.shareText || "Here is a NamEngine name list to review.",
      url: shareUrl,
    };

    if (navigator.share) {
      try {
        await navigator.share(sharePayload);
        return;
      } catch (error) {
        if (error && error.name === "AbortError") {
          return;
        }
      }
    }

    try {
      await navigator.clipboard.writeText(shareUrl);
      trigger.textContent = trigger.dataset.shareCopiedLabel || "Link copied";
      trigger.setAttribute("aria-live", "polite");
    } catch (error) {
      window.location.href = shareUrl;
    }
  });
})();

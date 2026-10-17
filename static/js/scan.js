/**
 * scan.js — USB HID Barcode Scanner Handler (Desktop Mode)
 *
 * Behaviour:
 *  - #scan-input is ALWAYS focused. If the user clicks elsewhere or a modal
 *    steals focus, this script silently reclaims focus after 120 ms.
 *  - USB HID scanners behave like keyboards: they type characters then send
 *    Enter (keyCode 13). We intercept Enter to submit #scan-form.
 *  - Debounce: 300 ms minimum between submits to prevent double-fire from
 *    scanners that send a trailing \r\n.
 *  - Error banners auto-dismiss after 4 seconds so the operator can see the
 *    input immediately on the next scan.
 *  - Input is cleared after each submit attempt so the field is always empty
 *    and ready for the next card.
 */
(function () {
  "use strict";

  var lastSubmit = 0;
  var DEBOUNCE_MS = 300;       // min ms between two submits
  var REFOCUS_DELAY_MS = 120;  // ms after blur before reclaiming focus
  var AUTO_DISMISS_MS = 4000;  // ms before error banner fades out

  function getInput()  { return document.getElementById("scan-input"); }
  function getForm()   { return document.getElementById("scan-form"); }
  function getBanner() { return document.getElementById("error-banner"); }

  /* ── Focus guard ─────────────────────────────────────────────────────── */
  function claimFocus() {
    var inp = getInput();
    if (inp && document.activeElement !== inp) {
      inp.focus();
    }
  }

  function installFocusGuard(inp) {
    /* Reclaim focus whenever the input loses it (click on table, etc.) */
    inp.addEventListener("blur", function () {
      setTimeout(claimFocus, REFOCUS_DELAY_MS);
    });

    /* Also reclaim when the whole window regains focus (Alt-Tab back) */
    window.addEventListener("focus", function () {
      setTimeout(claimFocus, REFOCUS_DELAY_MS);
    });

    /* Click anywhere on the page → redirect to input */
    document.addEventListener("click", function (e) {
      if (e.target !== inp) {
        setTimeout(claimFocus, 50);
      }
    });
  }

  /* ── Submit logic ────────────────────────────────────────────────────── */
  function trySubmit() {
    var now = Date.now();
    if (now - lastSubmit < DEBOUNCE_MS) return;

    var inp  = getInput();
    var form = getForm();
    if (!inp || !form) return;

    var val = inp.value.trim();
    if (!val) return;          // empty — scanner not finished typing yet

    lastSubmit = now;
    form.requestSubmit();

    /* Clear the field so the scanner doesn't double-submit if the page
       stays open (e.g. an error was returned). */
    inp.value = "";
  }

  /* ── Keyboard handler ────────────────────────────────────────────────── */
  function onKeyDown(e) {
    /* Enter / Return — scanner sends this after the barcode digits */
    if (e.key === "Enter" || e.keyCode === 13) {
      e.preventDefault();
      trySubmit();
    }
  }

  /* ── Error banner auto-dismiss ───────────────────────────────────────── */
  function autoDismissBanner() {
    var banner = getBanner();
    if (!banner) return;

    setTimeout(function () {
      banner.style.transition = "opacity 0.6s ease";
      banner.style.opacity = "0";
      setTimeout(function () {
        if (banner.parentNode) banner.parentNode.removeChild(banner);
        /* Re-focus after banner removal */
        claimFocus();
      }, 650);
    }, AUTO_DISMISS_MS);
  }

  /* ── Init ────────────────────────────────────────────────────────────── */
  function init() {
    var inp = getInput();
    if (!inp) return;

    inp.value = "";             // clear any browser-cached value
    inp.addEventListener("keydown", onKeyDown);
    installFocusGuard(inp);

    /* Initial focus */
    claimFocus();

    /* Auto-dismiss error banner if present */
    autoDismissBanner();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

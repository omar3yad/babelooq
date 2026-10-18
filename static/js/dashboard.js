// static/js/dashboard.js — Fast Direct POS Scanner & Customer Display (IE11 & ES5 Compatible)

(function () {
  "use strict";

  // Polyfills for legacy browsers (IE11)
  if (!String.prototype.padStart) {
    String.prototype.padStart = function (targetLength, padString) {
      targetLength = targetLength >> 0;
      padString = String(typeof padString !== "undefined" ? padString : " ");
      if (this.length > targetLength) return String(this);
      targetLength = targetLength - this.length;
      if (targetLength > padString.length) {
        padString += padString.repeat ? padString.repeat(targetLength / padString.length) : padString;
      }
      return padString.slice(0, targetLength) + String(this);
    };
  }

  if (!String.prototype.trim) {
    String.prototype.trim = function () {
      return this.replace(/^\s+|\s+$/g, "");
    };
  }

  var currentExitSessionId = null;
  var lastReceiptUrl = null;
  var autoResetTimer = null;

  function padZero(num) {
    return (num < 10 ? "0" : "") + num;
  }

  // Web Audio API tactile feedback with safe fallback
  function playSound(type) {
    try {
      var AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      var ctx = new AudioCtx();
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      if (type === "success") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(587.33, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15);
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
        osc.start(0);
        osc.stop(ctx.currentTime + 0.2);
      } else if (type === "checkout") {
        osc.type = "triangle";
        osc.frequency.setValueAtTime(523.25, ctx.currentTime);
        osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.08);
        osc.frequency.setValueAtTime(783.99, ctx.currentTime + 0.16);
        osc.frequency.setValueAtTime(1046.50, ctx.currentTime + 0.24);
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
        osc.start(0);
        osc.stop(ctx.currentTime + 0.35);
      } else if (type === "error") {
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(220, ctx.currentTime);
        osc.frequency.setValueAtTime(160, ctx.currentTime + 0.1);
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
        osc.start(0);
        osc.stop(ctx.currentTime + 0.25);
      }
    } catch (e) {
      // AudioContext unavailable or blocked
    }
  }

  // 100% ES5 Clock with no ES6+ dependencies and no complex Intl options
  function updateLiveClock() {
    var el = document.getElementById("live-clock");
    if (!el) return;

    var now = new Date();
    var hours = now.getHours();
    var minutes = now.getMinutes();
    var seconds = now.getSeconds();
    var isPM = hours >= 12;
    var ampm = isPM ? "م" : "ص";

    hours = hours % 12;
    hours = hours ? hours : 12;

    var timeStr = padZero(hours) + ":" + padZero(minutes) + ":" + padZero(seconds);
    var arabicDigits = {
      "0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤",
      "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩"
    };

    var arabicTime = "";
    for (var i = 0; i < timeStr.length; i++) {
      var c = timeStr.charAt(i);
      arabicTime += arabicDigits[c] ? arabicDigits[c] : c;
    }

    el.textContent = arabicTime + " " + ampm;
  }

  function startClock() {
    updateLiveClock();
    setInterval(updateLiveClock, 1000);
  }

  function initDirectPOSScanner() {
    var input = document.getElementById("card-code-input");
    if (!input) return;

    function maintainFocus() {
      if (document.activeElement && (
        document.activeElement.tagName === "INPUT" ||
        document.activeElement.tagName === "BUTTON" ||
        document.activeElement.tagName === "TEXTAREA"
      )) {
        return;
      }
      input.focus();
    }

    document.addEventListener("click", function () {
      setTimeout(maintainFocus, 100);
    });

    maintainFocus();

    // Keyboard shortcuts (Escape, Enter, P)
    document.addEventListener("keydown", function (e) {
      var key = e.key || "";
      var code = e.keyCode || e.which;

      if (key === "Escape" || key === "Esc" || code === 27) {
        resetCustomerDisplay();
      } else if (key === "Enter" || code === 13 || key === "p" || key === "P" || code === 80) {
        var exitBox = document.getElementById("exit-display-box");
        if (exitBox && exitBox.className.indexOf("hidden") === -1 && lastReceiptUrl) {
          if ((key === "Enter" || code === 13) && input && input.value && input.value.replace(/^\s+|\s+$/g, "").length > 0) {
            return;
          }
          if (e.preventDefault) e.preventDefault();
          else e.returnValue = false;
          printLastReceipt();
        }
      }
    });

    // Auto poll session count every 20 seconds
    setInterval(refreshRecentSessions, 20000);
  }

  function handleDirectScan(e) {
    if (e) {
      if (e.preventDefault) e.preventDefault();
      else e.returnValue = false;
    }

    var input = document.getElementById("card-code-input");
    var spinner = document.getElementById("scan-spinner");
    if (!input) return;

    var cardCode = input.value ? input.value.replace(/^\s+|\s+$/g, "") : "";
    if (!cardCode) return;

    dismissError();
    if (autoResetTimer) {
      clearTimeout(autoResetTimer);
      autoResetTimer = null;
    }

    if (spinner) {
      spinner.className = spinner.className.replace(/\bhidden\b/g, "").replace(/\s+/g, " ");
    }

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/ui/operator/api/scan", true);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    xhr.setRequestHeader("Accept", "application/json");

    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4) {
        if (spinner) {
          if (spinner.className.indexOf("hidden") === -1) {
            spinner.className += " hidden";
          }
        }

        var data = null;
        try {
          data = JSON.parse(xhr.responseText);
        } catch (parseErr) {
          data = null;
        }

        if (xhr.status >= 200 && xhr.status < 300 && data && data.success) {
          if (data.type === "entry") {
            playSound("success");
            showEntrySuccess(data);
            input.value = "";
            refreshRecentSessions();
          } else if (data.type === "exit_completed" || data.type === "exit_preview") {
            playSound("checkout");
            showExitCompleted(data);
            input.value = "";
            refreshRecentSessions();
          } else {
            playSound("success");
            input.value = "";
            refreshRecentSessions();
          }
        } else {
          playSound("error");
          var errMsg = (data && data.error) ? data.error : "تعذر إتمام العملية";
          showError(errMsg);
          if (input.select) input.select();
        }
      }
    };

    xhr.onerror = function () {
      if (spinner) {
        if (spinner.className.indexOf("hidden") === -1) {
          spinner.className += " hidden";
        }
      }
      playSound("error");
      showError("حدث خطأ في الاتصال بالخادم. يرجى إعادة المحاولة.");
    };

    xhr.send(JSON.stringify({ card_code: cardCode }));
  }

  function showExitCompleted(data) {
    currentExitSessionId = data.session_id;
    lastReceiptUrl = data.receipt_url || null;

    var standbyBox = document.getElementById("standby-display");
    var exitBox = document.getElementById("exit-display-box");
    var entryBox = document.getElementById("entry-display-box");

    if (!exitBox) return;

    if (standbyBox) standbyBox.classList.add("hidden");
    if (entryBox) entryBox.classList.add("hidden");
    exitBox.classList.remove("hidden");

    var priceEl = document.getElementById("exit-huge-price");
    var badgeText = document.getElementById("exit-badge-text");
    var cardCodeEl = document.getElementById("exit-card-code");
    var plateEl = document.getElementById("exit-plate-number");
    var entryTimeEl = document.getElementById("exit-entry-time");
    var durationEl = document.getElementById("exit-duration");
    var rateLabelEl = document.getElementById("exit-rate-label");

    if (priceEl) priceEl.textContent = data.total_egp || "0.00";
    if (cardCodeEl) cardCodeEl.textContent = data.card_code || "—";
    if (entryTimeEl) entryTimeEl.textContent = data.entry_time || "—";
    if (durationEl) durationEl.textContent = data.duration_display || "—";
    if (rateLabelEl) {
      rateLabelEl.textContent = data.is_subscribed
        ? "اشتراك معتمد (مجاني)"
        : (data.rate_label || "عادي") + " (" + (data.rate_per_hour || "") + ")";
    }

    if (badgeText) {
      badgeText.textContent = data.is_subscribed
        ? "مشترك معتمد — خروج مجاني"
        : "تم تأكيد الخروج بنجاح — المبلغ المستحق";
    }

    if (plateEl) {
      plateEl.textContent = data.plate_number || "—";
    }

    var input = document.getElementById("card-code-input");
    if (input) {
      input.focus();
    }
  }

  function printLastReceipt() {
    if (!lastReceiptUrl) return;
    try {
      window.open(lastReceiptUrl, "_blank", "width=420,height=600");
    } catch (e) {
      // Popup blocked
    }
  }

  function showEntrySuccess(data) {
    var standbyBox = document.getElementById("standby-display");
    var exitBox = document.getElementById("exit-display-box");
    var entryBox = document.getElementById("entry-display-box");

    if (!entryBox) return;

    if (standbyBox) standbyBox.classList.add("hidden");
    if (exitBox) exitBox.classList.add("hidden");
    entryBox.classList.remove("hidden");

    var cardCodeEl = document.getElementById("entry-card-code");
    var entryTimeEl = document.getElementById("entry-time");
    var subRow = document.getElementById("entry-subscriber-box");
    var subNameEl = document.getElementById("entry-subscriber-name");
    var plateBox = document.getElementById("entry-plate-container");
    var plateText = document.getElementById("entry-plate-text");
    var titleText = document.getElementById("entry-title-text");

    if (cardCodeEl) cardCodeEl.textContent = data.card_code || "—";
    if (entryTimeEl) entryTimeEl.textContent = data.entry_time || "—";

    if (data.is_subscribed && data.subscription) {
      if (titleText) titleText.textContent = "تم تسجيل دخول المشترك";
      if (subRow && subNameEl) {
        subNameEl.textContent = data.subscription.subscriber_name + " (" + data.subscription.plan_label + ")";
        subRow.classList.remove("hidden");
      }
      if (plateBox && plateText && data.subscription.plate_number) {
        plateText.textContent = data.subscription.plate_number;
        plateBox.classList.remove("hidden");
      }
    } else {
      if (titleText) titleText.textContent = "تم تسجيل الدخول بنجاح";
      if (subRow) subRow.classList.add("hidden");
      if (plateBox) plateBox.classList.add("hidden");
    }

    autoResetTimer = setTimeout(function () {
      resetCustomerDisplay();
    }, 4000);
  }

  function resetCustomerDisplay() {
    currentExitSessionId = null;
    lastReceiptUrl = null;
    if (autoResetTimer) {
      clearTimeout(autoResetTimer);
      autoResetTimer = null;
    }

    var standbyBox = document.getElementById("standby-display");
    var exitBox = document.getElementById("exit-display-box");
    var entryBox = document.getElementById("entry-display-box");

    if (exitBox) exitBox.classList.add("hidden");
    if (entryBox) entryBox.classList.add("hidden");
    if (standbyBox) standbyBox.classList.remove("hidden");

    var input = document.getElementById("card-code-input");
    if (input) {
      input.value = "";
      input.focus();
    }
  }

  function showError(msg) {
    var box = document.getElementById("status-error-box");
    var msgEl = document.getElementById("error-message");
    if (box && msgEl) {
      msgEl.textContent = msg;
      box.classList.remove("hidden");
    }
  }

  function dismissError() {
    var box = document.getElementById("status-error-box");
    if (box) box.classList.add("hidden");
  }

  function refreshRecentSessions() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/ui/operator/api/recent-sessions", true);
    xhr.setRequestHeader("Accept", "application/json");

    xhr.onreadystatechange = function () {
      if (xhr.readyState === 4 && xhr.status >= 200 && xhr.status < 300) {
        var data = null;
        try {
          data = JSON.parse(xhr.responseText);
        } catch (e) {
          return;
        }

        if (!data || !data.sessions) return;

        var countEl = document.getElementById("session-count");
        if (countEl && typeof data.total === "number") {
          countEl.textContent = data.total;
        }

        var tbody = document.getElementById("recent-sessions-tbody");
        if (!tbody) return;

        if (data.sessions.length === 0) {
          tbody.innerHTML = '<tr><td colspan="4" class="py-4 text-center text-xs text-slate-400">لا توجد عمليات مسجلة بعد في هذه الوردية.</td></tr>';
          return;
        }

        var html = "";
        for (var i = 0; i < data.sessions.length; i++) {
          var s = data.sessions[i];
          var exitStatus = s.exit_time
            ? s.exit_time
            : '<span class="text-emerald-400 font-bold bg-emerald-950/80 px-2.5 py-0.5 rounded-full border border-emerald-500/40 text-xs">داخل الجراج</span>';
          var amount = s.amount_formatted
            ? '<span class="font-bold text-emerald-400 font-digital text-sm">' + s.amount_formatted + '</span>'
            : '<span class="text-slate-500 font-bold">—</span>';

          html += '<tr class="border-b border-slate-800/60 hover:bg-slate-800/40 transition">' +
            '<td class="py-2 px-3 font-digital text-slate-200 font-bold text-sm">' + (s.card_code || "—") + '</td>' +
            '<td class="py-2 px-3 text-slate-300 font-digital text-xs">' + (s.entry_time || "—") + '</td>' +
            '<td class="py-2 px-3 text-slate-300 font-digital text-xs">' + exitStatus + '</td>' +
            '<td class="py-2 px-3 font-digital">' + amount + '</td>' +
            '</tr>';
        }
        tbody.innerHTML = html;
      }
    };

    xhr.send(null);
  }

  // Export functions to window
  window.startClock = startClock;
  window.updateLiveClock = updateLiveClock;
  window.initDirectPOSScanner = initDirectPOSScanner;
  window.handleDirectScan = handleDirectScan;
  window.resetCustomerDisplay = resetCustomerDisplay;
  window.printLastReceipt = printLastReceipt;
  window.dismissError = dismissError;
  window.refreshRecentSessions = refreshRecentSessions;

  // Auto initialize clock immediately
  startClock();
})();

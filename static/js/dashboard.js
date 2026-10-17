// static/js/dashboard.js — Fast Direct POS Scanner & Customer Display

let currentExitSessionId = null;
let lastReceiptUrl = null;
let autoResetTimer = null;

// Simple Web Audio API Synthesizer for pleasant tactile feedback
function playSound(type) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (type === 'success') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.15); // A5
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
      osc.start();
      osc.stop(ctx.currentTime + 0.2);
    } else if (type === 'checkout') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(523.25, ctx.currentTime); // C5
      osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.08); // E5
      osc.frequency.setValueAtTime(783.99, ctx.currentTime + 0.16); // G5
      osc.frequency.setValueAtTime(1046.50, ctx.currentTime + 0.24); // C6
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } else if (type === 'error') {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(220, ctx.currentTime);
      osc.frequency.setValueAtTime(160, ctx.currentTime + 0.1);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
      osc.start();
      osc.stop(ctx.currentTime + 0.25);
    }
  } catch (e) {
    // AudioContext may be blocked before first user gesture
  }
}

function startClock() {
  const arabicDigits = {
    '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
    '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
  };

  function update() {
    const el = document.getElementById("live-clock");
    if (!el) return;

    try {
      const now = new Date();
      const formatter = new Intl.DateTimeFormat("en-US", {
        timeZone: "Africa/Cairo",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true
      });

      const parts = formatter.formatToParts(now);
      let hour = "", minute = "", second = "", dayPeriod = "";
      for (const part of parts) {
        if (part.type === "hour") hour = part.value;
        if (part.type === "minute") minute = part.value;
        if (part.type === "second") second = part.value;
        if (part.type === "dayPeriod") dayPeriod = part.value;
      }

      const isPM = (dayPeriod && dayPeriod.toUpperCase() === "PM");
      const ampmArabic = isPM ? "م" : "ص";
      const timeFormatted = `${hour}:${minute}:${second}`;
      const arabicTime = timeFormatted.split("").map(c => arabicDigits[c] || c).join("");
      el.textContent = `${arabicTime} ${ampmArabic}`;
    } catch (e) {
      const now = new Date();
      let hours = now.getHours();
      const ampm = hours >= 12 ? "م" : "ص";
      hours = hours % 12;
      hours = hours ? hours : 12;
      const hh = String(hours).padStart(2, "0");
      const mm = String(now.getMinutes()).padStart(2, "0");
      const ss = String(now.getSeconds()).padStart(2, "0");
      const formatted = hh + ":" + mm + ":" + ss;
      const arabic = formatted.split("").map(c => arabicDigits[c] || c).join("");
      el.textContent = arabic + " " + ampm;
    }
  }

  update();
  setInterval(update, 1000);
}

function initDirectPOSScanner() {
  const input = document.getElementById("card-code-input");
  if (!input) return;

  function maintainFocus() {
    if (document.activeElement && (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "BUTTON" || document.activeElement.tagName === "TEXTAREA")) {
      return;
    }
    input.focus();
  }

  document.addEventListener("click", () => {
    setTimeout(maintainFocus, 100);
  });

  maintainFocus();

  // Keyboard shortcut listener: Enter / P / Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      resetCustomerDisplay();
    } else if (e.key === "Enter" || e.key === "p" || e.key === "P") {
      const exitBox = document.getElementById("exit-display-box");
      if (exitBox && !exitBox.classList.contains("hidden") && lastReceiptUrl) {
        // If typing inside the input, Enter submits scan unless input is empty
        if (e.key === "Enter" && input && input.value.trim().length > 0) {
          return;
        }
        e.preventDefault();
        printLastReceipt();
      }
    }
  });

  // Auto poll session count every 20 seconds
  setInterval(refreshRecentSessions, 20000);
}

async function handleDirectScan(e) {
  if (e) e.preventDefault();
  const input = document.getElementById("card-code-input");
  const spinner = document.getElementById("scan-spinner");
  if (!input) return;

  const cardCode = input.value.trim();
  if (!cardCode) return;

  dismissError();
  if (autoResetTimer) clearTimeout(autoResetTimer);

  if (spinner) spinner.classList.remove("hidden");

  try {
    const res = await fetch("/ui/operator/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ card_code: cardCode })
    });

    const data = await res.json();
    if (spinner) spinner.classList.add("hidden");

    if (!res.ok || !data.success) {
      playSound('error');
      showError(data.error || "تعذر إتمام العملية");
      input.select();
      return;
    }

    // Success response handling
    if (data.type === "entry") {
      playSound('success');
      showEntrySuccess(data);
      input.value = "";
      refreshRecentSessions();
    } else if (data.type === "exit_completed" || data.type === "exit_preview") {
      playSound('checkout');
      showExitCompleted(data);
      input.value = "";
      refreshRecentSessions();
    }

  } catch (err) {
    if (spinner) spinner.classList.add("hidden");
    playSound('error');
    showError("حدث خطأ في الاتصال بالخادم. يرجى إعادة المحاولة.");
  }
}

function showExitCompleted(data) {
  currentExitSessionId = data.session_id;
  lastReceiptUrl = data.receipt_url || null;

  const standbyBox = document.getElementById("standby-display");
  const exitBox = document.getElementById("exit-display-box");
  const entryBox = document.getElementById("entry-display-box");

  if (!exitBox) return;

  if (standbyBox) standbyBox.classList.add("hidden");
  if (entryBox) entryBox.classList.add("hidden");
  exitBox.classList.remove("hidden");

  // Populate Customer Big-Screen Details
  const priceEl = document.getElementById("exit-huge-price");
  const badgeText = document.getElementById("exit-badge-text");
  const cardCodeEl = document.getElementById("exit-card-code");
  const plateEl = document.getElementById("exit-plate-number");
  const entryTimeEl = document.getElementById("exit-entry-time");
  const durationEl = document.getElementById("exit-duration");
  const rateLabelEl = document.getElementById("exit-rate-label");

  if (priceEl) priceEl.textContent = data.total_egp || "0.00";
  if (cardCodeEl) cardCodeEl.textContent = data.card_code || "—";
  if (entryTimeEl) entryTimeEl.textContent = data.entry_time || "—";
  if (durationEl) durationEl.textContent = data.duration_display || "—";
  if (rateLabelEl) rateLabelEl.textContent = data.is_subscribed ? "اشتراك معتمد (مجاني)" : `${data.rate_label || 'عادي'} (${data.rate_per_hour || ''})`;

  if (badgeText) {
    badgeText.textContent = data.is_subscribed ? "مشترك معتمد — خروج مجاني" : "تم تأكيد الخروج بنجاح — المبلغ المستحق";
  }

  if (plateEl) {
    plateEl.textContent = data.plate_number || "—";
  }

  // Refocus input for immediate next car scan
  const input = document.getElementById("card-code-input");
  if (input) {
    input.focus();
  }
}

function printLastReceipt() {
  if (!lastReceiptUrl) return;
  try {
    window.open(lastReceiptUrl, '_blank', 'width=420,height=600');
  } catch (e) {
    console.error("Popup blocked", e);
  }
}

function showEntrySuccess(data) {
  const standbyBox = document.getElementById("standby-display");
  const exitBox = document.getElementById("exit-display-box");
  const entryBox = document.getElementById("entry-display-box");

  if (!entryBox) return;

  if (standbyBox) standbyBox.classList.add("hidden");
  if (exitBox) exitBox.classList.add("hidden");
  entryBox.classList.remove("hidden");

  const cardCodeEl = document.getElementById("entry-card-code");
  const entryTimeEl = document.getElementById("entry-time");
  const subRow = document.getElementById("entry-subscriber-box");
  const subNameEl = document.getElementById("entry-subscriber-name");
  const plateBox = document.getElementById("entry-plate-container");
  const plateText = document.getElementById("entry-plate-text");
  const titleText = document.getElementById("entry-title-text");

  if (cardCodeEl) cardCodeEl.textContent = data.card_code || "—";
  if (entryTimeEl) entryTimeEl.textContent = data.entry_time || "—";

  if (data.is_subscribed && data.subscription) {
    titleText.textContent = "تم تسجيل دخول المشترك";
    if (subRow && subNameEl) {
      subNameEl.textContent = `${data.subscription.subscriber_name} (${data.subscription.plan_label})`;
      subRow.classList.remove("hidden");
    }
    if (plateBox && plateText && data.subscription.plate_number) {
      plateText.textContent = data.subscription.plate_number;
      plateBox.classList.remove("hidden");
    }
  } else {
    titleText.textContent = "تم تسجيل الدخول بنجاح";
    if (subRow) subRow.classList.add("hidden");
    if (plateBox) plateBox.classList.add("hidden");
  }

  // Auto-reset after 4 seconds for entry
  autoResetTimer = setTimeout(() => {
    resetCustomerDisplay();
  }, 4000);
}

function resetCustomerDisplay() {
  currentExitSessionId = null;
  lastReceiptUrl = null;
  if (autoResetTimer) clearTimeout(autoResetTimer);

  const standbyBox = document.getElementById("standby-display");
  const exitBox = document.getElementById("exit-display-box");
  const entryBox = document.getElementById("entry-display-box");

  if (exitBox) exitBox.classList.add("hidden");
  if (entryBox) entryBox.classList.add("hidden");
  if (standbyBox) standbyBox.classList.remove("hidden");

  const input = document.getElementById("card-code-input");
  if (input) {
    input.value = "";
    input.focus();
  }
}

function showError(msg) {
  const box = document.getElementById("status-error-box");
  const msgEl = document.getElementById("error-message");
  if (box && msgEl) {
    msgEl.textContent = msg;
    box.classList.remove("hidden");
  }
}

function dismissError() {
  const box = document.getElementById("status-error-box");
  if (box) box.classList.add("hidden");
}

async function refreshRecentSessions() {
  try {
    const res = await fetch("/ui/operator/api/recent-sessions");
    const data = await res.json();
    if (!data || !data.sessions) return;

    const countEl = document.getElementById("session-count");
    if (countEl && typeof data.total === "number") {
      countEl.textContent = data.total;
    }

    const tbody = document.getElementById("recent-sessions-tbody");
    if (!tbody) return;

    if (data.sessions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="py-8 text-center text-xs text-slate-500">لا توجد عمليات مسجلة بعد في هذه الوردية.</td></tr>`;
      return;
    }

    let html = "";
    for (const s of data.sessions) {
      const exitStatus = s.exit_time ? s.exit_time : `<span class="text-emerald-400 font-bold bg-emerald-950/80 px-3 py-1 rounded-full border border-emerald-500/40 text-xs">داخل</span>`;
      const amount = s.amount_formatted ? `<span class="font-bold text-emerald-400 font-digital text-sm">${s.amount_formatted}</span>` : `<span class="text-slate-500 font-bold">—</span>`;
      html += `
        <tr class="border-b border-slate-800/50 hover:bg-slate-800/40 transition">
          <td class="py-2.5 px-2.5 font-digital text-slate-300 font-bold">${s.card_code}</td>
          <td class="py-2.5 px-2.5 text-slate-400 font-digital text-[11px]">${s.entry_time || '—'}</td>
          <td class="py-2.5 px-2.5 text-slate-400 font-digital text-[11px]">${exitStatus}</td>
          <td class="py-2.5 px-2.5 font-digital">${amount}</td>
        </tr>
      `;
    }
    tbody.innerHTML = html;
  } catch (e) {
    // Silently ignore background polling errors
  }
}

startClock();



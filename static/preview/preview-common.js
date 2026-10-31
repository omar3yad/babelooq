// Preview Demo Common JavaScript - Guaranteed Mobile Responsive

function initPreviewBar(activePage) {
  const isMobile = window.innerWidth <= 768;

  // 1. Desktop Floating Bar (Created ONLY on desktop or hidden by default on mobile)
  if (!document.getElementById('preview-floating-bar')) {
    const bar = document.createElement('div');
    bar.id = 'preview-floating-bar';
    if (isMobile) {
      bar.style.display = 'none';
    }
    bar.innerHTML = `
      <div class="preview-pill-badge hidden lg:inline-flex">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>وضع المعاينة والعرض</span>
      </div>

      <div class="flex items-center gap-1.5 flex-wrap">
        <a href="index.html" class="preview-nav-btn ${activePage === 'home' ? 'active' : ''}">
          <span>🏠 الرئيسية</span>
        </a>
        <a href="operator_entry.html" class="preview-nav-btn ${activePage === 'entry' ? 'active' : ''}">
          <span>🖥️ عامل دخول كمبيوتر</span>
        </a>
        <a href="operator_exit.html" class="preview-nav-btn ${activePage === 'exit' ? 'active' : ''}">
          <span>🖥️ عامل خروج كمبيوتر</span>
        </a>
        <a href="pos_device.html" class="preview-nav-btn ${activePage === 'pos' ? 'active' : ''}">
          <span>📱 جهاز POS</span>
        </a>
        <a href="admin_dashboard.html" class="preview-nav-btn ${activePage === 'admin' ? 'active' : ''}">
          <span>👔 لوحة المدير</span>
        </a>
      </div>

      <button type="button" onclick="toggleFloatingBar()" class="text-slate-400 hover:text-white p-1 rounded-full text-xs font-bold transition mr-1" title="تصغير/إظهار">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    `;
    document.body.appendChild(bar);
  }

  // 2. Mobile Floating Button (FAB)
  if (!document.getElementById('preview-mobile-fab')) {
    const fab = document.createElement('button');
    fab.id = 'preview-mobile-fab';
    fab.type = 'button';
    fab.onclick = openMobileDrawer;
    fab.innerHTML = `
      <span class="text-base">🧭</span>
      <span>تنقل بين الشاشات</span>
    `;
    document.body.appendChild(fab);
  }

  // 3. Mobile Drawer Bottom Sheet
  if (!document.getElementById('preview-mobile-drawer')) {
    const drawer = document.createElement('div');
    drawer.id = 'preview-mobile-drawer';
    drawer.onclick = function(e) {
      if (e.target === drawer) closeMobileDrawer();
    };
    drawer.innerHTML = `
      <div class="mobile-drawer-sheet" onclick="event.stopPropagation()">
        <div class="flex items-center justify-between border-b border-slate-800 pb-2.5 mb-3">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
            <span class="text-sm font-black text-white">اختر الشاشة للانتقال إليها</span>
          </div>
          <button type="button" onclick="closeMobileDrawer()" class="text-slate-400 hover:text-white p-1 rounded-lg">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex flex-col gap-2">
          <a href="index.html" class="flex items-center justify-between p-2.5 rounded-xl border border-slate-800 ${activePage === 'home' ? 'bg-cyan-600/25 border-cyan-500 text-cyan-300 font-bold' : 'bg-slate-900 text-slate-200'}">
            <div class="flex items-center gap-2.5">
              <span class="text-lg">🏠</span>
              <div>
                <strong class="block text-xs sm:text-sm">البوابة الرئيسية (Hub)</strong>
                <span class="text-[10px] text-slate-400">صفحة الاختيار والمقدمة</span>
              </div>
            </div>
            <span>←</span>
          </a>

          <a href="operator_entry.html" class="flex items-center justify-between p-2.5 rounded-xl border border-slate-800 ${activePage === 'entry' ? 'bg-emerald-600/25 border-emerald-500 text-emerald-300 font-bold' : 'bg-slate-900 text-slate-200'}">
            <div class="flex items-center gap-2.5">
              <span class="text-lg">🖥️</span>
              <div>
                <strong class="block text-xs sm:text-sm">عامل دخول كمبيوتر</strong>
                <span class="text-[10px] text-slate-400">بوابة 1 • كاميرا LPR واللوحة المصرية</span>
              </div>
            </div>
            <span>←</span>
          </a>

          <a href="operator_exit.html" class="flex items-center justify-between p-2.5 rounded-xl border border-slate-800 ${activePage === 'exit' ? 'bg-cyan-600/25 border-cyan-500 text-cyan-300 font-bold' : 'bg-slate-900 text-slate-200'}">
            <div class="flex items-center gap-2.5">
              <span class="text-lg">🖥️</span>
              <div>
                <strong class="block text-xs sm:text-sm">عامل خروج كمبيوتر</strong>
                <span class="text-[10px] text-slate-400">بوابة 2 • السعر الرقمي وطباعة الإيصال</span>
              </div>
            </div>
            <span>←</span>
          </a>

          <a href="pos_device.html" class="flex items-center justify-between p-2.5 rounded-xl border border-slate-800 ${activePage === 'pos' ? 'bg-amber-600/25 border-amber-500 text-amber-300 font-bold' : 'bg-slate-900 text-slate-200'}">
            <div class="flex items-center gap-2.5">
              <span class="text-lg">📱</span>
              <div>
                <strong class="block text-xs sm:text-sm">جهاز POS المحمول</strong>
                <span class="text-[10px] text-slate-400">كاشير محمول Sunmi لمس وطباعة</span>
              </div>
            </div>
            <span>←</span>
          </a>

          <a href="admin_dashboard.html" class="flex items-center justify-between p-2.5 rounded-xl border border-slate-800 ${activePage === 'admin' ? 'bg-indigo-600/25 border-indigo-500 text-indigo-300 font-bold' : 'bg-slate-900 text-slate-200'}">
            <div class="flex items-center gap-2.5">
              <span class="text-lg">👔</span>
              <div>
                <strong class="block text-xs sm:text-sm">لوحة تحكم المدير</strong>
                <span class="text-[10px] text-slate-400">الورديات • الإيرادات • الحركات • الأسعار</span>
              </div>
            </div>
            <span>←</span>
          </a>
        </div>
      </div>
    `;
    document.body.appendChild(drawer);
  }

  // Handle resize events
  window.addEventListener('resize', () => {
    const bar = document.getElementById('preview-floating-bar');
    const fab = document.getElementById('preview-mobile-fab');
    if (window.innerWidth <= 768) {
      if (bar) bar.style.display = 'none';
      if (fab) fab.style.display = 'inline-flex';
    } else {
      if (bar) bar.style.display = 'flex';
      if (fab) fab.style.display = 'none';
    }
  });
}

function openMobileDrawer() {
  const d = document.getElementById('preview-mobile-drawer');
  if (d) d.classList.add('active');
}

function closeMobileDrawer() {
  const d = document.getElementById('preview-mobile-drawer');
  if (d) d.classList.remove('active');
}

function toggleFloatingBar() {
  const bar = document.getElementById('preview-floating-bar');
  if (bar) bar.classList.toggle('minimized');
}

// Digital Live Clock
function startPreviewClock(elementId) {
  const el = document.getElementById(elementId || 'live-clock');
  if (!el) return;

  function update() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    el.textContent = `${h}:${m}:${s}`;
  }
  update();
  setInterval(update, 1000);
}

// Thermal Receipt Modal
function showThermalReceipt(data) {
  const defaults = {
    garageName: "جراج باب اللوق الذكي",
    companyName: "garage4u",
    sessionId: "00028491",
    cardCode: "10048291",
    plateNumber: "س ص ع ١٩٨٤",
    gate: "بوابة الخروج الرئيسية (2B)",
    operator: "محمود حسن",
    entryTime: "2026-10-31 15:10:00",
    exitTime: "2026-10-31 17:25:00",
    duration: "ساعتان و 15 دقيقة",
    rateType: "تعريفة الساعات العادية",
    amount: "45.00 ج.م"
  };

  const info = Object.assign({}, defaults, data);

  let modal = document.getElementById('preview-receipt-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'preview-receipt-modal';
    modal.className = 'fixed inset-0 z-[999999] bg-slate-950/85 backdrop-blur-sm flex items-center justify-center p-4 transition-all duration-300';
    document.body.appendChild(modal);
  }

  modal.innerHTML = `
    <div class="relative flex flex-col items-center max-h-[95vh] overflow-y-auto">
      <div class="receipt-paper p-5 sm:p-6 text-black my-4 text-xs sm:text-sm font-mono shadow-2xl rounded border border-gray-300">
        <div class="text-center font-bold text-base tracking-wider mb-1">${info.companyName}</div>
        <div class="text-center font-bold text-xs sm:text-sm text-gray-700">${info.garageName}</div>
        <div class="border-b border-dashed border-gray-400 my-2"></div>
        <div class="text-center font-bold text-xs text-gray-800">إيصال تحصيل مغادرة سيارة</div>
        <div class="text-center text-[11px] text-gray-500 font-mono">رقم العملية: ${info.sessionId}</div>
        <div class="border-b border-dashed border-gray-400 my-2"></div>

        <div class="space-y-1 text-xs">
          <div class="flex justify-between"><span>رقم الكارت:</span><span class="font-bold">${info.cardCode}</span></div>
          <div class="flex justify-between"><span>رقم اللوحة:</span><span class="font-bold">${info.plateNumber}</span></div>
          <div class="flex justify-between"><span>البوابة:</span><span>${info.gate}</span></div>
          <div class="flex justify-between"><span>المشغل:</span><span>${info.operator}</span></div>
        </div>

        <div class="border-b border-dashed border-gray-400 my-2"></div>

        <div class="space-y-1 text-xs">
          <div class="flex justify-between"><span>وقت الدخول:</span><span>${info.entryTime}</span></div>
          <div class="flex justify-between"><span>وقت الخروج:</span><span>${info.exitTime}</span></div>
          <div class="flex justify-between"><span>مدة الانتظار:</span><span class="font-bold">${info.duration}</span></div>
          <div class="flex justify-between"><span>نوع التسعيرة:</span><span>${info.rateType}</span></div>
        </div>

        <div class="border-b-2 border-gray-900 my-2.5"></div>

        <div class="flex justify-between items-center text-sm sm:text-base font-black">
          <span>المبلغ الإجمالي:</span>
          <span class="text-base sm:text-lg">${info.amount}</span>
        </div>

        <div class="border-b border-dashed border-gray-400 my-2.5"></div>

        <!-- Simulated Barcode -->
        <div class="flex flex-col items-center justify-center my-2">
          <div class="h-8 w-40 bg-gradient-to-r from-black via-white to-black flex items-center justify-center" style="background: repeating-linear-gradient(90deg, #000 0px, #000 2px, #fff 2px, #fff 4px, #000 4px, #000 7px, #fff 7px, #fff 9px);"></div>
          <span class="text-[10px] tracking-widest font-mono text-gray-600 mt-1">${info.cardCode}</span>
        </div>

        <div class="text-center text-[10px] text-gray-500 mt-1">
          نتمنى لكم يوماً سعيداً • شكراً لزيارتكم
        </div>
      </div>

      <div class="flex items-center gap-2 sm:gap-3 mt-1">
        <button type="button" onclick="window.print()" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-4 rounded-xl text-xs sm:text-sm flex items-center gap-1.5 shadow-lg transition">
          <span>🖨️ طباعة فورية</span>
        </button>
        <button type="button" onclick="closeThermalReceipt()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold py-2 px-3.5 rounded-xl text-xs sm:text-sm transition">
          إغلاق (Esc)
        </button>
      </div>
    </div>
  `;

  modal.style.display = 'flex';

  const escHandler = (e) => {
    if (e.key === 'Escape') {
      closeThermalReceipt();
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);
}

function closeThermalReceipt() {
  const modal = document.getElementById('preview-receipt-modal');
  if (modal) modal.style.display = 'none';
}

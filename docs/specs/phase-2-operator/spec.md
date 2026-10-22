# Phase 2 Specification — Operator Application & Core Business Logic

> **Version:** 1.0
> **Scope:** Card scanning workflow, session lifecycle, pricing engine, shift management,
> 58mm receipt printing, and the complete operator UI on the Sunmi V2 POS terminal.
> **Prerequisite reading:** `constitution.md`, `plan.md`, `spec_phase1.md`
> **Out of scope:** Admin dashboard, reporting, multi-currency, token refresh,
> rate limiting, Docker deployment.

---

## 1. User Stories & Acceptance Criteria

### 1.1 Shift Management

---

**US-101 — Start a Shift**
> *As an operator, I want to open my shift before I start processing cars, so that all
> sessions I create are linked to my shift and my cash collection is tracked separately.*

**Acceptance Criteria:**
- The operator dashboard shows a prominent "ابدأ الشيفت" button when no shift is open.
- `POST /api/v1/shifts/` creates a shift record with `started_at = utcnow()`,
  `gate_number` from the operator's profile, and `opening_cash_egp` entered by the
  operator.
- An operator with an already-open shift cannot open a second one; the system returns
  `409` with code `SHIFT_ALREADY_OPEN`.
- After a successful shift start, the operator is redirected to the main gate dashboard
  showing two large buttons: **[دخول]** and **[خروج]**.
- The shift start is recorded in `audit_logs` with action `SHIFT_OPENED`.

---

**US-102 — End a Shift**
> *As an operator, I want to close my shift at the end of my work period and enter the
> cash I collected, so that the admin can reconcile totals.*

**Acceptance Criteria:**
- `PATCH /api/v1/shifts/{id}/close` accepts `closing_cash_egp` (integer, piastres).
- The response includes a shift summary: total sessions, total amount collected
  (computed from sessions), cash entered, and the difference (discrepancy).
- A shift with open (ACTIVE) sessions can still be closed; those sessions are flagged
  in the summary as unresolved.
- `ended_at` is set to `utcnow()` on close.
- The shift close is recorded in `audit_logs` with action `SHIFT_CLOSED`.
- After closing, the operator is redirected to `/ui/login` (session ends with shift).

---

**US-103 — Gate Dashboard (Main Operator Screen)**
> *As an operator, I want a single clear screen with two large buttons — Entry and Exit
> — so that I can operate quickly without navigating menus.*

**Acceptance Criteria:**
- `GET /ui/operator/dashboard` renders within 300ms on LAN.
- Both buttons are at minimum `120px` tall and each occupies 50% of the screen width.
- The screen displays: operator name, gate number, shift start time, session count
  today, and a live clock.
- If no shift is open, the Entry and Exit buttons are disabled and a banner says
  "افتح شيفتك أولاً".
- The page auto-refreshes the session counter every 60 seconds via a lightweight
  `fetch` call (no full page reload).

---

### 1.2 Entry Flow

---

**US-104 — Scan Card on Entry**
> *As an operator, I want to scan a card barcode when a car arrives, so that the system
> creates a timed parking session without me typing anything manually.*

**Acceptance Criteria:**
- `GET /ui/operator/entry` renders a full-screen scan input: one large `<input>`
  autofocused, labelled "امسح الكرت" in Arabic, with `inputmode="none"` so the
  software keyboard does not appear (the Sunmi hardware scanner injects text directly).
- The input accepts the barcode value and auto-submits on receiving a carriage return
  (which the Sunmi scanner appends by default).
- `POST /ui/operator/entry` calls `CardService.validate_for_entry(card_code)` then
  `SessionService.open_session(card_code, operator_id, shift_id)`.
- On success: the page renders a confirmation screen showing the card code and entry
  time in large Arabic text, then automatically redirects back to the dashboard after
  3 seconds.
- On error: the page re-renders with a full-screen Arabic error message and a
  "حاول تاني" button. No redirect happens automatically on error.
- The scan input is re-focused after every submission (success or error) so the
  operator can scan the next card without tapping the screen.
- The session open is recorded in `audit_logs` with action `SESSION_OPENED`.

---

**US-105 — Optional Plate Number on Entry**
> *As an operator, I want to optionally enter a car's plate number after scanning the
> card, so that we have a secondary identifier for dispute resolution.*

**Acceptance Criteria:**
- After a successful card scan on entry, a secondary optional field appears: "رقم
  اللوحة (اختياري)" with `dir="rtl"` and `inputmode="text"`.
- If left blank and the operator presses "تأكيد بدون لوحة", the session is saved with
  `plate_number = NULL`.
- If a plate is entered, it is passed through `PlateService.normalize(plate)` before
  storage (strips whitespace, converts Eastern Arabic numerals to Western).
- The plate field is not required and its absence must never block session creation.
- Plate entry has a 10-second timeout; if the operator does not interact, the session
  is confirmed without a plate automatically.

---

### 1.3 Exit Flow

---

**US-106 — Scan Card on Exit**
> *As an operator, I want to scan the card a driver returns, so that the system
> automatically calculates the duration and fee without me doing any maths.*

**Acceptance Criteria:**
- `GET /ui/operator/exit` renders an identical full-screen scan input to the entry
  screen, labelled "امسح الكرت للخروج".
- `POST /ui/operator/exit/lookup` calls `CardService.validate_for_exit(card_code)`
  then `PricingService.calculate(session)`.
- The response renders `operator/exit_confirm.html` showing:
  - Card code.
  - Entry time (formatted: `DD/MM/YYYY HH:mm` in Arabic).
  - Exit time (current time).
  - Duration (hours and minutes in Arabic, e.g., "ساعتان و٣٥ دقيقة").
  - Itemised breakdown: first N minutes free, remaining duration, rate applied.
  - **Total amount due in large font** (EGP, Arabic-Indic numerals).
- A single large "تأكيد الدفع وطباعة الإيصال" button confirms and prints.
- `POST /ui/operator/exit/{session_id}/confirm` closes the session, frees the card,
  and redirects to the receipt page.
- The session close is recorded in `audit_logs` with action `SESSION_CLOSED`.

---

**US-107 — Print Receipt on Exit**
> *As an operator, I want the receipt to print automatically on the Sunmi V2's 58mm
> thermal printer when I confirm an exit, so that the driver gets their receipt without
> extra steps.*

**Acceptance Criteria:**
- After confirming exit, the browser is redirected to
  `GET /ui/operator/receipt/{session_id}`.
- The receipt page calls `window.print()` automatically via an inline `<script>` tag
  that runs on `DOMContentLoaded`.
- The receipt renders only within `@media print` styles defined in `static/print.css`.
- All non-receipt UI is `display: none` in print media.
- After printing, the page automatically redirects to the dashboard after 2 seconds
  via `setTimeout`.
- The operator can also tap a "طباعة مرة أخرى" button to re-trigger `window.print()`.
- `receipt_printed_at` is set to `utcnow()` on first load of this page.

---

### 1.4 Lost Card Flow

---

**US-108 — Resolve a Lost Card**
> *As an operator, I want to handle the case where a driver has lost their card, so
> that I can charge the correct penalty and close the session.*

**Acceptance Criteria:**
- The dashboard has a third button: "كرت مفقود" styled distinctly (warning colour).
- `GET /ui/operator/lost-card` renders a form with one field: plate number (required
  in this flow as the primary lookup since no card is available), plus an optional
  notes field.
- The operator enters the plate number; `SessionService.find_active_by_plate(plate)`
  returns matching active sessions.
- If multiple sessions match (same plate, different gates), a list is shown for the
  operator to choose the correct one.
- `POST /ui/operator/lost-card/{session_id}/confirm` calls
  `SessionService.resolve_lost_card(session_id, operator_id, shift_id)`.
- The fee is calculated as: `max(all_possible_hours * rate, minimum_charge) +
  lost_ticket_penalty` where `lost_ticket_penalty` is read from the active
  `PricingRule`.
- The card's status is set to `lost`.
- The session's `is_lost_card` is set to `TRUE`.
- A penalty receipt is printed (distinct template, marked "كرت مفقود").
- The action is recorded in `audit_logs` with action `LOST_CARD_RESOLVED`.

---

**US-109 — View Today's Sessions on Dashboard**
> *As an operator, I want to see a compact list of my shift's sessions at the bottom of
> the dashboard, so that I can quickly verify recent activity.*

**Acceptance Criteria:**
- The dashboard shows the last 10 sessions for the current shift in a compact table:
  card code, entry time, exit time (or "داخل" if still active), amount.
- The table is read-only; no action buttons per row.
- The table loads asynchronously and does not block the main dashboard render.
- Sessions are ordered newest first.

---

### 1.5 Pricing Configuration (Admin — referenced in Phase 2 for completeness)

---

**US-110 — View Active Pricing Rule**
> *As an operator, I want to see the current pricing rule on the exit confirmation
> screen, so that I can explain the charge to the driver if asked.*

**Acceptance Criteria:**
- The exit confirmation screen shows: hourly rate (e.g., "١٠ جنيه / ساعة"), grace
  period (e.g., "أول ١٥ دقيقة مجاناً"), and minimum charge.
- This data is read from `GET /api/v1/rates/active`.
- If no active pricing rule exists, the exit flow is blocked and an error is shown:
  "لا توجد تعريفة سعرية نشطة — تواصل مع الإدارة".

---

## 2. Functional Requirements

### 2.1 Session State Machine

A `ParkingSession` moves through exactly these states. No other transitions are valid.

                ┌─────────────┐
                │   (none)    │  Card status: available
                └──────┬──────┘
                       │  SessionService.open_session()
                       ▼
                ┌─────────────┐
                │   ACTIVE    │  Card status: in_use
                └──────┬──────┘
           ┌───────────┴────────────┐
           │                        │
           │ Session.close_exit()   │ Session.resolve_lost_card()
           ▼                        ▼
    ┌─────────────┐         ┌──────────────┐
    │  COMPLETED  │         │   LOST_CARD  │
    │             │         │              │
    │ Card:       │         │ Card: lost   │
    │ available   │         │              │
    └─────────────┘         └──────────────┘


**State Rules:**

| From | To | Trigger | Condition |
|---|---|---|---|
| — | `ACTIVE` | `open_session()` | Card must be `available` |
| `ACTIVE` | `COMPLETED` | `close_session()` | Session must be `ACTIVE` |
| `ACTIVE` | `LOST_CARD` | `resolve_lost_card()` | Session must be `ACTIVE` |
| `COMPLETED` | any | — | **Forbidden. Immutable.** |
| `LOST_CARD` | any | — | **Forbidden. Immutable.** |

The `status` field is stored as `ENUM('ACTIVE','COMPLETED','LOST_CARD')` on
`parking_sessions`. Transitions are enforced at the **service layer** and must
also be validated at the **repository layer** using a `WHERE status = 'ACTIVE'`
clause on update queries to prevent race conditions.

---

### 2.2 Card Service (`CardService`)

| ID | Requirement |
|---|---|
| FR-CARD-001 | `validate_for_entry(card_code: str) -> ParkingCard` — fetches card by `card_code`. Raises `CardNotFoundError` if not found. Raises `CardNotAvailableError` if `status != 'available'`. Returns the `ParkingCard` object. |
| FR-CARD-002 | `validate_for_exit(card_code: str) -> ParkingSession` — fetches card by `card_code`. Raises `CardNotFoundError` if not found. Fetches the active session for this card. Raises `CardHasNoActiveSessionError` if none found. Returns the `ParkingSession`. |
| FR-CARD-003 | `set_status(card: ParkingCard, status: CardStatus, db) -> ParkingCard` — updates `card.status` and `card.last_seen_at = utcnow()`. Flushes but does not commit. Caller commits. |
| FR-CARD-004 | `normalize_code(raw: str) -> str` — strips all whitespace, uppercases the string. Returns the normalized code. Raises `InvalidBarcodeFormatError` if the result is empty or contains characters outside `[A-Z0-9\-_]` or exceeds 50 characters. |
| FR-CARD-005 | All `CardService` methods call `normalize_code` on every `card_code` input before any database lookup. Raw input is never passed to a query. |
| FR-CARD-006 | `get_inventory(status: CardStatus | None, page, size) -> tuple[list[ParkingCard], int]` — returns paginated card list filtered by status if provided. |
| FR-CARD-007 | `bulk_create(codes: list[str], db) -> list[ParkingCard]` — validates each code with `normalize_code`, checks for duplicates within the list and against existing DB records, creates all valid cards in a single flush. Returns created cards. Raises `BulkCardConflictError` listing duplicate codes if any exist. |

---

### 2.3 Session Service (`SessionService`)

| ID | Requirement |
|---|---|
| FR-SESS-001 | `open_session(card_code, operator_id, shift_id, plate_number=None, db) -> ParkingSession` — calls `CardService.validate_for_entry`, creates a `ParkingSession` with `status='ACTIVE'`, `entry_time=utcnow()`, then calls `CardService.set_status(card, 'in_use')`. Both writes happen in the same transaction. Commits once. Returns the session. |
| FR-SESS-002 | `close_session(session_id, exit_operator_id, exit_shift_id, db) -> ParkingSession` — fetches session with `status='ACTIVE'` using a `SELECT ... FOR UPDATE` (or equivalent pessimistic lock). Raises `SessionNotActiveError` if not found. Calls `PricingService.calculate(session)`. Updates session: `exit_time=utcnow()`, `status='COMPLETED'`, `is_paid=True`, `amount_charged`, `duration_minutes`, `pricing_rule_id`, `exit_operator_id`, `exit_shift_id`. Calls `CardService.set_status(card, 'available')`. Commits once. |
| FR-SESS-003 | `resolve_lost_card(session_id, operator_id, shift_id, notes=None, db) -> ParkingSession` — same lock as FR-SESS-002. Calls `PricingService.calculate_lost_card(session)`. Updates session: `status='LOST_CARD'`, `is_lost_card=True`, `exit_time=utcnow()`, `amount_charged` (penalty amount), `lost_card_penalty_applied` (snapshot), `exit_operator_id`, `exit_shift_id`, `notes`. Calls `CardService.set_status(card, 'lost')`. Commits once. |
| FR-SESS-004 | `find_active_by_plate(plate: str, db) -> list[ParkingSession]` — normalizes plate via `PlateService.normalize`, queries sessions where `status='ACTIVE'` and `plate_number` matches (diacritic-insensitive). Returns list (may be empty or multiple). |
| FR-SESS-005 | `get_shift_sessions(shift_id, page, size, db) -> tuple[list[ParkingSession], int]` — returns sessions for the given shift ordered by `entry_time DESC`. |
| FR-SESS-006 | `mark_receipt_printed(session_id, db) -> None` — sets `receipt_printed_at = utcnow()` only if currently `NULL`. Idempotent on second call (does not overwrite). |

---

### 2.4 Pricing Service (`PricingService`)

| ID | Requirement |
|---|---|
| FR-PRICE-001 | `get_active_rule(db) -> PricingRule` — queries `pricing_rules` where `is_active=TRUE`. Raises `NoPricingRuleError` if none found. |
| FR-PRICE-002 | `calculate(session: ParkingSession, db) -> PriceCalculation` — fetches the active rule. Computes `duration_minutes = ceil((exit_time - entry_time).total_seconds() / 60)`. Applies grace period: if `duration_minutes <= grace_period_mins`, total = `minimum_charge`. Otherwise: `billable_minutes = duration_minutes - grace_period_mins`; `billable_hours = ceil(billable_minutes / 60)`; `raw_total = billable_hours * rate_per_hour`; `total = max(raw_total, minimum_charge)`. Returns `PriceCalculation` dataclass with all intermediate values. |
| FR-PRICE-003 | `calculate_lost_card(session: ParkingSession, db) -> PriceCalculation` — calls `calculate(session)` to get the base amount, then adds `pricing_rule.lost_card_penalty`. Returns the combined total. The penalty is always added on top, even if the base is `minimum_charge`. |
| FR-PRICE-004 | All monetary values in `PriceCalculation` are integers (piastres). No float arithmetic is used anywhere in pricing logic. Duration is always rounded **up** (`math.ceil`). |
| FR-PRICE-005 | `PriceCalculation` is a pure Python dataclass (no SQLAlchemy, no HTTP concepts): `duration_minutes: int`, `billable_minutes: int`, `billable_hours: int`, `rate_per_hour: int`, `grace_period_mins: int`, `minimum_charge: int`, `base_amount: int`, `penalty_amount: int`, `total_amount: int`, `pricing_rule_id: int`, `is_grace_period: bool`. |
| FR-PRICE-006 | `preview(entry_time: datetime, db) -> PriceCalculation` — same as `calculate` but uses `utcnow()` as the exit time. Used for the operator's real-time price preview endpoint. |
| FR-PRICE-007 | `format_duration(minutes: int) -> str` — converts minutes to a human-readable Arabic string. Examples: `90` → `"ساعة و٣٠ دقيقة"`, `60` → `"ساعة واحدة"`, `120` → `"ساعتان"`, `200` → `"٣ ساعات و٢٠ دقيقة"`, `10` → `"١٠ دقائق"`. Uses Arabic-Indic numerals. This is a pure function with no dependencies. |

---

### 2.5 Shift Service (`ShiftService`)

| ID | Requirement |
|---|---|
| FR-SHIFT-001 | `open_shift(operator_id, opening_cash_egp, db) -> Shift` — checks for existing open shift via `get_active_shift`. Raises `ShiftAlreadyOpenError` if found. Creates shift with `started_at=utcnow()`, `gate_number` from operator profile. Commits. Logs `SHIFT_OPENED`. |
| FR-SHIFT-002 | `get_active_shift(operator_id, db) -> Shift | None` — returns the shift where `operator_id` matches and `ended_at IS NULL`. Returns `None` if not found. |
| FR-SHIFT-003 | `close_shift(shift_id, operator_id, closing_cash_egp, db) -> ShiftSummary` — verifies the shift belongs to `operator_id`. Sets `ended_at=utcnow()`, `closing_cash_egp`. Computes `ShiftSummary` (see FR-SHIFT-004). Commits. Logs `SHIFT_CLOSED`. |
| FR-SHIFT-004 | `ShiftSummary` dataclass: `shift_id`, `operator_id`, `gate_number`, `started_at`, `ended_at`, `total_sessions`, `completed_sessions`, `lost_card_sessions`, `active_sessions` (unresolved), `computed_total_egp` (sum of `amount_charged` for COMPLETED + LOST_CARD), `closing_cash_egp`, `discrepancy_egp` (`closing_cash_egp - computed_total_egp`). |
| FR-SHIFT-005 | `require_active_shift(operator_id, db) -> Shift` — calls `get_active_shift`. Raises `NoActiveShiftError` if `None`. Used as a guard in `SessionService` before every entry/exit operation. |

---

### 2.6 Plate Service (`PlateService`) — Phase 2 Full Implementation

| ID | Requirement |
|---|---|
| FR-PLATE-001 | `normalize(plate: str) -> str` — strips leading/trailing whitespace; replaces Eastern Arabic-Indic numerals (٠١٢٣٤٥٦٧٨٩) with Western (0–9); collapses multiple spaces to single space; returns result. |
| FR-PLATE-002 | `validate(plate: str) -> bool` — after normalizing, checks the plate matches the Egyptian format: 1–3 Arabic letters followed by 1–4 Western digits (space-separated). Returns `True` or `False`. Does not raise. |
| FR-PLATE-003 | `search_normalized(plate: str) -> str` — normalizes, then strips all diacritics using `unicodedata.normalize('NFKD', ...)` and removes combining characters. Used for DB comparison only, never for storage. |

---

### 2.7 Barcode Input Handling

| ID | Requirement |
|---|---|
| FR-SCAN-001 | All scan input fields use `<input type="text" inputmode="none" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">`. |
| FR-SCAN-002 | JavaScript on the scan screen listens for `keydown` event on the input. When `Enter` or `Return` is detected (keyCode 13), the form is submitted programmatically via `form.requestSubmit()`. No submit button is required on the scan screen. |
| FR-SCAN-003 | The scan input is given `autofocus` on page load and is re-focused after every form submission result via JavaScript: `document.addEventListener('DOMContentLoaded', () => input.focus())`. |
| FR-SCAN-004 | A configurable scan debounce of 100ms is applied: if two `Enter` events arrive within 100ms, only the first triggers a submission. Prevents double-scans from Sunmi scanner hardware quirk. |
| FR-SCAN-005 | The input field has no minimum length validation at the HTML level (`minlength` not set). Length validation is done server-side only in `CardService.normalize_code`. |
| FR-SCAN-006 | If the form submission returns an error, the input is cleared (`.value = ''`) and re-focused so the operator can scan again immediately. |
| FR-SCAN-007 | The scan page shows a subtle animated indicator (CSS pulse on the input border, no JS required) to signal "ready to scan" state. |

---

### 2.8 58mm Thermal Receipt

| ID | Requirement |
|---|---|
| FR-RCPT-001 | Receipt template path: `templates/receipts/thermal.html`. It does NOT extend `base.html`. It is a standalone HTML file with only receipt content. |
| FR-RCPT-002 | The receipt `<body>` has `style="width:58mm; font-family: 'Courier New', monospace; font-size:10pt; direction:rtl;"`. |
| FR-RCPT-003 | `@media print` in `static/print.css` sets: `@page { size: 58mm auto; margin: 2mm; }` and `body { width: 58mm; }`. All other UI is `display:none !important`. |
| FR-RCPT-004 | **Required fields on every receipt:** Garage name (`APP_NAME` from config), receipt type label ("إيصال وقوف سيارات" or "إيصال كرت مفقود"), ticket/session ID, card code, plate number (or "غير مسجل"), gate number, operator name, entry time (`DD/MM/YYYY HH:mm`), exit time, duration (Arabic string from `format_duration`), pricing rule label, amount charged (format: `٢٥٫٠٠ ج.م`), payment method ("نقداً"), and a footer line: "شكراً لزيارتكم". |
| FR-RCPT-005 | Lost card receipts add two additional lines: "نوع الإيصال: كرت مفقود", "غرامة الكرت المفقود: XX.XX ج.م". |
| FR-RCPT-006 | Amounts are formatted as Arabic-Indic numerals with two decimal places using a Jinja2 `format_egp` filter. Example: `2500` piastres → `"٢٥٫٠٠ ج.م"`. |
| FR-RCPT-007 | A separator line is rendered as 32 dashes: `"--------------------------------"` (fits 58mm monospace width). |
| FR-RCPT-008 | `window.print()` is called inside `<script>window.addEventListener('load', () => { window.print(); setTimeout(() => { window.location.href='/ui/operator/dashboard'; }, 2000); });</script>`. The 2000ms delay gives the print dialog time to appear before redirect. |
| FR-RCPT-009 | The receipt page itself (non-print view) shows a preview of all receipt fields in a styled card, plus a "طباعة مرة أخرى" button that calls `window.print()`. |
| FR-RCPT-010 | No images, logos, or external fonts are used on the receipt. Thermal printer rendering of images is unreliable and slow. |
| FR-RCPT-011 | Session ID is displayed as a zero-padded 8-digit number (e.g., `00000042`) for easy verbal reference. |

---

### 2.9 Operator UI Templates

| ID | Requirement |
|---|---|
| FR-UI-101 | `templates/operator/dashboard.html` — extends `base.html`. Two primary buttons: `[دخول]` and `[خروج]`, each `min-height: 120px`, `width: 50%`, inline-block, large Arabic label (`font-size: 1.5rem`). Third button `[كرت مفقود]` full-width below, `min-height: 60px`, amber/warning colour. |
| FR-UI-102 | `templates/operator/entry.html` — full-screen scan view: single centred `<input>` with label, autofocused, large border with pulse animation. No other interactive elements except a "رجوع" back link. |
| FR-UI-103 | `templates/operator/entry_confirm.html` — success screen after entry: large green checkmark SVG (inline, no external request), card code in large monospace, entry time. Auto-redirect to dashboard after 3 seconds via `setTimeout`. |
| FR-UI-104 | `templates/operator/exit_scan.html` — identical layout to `entry.html` but labelled for exit. |
| FR-UI-105 | `templates/operator/exit_confirm.html` — shows all pricing details, duration, and total. The confirm button is `min-height: 64px`, full-width, green. A "إلغاء" cancel link returns to dashboard without closing the session. |
| FR-UI-106 | `templates/operator/lost_card.html` — plate input form (required), notes field (optional), a prominent warning banner: "سيتم تطبيق غرامة الكرت المفقود". |
| FR-UI-107 | `templates/operator/lost_card_confirm.html` — shows the session details found by plate, calculated penalty total, and a confirm button. |
| FR-UI-108 | `templates/operator/shift_start.html` — form with one numeric field: "الكاش الافتتاحي (بالجنيه)" and a large "ابدأ الشيفت" button. |
| FR-UI-109 | `templates/operator/shift_end.html` — shows computed session totals for the shift, one numeric input for closing cash, discrepancy preview (auto-computed via inline JS as the operator types), and a "أنهِ الشيفت" button. |
| FR-UI-110 | All operator templates use `<html lang="ar" dir="rtl">` (via `base.html`). All CSS uses logical properties (`margin-inline-start`, not `margin-left`). Touch targets are minimum `48×48px`. Font size minimum `16px` on all inputs. |
| FR-UI-111 | Total page weight (HTML + CSS + JS) for any operator page must not exceed 150KB. No external CDN calls at runtime. |

---

### 2.10 API Endpoints — Phase 2

#### Sessions

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/sessions/` | operator | Open session; body: `{card_code, plate_number?}` |
| `GET` | `/api/v1/sessions/active` | admin | All currently active sessions |
| `GET` | `/api/v1/sessions/{id}` | operator, admin | Session detail |
| `PATCH` | `/api/v1/sessions/{id}/exit` | operator | Close session (exit flow) |
| `PATCH` | `/api/v1/sessions/{id}/lost-card` | operator | Resolve lost card |
| `GET` | `/api/v1/sessions/{id}/receipt` | operator | Receipt data (JSON) |

#### Cards

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/cards/` | admin | List cards with status filter |
| `POST` | `/api/v1/cards/` | admin | Add single card |
| `POST` | `/api/v1/cards/bulk` | admin | Add range of cards |
| `GET` | `/api/v1/cards/{card_code}` | operator, admin | Card detail + active session if any |
| `PATCH` | `/api/v1/cards/{card_code}/status` | admin | Change card status |

#### Shifts

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/shifts/` | operator | Open shift |
| `GET` | `/api/v1/shifts/active` | operator, admin | Current open shift |
| `PATCH` | `/api/v1/shifts/{id}/close` | operator | Close shift |
| `GET` | `/api/v1/shifts/{id}/summary` | operator, admin | Shift financial summary |
| `GET` | `/api/v1/shifts/{id}/sessions` | operator, admin | Paginated sessions for shift |

#### Rates

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/rates/active` | operator, admin | Active pricing rule |
| `GET` | `/api/v1/rates/preview` | operator | Price preview given `entry_time` query param |

---

## 3. Non-Functional Requirements

### 3.1 Performance on Sunmi V2

| ID | Requirement |
|---|---|
| NFR-PERF-101 | Barcode lookup (`POST /ui/operator/entry` or `/ui/operator/exit/lookup`) must respond with a fully rendered HTML page within **800ms** on LAN under normal load. |
| NFR-PERF-102 | `POST /api/v1/sessions/` JSON endpoint must respond within **300ms** (no bcrypt; only DB read + write). |
| NFR-PERF-103 | The `PricingService.calculate()` function must complete in under **5ms** (pure Python, no I/O after rule is fetched). |
| NFR-PERF-104 | The operator dashboard page must render within **300ms** on LAN. The session counter async refresh must complete within **500ms**. |
| NFR-PERF-105 | The receipt page (`GET /ui/operator/receipt/{id}`) must load and trigger `window.print()` within **1 second** of navigation. |
| NFR-PERF-106 | Database queries for card lookup by `card_code` must use a unique index. The index on `parking_sessions.status` must exist to efficiently find active sessions. Query time must be under **50ms** in isolation. |
| NFR-PERF-107 | The application must handle 5 simultaneous operator requests (one per gate) without response time degradation beyond 20% of baseline. |

---

### 3.2 Reliability & Offline Tolerance

| ID | Requirement |
|---|---|
| NFR-REL-101 | If the database is temporarily unreachable during a session open or close, the server returns `503` with Arabic message: "الخادم غير متاح مؤقتاً — انتظر لحظة وحاول تاني". The operator page must display this message clearly without a raw error page. |
| NFR-REL-102 | Session open and close operations use a single database transaction. If any part fails, the entire operation rolls back — no partial state (e.g., session created but card status not updated). |
| NFR-REL-103 | The `SELECT ... FOR UPDATE` pattern (or equivalent) is used on session close to prevent two simultaneous exit scans on the same card from creating a race condition. |
| NFR-REL-104 | `receipt_printed_at` is set idempotently on first receipt page load. Refreshing the receipt page does not overwrite the timestamp. |
| NFR-REL-105 | If the Sunmi printer is offline, `window.print()` still fires (browser handles the dialog). The system does not detect or handle printer failure — receipt data remains accessible via `GET /ui/operator/receipt/{id}` for reprinting. |
| NFR-REL-106 | All monetary amounts are stored and computed as integers (piastres). Floating-point arithmetic is forbidden in `PricingService`. The Jinja2 `format_egp` filter handles display conversion (`amount / 100`) using Python `Decimal` for the display format only. |

---

### 3.3 Security

| ID | Requirement |
|---|---|
| NFR-SEC-101 | Every session open and close route verifies the operator has an active shift via `ShiftService.require_active_shift`. An operator without an open shift receives `403` with code `NO_ACTIVE_SHIFT`. |
| NFR-SEC-102 | An operator can only close a shift that belongs to them (`shift.operator_id == current_user.id`). Attempting to close another operator's shift returns `403`. |
| NFR-SEC-103 | The lost card flow is accessible to operators but `admin_override_by` is only settable by admin. Operators resolve lost cards through the operator flow; admins through the admin override. |
| NFR-SEC-104 | All barcode input is sanitized through `CardService.normalize_code` before any DB query. No raw scanner input reaches SQLAlchemy. |
| NFR-SEC-105 | `amount_charged`, `duration_minutes`, and `pricing_rule_id` are set by the server at exit time. These fields are never accepted from the client request body on exit. |

---

### 3.4 Maintainability

| ID | Requirement |
|---|---|
| NFR-MNT-101 | `PricingService.calculate()` is a pure function testable without a database (pass a mock session and a `PricingRule` object directly). |
| NFR-MNT-102 | `PriceCalculation` and `ShiftSummary` are Python dataclasses, not Pydantic models and not SQLAlchemy models. |
| NFR-MNT-103 | `format_duration` and `format_egp` are pure functions with 100% unit test coverage. |
| NFR-MNT-104 | No business logic (pricing calculation, state transition validation) lives in route handlers. Routes call services only. |
| NFR-MNT-105 | The session state machine transitions are documented in a docstring on `SessionService` listing all valid and invalid transitions. |

---

### 3.5 Accessibility & Localization

| ID | Requirement |
|---|---|
| NFR-L10N-101 | All duration strings use Arabic grammatical rules for numbers: singular (١), dual (٢), plural (٣–١٠), etc. `format_duration` must handle all cases correctly. |
| NFR-L10N-102 | All monetary amounts displayed to operators use Arabic-Indic numerals (٠١٢٣٤٥٦٧٨٩). The `format_egp` Jinja2 filter performs this conversion. |
| NFR-L10N-103 | All datetime values are displayed in `Africa/Cairo` timezone (UTC+2). Conversion from stored UTC happens in the Jinja2 `format_datetime` filter, not in the service layer. |
| NFR-L10N-104 | The receipt template uses only characters guaranteed to render on a standard thermal printer: Arabic Unicode block (U+0600–U+06FF) and basic Latin. No emoji, no special symbols. |
| NFR-L10N-105 | The dashboard live clock displays Cairo local time updated every second via a 4-line vanilla JS snippet. No external library. |

---

## 4. Edge Cases

### 4.1 Barcode Scanning Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SCAN-001 | Operator scans a card that is already `in_use` (ACTIVE session exists) on the **entry** screen | `409` with code `CARD_ALREADY_ACTIVE`. Page shows: "تم ادخال هذا الكارت بالفعل". Entry is not created. Card is not touched. |
| EC-SCAN-002 | Operator scans a card that is marked `lost` on the entry screen | `409` with code `CARD_NOT_AVAILABLE`. Page shows: "الكرت ده متعطل — تواصل مع الإدارة". |
| EC-SCAN-003 | Operator scans a card that is marked `damaged` on the entry screen | `409` with code `CARD_NOT_AVAILABLE`. Same message as EC-SCAN-002. |
| EC-SCAN-004 | Operator scans a `card_code` that does not exist in the `parking_cards` table | `404` with code `CARD_NOT_FOUND`. Page shows: "هذا الكارت غير مسجل في النظام". |
| EC-SCAN-005 | Operator scans an `available` card on the **exit** screen (no active session) | `404` with code `CARD_HAS_NO_ACTIVE_SESSION`. Page shows: "مفيش جلسة مفتوحة لهذا الكرت". |
| EC-SCAN-006 | Operator scans a `COMPLETED` session's card on the exit screen (card already freed) | Card will be `available`; falls through to EC-SCAN-005 behaviour. |
| EC-SCAN-007 | Scanner injects barcode with leading/trailing whitespace or newline characters | `CardService.normalize_code` strips whitespace before lookup. The raw input is never logged or stored. |
| EC-SCAN-008 | Scanner injects an empty string (scanner misfire) | `normalize_code` returns empty string → raises `InvalidBarcodeFormatError` → `422` with code `INVALID_BARCODE_FORMAT`. Page re-focuses input silently. |
| EC-SCAN-009 | Barcode contains lowercase letters (some card printers use mixed case) | `normalize_code` uppercases before lookup. `CARD-0042` and `card-0042` resolve to the same record. |
| EC-SCAN-010 | Barcode contains special characters outside `[A-Z0-9\-_]` (e.g., accented letters, Arabic) | `normalize_code` raises `InvalidBarcodeFormatError` → `422` with code `INVALID_BARCODE_FORMAT`. |
| EC-SCAN-011 | Two operators at different gates scan the same card within milliseconds of each other (race condition on entry) | `SELECT ... FOR UPDATE` on the card record; the second transaction sees `status = 'in_use'` and raises `CARD_ALREADY_ACTIVE`. Only one session is created. |
| EC-SCAN-012 | Two exit scans of the same card arrive simultaneously (race condition on exit) | `SELECT ... FOR UPDATE` on the session; only the first succeeds. The second receives `SESSION_NOT_ACTIVE`. |

---

### 4.2 Session & Pricing Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SESS-001 | Exit is processed within the grace period (e.g., entry at 10:00, exit at 10:10, grace = 15 mins) | `duration_minutes = 10`, `is_grace_period = True`, `total = minimum_charge` (even if `minimum_charge = 0`). Receipt shows "ضمن فترة السماح". |
| EC-SESS-002 | Duration is exactly equal to grace period (e.g., 15 minutes exactly) | `is_grace_period = True`. `billable_minutes = 0`. Total = `minimum_charge`. |
| EC-SESS-003 | Exit is processed within the same minute as entry (duration = 0 minutes) | `duration_minutes = 0`. Treated as inside grace period. Total = `minimum_charge`. System does not divide by zero. |
| EC-SESS-004 | Duration is fractional hours (e.g., 90 minutes = 1.5 hours) | `billable_hours = ceil(75 / 60) = ceil(1.25) = 2`. Operator is charged for 2 hours. This is by design (ceiling rounding). |
| EC-SESS-005 | A session has been open for more than 24 hours | Pricing calculation proceeds normally. No automatic session close. Duration is displayed correctly (e.g., "٢٦ ساعة و١٥ دقيقة"). A warning flag `is_long_stay = True` is computed when `duration_minutes > 1440` for admin dashboard display only. |
| EC-SESS-006 | No active pricing rule exists when an exit is attempted | `NoPricingRuleError` raised. Exit is blocked. Page shows: "لا توجد تعريفة سعرية — تواصل مع الإدارة". Session remains ACTIVE. |
| EC-SESS-007 | Pricing rule changes between a car's entry and exit | The pricing rule active **at exit time** is used. This is by design (per `plan.md`). The rule used is snapshotted into `pricing_rule_id` on the session at close time. |
| EC-SESS-008 | `minimum_charge` is zero and duration is within grace period | `total_amount = 0`. Receipt prints with "٠٫٠٠ ج.م". This is valid — no division or negative amounts. |
| EC-SESS-009 | `lost_card_penalty` in the pricing rule is set to zero | Lost card total = base amount only (no penalty added). Receipt does not show a penalty line. |
| EC-SESS-010 | Operator tries to exit a session they did not open (different gate) | Permitted. `exit_operator_id` and `exit_shift_id` may differ from `operator_id` and `shift_id`. No restriction on cross-gate exit. |

---

### 4.3 Shift Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SHIFT-001 | Operator tries to open a session without an open shift | `403` with code `NO_ACTIVE_SHIFT`. Page shows: "افتح شيفتك الأول قبل ما تبدأ". |
| EC-SHIFT-002 | Operator tries to open a second shift while first is open | `409` with code `SHIFT_ALREADY_OPEN`. |
| EC-SHIFT-003 | Operator closes shift with active (unresolved) sessions | Shift closes successfully. `active_sessions` count in `ShiftSummary` is non-zero. Admin dashboard flags this shift with an "⚠ جلسات غير محلولة" indicator. |
| EC-SHIFT-004 | `closing_cash_egp` is less than computed total (negative discrepancy) | Allowed. `discrepancy_egp` is negative. Admin sees this in the shift summary. No block. |
| EC-SHIFT-005 | `closing_cash_egp` is zero | Allowed (operator may have had no cash transactions or forgot to count). |
| EC-SHIFT-006 | Operator's session (JWT) expires mid-shift | Operator is redirected to `/ui/login`. After re-login, their open shift is detected and they are returned to the dashboard automatically. |

---

### 4.4 Lost Card Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-LOST-001 | Plate number entered returns no active sessions | Page shows: "مفيش عربية داخلة بالنمر ده". Form is re-rendered with the plate pre-filled for correction. |
| EC-LOST-002 | Plate number returns multiple active sessions (same plate, different gates) | All matching sessions are listed with gate number, entry time, and card code. Operator selects the correct one. |
| EC-LOST-003 | Operator tries to resolve a session that is already COMPLETED or LOST_CARD | `409` with code `SESSION_NOT_ACTIVE`. |
| EC-LOST-004 | Lost card resolved for a session that is within the grace period | Penalty is still applied on top of the grace period minimum charge. The total is: `minimum_charge + lost_card_penalty`. |
| EC-LOST-005 | The lost card's `card_code` is scanned on the entry screen after being marked `lost` | `CARD_NOT_AVAILABLE` error. Admin must manually reset it to `available` before it can be reused. |

---

### 4.5 Receipt Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-RCPT-001 | Operator navigates to receipt page but printer is offline | `window.print()` fires; browser shows system print dialog; operator dismisses. Receipt page remains accessible. "طباعة مرة أخرى" button visible. |
| EC-RCPT-002 | Operator refreshes the receipt page | `receipt_printed_at` is not updated (idempotent). `window.print()` fires again. Dashboard redirect fires again after 2 seconds. |
| EC-RCPT-003 | Plate number was not entered at entry (`NULL`) | Receipt shows "رقم اللوحة: غير مسجل" — never shows `null`, `None`, or an empty field. |
| EC-RCPT-004 | Duration is exactly 60 minutes | Display: "ساعة واحدة". Not "١ ساعة". Arabic dual and singular forms are handled correctly. |
| EC-RCPT-005 | Amount is 0 piastres (free parking within grace period) | Receipt prints with "المبلغ المستحق: ٠٫٠٠ ج.م". No amount field is hidden or omitted. |
| EC-RCPT-006 | Session ID is a large number (e.g., 1,500,000) | Still displayed as 8-digit zero-padded: `01500000`. If ID exceeds 8 digits, display as-is without truncation. |

---

## 5. Defined Error Codes

All error responses follow the envelope:
`{"detail": "<Arabic or English message>", "code": "<MACHINE_CODE>"}`.

### 5.1 Card Errors

| Code | HTTP | Trigger |
|---|---|---|
| `CARD_NOT_FOUND` | 404 | `card_code` not in `parking_cards` table |
| `CARD_ALREADY_ACTIVE` | 409 | Card scanned on entry but `status = 'in_use'` |
| `CARD_NOT_AVAILABLE` | 409 | Card scanned on entry but `status = 'lost'` or `'damaged'` |
| `CARD_HAS_NO_ACTIVE_SESSION` | 404 | Card scanned on exit but no `ACTIVE` session found |
| `INVALID_BARCODE_FORMAT` | 422 | Normalized barcode is empty or contains invalid characters |
| `CARD_CODE_ALREADY_EXISTS` | 409 | Admin tries to create a card with a duplicate `card_code` |
| `BULK_CARD_CONFLICT` | 409 | Bulk card creation has duplicates (lists conflicting codes in detail) |

### 5.2 Session Errors

| Code | HTTP | Trigger |
|---|---|---|
| `SESSION_NOT_FOUND` | 404 | No session with the given ID |
| `SESSION_NOT_ACTIVE` | 409 | Attempt to close/resolve a non-ACTIVE session |
| `SESSION_ALREADY_COMPLETED` | 409 | Specific variant for debugging (maps to `SESSION_NOT_ACTIVE` in prod) |

### 5.3 Shift Errors

| Code | HTTP | Trigger |
|---|---|---|
| `NO_ACTIVE_SHIFT` | 403 | Operator performs session action without an open shift |
| `SHIFT_ALREADY_OPEN` | 409 | Operator tries to open a second shift |
| `SHIFT_NOT_FOUND` | 404 | Shift ID does not exist |
| `SHIFT_NOT_OWNED` | 403 | Operator tries to close another operator's shift |

### 5.4 Pricing Errors

| Code | HTTP | Trigger |
|---|---|---|
| `NO_ACTIVE_PRICING_RULE` | 503 | Exit attempted but no `is_active=TRUE` pricing rule exists |
| `PRICING_RULE_NOT_FOUND` | 404 | Admin requests a specific pricing rule ID that does not exist |

### 5.5 Lost Card Errors

| Code | HTTP | Trigger |
|---|---|---|
| `NO_SESSIONS_FOR_PLATE` | 404 | Lost card lookup by plate returns no active sessions |
| `LOST_CARD_OPERATOR_ONLY` | 403 | Non-operator role attempts the operator lost card flow |

### 5.6 General Errors (Phase 2 additions)

| Code | HTTP | Trigger |
|---|---|---|
| `DATABASE_UNAVAILABLE` | 503 | DB unreachable during request |
| `INTERNAL_ERROR` | 500 | Unhandled exception (detail sanitized in non-development) |
| `INSUFFICIENT_PERMISSIONS` | 403 | Valid JWT but wrong role |
| `UNAUTHORIZED` | 401 | Missing or invalid JWT |

---

## 6. Testing Requirements

### 6.1 Unit Tests

| Module | Required Coverage | Key Cases |
|---|---|---|
| `CardService` | 100% | All status combinations, normalize_code edge cases, race condition logic |
| `SessionService` | 100% | All state transitions, atomic transaction verification, lost card flow |
| `PricingService` | 100% | Grace period boundary, ceiling rounding, zero duration, lost card penalty, no rule found |
| `ShiftService` | 100% | Open/close/conflict/summary computation |
| `PlateService` | 100% | Eastern numeral conversion, diacritic stripping, validation edge cases |
| `format_duration` | 100% | 0 min, 1 min, 15 min, 59 min, 60 min, 90 min, 120 min, 200 min, 1440 min |
| `format_egp` | 100% | 0, 100, 2500, 99999, Arabic-Indic output |

### 6.2 Integration Tests

| Flow | Required Scenarios |
|---|---|
| Entry flow | Happy path, card not found, card already active, card damaged, no active shift |
| Exit flow | Happy path, grace period, exact grace boundary, no active session, no pricing rule |
| Lost card flow | Happy path, plate not found, multiple matches, session already closed |
| Shift flow | Open, close with summary, double-open rejected, close another's shift rejected |
| Receipt page | First load sets `receipt_printed_at`, second load does not overwrite, plate null display |

### 6.3 Manual QA Checklist (Sunmi V2)

- [ ] Scanner injects barcode into input and auto-submits on Sunmi hardware.
- [ ] Input re-focuses after each scan without operator touching the screen.
- [ ] Entry confirmation screen displays and redirects to dashboard in 3 seconds.
- [ ] Exit confirmation screen shows correct Arabic numerals for duration and price.
- [ ] Receipt prints at correct 58mm width on thermal printer.
- [ ] All text on receipt is legible at 10pt on thermal paper.
- [ ] Dashboard buttons are large enough for comfortable thumb tapping.
- [ ] No horizontal scroll at 360px viewport on any operator screen.
- [ ] Live clock on dashboard updates every second.
- [ ] Lost card flow completes without requiring any barcode scan.

---

## 7. Out of Scope for Phase 2

The following are explicitly deferred and must not be implemented:

- Admin dashboard UI and admin reporting screens.
- Pricing rule creation or activation via UI (admin sets via API only in Phase 2).
- Multiple payment methods (card, mobile wallet).
- Automatic time-of-day pricing rule switching.
- Token refresh or session extension.
- Offline mode or local caching on the Sunmi device.
- Car plate OCR or camera-based plate recognition.
- SMS or email receipt delivery.
- Multi-garage or multi-branch support.
- Export to PDF or Excel.
- Push notifications for long-stay vehicles.

---

*This specification is complete when all Acceptance Criteria, Functional Requirements,
Non-Functional Requirements, and Edge Cases listed above have corresponding passing
tests, and the manual QA checklist has been signed off on a physical Sunmi V2 device.*
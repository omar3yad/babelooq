# Phase 2 Specification — Operator Application & Core Business Logic

> **Version:** 2.0
> **Scope:** Card scanning workflow, session lifecycle, tiered pricing engine, shift management,
> 80mm/58mm thermal receipt printing, ANPR camera integration, and the complete operator UI on Gate Workstation PCs (Desktop PCs).
> **Prerequisite reading:** `constitution.md`, `master-plan.md`, `edge-plate-capture.md`, `phase-1-core/spec.md`
> **Out of scope:** Multi-currency, token refresh, rate limiting, Docker deployment.

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
  `gate_number` from the operator's profile, and `opening_cash_egp` entered by the operator (stored in piastres).
- An operator with an already-open shift cannot open a second one; the system returns
  `409 Conflict` with code `SHIFT_ALREADY_OPEN`.
- After a successful shift start, the operator is redirected to the main gate dashboard.
- The shift start is recorded in `audit_logs` with action `SHIFT_OPENED`.

---

**US-102 — End a Shift**
> *As an operator, I want to close my shift at the end of my work period, so that the admin can reconcile totals.*

**Acceptance Criteria:**
- For **Gate 1 (Entry Operator)**: Shift close displays the entry flow summary (`total_entered`, `active_count`, `completed_count`, `subs_count`) without cash collection (entry operators do not collect money).
- For **Gate 2 (Exit Operator)**: `PATCH /api/v1/shifts/{id}/close` accepts `closing_cash_egp` (stored in piastres).
- The response includes a shift summary: total sessions, total amount collected
  (computed strictly from sessions closed in this shift via `exit_shift_id`), cash entered, and the discrepancy.
- A shift with open (ACTIVE) entry sessions can still be closed; those sessions remain ACTIVE and are counted as active in the summary.
- `ended_at` is set to `utcnow()` on close.
- The shift close is recorded in `audit_logs` with action `SHIFT_CLOSED`.
- After closing, the operator is redirected to `/ui/login`.

---

**US-103 — Gate Dashboard (Main Operator Screen)**
> *As an operator, I want a single clear screen tailored to my assigned gate, so that I can operate quickly without navigating menus.*

**Acceptance Criteria:**
- `GET /ui/operator/dashboard` renders within 300ms on LAN.
- For Gate 1 (Entry Gate), displays prominent **[دخول]** button. Access to exit routes redirects to entry.
- For Gate 2 (Exit Gate), displays prominent **[خروج]** and **[كرت مفقود]** buttons.
- The screen displays: operator name, gate number, shift start time, session count today, and a live clock.
- If no shift is open, gate action buttons are disabled and a banner says "افتح شيفتك أولاً".
- The page auto-refreshes the session counter every 60 seconds via a lightweight `fetch` call.

---

### 1.2 Entry Flow

---

**US-104 — Scan Card on Entry**
> *As an operator, I want to swipe an RFID card or scan a barcode when a car arrives, so that the system
> creates a timed parking session without me typing anything manually.*

**Acceptance Criteria:**
- `GET /ui/operator/entry` renders a full-screen scan input: one large `<input>`
  autofocused, labelled "امسح الكرت" in Arabic, with `inputmode="none"` (preventing software on-screen keyboards).
- The standard USB barcode / RFID wedge scanner connected to the Gate Workstation PC injects the card code and auto-submits on carriage return.
- `POST /ui/operator/entry` (or `POST /ui/operator/api/scan`) calls `SessionService.open_session(card_code, operator_id, plate_number)`.
- The system checks if the card belongs to an active subscription (`is_subscribed = True`); if so, it links the subscription and enforces daily entry limits.
- On success: the page renders a confirmation screen showing the card code and entry time, and automatically redirects back to the dashboard after 3 seconds.
- On error: the page re-renders with a full-screen Arabic error message and a "حاول تاني" button. No redirect happens on error.
- The scan input is re-focused after every submission so the operator can scan the next card immediately.
- The session open is recorded in `audit_logs` with action `SESSION_OPENED`.

---

**US-105 — Automated ANPR Plate Capture & Optional Manual Entry**
> *As an operator, I want the system camera to automatically capture and recognize the vehicle plate, with an option for manual correction if needed.*

**Acceptance Criteria:**
- Upon card scan at Gate 1, the server dispatches a capture trigger over WebSocket (`/ws/edge`) to the local garage Edge PC.
- The camera capture state (`PlateCaptureStatus`) transitions: `PENDING` → `SUCCESS` / `NO_PLATE` / `TIMEOUT` / `FAILED` / `OFFLINE`.
- The operator can view the captured plate and crop image, or enter/correct the plate manually (`POST /ui/operator/api/sessions/{id}/plate-override`).
- All plate numbers pass through `PlateService.normalize(plate)` (strips whitespace, converts Eastern Arabic numerals to Western).
- The absence or delay of camera plate recognition never blocks ticket issuance or barrier opening.

---

### 1.3 Exit Flow

---

**US-106 — Scan Card on Exit**
> *As an operator at Gate 2, I want to scan the card returned by the driver, so that the system
> automatically calculates the parking duration and fee.*

**Acceptance Criteria:**
- `GET /ui/operator/exit` renders the exit scan input (accessible to Gate 2 operators).
- `POST /ui/operator/exit/lookup` calls `CardService.validate_for_exit(card_code)`
  then `PricingService.calculate(session, rule, exit_time)`.
- The response renders `operator/exit_confirm.html` showing:
  - Card code.
  - Entry time (`DD/MM/YYYY HH:mm` in Cairo local time).
  - Exit time (current time).
  - Duration in Arabic (e.g., "ساعتان و٣٥ دقيقة").
  - Itemised breakdown: tiered rates or flat hourly rate, grace period deduction.
  - **Total amount due in large font** (EGP formatted via `format_egp`).
  - For subscriber cards: displays "مشترك ✓" with 0.00 EGP charge.
- A single large "تأكيد الدفع وطباعة الإيصال" button confirms payment and prints.
- `POST /ui/operator/exit/{session_id}/confirm` closes the session, marks it `COMPLETED`, frees non-subscribed cards to `available`, and redirects to receipt.
- The session close is recorded in `audit_logs` with action `SESSION_CLOSED`.

---

**US-107 — Print Thermal Receipt on Exit**
> *As an operator, I want the receipt to print automatically on the 80mm/58mm thermal printer when I confirm exit, so that the driver receives their proof of payment.*

**Acceptance Criteria:**
- After confirming exit, the browser is redirected to `GET /ui/operator/receipt/{session_id}`.
- The receipt page automatically calls `window.print()` on DOM load.
- The receipt renders using `@media print` styles in `static/print.css` formatted for thermal printers (80mm / 58mm).
- All non-receipt navigation elements are hidden in print media.
- After printing, the page automatically redirects back to the dashboard after 2 seconds.
- The operator can click "طباعة مرة أخرى" to re-trigger `window.print()`.
- `receipt_printed_at` is set to `utcnow()` idempotently on first load.

---

### 1.4 Lost Card Flow

---

**US-108 — Resolve a Lost Card**
> *As an operator, I want to resolve a lost card session by vehicle plate number, so that I can apply the penalty fee and close the session.*

**Acceptance Criteria:**
- Gate 2 dashboard displays a distinct "كرت مفقود" button.
- `GET /ui/operator/lost-card` renders a search form with plate number.
- `SessionService.find_active_by_plate(plate)` returns matching active sessions.
- If multiple sessions match, the operator selects the matching vehicle entry.
- `POST /ui/operator/lost-card/confirm/{session_id}` calls `SessionService.resolve_lost_card(session_id, operator_id, notes)`.
- The fee is calculated via `PricingService.calculate_lost_card(session, rule, exit_time)`: `base_amount + rule.lost_card_penalty`.
- The card's status is set to `lost`.
- A lost card penalty thermal receipt is printed.
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


### 2.1 Session State Machine & Subscription Awareness

A `ParkingSession` moves through exactly these states:

```
                ┌────────────────┐
                │     (none)     │  Card status: available
                └───────┬────────┘
                        │  SessionService.open_session()
                        ▼
                ┌────────────────┐
                │     ACTIVE     │  Card status: in_use
                └───────┬────────┘
           ┌────────────┴─────────────┐
           │                          │
           │ Session.close_session()  │ Session.resolve_lost_card()
           ▼                          ▼
    ┌──────────────┐          ┌───────────────┐
    │  COMPLETED   │          │   LOST_CARD   │
    │              │          │               │
    │ Non-sub card:│          │ Card: lost    │
    │ available    │          │               │
    │ Sub card:    │          │               │
    │ in_use       │          │               │
    └──────────────┘          └───────────────┘
```

**State Rules & Edge Camera Integration:**

| From | To | Trigger | Condition |
|---|---|---|---|
| — | `ACTIVE` | `open_session()` | Card must be `available` (or active subscriber card). Dispatches ANPR trigger to Edge PC. |
| `ACTIVE` | `COMPLETED` | `close_session()` | Standard: calculates fee, marks `COMPLETED`, frees card to `available`. Subscribed: marks `COMPLETED` with 0 EGP, card remains `in_use`. |
| `ACTIVE` | `LOST_CARD` | `resolve_lost_card()` | Calculates lost card penalty, marks `LOST_CARD`, sets card to `lost`. |
| `ACTIVE` | `COMPLETED` | `admin_override_close_session()` | Admin override with optional custom amount and audit note. |
| `COMPLETED` | any | — | **Forbidden. Immutable.** |
| `LOST_CARD` | any | — | **Forbidden. Immutable.** |

Edge camera recognition lifecycle (`PlateCaptureStatus`):
`PENDING` → `SUCCESS` (plate recognized) | `NO_PLATE` (no plate detected) | `TIMEOUT` | `FAILED` | `OFFLINE`.

---

### 2.2 Card Service (`CardService`)

| ID | Requirement |
|---|---|
| FR-CARD-001 | `validate_for_entry(card_code: str) -> ParkingCard` — fetches card by `card_code`. Raises `CardNotFoundError` if not found. Raises `CardNotAvailableError` if `status in ('lost', 'damaged')`. Raises `CardAlreadyActiveError` if `status == 'in_use'`. Returns the `ParkingCard`. |
| FR-CARD-002 | `validate_for_exit(card_code: str, session_repo) -> ParkingSession` — fetches card by `card_code`. Raises `CardNotFoundError` if not found. Fetches the active session. Raises `CardHasNoActiveSessionError` if none found. Returns the `ParkingSession`. |
| FR-CARD-003 | `set_status(card: ParkingCard, status: CardStatus) -> ParkingCard` — updates `card.status` and `card.last_seen_at = utcnow()`. Flushes changes to session. |
| FR-CARD-004 | `normalize_code(raw: str) -> str` — strips all whitespace, converts to uppercase. Validates format against regex `^[A-Z0-9\-_]{1,50}$`. Raises `InvalidBarcodeFormatError` if empty or invalid. |
| FR-CARD-005 | All `CardService` methods call `normalize_code` on every `card_code` input before database operations. Raw un-normalized input is never queried. |
| FR-CARD-006 | `bulk_create(codes: list[str])` — normalizes codes, checks for existing records, inserts newly added cards in bulk, skips conflicting ones. Returns created count and skipped count. Raises `409 ALL_CARDS_EXIST` only if all provided cards already exist. |

---

### 2.3 Session Service (`SessionService`)

| ID | Requirement |
|---|---|
| FR-SESS-001 | `open_session(card_code, operator_id, plate_number=None) -> SessionOpenResult` — verifies operator active shift via `ShiftService.require_active_shift`. Checks active subscriptions via `SubscriptionService.get_active_for_card` and verifies daily entry limits. Creates `ParkingSession` (`status='ACTIVE'`). Sets card to `in_use`. Records `SESSION_OPENED` in audit logs. Concurrency-safe with unique partial index `idx_active_card_id` on `(card_id)` WHERE `exit_time IS NULL`. |
| FR-SESS-002 | `close_session(session_id, exit_operator_id) -> tuple[ParkingSession, PriceCalculation | None]` — executed under concurrency lock `async with self._lock:`. Verifies exit operator has active shift (`exit_shift_id`). For subscribed sessions: completes at 0 EGP with card remaining `in_use`. For standard sessions: calculates fee via `PricingService.calculate`, completes session, frees card to `available`. Commits transaction and records `SESSION_CLOSED` in audit logs. |
| FR-SESS-003 | `resolve_lost_card(session_id, operator_id, notes=None) -> tuple[ParkingSession, PriceCalculation]` — executed under concurrency lock `async with self._lock:`. Calculates fee and penalty via `PricingService.calculate_lost_card`. Sets session `status='LOST_CARD'`, `is_lost_card=True`, sets card to `lost`. Records `LOST_CARD_RESOLVED` in audit logs. |
| FR-SESS-004 | `admin_override_close_session(session_id, admin_id, amount_charged_egp=0.0, override_note=None) -> ParkingSession` — allows an admin to close an active session without requiring an active shift, setting custom fee, freeing card, and logging `ADMIN_SESSION_CLOSED`. |
| FR-SESS-005 | `find_active_by_plate(plate: str) -> list[ParkingSession]` — normalizes plate via `PlateService.normalize`, queries sessions where `status='ACTIVE'` and `plate_number` matches. |
| FR-SESS-006 | `mark_receipt_printed(session_id) -> None` — sets `receipt_printed_at = utcnow()` idempotently on first receipt load. |

---

### 2.4 Pricing Service (`PricingService`)

| ID | Requirement |
|---|---|
| FR-PRICE-001 | `get_active_rule() -> PricingRule` — queries `pricing_rules` where `is_active=TRUE`. Raises `NoPricingRuleError` if none found. |
| FR-PRICE-002 | `calculate(session, rule, exit_time) -> PriceCalculation` — computes `duration_minutes = ceil((exit_time - entry_time).total_seconds() / 60)`. If `duration_minutes <= grace_period_mins`, total = `minimum_charge`. Otherwise: `billable_minutes = duration_minutes - grace_period_mins`; `billable_hours = ceil(billable_minutes / 60)`. Tiered pricing: if `first_hour_charge > 0`, first hour costs `first_hour_charge`, each subsequent hour costs `subsequent_hour_charge`. Otherwise fallback to `billable_hours * rate_per_hour`. Final base amount is `max(raw, minimum_charge)`. |
| FR-PRICE-003 | `calculate_lost_card(session, rule, exit_time) -> PriceCalculation` — calculates base amount via `calculate()`, then adds `rule.lost_card_penalty`. Total = `base_amount + lost_card_penalty`. |
| FR-PRICE-004 | All monetary values in `PriceCalculation` and `ParkingSession` are integers stored in piastres (1 EGP = 100 piastres). Float arithmetic is forbidden. |
| FR-PRICE-005 | `format_egp(piastres: int) -> str` — converts piastres to EGP string with Arabic-Indic numerals. Formats whole amounts cleanly (e.g. `1000` piastres → `"١٠ ج.م"`) and fractional amounts with decimals (e.g. `2550` piastres → `"٢٥٫٥٠ ج.م"`). |
| FR-PRICE-006 | `format_duration(minutes: int) -> str` — converts minutes into a grammatical Arabic duration string (e.g. `"ساعة واحدة"`, `"ساعتان"`, `"٣ ساعات و٢٠ دقيقة"`). |

---

### 2.5 Shift Service (`ShiftService`)

| ID | Requirement |
|---|---|
| FR-SHIFT-001 | `open_shift(operator_id, gate_number, opening_cash_egp) -> Shift` — checks for existing open shift via `get_active_shift`. Raises `ShiftAlreadyOpenError` if found. Creates shift with `started_at=utcnow()`, `gate_number` from operator profile. Commits and logs `SHIFT_OPENED`. |
| FR-SHIFT-002 | `get_active_shift(operator_id) -> Shift | None` — returns shift where `operator_id` matches and `ended_at IS NULL`. |
| FR-SHIFT-003 | `close_shift(shift_id, operator_id, closing_cash_piastres) -> ShiftSummary` — verifies shift belongs to operator. Computes summary via `_compute_summary`. Sets `ended_at=utcnow()`, `closing_cash_egp`. Commits and logs `SHIFT_CLOSED`. |
| FR-SHIFT-004 | `_compute_summary(shift, closing_cash_piastres) -> ShiftSummary` — Entry shift (`shift_id`) tracks currently active sessions. Exit shift (`exit_shift_id`) tracks revenue and completed sessions. `discrepancy = closing_cash_piastres - computed_total`. |
| FR-SHIFT-005 | Gate differentiation at shift close: Gate 1 (entry) displays movement summary (`total_entered`, `active_count`, `completed_count`, `subs_count`) without cash input. Gate 2 (exit) displays cash reconciliation and discrepancy. |
| FR-SHIFT-006 | `force_close_shift(shift_id, admin_id, closing_cash_piastres, admin_note)` — allows admin to force-close an open shift with an audit note. |

---

### 2.6 Plate Service (`PlateService`)

| ID | Requirement |
|---|---|
| FR-PLATE-001 | `normalize(plate: str) -> str` — strips whitespace, converts Eastern Arabic-Indic numerals (`٠١٢٣٤٥٦٧٨٩`) to Western digits (`0123456789`), collapses multiple spaces into a single space. |
| FR-PLATE-002 | `validate(plate: str) -> bool` — validates against Egyptian format: 1–3 Arabic letters followed by 1–4 Western digits, space-separated (`^[\u0600-\u06FF](\s?[\u0600-\u06FF]){0,2} \d{1,4}$`). |
| FR-PLATE-003 | `search_normalized(plate: str) -> str` — normalizes and strips diacritics/tashkeel using NFKD decomposition for database search matching. |

---

### 2.7 Barcode & RFID Input Handling

| ID | Requirement |
|---|---|
| FR-SCAN-001 | Scan inputs use `<input type="text" inputmode="none" autocomplete="off" spellcheck="false">` to receive characters directly from USB wedge scanners without on-screen keyboards. |
| FR-SCAN-002 | Input listens for carriage return (`Enter` / keycode 13) sent by USB wedge scanners and auto-submits the form. |
| FR-SCAN-003 | Input is autofocused on load and re-focused after submission so the operator never needs to touch the screen or mouse. |
| FR-SCAN-004 | Unified scan endpoint `POST /ui/operator/api/scan` routes barcode/RFID input automatically to entry or exit based on assigned gate and card status. |

---

### 2.8 80mm / 58mm Thermal Receipt

| ID | Requirement |
|---|---|
| FR-RCPT-001 | Receipt template path: `templates/receipts/thermal.html`. Standalone HTML styled for thermal printers via `static/print.css`. |
| FR-RCPT-002 | Standard thermal receipt layout: Company name (`"garage4u"`), garage name (`"جراج باب اللوق"`), receipt type, operation number (8-digit padded session ID), card code, vehicle plate, gate number, operator name, entry time, exit time, duration, rate applied, total amount, payment method ("نقدي"), and footer: "شكراً لزيارتكم". |
| FR-RCPT-003 | Lost card receipt adds: "نوع الإيصال: كرت مفقود", "غرامة الكرت المفقود: XX ج.م". |
| FR-RCPT-004 | Auto-print: `window.print()` triggers automatically on load; redirect back to dashboard triggers after 2 seconds. |

---

### 2.9 Operator UI Templates & Gate Routing

| ID | Requirement |
|---|---|
| FR-UI-101 | Gate 1 (Entry): dedicated view `operator/entry.html` with big scan input and live ANPR plate preview. Attempting to access exit redirects to entry. |
| FR-UI-102 | Gate 2 (Exit): dedicated views `operator/exit_scan.html` and `operator/exit_confirm.html` showing full fee breakdown, subscriber status badge, and print confirmation. |
| FR-UI-103 | Lost card workflow: `operator/lost_card.html` search by plate and `operator/lost_card_confirm.html` penalty settlement. |
| FR-UI-104 | Shift templates: `operator/shift_start.html`, `operator/shift_end.html` (with conditional cash collection for exit gates vs entry stats for entry gates). |
| FR-UI-105 | All templates use Arabic RTL (`<html lang="ar" dir="rtl">`), touch-friendly dimensions (min 48px), and responsive layout. |

---

### 2.10 API Endpoints — Phase 2

#### Sessions API

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/sessions/` | operator | Open session; body: `{card_code, plate_number?}` |
| `GET` | `/api/v1/sessions/active` | admin | All currently active sessions |
| `GET` | `/api/v1/sessions/{id}` | operator, admin | Session detail |
| `PATCH` | `/api/v1/sessions/{id}/exit` | operator | Close session (exit flow with pricing) |
| `PATCH` | `/api/v1/sessions/{id}/lost-card` | operator | Resolve lost card penalty |
| `GET` | `/api/v1/sessions/{id}/receipt` | operator, admin | Receipt data model (JSON) |

#### Operator UI Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/ui/operator/dashboard` | operator | Main dashboard tailored to assigned gate |
| `GET` | `/ui/operator/entry` | operator (gate 1) | Entry scan screen |
| `POST` | `/ui/operator/entry` | operator (gate 1) | Submit entry card scan |
| `GET` | `/ui/operator/entry/confirm/{id}` | operator | Entry confirmation screen |
| `GET` | `/ui/operator/exit` | operator (gate 2) | Exit scan screen |
| `POST` | `/ui/operator/exit/lookup` | operator (gate 2) | Exit lookup & price calculation screen |
| `POST` | `/ui/operator/exit/{id}/confirm` | operator (gate 2) | Confirm exit payment & print |
| `GET` | `/ui/operator/lost-card` | operator (gate 2) | Lost card plate search screen |
| `POST` | `/ui/operator/lost-card` | operator (gate 2) | Query active sessions by plate |
| `POST` | `/ui/operator/lost-card/confirm/{id}` | operator (gate 2) | Confirm lost card penalty |
| `GET` | `/ui/operator/receipt/{id}` | operator | Thermal receipt page with auto-print |
| `POST` | `/ui/operator/api/scan` | operator | Unified scan endpoint (barcode, RFID, ANPR trigger) |
| `GET` | `/ui/operator/api/sessions/{id}/plate` | operator | Poll ANPR camera recognition result |
| `GET` | `/ui/operator/api/sessions/{id}/plate-image` | operator | Serve captured vehicle plate image |
| `POST` | `/ui/operator/api/sessions/{id}/plate-override` | operator | Manual plate override/correction |


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

### 3.1 Performance on Gate Workstation PC & LAN

| ID | Requirement |
|---|---|
| NFR-PERF-101 | Barcode and RFID lookup (`POST /ui/operator/entry`, `/ui/operator/exit/lookup`, or `/ui/operator/api/scan`) must respond with a fully rendered HTML page or JSON within **500ms** on LAN under normal load. |
| NFR-PERF-102 | `POST /api/v1/sessions/` JSON endpoint must respond within **300ms** (DB read + write, atomic transaction). |
| NFR-PERF-103 | The `PricingService.calculate()` function must complete in under **5ms** (pure Python, zero I/O after rule fetch). |
| NFR-PERF-104 | The operator dashboard page must render within **300ms** on LAN. The session counter async refresh must complete within **500ms**. |
| NFR-PERF-105 | The receipt page (`GET /ui/operator/receipt/{id}`) must load and trigger `window.print()` within **1 second** of navigation. |
| NFR-PERF-106 | Database queries for card lookup by `card_code` must use a unique index. The index on `parking_sessions.status` must exist to efficiently find active sessions. Query time must be under **50ms** in isolation. |
| NFR-PERF-107 | The application must handle simultaneous operator workstation requests across Gate 1 and Gate 2 without response time degradation beyond 20% of baseline. |
| NFR-PERF-108 | ANPR plate recognition over WebSocket (`/ws/edge`) must resolve recognition or fallback within **2.5s** (edge agent camera timeout is 2.0s). |

---

### 3.2 Reliability & Offline Tolerance

| ID | Requirement |
|---|---|
| NFR-REL-101 | If the database is temporarily unreachable during a session open or close, the server returns `503` with Arabic message: "الخادم غير متاح مؤقتاً — انتظر لحظة وحاول تاني". The operator page must display this message clearly without a raw error page. |
| NFR-REL-102 | Session open and close operations use a single database transaction. If any part fails, the entire operation rolls back — no partial state (e.g., session created but card status not updated). |
| NFR-REL-103 | The `SELECT ... FOR UPDATE` pattern is used on session close and card allocation to prevent simultaneous scans from creating race conditions. |
| NFR-REL-104 | `receipt_printed_at` is set idempotently on first receipt page load. Refreshing the receipt page does not overwrite the timestamp. |
| NFR-REL-105 | If the ESC/POS thermal printer is offline or out of paper, `window.print()` still dispatches to the OS print spooler. The system does not block gate flow on printer disconnect — receipt data remains accessible via `GET /ui/operator/receipt/{id}` for reprinting. |
| NFR-REL-106 | All monetary amounts are stored and computed as integers (piastres). Floating-point arithmetic is forbidden in `PricingService`. The Jinja2 `format_egp` filter handles display conversion (`amount / 100`) using Python `Decimal` for the display format only. |
| NFR-REL-107 | If the ANPR edge camera is offline or unreadable, entry/exit workflow continues uninterrupted with status `OFFLINE` or `UNREADABLE`, allowing optional manual plate entry or direct override. |

---

### 3.3 Security

| ID | Requirement |
|---|---|
| NFR-SEC-101 | Every session open and close route verifies the operator has an active shift via `ShiftService.require_active_shift`. An operator without an open shift receives `403` with code `NO_ACTIVE_SHIFT`. |
| NFR-SEC-102 | An operator can only close a shift that belongs to them (`shift.operator_id == current_user.id`). Attempting to close another operator's shift returns `403`. |
| NFR-SEC-103 | Gate separation is strictly enforced: Gate 1 operators (`gate_number=1`) are entry-only and cannot process exits (`/ui/operator/exit` redirects to entry). Gate 2 operators (`gate_number=2`) process exits and lost card resolutions. |
| NFR-SEC-104 | All barcode and RFID inputs are sanitized through `CardService.normalize_code` before any DB query. No raw scanner input reaches SQLAlchemy queries. |
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
| NFR-L10N-102 | All monetary amounts displayed to operators use Arabic-Indic numerals (٠١٢٣٤٥٦٧٨٩). The `format_egp` Jinja2 filter performs this conversion. Whole pounds omit decimal zeros (e.g. `١٠ ج.م`), fractional amounts show two decimals (e.g. `٢٥٫٥٠ ج.م`). |
| NFR-L10N-103 | All datetime values are displayed in `Africa/Cairo` timezone (UTC+2). Conversion from stored UTC happens in the Jinja2 `format_datetime` filter, not in the service layer. |
| NFR-L10N-104 | The receipt template uses standard ESC/POS CSS print styling (`@media print`) guaranteed to render cleanly on 80mm and 58mm thermal paper rolls. |
| NFR-L10N-105 | The dashboard live clock displays Cairo local time updated every second via a lightweight vanilla JS snippet. |

---

## 4. Edge Cases

### 4.1 Barcode & RFID Scanning Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SCAN-001 | Operator scans a card that is already `in_use` (ACTIVE session exists) on the **entry** screen | `409` with code `CARD_ALREADY_ACTIVE`. Page shows: "تم ادخال هذا الكارت بالفعل". Entry is not created. Card is not touched. |
| EC-SCAN-002 | Operator scans a card that is marked `lost` on the entry screen | `409` with code `CARD_NOT_AVAILABLE`. Page shows: "الكرت ده متعطل — تواصل مع الإدارة". |
| EC-SCAN-003 | Operator scans a card that is marked `damaged` on the entry screen | `409` with code `CARD_NOT_AVAILABLE`. Same message as EC-SCAN-002. |
| EC-SCAN-004 | Operator scans a `card_code` that does not exist in the `parking_cards` table | `404` with code `CARD_NOT_FOUND`. Page shows: "هذا الكارت غير مسجل في النظام". |
| EC-SCAN-005 | Operator scans an `available` card on the **exit** screen (no active session) | `404` with code `CARD_HAS_NO_ACTIVE_SESSION`. Page shows: "مفيش جلسة مفتوحة لهذا الكرت". |
| EC-SCAN-006 | Operator scans a `COMPLETED` session's card on the exit screen (card already freed) | Card will be `available`; falls through to EC-SCAN-005 behaviour. |
| EC-SCAN-007 | Scanner injects barcode/RFID with leading/trailing whitespace or newline characters (`\r\n`) | `CardService.normalize_code` strips whitespace before lookup. The raw input is never logged or stored. |
| EC-SCAN-008 | Scanner injects an empty string (scanner misfire) | `normalize_code` returns empty string → raises `InvalidBarcodeFormatError` → `422` with code `INVALID_BARCODE_FORMAT`. Page re-focuses input silently. |
| EC-SCAN-009 | Barcode contains lowercase letters (some card printers use mixed case) | `normalize_code` uppercases before lookup. `CARD-0042` and `card-0042` resolve to the same record. |
| EC-SCAN-010 | Barcode contains special characters outside `[A-Z0-9\-_]` (e.g., accented letters, Arabic) | `normalize_code` raises `InvalidBarcodeFormatError` → `422` with code `INVALID_BARCODE_FORMAT`. |
| EC-SCAN-011 | Two operators at different gates scan the same card within milliseconds of each other (race condition on entry) | `SELECT ... FOR UPDATE` on the card record; the second transaction sees `status = 'in_use'` and raises `CARD_ALREADY_ACTIVE`. Only one session is created. |
| EC-SCAN-012 | Two exit scans of the same card arrive simultaneously (race condition on exit) | `SELECT ... FOR UPDATE` on the session; only the first succeeds. The second receives `SESSION_NOT_ACTIVE`. |
| EC-SCAN-013 | Gate 1 operator attempts to navigate to exit route (`/ui/operator/exit`) | Gate 1 is entry-only; server redirects with `303 See Other` to `/ui/operator/entry`. |
| EC-SCAN-014 | Active subscriber card scanned at Entry | Validated against active subscription; daily entry limit enforced; opens session linked to subscriber ID without charging. |
| EC-SCAN-015 | Active subscriber card scanned at Exit | Fee computed as 0 EGP; card status remains `in_use` (assigned to subscriber); session marked `COMPLETED`. |

---

### 4.2 Session & Pricing Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SESS-001 | Exit is processed within the grace period (e.g., entry at 10:00, exit at 10:10, grace = 15 mins) | `duration_minutes = 10`, `is_grace_period = True`, `total = minimum_charge` (even if `minimum_charge = 0`). Receipt shows "ضمن فترة السماح". |
| EC-SESS-002 | Duration is exactly equal to grace period (e.g., 15 minutes exactly) | `is_grace_period = True`. `billable_minutes = 0`. Total = `minimum_charge`. |
| EC-SESS-003 | Exit is processed within the same minute as entry (duration = 0 minutes) | `duration_minutes = 0`. Treated as inside grace period. Total = `minimum_charge`. System does not divide by zero. |
| EC-SESS-004 | Duration is fractional hours (e.g., 90 minutes = 1.5 hours) | Billable hours calculated via `ceil((duration - grace) / 60)`. If tiered pricing is configured, first billable hour charged at `first_hour_charge`, subsequent hours at `subsequent_hour_charge`. Otherwise charged at `rate_per_hour * billable_hours`. |
| EC-SESS-005 | A session has been open for more than 24 hours | Pricing calculation proceeds normally. No automatic session close. Duration is displayed correctly (e.g., "٢٦ ساعة و١٥ دقيقة"). A warning flag `is_long_stay = True` is computed when `duration_minutes > 1440` for admin dashboard display only. |
| EC-SESS-006 | No active pricing rule exists when an exit is attempted | `NoPricingRuleError` raised. Exit is blocked. Page shows: "لا توجد تعريفة سعرية — تواصل مع الإدارة". Session remains ACTIVE. |
| EC-SESS-007 | Pricing rule changes between a car's entry and exit | The pricing rule active **at exit time** is used. The rule used is snapshotted into `pricing_rule_id` on the session at close time. |
| EC-SESS-008 | `minimum_charge` is zero and duration is within grace period | `total_amount = 0`. Receipt prints with "٠ ج.م". This is valid — no division or negative amounts. |
| EC-SESS-009 | `lost_card_penalty` in the pricing rule is set to zero | Lost card total = base amount only (no penalty added). Receipt does not show a penalty line. |
| EC-SESS-010 | Operator tries to exit a session opened at Gate 1 | Standard cross-gate flow: Gate 1 handles entry, Gate 2 handles exit. `exit_operator_id` and `exit_shift_id` record the exit workstation details. |

---

### 4.3 Shift Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SHIFT-001 | Operator tries to open a session without an open shift | `403` with code `NO_ACTIVE_SHIFT`. Page shows: "افتح شيفتك الأول قبل ما تبدأ". |
| EC-SHIFT-002 | Operator tries to open a second shift while first is open | `409` with code `SHIFT_ALREADY_OPEN`. |
| EC-SHIFT-003 | Gate 1 operator closes shift | Displays movement summary (`total_entered`, `active_count`, `completed_count`, `subs_count`). No cash collection fields required. |
| EC-SHIFT-004 | Gate 2 operator closes shift with active (unresolved) sessions | Shift closes successfully. Revenue summary is calculated based on `exit_shift_id`. Active sessions opened under this shift remain open for future exit. |
| EC-SHIFT-005 | `closing_cash_egp` is less than computed total (negative discrepancy) on Gate 2 | Allowed. `discrepancy_egp` is negative. Logged for supervisor review. |
| EC-SHIFT-006 | Operator's session (cookie/JWT) expires mid-shift | Operator is redirected to `/ui/login`. After re-login, their open shift is detected and they are returned to the gate screen automatically. |

---

### 4.4 Lost Card Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-LOST-001 | Plate number entered returns no active sessions | Page shows: "مفيش عربية داخلة بالنمر ده". Form is re-rendered with the plate pre-filled for correction. |
| EC-LOST-002 | Plate number returns multiple active sessions | All matching sessions are listed with gate number, entry time, and card code. Operator selects the correct vehicle. |
| EC-LOST-003 | Operator tries to resolve a session that is already COMPLETED or LOST_CARD | `409` with code `SESSION_NOT_ACTIVE`. |
| EC-LOST-004 | Lost card resolved for a session that is within the grace period | Penalty is applied on top of the grace period minimum charge: `minimum_charge + lost_card_penalty`. |
| EC-LOST-005 | The lost card's `card_code` is scanned on the entry screen after being marked `lost` | `CARD_NOT_AVAILABLE` error. Admin must manually reset it to `available` before it can be reused. |

---

### 4.5 Receipt Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-RCPT-001 | Operator navigates to receipt page but printer is offline | `window.print()` fires; browser shows system print dialog; operator dismisses. Receipt page remains accessible. "طباعة مرة أخرى" button visible. |
| EC-RCPT-002 | Operator refreshes the receipt page | `receipt_printed_at` is not updated (idempotent). `window.print()` fires again. |
| EC-RCPT-003 | Plate number was not captured (`NULL`) | Receipt shows "رقم اللوحة: غير مسجل" — never displays raw `null` or blank. |
| EC-RCPT-004 | Duration is exactly 60 minutes | Display: "ساعة واحدة". Arabic grammatical dual and singular forms handled correctly. |
| EC-RCPT-005 | Amount is 0 piastres (free parking / subscriber) | Receipt prints with "المبلغ المستحق: ٠ ج.م". |
| EC-RCPT-006 | Session ID formatting | Displayed formatted with zero-padding (e.g. `00000042`) or standard numeric representation. |

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
| `CARD_CODE_ALREADY_EXISTS` | 409 | Admin tries to create a card with an existing `card_code` |
| `ALL_CARDS_EXIST` | 409 | Bulk card creation where all requested card codes already exist |

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
| `CardService` | 100% | All status combinations, normalize_code edge cases, race condition logic, bulk creation |
| `SessionService` | 100% | All state transitions, atomic transaction verification, subscriber verification, lost card flow |
| `PricingService` | 100% | Grace period boundary, tiered pricing (first hour vs subsequent), ceiling rounding, zero duration, lost card penalty, no rule found |
| `ShiftService` | 100% | Open/close/conflict, Gate 1 movement summary, Gate 2 financial reconciliation (`exit_shift_id`) |
| `PlateService` | 100% | Eastern numeral conversion, diacritic stripping, validation edge cases |
| `format_duration` | 100% | 0 min, 1 min, 15 min, 59 min, 60 min, 90 min, 120 min, 200 min, 1440 min |
| `format_egp` | 100% | 0, 100, 2500, 99999, Arabic-Indic output with integer formatting |

### 6.2 Integration Tests

| Flow | Required Scenarios |
|---|---|
| Entry flow | Happy path, card not found, card already active, card damaged, no active shift, Gate 1 specialization |
| Exit flow | Happy path, grace period, exact grace boundary, no active session, no pricing rule, Gate 2 exit confirm |
| Lost card flow | Happy path, plate not found, multiple matches, session already closed |
| Shift flow | Open, close with summary, double-open rejected, close another's shift rejected |
| Receipt page | First load sets `receipt_printed_at`, second load does not overwrite, plate null display |
| ANPR Scan API | Unified scan endpoint triggers edge agent camera capture, polls recognition result, and supports manual override |

### 6.3 Manual QA Checklist (Gate Workstation PC & ESC/POS Thermal Printer)

- [ ] USB wedge scanner injects barcode/RFID into input and auto-submits via Enter key.
- [ ] Input field re-focuses automatically after each scan without manual mouse interaction.
- [ ] Gate 1 operator is restricted to entry flow (accessing exit redirects with 303).
- [ ] Gate 2 operator processes exit lookup and prints receipts.
- [ ] Live camera feed / capture preview triggers on card scan and updates plate number via WebSocket.
- [ ] Entry confirmation screen displays recognized plate and redirects in 3 seconds.
- [ ] Exit confirmation screen displays correct Arabic numerals for duration, tier breakdown, and total.
- [ ] Receipt prints cleanly on 80mm / 58mm ESC/POS thermal printer via browser print stylesheet (`print.css`).
- [ ] All text on thermal receipt is legible at 10pt with high contrast.
- [ ] Live clock on operator dashboard updates every second.
- [ ] Lost card plate search and penalty confirmation completes seamlessly.

---

## 7. Out of Scope for Phase 2

The following are explicitly deferred and must not be implemented in Phase 2:

- Admin reporting dashboards & subscription billing management UI (deferred to Phase 3 & 4).
- Multiple payment gateways (credit cards, Visa, mobile wallets) — Cash and active subscriptions only in Phase 2.
- Automatic time-of-day dynamic surge pricing rules.
- Multi-branch / multi-tenant database synchronization.
- SMS or WhatsApp receipt delivery.
- Push notifications for long-stay vehicles.

---

*This specification is complete when all Acceptance Criteria, Functional Requirements,
Non-Functional Requirements, and Edge Cases listed above have corresponding passing
tests, and the manual QA checklist has been signed off on Gate Workstations with USB wedge scanners and thermal printers.*
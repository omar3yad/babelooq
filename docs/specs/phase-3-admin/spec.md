# Phase 3 Specification — Admin Dashboard & Financial Reports

> **Version:** 1.0
> **Scope:** Admin dashboard overview, shift & financial management, pricing &
> rates management, reporting & filtering, CSV export, A4 print views, and Arabic
> RTL admin layout.
> **Prerequisite reading:** `constitution.md`, `master-plan.md`, `docs/specs/phase-1-core/spec.md`,
> `docs/specs/phase-2-operator/spec.md`
> **Out of scope:** Operator UI gate scanning, physical thermal receipt printing (handled in Phase 2),
> multi-branch support, automated email delivery, role-based sub-admins,
> real-time WebSocket push, Docker deployment.

---

## 1. User Stories & Acceptance Criteria

### 1.1 Admin Dashboard Overview

---

**US-301 — Live Garage Statistics**
> *As an admin, I want to see a live overview of the garage's current state the
> moment I open the dashboard, so that I can monitor operations without running
> manual queries.*

**Acceptance Criteria:**
- `GET /ui/admin/dashboard` renders within 800ms on LAN.
- The dashboard displays four KPI cards in a 2×2 grid (collapses to 1-column
  on small screens):
  1. **العربيات الداخلة حالياً** — count of sessions with `status = ACTIVE`.
  2. **نسبة الإشغال** — `(active_sessions / total_card_capacity) * 100`
     formatted as a percentage. `total_card_capacity` is the total count of
     non-`DAMAGED` cards in `parking_cards`.
  3. **إيراد اليوم** — sum of `amount_charged` for sessions with
     `status IN (COMPLETED, LOST_CARD)` where `exit_time` falls within the
     current Cairo calendar day (00:00–23:59 Cairo time). Displayed via
     `format_egp` filter.
  4. **الشيفتات الشغالة** — count of shifts where `ended_at IS NULL`.
- Each KPI card refreshes every 30 seconds via a lightweight `fetch` call to a
  dedicated JSON endpoint `GET /api/v1/admin/stats/live`. No full page reload.
- If a KPI cannot be computed (e.g., no cards in system), the card shows `—`
  with an Arabic sub-label explaining the absence.

---

**US-302 — Per-Gate Occupancy Panel**
> *As an admin, I want to see occupancy broken down by gate, so that I can
> identify which gates are busy and whether all operators are active.*

**Acceptance Criteria:**
- Below the KPI cards, a gate panel renders one row per gate (1–5).
- Each row shows: gate number, assigned operator name (or "لا يوجد عامل" if no
  active shift), shift start time, active session count for that gate, and a
  green/red status indicator (shift open / shift closed).
- Gates with no active shift show a grey row.
- The gate panel is included in the same 30-second refresh as the KPI cards.
- Clicking a gate row navigates to
  `GET /ui/admin/shifts?gate_number={n}` (the filtered shift list).

---

**US-303 — Unresolved Sessions Alert**
> *As an admin, I want to be alerted when sessions have been open for more than
> 24 hours, so that I can investigate potential problems or forgotten cards.*

**Acceptance Criteria:**
- If any session has `status = ACTIVE` and
  `entry_time < utcnow() - 24 hours`, an amber alert banner appears at the
  top of the dashboard listing the count of such sessions.
- The banner includes a link to
  `GET /ui/admin/sessions?status=ACTIVE&long_stay=true` which filters to show
  only those sessions.
- The alert is computed server-side on every dashboard load; it is not part of
  the 30-second refresh.
- If no long-stay sessions exist, the banner is not rendered (no empty element
  left in the DOM).

---

**US-304 — Unclosed Shift Alert**
> *As an admin, I want to be alerted when a shift has been open for more than
> 12 hours, so that I can follow up with the operator.*

**Acceptance Criteria:**
- A separate red alert banner appears if any shift has `ended_at IS NULL` and
  `started_at < utcnow() - 12 hours`.
- The banner lists the count and links to
  `GET /ui/admin/shifts?status=open&overdue=true`.
- Computed server-side on each dashboard load.

---

### 1.2 Shift & Financial Management

---

**US-305 — List All Shifts**
> *As an admin, I want to browse all operator shifts with filters, so that I can
> review any period's operations.*

**Acceptance Criteria:**
- `GET /ui/admin/shifts` renders a paginated table of shifts.
- Columns: shift ID, operator name, gate, start time, end time (or "مفتوح"),
  session count, computed total (sum of `amount_charged`), closing cash, cash
  discrepancy, status badge.
- Discrepancy column: green if zero, amber if within 5% of computed total, red
  otherwise. Rendered via a Jinja2 `discrepancy_class` filter.
- Supports query param filters: `operator_id`, `gate_number`, `status`
  (`open` | `closed`), `start_date` (Cairo date, `YYYY-MM-DD`),
  `end_date` (Cairo date, `YYYY-MM-DD`), `overdue` (`true`).
- Pagination: 20 rows per page, `page` query param. Total count shown.
- Filters persist in the URL so the page can be bookmarked and shared.

---

**US-306 — Shift Detail & Reconciliation**
> *As an admin, I want to view the full detail of a single shift including all
> its sessions and cash reconciliation, so that I can audit any discrepancy.*

**Acceptance Criteria:**
- `GET /ui/admin/shifts/{shift_id}` renders the shift detail page.
- Header: operator name, gate, shift open/close times, duration.
- Financial summary card: total sessions, completed, lost card, still active,
  computed total (piastres → `format_egp`), closing cash entered, discrepancy
  (`closing_cash - computed_total`), discrepancy colour-coded.
- Sessions table: paginated (10 per page), columns — session ID, card code,
  plate (or "—"), entry time, exit time, duration, amount. Table is read-only.
- An "Admin Override: Force Close Shift" button is present if `ended_at IS
  NULL`. Clicking it opens a confirmation modal before calling
  `PATCH /api/v1/admin/shifts/{id}/force-close`.
- An "Export Sessions CSV" button calls
  `GET /api/v1/admin/shifts/{id}/export/csv`.
- A "طباعة" print button navigates to
  `GET /ui/admin/reports/print?shift_id={id}`.

---

**US-307 — Force-Close a Shift (Admin Override)**
> *As an admin, I want to force-close a shift that an operator left open, so
> that financial records remain accurate and the operator can start a new shift.*

**Acceptance Criteria:**
- `PATCH /api/v1/admin/shifts/{id}/force-close` accepts an optional body:
  `{"closing_cash_egp": int, "admin_note": string}`.
- Sets `shift.ended_at = utcnow()`. Sets `closing_cash_egp` if provided.
  Sets `admin_override_note` on the shift.
- Logs `"SHIFT_FORCE_CLOSED"` in `audit_logs` with `before` (shift state) and
  `after` (updated state) payloads.
- Returns `ShiftSummaryResponse`.
- Only `role = 'admin'` may call this endpoint.
- If the shift is already closed, returns `409` with code `SHIFT_ALREADY_CLOSED`.

---

**US-308 — Pricing Rule Management**
> *As an admin, I want to create new pricing rules and activate one at a time,
> so that I can adjust garage fees without touching code.*

**Acceptance Criteria:**
- `GET /ui/admin/rates` renders the pricing management page:
  - A table of all pricing rules (newest first): ID, label, rate per hour,
    first hour charge, subsequent hour charge, grace period, minimum charge,
    lost card penalty, effective from, active badge.
  - An "إنشاء تعريفة جديدة" button opens an inline form (no page navigation).
  - Each row has an "تفعيل" button (disabled on the currently active rule).
- The inline creation form fields: label (text), rate per hour (EGP),
  first hour charge (EGP), subsequent hour charge (EGP), grace period minutes,
  minimum charge (EGP), lost card penalty (EGP), effective from (datetime-local).
- Supports tiered pricing: when `first_hour_charge > 0`, the first billable hour
  is charged at this amount and subsequent hours at `subsequent_hour_charge`.
- All EGP inputs accept decimal values and are converted to integer piastres server-side.
- On successful creation, the form clears and the new rule appears in the table.
- Activating a rule calls `PATCH /api/v1/rates/{id}/activate` and updates the
  active badge in the table without a full page reload.

---

### 1.3 Reporting & Filtering

---

**US-309 — Revenue Report**
> *As an admin, I want to view aggregated revenue for any date range, broken
> down by gate and operator, so that I can produce financial summaries for
> management.*

**Acceptance Criteria:**
- `GET /ui/admin/reports/revenue` renders the revenue report page.
- Filter bar (always visible): `start_date`, `end_date` (date pickers, default
  = current Cairo calendar day), `gate_number` (dropdown, "الكل" option),
  `operator_id` (dropdown, "الكل" option).
- Report sections rendered after filter submission:
  1. **ملخص الفترة:** total sessions (completed + lost card), total revenue
     (`format_egp`), average session duration, average revenue per session.
  2. **إيراد حسب البوابة:** one row per gate with session count and total
     revenue.
  3. **إيراد حسب نوع الخدمة:** revenue breakdown by service type (Tickets, Subscriptions, Lost Cards).
  4. **إيراد حسب العامل:** one row per operator with session count and total
     revenue.
  5. **إيراد يومي:** one row per calendar day in the range with session count
     and total revenue.
- All monetary values displayed via `format_egp` filter (Arabic-Indic numerals).
- An "Export CSV" button exports the full filtered session list.
- A "طباعة" button navigates to the A4 print view.
- Submitting the filter form updates the URL query params, making the report
  bookmarkable.

---

**US-310 — Session List Report ("دخول وخروج")**
> *As an admin, I want to search and filter all parking sessions, so that I can
> investigate specific transactions.*

**Acceptance Criteria:**
- `GET /ui/admin/sessions` renders a filterable session list titled "دخول وخروج".
- Filters: `start_date`, `end_date`, `gate_number`, `operator_id`, `status`
  (`ACTIVE` | `COMPLETED` | `LOST_CARD`), `card_code` (text, partial match
  via `LIKE`), `plate_number` (text, normalized search),
  `long_stay` (`true` shows only sessions open > 24h).
- Table columns: session ID, card code, plate, gate, operator, status badge,
  entry time, exit time, duration, amount charged.
- Quick Actions: Each ACTIVE session row includes an "تسوية إدارية" button that
  opens an inline modal to force-close and resolve the session immediately.
- Pagination: 20 rows per page. Total count shown above the table.
- Clicking a session row navigates to `GET /ui/admin/sessions/{session_id}`.
- "Export CSV" button exports all rows matching the current filter.

---

**US-311 — Session Detail & Admin Override**
> *As an admin, I want to view the complete detail of a single session, inspect
> camera plate photos, view audit trails, and override/force-close stuck sessions.*

**Acceptance Criteria:**
- `GET /ui/admin/sessions/{session_id}` renders full session detail:
  - Complete session metadata: card code, plate, gate, entry/exit operators, entry/exit timestamps,
    duration, pricing rule, amount charged, payment method, lost card flag, penalty applied.
  - **ANPR Vehicle Capture Section:** If a plate photo exists (`plate_image_path`), displays the
    captured vehicle photo, recognition confidence percentage, timestamp badge, and a high-resolution link
    (`GET /ui/admin/sessions/{id}/plate-image`). Displays visual Egyptian license plate badge
    ("مـصـر / EGYPT" with Arabic plate text).
  - **Admin Override Action Box:** If the session is `ACTIVE`, renders an admin settlement form:
    allows entering an optional amount and required override note (e.g. "كارت مسجل بالخطأ - تسوية إدارية").
    Submitting calls `POST /api/v1/admin/sessions/{id}/override-close`, which closes the session,
    frees the card to `available`, snapshots `admin_override_note`, and logs the action in audit logs.
  - **Audit Log Section:** Displays all `audit_logs` entries for the session (`action`, `actor_id`,
    `payload_before`, `payload_after`, `created_at`).

---

### 1.4 Export & Print

---

**US-312 — CSV Export**
> *As an admin, I want to export any filtered report as a CSV file, so that I
> can import the data into spreadsheets for further analysis.*

**Acceptance Criteria:**
- All CSV exports are triggered by a `GET` request with the same filter query
  params as the corresponding report page.
- The response sets headers:
  `Content-Type: text/csv; charset=utf-8`,
  `Content-Disposition: attachment; filename="pgms_report_YYYYMMDD.csv"`.
- CSV files include a UTF-8 BOM (`\ufeff`) so that Microsoft Excel opens them
  correctly with Arabic text.
- Column headers are in Arabic (e.g., `"رقم الجلسة"`, `"رمز الكرت"`).
- Monetary columns are formatted as plain decimal numbers (e.g., `25.00`) — not
  Arabic-Indic — so that spreadsheet software treats them as numbers.
- Datetime columns are formatted as `YYYY-MM-DD HH:mm` in Cairo local time.
- Empty cells render as an empty string, never `None` or `null`.
- Exports are streamed as `StreamingResponse` to avoid loading all rows into
  memory at once.

---

**US-313 — A4 Print View**
> *As an admin, I want a dedicated print-friendly page for reports that renders
> cleanly on A4 paper, so that I can produce physical records for management.*

**Acceptance Criteria:**
- `GET /ui/admin/reports/print` accepts query params: `report_type`
  (`revenue` | `sessions` | `shift`), `shift_id` (required when
  `report_type=shift`), plus all standard filter params.
- The route renders a standalone template `templates/admin/reports/print.html`
  that does **not** extend `base.html`.
- The print template sets `<html lang="ar" dir="rtl">` and uses a dedicated
  `static/admin_print.css`.
- `static/admin_print.css` defines:
  - `@page { size: A4; margin: 15mm; }`
  - `body { font-family: 'Arial', sans-serif; font-size: 11pt; direction: rtl; }`
  - All `.no-print` elements are `display: none`.
- The printed page includes: garage name, report type label, filter parameters
  used (date range, gate, operator), generation timestamp, and the full data
  table.
- Monetary values in the print view use Arabic-Indic numerals via
  `format_egp`.
- `window.print()` is called automatically via
  `window.addEventListener('load', () => window.print())`.
- A "رجوع" back link is visible on screen but hidden in print via
  `.no-print`.
- The route is accessible to `role = 'admin'` only.

---

### 1.5 Operator & Card Management

---

**US-314 — Operator List**
> *As an admin, I want to see all operators and their current shift status, so
> that I can manage staffing.*

**Acceptance Criteria:**
- `GET /ui/admin/operators` renders a table: operator name, username, gate,
  active status badge, current shift status (open/closed), last shift date.
- Links to create, deactivate, and reset password (already implemented in Phase
  1 API; this page adds the UI).
- Read-only in this phase; the existing Phase 1 API endpoints handle mutations.

---

**US-315 — Card & Barcode Management**
> *As an admin, I want to manage parking cards and barcodes from a dedicated interface,
> so that I can create, inspect, update status, and print barcode batches.*

**Acceptance Criteria:**
- `GET /ui/admin/cards` renders the cards management view.
- Provides real-time cards counter by status (`total`, `available`, `in_use`, `lost`, `damaged`).
- Provides inline form for adding a single card code (`POST /api/v1/cards/`).
- Provides bulk card generation modal (`POST /api/v1/cards/bulk`) generating ranges or sets of codes with conflict-skipping reporting.
- Supports card status updates (`available`, `lost`, `damaged`) via `PATCH /api/v1/cards/{card_code}/status`.
- Supports barcode printable sheet layout for thermal and sticker printing.

---

## 2. Functional Requirements

### 2.1 Live Statistics Service (`ReportService`)

| ID | Requirement |
|---|---|
| FR-RPT-001 | `get_live_stats(db) -> LiveStats` — returns a dataclass with: `active_sessions: int`, `total_capacity: int`, `occupancy_pct: int`, `revenue_today_piastres: int`, `open_shifts: int`. All computed in a single round-trip to the DB using one query per field (five async queries fired concurrently via `asyncio.gather`). |
| FR-RPT-002 | `revenue_today_piastres` uses Cairo midnight (UTC+2) as the day boundary. Computed as: `SUM(amount_charged) WHERE status IN ('COMPLETED','LOST_CARD') AND exit_time >= cairo_today_start AND exit_time < cairo_tomorrow_start`. Both boundary timestamps are computed in Python using `datetime.utcnow()` adjusted for UTC+2. |
| FR-RPT-003 | `occupancy_pct` is computed as `round(active_sessions * 100 / max(total_capacity, 1))`. Integer division. No floats stored. |
| FR-RPT-004 | `get_gate_panel(db) -> list[GateStatus]` — returns one `GateStatus` dataclass per gate (1–5) with: `gate_number`, `operator_name: str | None`, `operator_id: int | None`, `shift_start: datetime | None`, `active_sessions: int`. Implemented as a single JOIN query across `shifts`, `users`, and a subquery counting active sessions per gate. |
| FR-RPT-005 | `get_long_stay_count(db, threshold_hours: int = 24) -> int` — counts sessions where `status = 'ACTIVE'` and `entry_time < utcnow() - timedelta(hours=threshold_hours)`. |
| FR-RPT-006 | `get_overdue_shift_count(db, threshold_hours: int = 12) -> int` — counts shifts where `ended_at IS NULL` and `started_at < utcnow() - timedelta(hours=threshold_hours)`. |

---

### 2.2 Revenue Report Service

| ID | Requirement |
|---|---|
| FR-RPT-010 | `get_revenue_summary(filters: ReportFilters, db) -> RevenueSummary` — returns a dataclass: `total_sessions: int`, `total_revenue_piastres: int`, `avg_duration_minutes: int`, `avg_revenue_piastres: int`. Computed from sessions matching all active filters. |
| FR-RPT-011 | `get_revenue_by_gate(filters: ReportFilters, db) -> list[GateRevenue]` — one row per gate that had sessions in the period: `gate_number`, `session_count`, `total_piastres`. |
| FR-RPT-012 | `get_revenue_by_operator(filters: ReportFilters, db) -> list[OperatorRevenue]` — one row per operator: `operator_id`, `operator_name`, `session_count`, `total_piastres`. |
| FR-RPT-013 | `get_daily_revenue(filters: ReportFilters, db) -> list[DailyRevenue]` — one row per Cairo calendar day in the filter range: `date_str` (`YYYY-MM-DD`), `session_count`, `total_piastres`. Days with zero sessions still appear in the list if within the range. |
| FR-RPT-014 | `ReportFilters` is a Pydantic model (not a DB model): `start_date: date | None`, `end_date: date | None`, `gate_number: int | None` (1–5), `operator_id: int | None`, `status: SessionStatus | None`, `card_code: str | None`, `plate_number: str | None`, `long_stay: bool = False`. All fields optional. |
| FR-RPT-015 | When `start_date` and `end_date` are provided, they are Cairo calendar dates. The service converts them to UTC boundary timestamps: `start_utc = cairo_date_to_utc_start(start_date)`, `end_utc = cairo_date_to_utc_end(end_date)`. These timestamps bracket the `exit_time` column in session queries. |
| FR-RPT-016 | `avg_duration_minutes` and `avg_revenue_piastres` are computed as integer floor divisions: `total_duration // max(total_sessions, 1)` and `total_revenue // max(total_sessions, 1)`. No floats. |
| FR-RPT-017 | `get_revenue_by_service_type(filters: ReportFilters, db) -> list[ServiceTypeRevenueResponse]` — returns revenue breakdown by service category: standard tickets, active subscriptions, and lost card penalties. |

---

### 2.3 Session List & Filtering

| ID | Requirement |
|---|---|
| FR-SESS-101 | `get_sessions_filtered(filters: ReportFilters, page: int, size: int, db) -> tuple[list[ParkingSession], int]` — applies all active filter fields as SQL WHERE clauses. Returns paginated results ordered by `entry_time DESC`. |
| FR-SESS-102 | `card_code` filter uses `ILIKE '%:code%'` on PostgreSQL, `LIKE '%:code%'` on SQLite (case-insensitive prefix/suffix match). |
| FR-SESS-103 | `plate_number` filter calls `PlateService.search_normalized(plate)` then queries `plate_number LIKE '%:normalized%'`. |
| FR-SESS-104 | `long_stay=True` filter adds: `AND status = 'ACTIVE' AND entry_time < :threshold` where `threshold = utcnow() - timedelta(hours=24)`. |
| FR-SESS-105 | `get_sessions_for_export(filters: ReportFilters, db) -> AsyncIterator[ParkingSession]` — yields sessions in chunks of 500 rows using `LIMIT/OFFSET` pagination. Used by the CSV streaming route. No full result set is loaded into memory. |

---

### 2.4 Shift Management

| ID | Requirement |
|---|---|
| FR-SHIFT-101 | `get_shifts_filtered(filters: ShiftFilters, page: int, size: int, db) -> tuple[list[Shift], int]` — filters by `operator_id`, `gate_number`, `status` (`open` / `closed`), `start_date`, `end_date`, `overdue` (bool). Returns paginated results ordered by `started_at DESC`. |
| FR-SHIFT-102 | `ShiftFilters` is a Pydantic model: `operator_id: int | None`, `gate_number: int | None`, `status: Literal['open','closed'] | None`, `start_date: date | None`, `end_date: date | None`, `overdue: bool = False`. |
| FR-SHIFT-103 | `overdue=True` adds: `AND ended_at IS NULL AND started_at < :threshold` where `threshold = utcnow() - timedelta(hours=12)`. |
| FR-SHIFT-104 | `force_close_shift(shift_id: int, admin_id: int, closing_cash_piastres: int | None, admin_note: str | None, db) -> ShiftSummary` — verifies shift exists and is open. Raises `ShiftAlreadyClosedError` if `ended_at IS NOT NULL`. Sets `ended_at = utcnow()`. Optionally sets `closing_cash_egp`. Sets `admin_override_note`. Commits. Logs `"SHIFT_FORCE_CLOSED"`. Returns `ShiftSummary`. |
| FR-SHIFT-105 | The discrepancy for a shift is always computed at query time, never stored. It is `shift.closing_cash_egp - computed_total_from_sessions`. If `closing_cash_egp IS NULL`, discrepancy is `NULL`. |

---

### 2.5 Pricing Management

| ID | Requirement |
|---|---|
| FR-RATE-101 | `create_pricing_rule(data: PricingRuleCreate, admin_id: int, db) -> PricingRule` — validates all monetary fields are non-negative integers (piastres). `effective_from` defaults to `utcnow()` if not provided. The new rule is created with `is_active = FALSE`. Returns the created rule. |
| FR-RATE-102 | `activate_pricing_rule(rule_id: int, admin_id: int, db) -> PricingRule` — sets `is_active = FALSE` on all other rules in a single UPDATE, then sets `is_active = TRUE` on the target rule. Both changes in one transaction. Logs `"RATE_ACTIVATED"`. Raises `PricingRuleNotFoundError` if the rule does not exist. |
| FR-RATE-103 | The `PricingRuleCreate` Pydantic schema accepts EGP values as `float` input fields (e.g., `rate_per_hour_egp: float`, `first_hour_charge_egp`, `subsequent_hour_charge_egp`) which are converted to piastres by `round(value * 100)` in the schema validator. The stored column is always `INTEGER` (piastres). |
| FR-RATE-104 | Pricing rule labels must be unique. Attempting to create a rule with a duplicate label returns `409` with code `RATE_LABEL_ALREADY_EXISTS`. |

---

### 2.6 CSV Export

| ID | Requirement |
|---|---|
| FR-CSV-001 | All CSV export routes return `StreamingResponse` with `media_type="text/csv"` and a UTF-8 BOM as the first bytes of the stream. |
| FR-CSV-002 | CSV generation uses Python's built-in `csv.writer` (no external library). Rows are yielded from an async generator, encoded to `UTF-8`, and streamed. |
| FR-CSV-003 | The `Content-Disposition` header filename uses the current Cairo date: `pgms_sessions_20240815.csv`. |
| FR-CSV-004 | **Session CSV columns (in order):** `رقم الجلسة`, `رمز الكرت`, `رقم اللوحة`, `البوابة`, `العامل`, `وقت الدخول`, `وقت الخروج`, `المدة (دقيقة)`, `الحالة`, `المبلغ (جنيه)`, `كرت مفقود`, `طريقة الدفع`. |
| FR-CSV-005 | **Shift CSV columns (in order):** `رقم الشيفت`, `العامل`, `البوابة`, `بداية الشيفت`, `نهاية الشيفت`, `عدد الجلسات`, `الإجمالي المحسوب (جنيه)`, `الكاش الختامي (جنيه)`, `الفرق (جنيه)`. |
| FR-CSV-006 | Monetary values in CSV are written as plain two-decimal-place strings using Python `f"{piastres / 100:.2f}"` (Latin digits, dot decimal separator). This is intentional for spreadsheet compatibility. |
| FR-CSV-007 | `None` / `NULL` values render as empty strings `""` in CSV. Booleans render as `"نعم"` / `"لا"`. |
| FR-CSV-008 | Cairo local datetime rendering for CSV: `(utc_dt + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")`. No external timezone library. |

---

### 2.7 Admin UI Layout

| ID | Requirement |
|---|---|
| FR-UI-301 | `templates/admin/base_admin.html` is a base template setting `<html lang="ar" dir="rtl">` and includes a fixed RTL sidebar navigation. |
| FR-UI-302 | The sidebar navigation links: لوحة التحكم (`/ui/admin/dashboard`), الشيفتات (`/ui/admin/shifts`), دخول وخروج (`/ui/admin/sessions`), التقارير (`/ui/admin/reports/revenue`), التعريفات (`/ui/admin/rates`), المشغلين (`/ui/admin/operators`), إدارة الكروت (`/ui/admin/cards`), تسجيل خروج (POST `/ui/logout`). |
| FR-UI-303 | The sidebar is collapsible on small screens via a hamburger button. Collapse state is stored in `localStorage` under key `"pgms_sidebar_collapsed"`. |
| FR-UI-304 | All admin templates extend `templates/admin/base_admin.html` via `{% extends "admin/base_admin.html" %}`. |
| FR-UI-305 | All admin pages are accessible only to `role = 'admin'`. Unauthorized access redirects to `/ui/login` with a query param `?next=<attempted_path>`. |
| FR-UI-306 | Filter forms on all admin list pages use `method="GET"` so filters are reflected in the URL and the page is bookmarkable. |
| FR-UI-307 | All admin data tables include a visible row count: "عرض ١–٢٠ من ١٢٥ نتيجة". |
| FR-UI-308 | Pagination controls render as: « prev | page numbers | next ». Arabic Indic numerals for page numbers via `to_arabic_indic`. Active page is visually highlighted. |
| FR-UI-309 | Status badges use Tailwind utility classes: `ACTIVE` → green, `COMPLETED` → blue, `LOST_CARD` → amber, shift open → green, shift closed → grey. |
| FR-UI-310 | All admin pages load from `/static/css/tailwind.min.css` (locally built). No external CDN calls. |

---

### 2.8 API Endpoints — Phase 3

#### Admin Stats

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/admin/stats/live` | admin | Returns `LiveStatsResponse` JSON for dashboard refresh |
| `GET` | `/api/v1/admin/stats/gates` | admin | Returns `list[GateStatusResponse]` for gate panel refresh |
| `GET` | `/api/v1/admin/stats/subscriptions` | admin | Returns subscriber & plan performance metrics JSON |

#### Admin Sessions

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/admin/sessions` | admin | Filtered, paginated session list |
| `GET` | `/api/v1/admin/sessions/{id}` | admin | Full session detail with audit log |
| `POST` | `/api/v1/admin/sessions/{id}/override-close` | admin | Force-close active session with admin note & optional charge |
| `GET` | `/api/v1/admin/sessions/{id}/export/csv` | admin | Streaming CSV of filtered sessions |

#### Admin Shifts

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/admin/shifts` | admin | Filtered, paginated shift list |
| `GET` | `/api/v1/admin/shifts/{id}` | admin | Shift detail with session summary |
| `GET` | `/api/v1/admin/shifts/{id}/export/csv` | admin | CSV of sessions for one shift |
| `PATCH` | `/api/v1/admin/shifts/{id}/force-close` | admin | Force-close an open shift |

#### Admin Reports

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/admin/reports/revenue` | admin | Revenue summary + breakdowns (gate, operator, service type) JSON |
| `GET` | `/api/v1/admin/reports/daily` | admin | Daily revenue rows JSON |
| `GET` | `/api/v1/admin/reports/subscriptions` | admin | Subscriptions revenue breakdown JSON |
| `GET` | `/api/v1/admin/reports/export/csv` | admin | Streaming CSV of filtered revenue sessions |

#### Admin UI Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/ui/admin/dashboard` | admin | Main dashboard HTML |
| `GET` | `/ui/admin/shifts` | admin | Shift list HTML |
| `GET` | `/ui/admin/shifts/{id}` | admin | Shift detail HTML |
| `GET` | `/ui/admin/sessions` | admin | Session list HTML ("دخول وخروج") |
| `GET` | `/ui/admin/sessions/{id}` | admin | Session detail HTML |
| `GET` | `/ui/admin/sessions/{id}/plate-image` | admin | Serve entry ANPR vehicle plate capture image |
| `GET` | `/ui/admin/sessions/{id}/exit-image` | admin | Serve exit ANPR vehicle plate capture image |
| `GET` | `/ui/admin/reports/revenue` | admin | Revenue report HTML |
| `GET` | `/ui/admin/reports/print` | admin | A4 print view HTML |
| `GET` | `/ui/admin/rates` | admin | Pricing management HTML |
| `GET` | `/ui/admin/operators` | admin | Operator list HTML |
| `GET` | `/ui/admin/cards` | admin | Card & barcode management HTML |

---

### 2.9 New Pydantic Schemas

| Schema | Fields |
|---|---|
| `LiveStatsResponse` | `active_sessions: int`, `total_capacity: int`, `occupancy_pct: int`, `revenue_today_piastres: int`, `open_shifts: int` |
| `GateStatusResponse` | `gate_number: int`, `operator_name: str | None`, `operator_id: int | None`, `shift_start: datetime | None`, `active_sessions: int` |
| `RevenueSummaryResponse` | `total_sessions: int`, `total_revenue_piastres: int`, `avg_duration_minutes: int`, `avg_revenue_piastres: int` |
| `GateRevenueResponse` | `gate_number: int`, `session_count: int`, `total_piastres: int` |
| `OperatorRevenueResponse` | `operator_id: int`, `operator_name: str`, `session_count: int`, `total_piastres: int` |
| `DailyRevenueResponse` | `date_str: str`, `session_count: int`, `total_piastres: int` |
| `ReportFilters` | All fields from FR-RPT-014 |
| `ShiftFilters` | All fields from FR-SHIFT-102 |
| `ForceCloseShiftRequest` | `closing_cash_egp: int | None`, `admin_note: str | None` |
| `AdminSessionDetail` | All `SessionResponse` fields + `audit_logs: list[AuditLogResponse]` |

---

### 2.10 New SQLAlchemy Models / Column Additions

| ID | Requirement |
|---|---|
| FR-MDL-301 | Add `admin_override_note: Mapped[str | None]` to the `Shift` model if not already present (TEXT, nullable). |
| FR-MDL-302 | No other new tables are required for Phase 3. All data is derived from existing tables via query-time aggregation. |
| FR-MDL-303 | A new Alembic migration adds the `admin_override_note` column to `shifts` if absent. Migration message: `"phase3_shift_admin_override_note"`. |

---

### 2.11 New Jinja2 Filters & Helpers

| ID | Requirement |
|---|---|
| FR-JINJA-301 | `discrepancy_class(discrepancy_piastres: int | None) -> str` — returns a Tailwind CSS class string: `"text-green-600"` if 0, `"text-amber-500"` if `abs(discrepancy) / max(computed_total, 1) <= 0.05`, `"text-red-600"` otherwise. Returns `"text-gray-400"` if `None`. |
| FR-JINJA-302 | `cairo_date(dt: datetime | None) -> str` — converts UTC datetime to Cairo local date string `"YYYY-MM-DD"`. Returns `"—"` if `None`. |
| FR-JINJA-303 | `session_status_label(status: str) -> str` — returns Arabic label: `"ACTIVE"` → `"داخل"`, `"COMPLETED"` → `"خرج"`, `"LOST_CARD"` → `"كرت مفقود"`. |
| FR-JINJA-304 | `shift_status_label(shift: Shift) -> str` — returns `"مفتوح"` if `ended_at IS NULL`, else `"مغلق"`. |
| FR-JINJA-305 | Register `zfill` as a Jinja2 filter: `lambda s, w: str(s).zfill(w)`. Used for session ID display: `{{ session.id | zfill(8) }}`. |
| FR-JINJA-306 | All new filters are registered in `utils/jinja.py` inside `create_jinja2_environment`. No filter logic lives in templates. |

---

### 2.12 New Translations (`translations/ar.json` additions)

Add the following keys:

```json
"admin.dashboard.title": "لوحة التحكم",
"admin.dashboard.active_vehicles": "العربيات الداخلة حالياً",
"admin.dashboard.occupancy": "نسبة الإشغال",
"admin.dashboard.revenue_today": "إيراد اليوم",
"admin.dashboard.open_shifts": "الشيفتات الشغالة",
"admin.dashboard.long_stay_alert": "جلسات مفتوحة أكثر من ٢٤ ساعة",
"admin.dashboard.overdue_shift_alert": "شيفتات مفتوحة أكثر من ١٢ ساعة",
"admin.shifts.title": "الشيفتات",
"admin.shifts.force_close": "إغلاق الشيفت إدارياً",
"admin.shifts.force_close_confirm": "هل أنت متأكد من إغلاق هذا الشيفت؟",
"admin.sessions.title": "الجلسات",
"admin.reports.revenue_title": "تقرير الإيراد",
"admin.reports.print_title": "تقرير مطبوع",
"admin.rates.title": "التعريفات السعرية",
"admin.rates.create": "إنشاء تعريفة جديدة",
"admin.rates.activate": "تفعيل",
"admin.operators.title": "العمال",
"admin.nav.dashboard": "داشبورد",
"admin.nav.shifts": "الشيفتات",
"admin.nav.sessions": "الجلسات",
"admin.nav.reports": "التقارير",
"admin.nav.rates": "التعريفات",
"admin.nav.operators": "العمال",
"admin.nav.logout": "تسجيل خروج",
"admin.export.csv_button": "تصدير CSV",
"admin.print.button": "طباعة",
"admin.filter.start_date": "من تاريخ",
"admin.filter.end_date": "إلى تاريخ",
"admin.filter.all_gates": "كل البوابات",
"admin.filter.all_operators": "كل العمال",
"admin.filter.submit": "تطبيق الفلتر",
"admin.table.no_results": "لا توجد نتائج للفلتر المحدد",
"admin.pagination.showing": "عرض {from}–{to} من {total} نتيجة"
```

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement |
|---|---|
| NFR-PERF-301 | `GET /api/v1/admin/stats/live` must respond within **200ms** under normal load. All five sub-queries are fired concurrently via `asyncio.gather`. |
| NFR-PERF-302 | `GET /ui/admin/dashboard` (full page) must respond within **800ms** on LAN. |
| NFR-PERF-303 | `GET /ui/admin/shifts` and `GET /ui/admin/sessions` (filtered list pages) must respond within **1000ms** on LAN for up to 10,000 total rows in the table. |
| NFR-PERF-304 | CSV export for up to 10,000 rows must begin streaming within **500ms** of the request. The stream must complete within **5 seconds**. |
| NFR-PERF-305 | All aggregate queries (revenue sums, session counts) must use indexed columns. The following indexes must exist or be created in the Phase 3 migration: `parking_sessions(exit_time)`, `parking_sessions(entry_time)`, `parking_sessions(status)`, `shifts(started_at)`, `shifts(ended_at)`. |
| NFR-PERF-306 | The `get_daily_revenue` query must not perform one query per day. It must use a single SQL `GROUP BY` query and then fill missing days in Python. |
| NFR-PERF-307 | The 30-second dashboard refresh must call two endpoints (`/stats/live` and `/stats/gates`) with separate `fetch` calls. Neither call blocks the other or blocks the main thread. |

---

### 3.2 Security

| ID | Requirement |
|---|---|
| NFR-SEC-301 | Every admin route (both `/ui/admin/*` and `/api/v1/admin/*`) uses `Depends(require_admin)`. A request from a user with `role = 'operator'` returns `403` with code `INSUFFICIENT_PERMISSIONS`. |
| NFR-SEC-302 | `PATCH /api/v1/admin/shifts/{id}/force-close` and `POST /api/v1/admin/sessions/{id}/override-close` log the admin's `actor_id` and full `before`/`after` state in `audit_logs`. This log must be written before the commit. If the audit log write fails, the override is still committed (per `docs/specs/phase-1-core/spec.md` FR-AUDIT-005). |
| NFR-SEC-303 | All filter query params are validated by Pydantic before reaching any SQL query. `start_date` and `end_date` must be valid `date` objects; invalid formats return `422`. |
| NFR-SEC-304 | `card_code` and `plate_number` filter values are sanitized before being used in `LIKE` queries: percent signs (`%`) and underscores (`_`) within the user input are escaped so they are treated as literals, not SQL wildcards. |
| NFR-SEC-305 | CSV export filenames are constructed from the server-side Cairo date only. No user input is included in the filename. |
| NFR-SEC-306 | The A4 print route computes all data server-side. No client-supplied data is rendered without escaping. Jinja2 auto-escaping is always on. |
| NFR-SEC-307 | The admin dashboard refresh JS does not use `innerHTML` to insert fetched data. It uses safe DOM methods (`textContent`, `setAttribute`) only. |

---

### 3.3 Reliability & Data Integrity

| ID | Requirement |
|---|---|
| NFR-REL-301 | All revenue and session aggregations use `COALESCE(SUM(amount_charged), 0)` so they return `0` rather than `NULL` when no rows match the filter. |
| NFR-REL-302 | `force_close_shift` uses an optimistic check: fetch shift, verify `ended_at IS NULL`, then update. If the shift was closed between the fetch and the update (concurrent request), the UPDATE affects 0 rows; the service detects this and raises `ShiftAlreadyClosedError`. |
| NFR-REL-303 | The CSV streaming generator must handle `GeneratorExit` gracefully: if the client disconnects mid-stream, the async generator exits cleanly without leaving an open DB cursor. |
| NFR-REL-304 | If `asyncio.gather` in `get_live_stats` raises an exception in any sub-query, the exception is caught per sub-query and that stat is returned as `0` (not a 500 error). The dashboard renders with a `—` on the affected card. |
| NFR-REL-305 | Date range filters: if `start_date > end_date`, the API returns `422` with code `INVALID_DATE_RANGE` and a descriptive message. |

---

### 3.4 Localization

| ID | Requirement |
|---|---|
| NFR-L10N-301 | All monetary values in admin UI use `format_egp` filter (Arabic-Indic numerals). Exception: CSV export uses Latin numerals for spreadsheet compatibility (FR-CSV-006). |
| NFR-L10N-302 | All datetime values in admin UI use `format_datetime` filter (Cairo local time, Arabic-Indic numerals). |
| NFR-L10N-303 | All admin date filter inputs use `<input type="date">` with `lang="ar"`. The submitted value is a plain `YYYY-MM-DD` string regardless of browser locale. |
| NFR-L10N-304 | The admin sidebar and all headings use translation keys from `translations/ar.json`. No Arabic strings are hardcoded in templates. |
| NFR-L10N-305 | Pagination display uses Arabic-Indic numerals via `to_arabic_indic` filter: "عرض ١–٢٠ من ١٢٥ نتيجة". |
| NFR-L10N-306 | The print CSS sets `font-family: 'Arial', sans-serif` which has adequate Arabic glyph coverage on Windows and macOS. No web font is loaded for print (avoids network dependency during printing). |

---

### 3.5 Maintainability

| ID | Requirement |
|---|---|
| NFR-MNT-301 | `ReportService` is a single class in `services/report_service.py`. All aggregation methods are async. No HTTP concepts (`Request`, `Response`, `HTTPException`) appear in this file. |
| NFR-MNT-302 | `ReportFilters` and `ShiftFilters` are Pydantic models, not SQLAlchemy models and not dataclasses. They are the single source of truth for filter parameters, used by both API routes and service methods. |
| NFR-MNT-303 | Cairo timezone arithmetic is implemented once in `utils/time.py` as module-level pure functions: `cairo_today_start() -> datetime`, `cairo_date_to_utc_start(d: date) -> datetime`, `cairo_date_to_utc_end(d: date) -> datetime`. All services import from `utils/time.py`. No time conversion logic is duplicated. |
| NFR-MNT-304 | CSV generation is implemented in `utils/csv_export.py` as async generator functions, one per export type. Routes call these generators and wrap them in `StreamingResponse`. No CSV logic lives in route handlers. |
| NFR-MNT-305 | The `discrepancy_class` Jinja2 filter is a pure function with no imports from the project. It takes only `int | None` arguments. |

---

## 4. Edge Cases

### 4.1 Dashboard & Stats Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-ADM-001 | No cards exist in `parking_cards` table (`total_capacity = 0`) | `occupancy_pct = 0`. KPI card shows `٠٪`. No division by zero (guarded by `max(capacity, 1)`). |
| EC-ADM-002 | No sessions have been completed today | `revenue_today_piastres = 0`. KPI card shows `٠٫٠٠ ج.م`. |
| EC-ADM-003 | All five gates have no active operator | Gate panel shows all five rows in grey with "لا يوجد عامل". No error. |
| EC-ADM-004 | Admin opens dashboard at 23:58 Cairo time; the day boundary crosses during the 30-second refresh | The next refresh naturally returns the new day's stats (which will be 0 or near-0). No special handling required. |
| EC-ADM-005 | `asyncio.gather` sub-query for `open_shifts` fails due to DB timeout | `open_shifts` returns `0` in the response; other stats are unaffected. Dashboard card shows `—`. Error is logged at `ERROR` level. |

---

### 4.2 Reporting & Filter Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-RPT-001 | `start_date = end_date` (single day report) | Valid. UTC boundaries: start = Cairo midnight, end = Cairo midnight + 24h. |
| EC-RPT-002 | `start_date > end_date` | `422` with `code = "INVALID_DATE_RANGE"` and Arabic message. |
| EC-RPT-003 | Date range spans 365 days | Valid. `get_daily_revenue` returns 365 rows. Performance is bounded by the index on `exit_time`. |
| EC-RPT-004 | `operator_id` filter value refers to a deactivated operator | Results include their sessions (historical data is preserved). No filter error. |
| EC-RPT-005 | `card_code` filter contains SQL wildcard `%` | Escaped to `\%` before use in LIKE query. Returns literal matches only. |
| EC-RPT-006 | Filter returns zero results | Report sections show `٠` counts and `٠٫٠٠ ج.م` totals. CSV export returns a file with headers only (no data rows). Print view renders with empty table and "لا توجد نتائج". |
| EC-RPT-007 | `long_stay=True` filter with no long-stay sessions | Returns empty list. No error. |
| EC-RPT-008 | Revenue report with no `start_date` or `end_date` | Defaults to current Cairo calendar day. `start_date` defaults to `cairo_today_start()`, `end_date` defaults to `cairo_date_to_utc_end(today)`. |

---

### 4.3 Shift & Session Override Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SHIFT-301 | Admin force-closes a shift that was already closed by the operator concurrently | `409` with `code = "SHIFT_ALREADY_CLOSED"`. |
| EC-SHIFT-302 | Force-close called on a shift with still-ACTIVE sessions | Shift closes. `active_sessions` count in `ShiftSummary` is non-zero. A warning is included in the response: `"has_unresolved_sessions": true`. |
| EC-SHIFT-303 | `closing_cash_egp` not provided on force-close | `closing_cash_egp` remains `NULL` in DB. Discrepancy is `NULL`. |
| EC-SHIFT-304 | Shift list filtered by `overdue=true` returns a shift that was closed while the page was loading | The closed shift appears in results if it was open at query time. No error. Next page load will exclude it. |
| EC-SHIFT-305 | Admin attempts force-close on a shift not belonging to any gate (corrupted data) | Force-close proceeds. No gate validation on admin force-close. |
| EC-SESS-301 | Admin override-closes an ACTIVE session | Session is marked `COMPLETED`, card status reset to `available`, `admin_override_note` saved, and action logged in audit log. |
| EC-SESS-302 | Admin override-closes a session already completed | `409` with code `SESSION_NOT_ACTIVE`. |

---

### 4.4 Pricing Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-RATE-301 | Admin creates a rule with the same label as an existing rule | `409` with `code = "RATE_LABEL_ALREADY_EXISTS"`. |
| EC-RATE-302 | Admin activates the currently active rule | Idempotent. The rule remains active. The deactivation UPDATE affects all other rules (0 rows if there are none). Returns `200` with the rule unchanged. |
| EC-RATE-303 | `rate_per_hour_egp = 0.0` submitted on rule creation | Valid (free parking). Stored as `0` piastres. |
| EC-RATE-304 | `lost_card_penalty = 0.0` | Valid. No penalty applied on lost card. |
| EC-RATE-305 | `rate_per_hour_egp = 5.555` (more than 2 decimal places) | `round(5.555 * 100) = 556` piastres. No error; value is rounded. |
| EC-RATE-306 | Admin deletes a pricing rule that is referenced by existing sessions | Deletion is not supported in Phase 3. The admin can only create and activate rules. Old rules are kept for historical reference. |

---

### 4.5 CSV Export Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-CSV-001 | Client disconnects during CSV stream | `GeneratorExit` is caught in the async generator; DB cursor is closed cleanly. No error logged above `INFO` level. |
| EC-CSV-002 | Export for 0 matching sessions | CSV file contains BOM + header row only. `Content-Length` is not set (streaming). File is valid and opens in Excel. |
| EC-CSV-003 | Session has `plate_number = NULL` | CSV cell renders as `""` (empty string). |
| EC-CSV-004 | Session has `amount_charged = NULL` (ACTIVE session included via filter) | CSV cell renders as `""`. |
| EC-CSV-005 | Export requested while another export is running for the same admin | Both proceed independently. No locking. Server memory impact is bounded by chunk size (500 rows). |

---

### 4.6 Print View Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-PRINT-001 | `report_type=shift` requested without `shift_id` | `422` with code `SHIFT_ID_REQUIRED_FOR_PRINT`. |
| EC-PRINT-002 | `shift_id` refers to a non-existent shift | `404` with `code = "SHIFT_NOT_FOUND"`. |
| EC-PRINT-003 | Print view for revenue report with 500 daily rows | All rows are rendered (no pagination on print view). If > 500 rows, a server-side limit truncates at 500 rows and a note is printed: "ملاحظة: يتم عرض أول ٥٠٠ نتيجة فقط". |
| EC-PRINT-004 | Admin prints and then navigates back using browser back button | The "رجوع" link (`.no-print`) is visible on screen and provides an explicit back navigation. Browser back also works. |

---

## 5. Defined Error Codes

All error responses: `{"detail": "<message>", "code": "<CODE>"}`.

### 5.1 Reporting Errors

| Code | HTTP | Trigger |
|---|---|---|
| `INVALID_DATE_RANGE` | 422 | `start_date > end_date` in filter |
| `INVALID_GATE_NUMBER` | 422 | `gate_number` outside 1–5 |
| `OPERATOR_NOT_FOUND` | 404 | `operator_id` filter refers to non-existent user |

### 5.2 Shift & Session Admin Errors

| Code | HTTP | Trigger |
|---|---|---|
| `SHIFT_NOT_FOUND` | 404 | `shift_id` does not exist |
| `SHIFT_ALREADY_CLOSED` | 409 | Force-close on an already-closed shift |
| `SESSION_NOT_FOUND` | 404 | `session_id` does not exist on override close |
| `SESSION_NOT_ACTIVE` | 409 | Attempting override close on a non-ACTIVE session |
| `INSUFFICIENT_PERMISSIONS` | 403 | Non-admin accesses admin endpoint |

### 5.3 Pricing Errors

| Code | HTTP | Trigger |
|---|---|---|
| `RATE_LABEL_ALREADY_EXISTS` | 409 | Duplicate pricing rule label on creation |
| `PRICING_RULE_NOT_FOUND` | 404 | `rule_id` does not exist |
| `NO_ACTIVE_PRICING_RULE` | 503 | No `is_active=TRUE` rule when previewing |

### 5.4 Export & Print Errors

| Code | HTTP | Trigger |
|---|---|---|
| `SHIFT_ID_REQUIRED_FOR_PRINT` | 422 | `report_type=shift` without `shift_id` |
| `INVALID_REPORT_TYPE` | 422 | `report_type` not one of `revenue`, `sessions`, `shift` |

### 5.5 General

| Code | HTTP | Trigger |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing or invalid JWT |
| `DATABASE_UNAVAILABLE` | 503 | DB unreachable during request |
| `INTERNAL_ERROR` | 500 | Unhandled exception (sanitized in production) |

---

## 6. Out of Scope for Phase 3

The following are explicitly deferred and must not be implemented during Phase 3:

- Real-time WebSocket push for dashboard updates (polling via `fetch` is used
  instead).
- Interactive charts or graphs (bar charts, line charts) for revenue data.
  Data tables only in Phase 3.
- Automated email or SMS delivery of reports.
- Role-based sub-admins (e.g., supervisor role with read-only access).
- Multi-branch or multi-garage support.
- Editing or deleting existing parking sessions by admin.
- PDF export (only CSV and browser print in Phase 3).
- Automated scheduled reports (cron jobs, task queues).
- Dark mode for the admin dashboard.
- Advanced search with full-text indexing.
- Admin activity log UI (audit logs are stored but only shown per-session in
  Phase 3).
- Operator performance scoring or gamification.
- Integration with external accounting software.
- Two-factor authentication for admin accounts.

---

## 7. File Structure Additions for Phase 3

```
pgms/
├── services/
│   └── report_service.py              # ReportService: all aggregation methods
├── repositories/
│   ├── report_repo.py                 # Raw SQL aggregation queries
│   └── admin_shift_repo.py            # Admin filtered shift queries
├── routes/
│   ├── admin_api.py                   # /api/v1/admin/* JSON endpoints
│   └── ui_admin.py                    # /ui/admin/* HTML routes
├── schemas/
│   └── admin_reports.py               # LiveStatsResponse, RevenueSummaryResponse, etc.
├── utils/
│   ├── time.py                        # cairo_today_start(), cairo_date_to_utc_*()
│   └── csv_export.py                  # Async CSV generator functions
├── templates/
│   └── admin/
│       ├── base_admin.html            # Admin base with RTL sidebar
│       ├── dashboard.html
│       ├── shifts.html
│       ├── shift_detail.html
│       ├── sessions.html
│       ├── session_detail.html
│       ├── rates.html
│       ├── operators.html
│       ├── cards.html
│       └── reports/
│           ├── revenue.html
│           ├── print.html             # Standalone A4 print template
│           ├── _print_revenue.html
│           ├── _print_sessions.html
│           └── _print_shift.html
└── static/
    └── admin_print.css                # A4 print stylesheet
```

---

*This specification is complete when all Acceptance Criteria, Functional
Requirements, Non-Functional Requirements, and Edge Cases listed above have
corresponding passing tests, and the manual QA checklist in `tasks.md` has been signed off.*
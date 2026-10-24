# Phase 4 Specification — Subscription Management System

> **Version:** 1.0
> **Scope:** Subscription plans, subscriber management, subscription lifecycle,
> automated entry/exit for subscribed vehicles, admin UI, reporting, and
> expiry alerts.
> **Prerequisite reading:** `docs/constitution.md`, `docs/master-plan.md`,
> `docs/specs/phase-1-core/spec.md`, `docs/specs/phase-2-operator/spec.md`,
> `docs/specs/phase-3-admin/spec.md`
> **Out of scope:** Online payment gateway integration, SMS/email notifications,
> mobile app for subscribers, multi-branch subscriptions, family/fleet plans,
> automatic renewal charging, QR code generation for subscribers.

---

## 1. Context & Core Concept

### 1.1 The Problem Being Solved

The existing system charges every entry by duration. Some customers park daily
and pay a predictable fixed amount every month. For them — and for the garage
owner — a flat monthly subscription is better than per-hour billing.

### 1.2 The Mental Model

Regular vehicle: Scan card → open session → pay on exit (hourly)
Subscribed vehicle: Scan card → system checks active subscription →
enter free → exit free → receipt says "اشتراك"


### 1.3 How It Fits the Existing Architecture

The subscription system is an **overlay** on the existing session system.
`ParkingSession` is reused unchanged in structure; two new columns
(`subscription_id`, `is_subscribed`) are added. `SessionService.open_session`
and `SessionService.close_session` gain a subscription awareness check.
No existing service is rewritten — only extended.

---

## 2. User Stories & Acceptance Criteria

### 2.1 Admin — Subscription Plan Management

---

**US-401 — Create a Subscription Plan**
> *As an admin, I want to create named subscription plans with a fixed price
> and duration, so that I can offer different tiers to customers.*

**Acceptance Criteria:**
- `GET /ui/admin/plans` renders the plan management page with a list of all
  existing plans and an inline creation form.
- The creation form fields: plan label (text, required), duration in days
  (integer, required, min 1), price in EGP (decimal, required, min 0),
  max entries per day (integer, optional — leave blank for unlimited),
  description (text, optional).
- `POST /api/v1/subscriptions/plans` creates the plan. Price is stored as
  integer piastres (`round(egp * 100)`). No float columns in the DB.
- On success, the new plan appears in the table without a full page reload.
- Duplicate plan labels return `409` with code `PLAN_LABEL_ALREADY_EXISTS`.
- A plan with `duration_days = 30` and `price = 150000` piastres represents
  a monthly plan at 1500 EGP.
- Plans are created with `is_active = TRUE` by default.
- Creation is recorded in `audit_logs` with action `PLAN_CREATED`.

---

**US-402 — Deactivate a Subscription Plan**
> *As an admin, I want to deactivate a plan so that no new subscriptions can
> be created under it, while existing active subscriptions continue normally.*

**Acceptance Criteria:**
- `PATCH /api/v1/subscriptions/plans/{id}/deactivate` sets
  `is_active = FALSE`.
- Existing subscriptions on this plan are not affected — they continue until
  their `end_date`.
- Deactivated plans are hidden from the "new subscription" form dropdown but
  remain visible in the plan list with a "غير نشط" badge.
- Attempting to create a new subscription under a deactivated plan returns
  `409` with code `PLAN_NOT_ACTIVE`.
- Deactivation is logged with action `PLAN_DEACTIVATED`.

---

**US-403 — Edit a Subscription Plan**
> *As an admin, I want to edit a plan's label, price, and description, so
> that I can update pricing without creating a new plan.*

**Acceptance Criteria:**
- `PATCH /api/v1/subscriptions/plans/{id}` accepts `label`, `price_egp`,
  `description`, `max_entries_per_day` as optional fields. Only provided
  fields are updated.
- `duration_days` cannot be edited after creation (it would invalidate
  existing subscriptions' end dates).
- Price changes do not affect existing subscriptions — only new ones created
  after the change.
- Edit is logged with action `PLAN_UPDATED` including `before` and `after`
  payloads.

---

### 2.2 Admin — Subscriber Management

---

**US-404 — Create a Subscriber**
> *As an admin, I want to register a subscriber's vehicle and personal details,
> so that I can link a subscription plan to a specific plate number.*

**Acceptance Criteria:**
- `GET /ui/admin/subscribers/new` renders the subscriber creation form.
- Required fields: `full_name` (text), `plate_number` (Arabic RTL input with
  `PlateService` normalization).
- Optional fields: `phone_number` (text, max 20 chars), `notes` (textarea).
- `POST /api/v1/subscriptions/subscribers` creates the subscriber record.
- `plate_number` is normalized via `PlateService.normalize` before storage.
- Duplicate plate numbers return `409` with code
  `SUBSCRIBER_PLATE_ALREADY_EXISTS`. One plate = one subscriber record.
- Creation is logged with action `SUBSCRIBER_CREATED`.
- After creation, the admin is redirected to
  `GET /ui/admin/subscribers/{id}` to create the first subscription.

---

**US-405 — View Subscriber Profile**
> *As an admin, I want to view a subscriber's full profile including their
> current subscription status and entry history, so that I can answer
> customer queries.*

**Acceptance Criteria:**
- `GET /ui/admin/subscribers/{id}` renders the subscriber detail page.
- Shows: full name, phone, plate number, notes.
- Shows the current active subscription (if any): plan label, start date,
  end date, days remaining, card assigned, amount paid, status badge.
- Shows a paginated list (10 per page) of all parking sessions linked to
  this subscriber's active subscriptions, ordered by `entry_time DESC`.
- Shows a list of all past subscriptions (expired/cancelled) with their dates.
- A "تجديد الاشتراك" button is shown when no active subscription exists or
  when the active subscription expires within 7 days.

---

**US-406 — Edit Subscriber Details**
> *As an admin, I want to update a subscriber's name or phone number, so
> that records stay accurate.*

**Acceptance Criteria:**
- `PATCH /api/v1/subscriptions/subscribers/{id}` accepts `full_name`,
  `phone_number`, `notes` as optional fields.
- `plate_number` cannot be edited after creation. To change a plate, the
  admin must cancel the subscription and create a new subscriber.
- Edit is logged with action `SUBSCRIBER_UPDATED`.

---

**US-407 — List & Search Subscribers**
> *As an admin, I want to search subscribers by name or plate number and
> filter by subscription status, so that I can quickly find any customer.*

**Acceptance Criteria:**
- `GET /ui/admin/subscribers` renders a paginated list (20 per page).
- Columns: full name, phone, plate number, plan label, status badge, expiry
  date, days remaining.
- Filter bar: `search` (text, searches `full_name` and `plate_number`),
  `status` (`active` | `expired` | `cancelled` | `all`),
  `plan_id` (dropdown).
- "Expiring soon" filter: shows subscribers whose subscription expires within
  the next N days (configurable, default 7).
- Clicking a row navigates to the subscriber detail page.

---

### 2.3 Admin — Subscription Lifecycle

---

**US-408 — Create a New Subscription**
> *As an admin, I want to assign a subscription plan to a subscriber, specify
> which card they will use, record the payment, and set the start date, so
> that the subscriber can begin using the garage.*

**Acceptance Criteria:**
- `GET /ui/admin/subscribers/{id}/subscribe` renders the subscription creation
  form.
- Fields:
  - Plan (dropdown of active plans only, shows price and duration).
  - Card (scan input or text — assigns a specific `parking_card` to this
    subscriber).
  - Start date (date picker, defaults to today).
  - Amount paid EGP (pre-filled from plan price, editable for discounts).
  - Payment notes (optional text).
- `POST /api/v1/subscriptions/` creates the subscription:
  - Sets `end_date = start_date + plan.duration_days`.
  - Sets `status = ACTIVE`.
  - Sets `card.status = IN_USE` — the card is now dedicated to this
    subscriber.
  - Sets `subscription.collected_by = current_user.id`.
  - Validates the card is `AVAILABLE` before assignment; raises `409` with
    code `CARD_NOT_AVAILABLE` if not.
  - Validates the subscriber has no other `ACTIVE` subscription; raises `409`
    with code `SUBSCRIBER_ALREADY_HAS_ACTIVE_SUBSCRIPTION` if so.
- `end_date` is computed as `start_date + timedelta(days=plan.duration_days)`.
- Creation is logged with action `SUBSCRIPTION_CREATED`.
- On success: redirect to subscriber detail page with a success banner.

---

**US-409 — Renew a Subscription**
> *As an admin, I want to renew a subscriber's plan when it expires or is
> about to expire, so that the subscriber's access continues without
> interruption.*

**Acceptance Criteria:**
- `POST /api/v1/subscriptions/{id}/renew` creates a **new** subscription
  record (does not mutate the old one).
- If renewing before expiry: new `start_date = old subscription's end_date`
  (seamless continuation, no gap).
- If renewing after expiry: new `start_date = today` (Cairo date).
- The same card assignment is carried over to the new subscription
  automatically.
- The old subscription's `status` is set to `EXPIRED` and `ended_at` is set
  to `utcnow()` when the new subscription's `start_date` is today. If
  renewing before expiry, the old one stays `ACTIVE` until its `end_date` —
  the new one's `status = ACTIVE` but `start_date` is in the future; a
  `PENDING` status is used in this case.
- Renewal is logged with action `SUBSCRIPTION_RENEWED` referencing both the
  old and new subscription IDs.
- The admin must enter the amount paid for the new period.

---

**US-410 — Cancel a Subscription**
> *As an admin, I want to cancel an active subscription, so that the
> subscriber can no longer enter the garage for free.*

**Acceptance Criteria:**
- `PATCH /api/v1/subscriptions/{id}/cancel` accepts an optional
  `cancel_reason` string.
- Sets `subscription.status = CANCELLED`, `subscription.ended_at = utcnow()`.
- Sets `card.status = AVAILABLE` — the card is freed for reuse.
- Any currently open session for this card proceeds to its natural end (the
  operator closes it normally); the session was opened while the subscription
  was active so it remains `is_subscribed = TRUE`.
- Cancellation is logged with action `SUBSCRIPTION_CANCELLED`.
- Returns `409` with code `SUBSCRIPTION_NOT_ACTIVE` if already cancelled or
  expired.

---

**US-411 — Automatic Expiry**
> *As an admin, I want subscriptions to be automatically marked as expired
> when their end date passes, so that expired subscribers cannot enter for
> free.*

**Acceptance Criteria:**
- Expiry is checked **at the moment of each entry scan** — not via a
  background cron job. If `subscription.end_date <= today (Cairo)` and
  `subscription.status = ACTIVE`, the system treats the subscription as
  expired for that entry attempt.
- Additionally, a lightweight startup check runs once when the FastAPI app
  starts: it marks all subscriptions where `end_date < cairo_today` and
  `status = ACTIVE` as `EXPIRED` in a single bulk UPDATE.
- This startup check is implemented as a FastAPI `lifespan` event.
- Automatic expiry is **not** logged per-row in `audit_logs` (bulk operation).
  Instead, a single `audit_log` row is written with action
  `SUBSCRIPTIONS_BULK_EXPIRED` and `payload_after = {"count": N}`.

---

### 2.4 Operator — Entry & Exit for Subscribed Vehicles

---

**US-412 — Scan Entry for Subscribed Vehicle**
> *As an operator, I want the system to automatically detect a subscribed
> card and grant free entry, so that I do not need to do anything differently
> from a regular card scan.*

**Acceptance Criteria:**
- The entry scan flow is **identical** to regular entry — the operator scans
  the card on `GET /ui/operator/entry`.
- The system internally checks: `SubscriptionService.get_active_for_card(
  card.id)`.
- If an active subscription is found:
  - Session is created with `is_subscribed = TRUE` and
    `subscription_id = subscription.id`.
  - The entry confirmation screen shows a **green banner** with:
    "مشترك ✓ — ينتهي الاشتراك: {end_date}".
  - The confirmation screen also shows the subscriber's name.
  - No pricing calculation is triggered at entry.
- If no active subscription: normal entry flow proceeds as in Phase 2.
- If a subscription exists but `end_date` has passed: treated as expired,
  normal paid entry flow is triggered. A warning is shown:
  "انتهى الاشتراك — سيتم الحساب بالساعة".
- If `max_entries_per_day` is set on the plan and the vehicle has already
  reached the daily limit: entry is blocked with code
  `SUBSCRIPTION_DAILY_LIMIT_REACHED`.

---

**US-413 — Scan Exit for Subscribed Vehicle**
> *As an operator, I want the exit scan for a subscribed vehicle to show zero
> charge and print a subscription receipt, so that the subscriber leaves
> without paying.*

**Acceptance Criteria:**
- The exit scan flow is **identical** to regular exit — operator scans the
  card on `GET /ui/operator/exit`.
- If `session.is_subscribed = TRUE`:
  - Exit confirmation screen shows: duration, subscriber name, plan label,
    and **zero amount due** in large green text: `٠٫٠٠ ج.م`.
  - The confirm button label changes to: "تأكيد الخروج (اشتراك)".
  - `amount_charged = 0`, `is_paid = TRUE`, pricing rule is NOT applied.
  - The subscription receipt template is used (distinct from paid receipt).
- If `session.is_subscribed = FALSE`: normal paid exit flow as in Phase 2.
- Subscription receipt is logged with `receipt_printed_at = utcnow()`.

---

**US-414 — Subscription Receipt**
> *As an operator, I want the receipt for a subscribed vehicle to clearly
> show it is a subscription exit, so that the driver has a record.*

**Acceptance Criteria:**
- Subscription receipt template: `templates/receipts/thermal_subscription.html`.
- Required fields: garage name, "إيصال اشتراك" header, session ID (zero-padded
  8 digits), subscriber name, plate number, card code, gate number, operator
  name, entry time, exit time, duration, plan label, subscription end date,
  amount: "٠٫٠٠ ج.م", footer: "شكراً لزيارتكم".
- Receipt is clearly distinguished from a paid receipt — different header,
  no pricing breakdown section.
- Same 58mm thermal print CSS applies.
- `window.print()` auto-triggers as in Phase 2.

---

### 2.5 Admin — Subscription Reporting

---

**US-415 — Subscription Revenue Report**
> *As an admin, I want to see subscription revenue separately from hourly
> revenue in my financial reports, so that I can understand both income
> streams.*

**Acceptance Criteria:**
- The existing Phase 3 revenue report gains a new section:
  "إيراد الاشتراكات" showing: total subscriptions created in the period,
  total subscription revenue collected, average subscription value.
- `GET /api/v1/admin/reports/subscriptions` returns this breakdown.
- Filter params: `start_date`, `end_date`, `plan_id`.
- The overall revenue KPI on the admin dashboard now shows two sub-figures:
  "اشتراكات: X ج.م" and "جلسات عادية: Y ج.م".

---

**US-416 — Expiry Alerts on Admin Dashboard**
> *As an admin, I want to see an alert on the dashboard when subscriptions
> are about to expire, so that I can proactively contact customers.*

**Acceptance Criteria:**
- A dedicated alert card on the admin dashboard shows:
  - Count of subscriptions expiring within 7 days (configurable via
    `SUBSCRIPTION_EXPIRY_ALERT_DAYS` env var, default 7).
  - Count of subscriptions already expired but not renewed.
- Clicking the expiring count navigates to
  `GET /ui/admin/subscribers?status=expiring`.
- Clicking the expired count navigates to
  `GET /ui/admin/subscribers?status=expired`.
- Alert counts refresh with the existing 30-second dashboard refresh.

---

**US-417 — Subscribed Sessions Report**
> *As an admin, I want to filter the session list to show only subscribed
> sessions, so that I can audit free-entry usage.*

**Acceptance Criteria:**
- `GET /ui/admin/sessions` gains a new filter checkbox: "جلسات الاشتراك فقط"
  which adds `is_subscribed=true` to the filter.
- Subscribed sessions display `٠٫٠٠ ج.م` in the amount column.
- The "اشتراك" status badge replaces the "COMPLETED" badge for subscribed
  sessions in the session list.
- CSV export includes an `is_subscribed` column (`نعم` / `لا`).

---

### 2.6 Admin — Bulk Onboarding & Flexible Billing

---

**US-418 — Excel/CSV Bulk Import for Subscribers & Cards**
> *As an admin, I want to bulk import subscribers from Excel or CSV files with card codes,
> company names, and automatic subscription creation, so that I can onboard hundreds of corporate
> and VIP clients in seconds.*

**Acceptance Criteria:**
- `GET /ui/admin/subscribers/import` renders the bulk import interface with drag-and-drop file upload.
- `GET /ui/admin/subscribers/template-excel` downloads a professionally styled Excel template (`subscribers_template.xlsx`) with Arabic headers:
  - كود الكارت (Card Code)
  - اسم المشترك (Subscriber Full Name)
  - رقم اللوحة (Plate Number)
  - رقم الهاتف (Phone Number)
  - الشركة / الجهة (Company / Organization)
  - ملاحظات (Notes)
- `POST /ui/admin/subscribers/import-preview` parses `.xlsx` or `.csv` (supporting UTF-8, CP1256), validates fields, matches cards (flags missing cards to be created or unavailable cards), detects existing subscribers, and returns an interactive summary with validation flags and warnings.
- `POST /ui/admin/subscribers/import-confirm` executes the import inside a single atomic database transaction:
  - Automatically creates new `ParkingCard` records with `status = AVAILABLE` if the card code is new.
  - Creates or updates `Subscriber` records (`full_name`, `plate_number`, `phone_number`, `company_name`, `card_code`).
  - Creates active `Subscription` records linking subscriber and card, setting `card.status = IN_USE`.
  - Default expiration aligns to the end of the calendar month.
  - Commits atomically or rolls back on critical errors, writing audit logs.

---

**US-419 — Custom Pricing & End-of-Calendar-Month Billing**
> *As an admin, I want flexibility to set custom subscription prices and durations without predefined plans,
> and have subscriptions expire at the end of the calendar month by default, conforming to Egyptian commercial garage norms.*

**Acceptance Criteria:**
- In the subscription creation screen (`/ui/admin/subscribers/{id}/subscribe`), the admin can choose between predefined plans or "اشتراك مخصص (سعر حر)".
- When choosing a custom plan, the admin specifies custom duration in days and custom price in EGP, which is stored in `amount_paid_piastres` and backed by an auto-created plan `اشتراك مخصص (سعر حر)`.
- If no explicit `end_date` is entered, `end_date` defaults to the last calendar day of the start date's month: `date(start_date.year, start_date.month, calendar.monthrange(start_date.year, start_date.month)[1])`.
- On renewal before expiry, if the current subscription expires on the 30th/31st, the renewed subscription continues seamlessly starting on the 1st of the next month (`old_sub.end_date + timedelta(days=1)`) and expires at the end of that subsequent month.
- Supports card assignment by typing the physical card code (`card_code`) or selecting from available cards.

---

## 3. Functional Requirements

### 3.1 Data Models

#### `subscription_plans` — Plan Definitions

subscription_plans
├── id INTEGER PK AUTO
├── label VARCHAR(100) UNIQUE NOT NULL
├── duration_days SMALLINT NOT NULL -- e.g. 30, 90, 365
├── price_piastres INTEGER NOT NULL -- stored in piastres
├── max_entries_per_day SMALLINT NULLABLE -- NULL = unlimited
├── description TEXT NULLABLE
├── is_active BOOLEAN NOT NULL DEFAULT TRUE
├── created_by INTEGER FK → users.id NOT NULL
├── created_at TIMESTAMP NOT NULL
└── updated_at TIMESTAMP NOT NULL


**Rules:**
- `duration_days` is immutable after creation.
- `price_piastres` must be a non-negative integer.
- Only `is_active = TRUE` plans appear in the subscription creation dropdown.
- A plan cannot be deleted if any subscription references it — only
  deactivated.

---

#### `subscribers` — Vehicle Owner Records

subscribers
├── id INTEGER PK AUTO
├── full_name VARCHAR(120) NOT NULL
├── phone_number VARCHAR(20) NULLABLE
├── plate_number VARCHAR(30) UNIQUE NOT NULL -- normalized, indexed
├── company_name VARCHAR(150) NULLABLE -- company / bank / organization, indexed
├── card_code VARCHAR(50) UNIQUE NULLABLE -- assigned physical card code, indexed
├── notes TEXT NULLABLE
├── created_at TIMESTAMP NOT NULL
└── updated_at TIMESTAMP NOT NULL


**Rules:**
- `plate_number` is normalized via `PlateService.normalize` before storage.
- `plate_number` is unique — one subscriber record per plate.
- `plate_number` is immutable after creation.
- `company_name` facilitates corporate fleet grouping (e.g. "البنك الأهلي", "شركة المصرية").
- `card_code` maps the subscriber directly to their RFID/barcode card.

---

#### `subscriptions` — Active & Historical Subscriptions

subscriptions
├── id INTEGER PK AUTO
├── subscriber_id INTEGER FK → subscribers.id NOT NULL, indexed
├── plan_id INTEGER FK → subscription_plans.id NOT NULL -- predefined or custom plan
├── card_id INTEGER FK → parking_cards.id NOT NULL, indexed
├── plate_number VARCHAR(30) NOT NULL -- snapshot at creation
├── start_date DATE NOT NULL -- Cairo calendar date
├── end_date DATE NOT NULL -- month-end or start + duration_days
├── status ENUM('ACTIVE','EXPIRED','CANCELLED','PENDING')
│   NOT NULL DEFAULT 'ACTIVE', indexed
├── amount_paid_piastres INTEGER NOT NULL -- actual amount paid
├── plan_price_snapshot INTEGER NOT NULL -- plan price at time of subscription
├── paid_at TIMESTAMP NULLABLE
├── collected_by INTEGER FK → users.id NULLABLE
├── renewal_count SMALLINT NOT NULL DEFAULT 0 -- 0 = first subscription
├── previous_subscription_id INTEGER FK → subscriptions.id NULLABLE -- renewal chain
├── cancel_reason TEXT NULLABLE
├── ended_at TIMESTAMP NULLABLE -- when cancelled/expired
├── notes TEXT NULLABLE
├── created_at TIMESTAMP NOT NULL
└── updated_at TIMESTAMP NOT NULL


**Rules:**
- Only one subscription per subscriber may have `status = ACTIVE` or `status = PENDING` at any time (enforced at service layer).
- Default expiration aligns to the end of the calendar month (`end_date = date(year, month, last_day_num)`), or custom `end_date` if provided.
- Dynamic custom plans ("اشتراك مخصص (سعر حر)") are automatically created/reused when `plan_id` is omitted.
- Card resolution accepts either `card_code` (typed/scanned code) or `card_id`.
- `plan_price_snapshot` captures the plan price at creation time so historical records are accurate even if the plan price later changes.
- `amount_paid_piastres` may differ from `plan_price_snapshot` (custom pricing, discounts, complimentary).
- When `status = ACTIVE`, the associated card must have `status = IN_USE`.
- When `status` transitions to `EXPIRED` or `CANCELLED`, the card must be freed (`status = AVAILABLE`).

---

#### `parking_sessions` — Two New Columns

parking_sessions (additions only)
├── subscription_id INTEGER FK → subscriptions.id NULLABLE
└── is_subscribed BOOLEAN NOT NULL DEFAULT FALSE


**Rules:**
- `subscription_id` is set at session open time if an active subscription
  is found for the card.
- `is_subscribed = TRUE` means `amount_charged = 0` at close time, always.
- A session with `is_subscribed = TRUE` must not have a pricing rule applied.
  `pricing_rule_id` remains `NULL` for subscribed sessions.

---

### 3.2 Subscription Status State Machine
                ┌──────────────┐
                │   (none)     │
                └──────┬───────┘
                       │ create_subscription()
                       ▼
          ┌────────────────────────┐
          │   ACTIVE               │  card: IN_USE
          │   (start_date = today) │
          └────────────┬───────────┘
                       │
      ┌────────────────┼────────────────┐
      │                │                │
      │ end_date        │ cancel()       │ renew() before
      │ reached         │                │ expiry
      ▼                ▼                ▼
┌──────────┐    ┌───────────┐    ┌──────────┐
│ EXPIRED  │    │ CANCELLED │    │ PENDING  │ ← new subscription
│          │    │           │    │ (future  │   start_date in future
│card:     │    │card:      │    │  start)  │
│AVAILABLE │    │AVAILABLE  │    └────┬─────┘
└──────────┘    └───────────┘         │ start_date arrives
                                      ▼
                                ┌──────────┐
                                │  ACTIVE  │
                                └──────────┘

**State Transition Rules:**

| From | To | Trigger | Condition |
|---|---|---|---|
| — | `ACTIVE` | `create_subscription()` | Card `AVAILABLE`, no other active sub |
| — | `PENDING` | `renew()` before expiry | Old sub still `ACTIVE` |
| `ACTIVE` | `EXPIRED` | Startup check or entry scan | `end_date < cairo_today` |
| `ACTIVE` | `CANCELLED` | `cancel_subscription()` | Admin action |
| `PENDING` | `ACTIVE` | Entry scan or startup check | `start_date <= cairo_today` |
| `EXPIRED` | — | Forbidden | Use `renew()` to create a new sub |
| `CANCELLED` | — | Forbidden | Create a new subscription instead |

---

### 3.3 SubscriptionService

| ID | Requirement |
|---|---|
| FR-SUB-001 | `get_active_for_card(card_id: int, db) -> Subscription | None` — queries subscriptions where `card_id = :id` and `status IN ('ACTIVE', 'PENDING')` and `start_date <= cairo_today` and `end_date >= cairo_today`. Returns the subscription or `None`. This is called on every entry scan. Must complete in under 50ms. |
| FR-SUB-002 | `check_daily_limit(subscription: Subscription, db) -> bool` — if `subscription.plan.max_entries_per_day IS NULL`, returns `True` (no limit). Otherwise counts sessions for this `subscription_id` where `entry_time >= cairo_today_start_utc`. Returns `True` if count < limit, `False` if limit reached. |
| FR-SUB-003 | `create_subscription(data: SubscriptionCreate, admin_id: int) -> Subscription` — accepts `plan_id` (predefined) or None (auto custom plan "اشتراك مخصص (سعر حر)"). Resolves card by `card_code` or `card_id`. Validates subscriber and active status. Computes default calendar month-end `end_date` if not provided. Sets `card.status = IN_USE`. Commits atomically. Logs `SUBSCRIPTION_CREATED`. |
| FR-SUB-004 | `renew_subscription(subscription_id: int, data: SubscriptionRenew, admin_id: int) -> Subscription` — fetches existing sub. Computes continuation start date (`end_date + timedelta(days=1)` if not yet expired, or `today` if already expired) and calendar month-end `end_date`. Creates new subscription record with `renewal_count = old.renewal_count + 1`. If `new_start <= today`: sets old sub `EXPIRED`, new sub `ACTIVE`, card remains `IN_USE`. If future: new sub `PENDING`, old sub stays `ACTIVE`. Commits. Logs `SUBSCRIPTION_RENEWED`. |
| FR-SUB-005 | `cancel_subscription(subscription_id, cancel_reason, admin_id, db) -> Subscription` — fetches sub. Raises `SubscriptionNotActiveError` if status is not `ACTIVE`. Sets status `CANCELLED`, `ended_at = utcnow()`, `cancel_reason`. Sets `card.status = AVAILABLE`. Commits. Logs `SUBSCRIPTION_CANCELLED`. |
| FR-SUB-006 | `expire_overdue_subscriptions(db) -> int` — bulk UPDATE: `UPDATE subscriptions SET status='EXPIRED', ended_at=utcnow() WHERE status='ACTIVE' AND end_date < :cairo_today`. Also bulk updates associated cards to `AVAILABLE`. Returns count of rows updated. Called once on app startup via lifespan event. |
| FR-SUB-007 | `activate_pending_subscriptions(db) -> int` — bulk UPDATE: `UPDATE subscriptions SET status='ACTIVE' WHERE status='PENDING' AND start_date <= :cairo_today`. Returns count updated. Called in the same lifespan event as FR-SUB-006. |
| FR-SUB-008 | `get_expiring_soon(days: int, db) -> list[Subscription]` — returns subscriptions where `status='ACTIVE'` and `end_date <= cairo_today + timedelta(days=days)`. Used for dashboard alerts. |
| FR-SUB-009 | `get_expired_unrenewed(db) -> list[Subscription]` — returns subscriptions where `status='EXPIRED'` and no linked subscription has `status IN ('ACTIVE','PENDING')` via `previous_subscription_id` chain. Used for dashboard alerts. |
| FR-SUB-010 | `ExcelImportService` — parses `.xlsx` / `.csv`, matches card codes, validates rows, previews counts and errors, and executes atomic bulk onboarding creating cards, subscribers, and active subscriptions. |

---

### 3.4 SessionService Modifications

| ID | Requirement |
|---|---|
| FR-SESS-SUB-001 | `open_session` is extended with one new step after card validation: call `SubscriptionService.get_active_for_card(card.id)`. If a subscription is returned, call `SubscriptionService.check_daily_limit(subscription)`. If limit reached, raise `SubscriptionDailyLimitReachedError`. If within limit or no limit, set `session.subscription_id = subscription.id` and `session.is_subscribed = True`. |
| FR-SESS-SUB-002 | `close_session` checks `session.is_subscribed` before pricing. If `True`: set `amount_charged = 0`, `is_paid = True`, `pricing_rule_id = None`. Skip all `PricingService` calls. If `False`: normal pricing flow as in Phase 2. |
| FR-SESS-SUB-003 | The entry confirmation template (`operator/entry_confirm.html`) receives `subscription` in the context. If `subscription` is not `None`, renders a green "مشترك ✓" banner with subscriber name and expiry date. |
| FR-SESS-SUB-004 | The exit confirmation template (`operator/exit_confirm.html`) receives `is_subscribed` in the context. If `True`, renders zero amount in green with "تأكيد الخروج (اشتراك)" button. The pricing breakdown section is hidden. |
| FR-SESS-SUB-005 | The receipt route checks `session.is_subscribed`. If `True`, renders `receipts/thermal_subscription.html` instead of `receipts/thermal.html`. |

---

### 3.5 Plan Service (`SubscriptionPlanService`)

| ID | Requirement |
|---|---|
| FR-PLAN-001 | `create_plan(data: PlanCreate, admin_id, db) -> SubscriptionPlan` — validates unique label. Converts `price_egp` to piastres via `round(data.price_egp * 100)`. Creates record. Logs `PLAN_CREATED`. |
| FR-PLAN-002 | `deactivate_plan(plan_id, admin_id, db) -> SubscriptionPlan` — sets `is_active = FALSE`. Raises `PlanNotFoundError` if absent. Logs `PLAN_DEACTIVATED`. |
| FR-PLAN-003 | `update_plan(plan_id, data: PlanUpdate, admin_id, db) -> SubscriptionPlan` — updates only provided fields. `duration_days` is excluded from `PlanUpdate` schema — it cannot be changed. Logs `PLAN_UPDATED` with before/after. |
| FR-PLAN-004 | `get_active_plans(db) -> list[SubscriptionPlan]` — returns all plans with `is_active = TRUE` ordered by `price_piastres ASC`. Used to populate subscription form dropdowns. |

---

### 3.6 Subscriber Service (`SubscriberService`)

| ID | Requirement |
|---|---|
| FR-SUBS-001 | `create_subscriber(data: SubscriberCreate, admin_id, db) -> Subscriber` — normalizes `plate_number` via `PlateService.normalize`. Supports `company_name` and `card_code`. Checks uniqueness. Creates record. Logs `SUBSCRIBER_CREATED`. |
| FR-SUBS-002 | `update_subscriber(subscriber_id, data: SubscriberUpdate, admin_id, db) -> Subscriber` — updates `full_name`, `phone_number`, `company_name`, `card_code`, `notes`. Logs `SUBSCRIBER_UPDATED`. |
| FR-SUBS-003 | `get_filtered(search, status, plan_id, expiring_days, page, size, db) -> tuple[list[Subscriber], int]` — applies filters. `search` performs `ILIKE` on `full_name`, `plate_number`, and `company_name`. `status` filters by the status of the most recent subscription. `expiring_days` filters by `end_date <= today + N`. Returns paginated results. |
| FR-SUBS-004 | `get_by_plate(plate: str, db) -> Subscriber | None` — normalizes plate, queries by `plate_number`. Returns subscriber or `None`. |

---

### 3.7 Reporting Extensions

| ID | Requirement |
|---|---|
| FR-RPT-SUB-001 | `get_subscription_revenue_summary(start_date, end_date, plan_id, db) -> SubscriptionRevenueSummary` — queries `subscriptions` where `paid_at` falls in the date range. Returns: `total_subscriptions`, `total_revenue_piastres`, `avg_revenue_piastres`, broken down by plan. |
| FR-RPT-SUB-002 | `get_dashboard_subscription_stats(db) -> SubscriptionDashboardStats` — returns: `expiring_soon_count` (within 7 days), `expired_unrenewed_count`, `active_subscriptions_count`. Fired concurrently in the dashboard stats gather. |
| FR-RPT-SUB-003 | The existing `get_live_stats` response gains two new integer fields: `subscription_revenue_today_piastres` and `active_subscriptions`. |
| FR-RPT-SUB-004 | Session export CSV gains one new column: `is_subscribed` (`نعم` / `لا`). |

---

### 3.8 API Endpoints — Phase 4

#### Subscription Plans

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/subscriptions/plans` | admin | Create a plan |
| `GET` | `/api/v1/subscriptions/plans` | admin | List all plans (active + inactive) |
| `GET` | `/api/v1/subscriptions/plans/active` | any | Active plans only (for dropdowns) |
| `PATCH` | `/api/v1/subscriptions/plans/{id}` | admin | Edit plan label/price/description |
| `PATCH` | `/api/v1/subscriptions/plans/{id}/deactivate` | admin | Deactivate plan |

#### Subscribers

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/subscriptions/subscribers` | admin | Create subscriber |
| `GET` | `/api/v1/subscriptions/subscribers` | admin | List/search subscribers |
| `GET` | `/api/v1/subscriptions/subscribers/{id}` | admin | Subscriber detail |
| `PATCH` | `/api/v1/subscriptions/subscribers/{id}` | admin | Edit subscriber |

#### Subscriptions

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/subscriptions/` | admin | Create subscription |
| `GET` | `/api/v1/subscriptions/` | admin | List subscriptions with filters |
| `GET` | `/api/v1/subscriptions/{id}` | admin | Subscription detail |
| `POST` | `/api/v1/subscriptions/{id}/renew` | admin | Renew subscription |
| `PATCH` | `/api/v1/subscriptions/{id}/cancel` | admin | Cancel subscription |

#### Reporting

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/admin/reports/subscriptions` | admin | Subscription revenue report |
| `GET` | `/api/v1/admin/stats/subscriptions` | admin | Dashboard subscription stats |

#### Admin UI Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/ui/admin/plans` | admin | Plan management page |
| `GET` | `/ui/admin/subscribers` | admin | Subscriber list page |
| `GET` | `/ui/admin/subscribers/new` | admin | Create subscriber form |
| `GET` | `/ui/admin/subscribers/import` | admin | Bulk Excel/CSV import page |
| `GET` | `/ui/admin/subscribers/template-excel` | admin | Download styled Excel onboarding template |
| `POST` | `/ui/admin/subscribers/import-preview` | admin | Validate & preview uploaded Excel/CSV rows |
| `POST` | `/ui/admin/subscribers/import-confirm` | admin | Batch execute atomic import for cards, subscribers & subscriptions |
| `GET` | `/ui/admin/subscribers/{id}` | admin | Subscriber detail + history |
| `GET` | `/ui/admin/subscribers/{id}/subscribe` | admin | New subscription form |
| `GET` | `/ui/admin/subscribers/{id}/renew` | admin | Renewal form |
| `GET` | `/ui/admin/subscriptions` | admin | All subscriptions list |

---

### 3.9 New Pydantic Schemas

| Schema | Key Fields |
|---|---|
| `PlanCreate` | `label: str`, `duration_days: int (ge=1)`, `price_egp: float (ge=0)`, `max_entries_per_day: int | None`, `description: str | None` |
| `PlanUpdate` | `label: str | None`, `price_egp: float | None`, `description: str | None`, `max_entries_per_day: int | None` — no `duration_days` |
| `PlanResponse` | All plan fields; `price_piastres: int`, `price_display: str` (via `format_egp`) |
| `SubscriberCreate` | `full_name: str`, `plate_number: str`, `phone_number: str | None`, `company_name: str | None`, `card_code: str | None`, `notes: str | None` |
| `SubscriberUpdate` | `full_name: str | None`, `phone_number: str | None`, `company_name: str | None`, `card_code: str | None`, `notes: str | None` — no `plate_number` |
| `SubscriberResponse` | All subscriber fields + `company_name: str | None`, `card_code: str | None`, `active_subscription: SubscriptionResponse | None` |
| `SubscriptionCreate` | `subscriber_id: int`, `plan_id: int | None`, `card_id: int | None`, `card_code: str | None`, `duration_days: int | None`, `start_date: date`, `end_date: date | None`, `amount_paid_egp: float (ge=0)`, `notes: str | None` |
| `SubscriptionRenew` / `SubscriptionRenewRequest` | `plan_id: int | None`, `start_date: date | None`, `end_date: date | None`, `amount_paid_egp: float (ge=0)`, `notes: str | None` |
| `SubscriptionCancel` / `SubscriptionCancelRequest` | `cancel_reason: str | None` |
| `SubscriptionResponse` | All subscription fields; monetary fields as integers (piastres); `days_remaining: int` computed field; `amount_paid_egp`, `plan_price_snapshot_egp` |
| `SubscriptionRevenueSummary` | `total_subscriptions: int`, `total_revenue_piastres: int`, `avg_revenue_piastres: int`, `by_plan: list[PlanRevenueResponse]` |
| `SubscriptionDashboardStats` | `expiring_soon_count: int`, `expired_unrenewed_count: int`, `active_subscriptions_count: int`, `total_subscribers: int` |

---

### 3.10 New Jinja2 Filters & Translations

#### New Filters

| Filter | Signature | Behaviour |
|---|---|---|
| `days_remaining` | `(end_date: date) -> int` | `(end_date - cairo_now().date()).days`. Returns 0 if negative. |
| `subscription_status_label` | `(status: str) -> str` | `ACTIVE` → `"نشط"`, `EXPIRED` → `"منتهي"`, `CANCELLED` → `"ملغي"`, `PENDING` → `"معلق"` |
| `subscription_status_class` | `(status: str) -> str` | Returns Tailwind badge class: `ACTIVE` → `"bg-green-100 text-green-800"`, `EXPIRED` → `"bg-gray-100 text-gray-600"`, `CANCELLED` → `"bg-red-100 text-red-700"`, `PENDING` → `"bg-amber-100 text-amber-700"` |

#### New Translation Keys (`translations/ar.json`)

```json
"subscriptions.plan.title": "خطط الاشتراك",
"subscriptions.plan.create": "إنشاء خطة جديدة",
"subscriptions.plan.label": "اسم الخطة",
"subscriptions.plan.duration": "المدة (أيام)",
"subscriptions.plan.price": "السعر (جنيه)",
"subscriptions.plan.max_entries": "أقصى دخولات يومياً",
"subscriptions.plan.unlimited": "غير محدود",
"subscriptions.subscriber.title": "المشتركون",
"subscriptions.subscriber.new": "إضافة مشترك",
"subscriptions.subscriber.plate": "رقم اللوحة",
"subscriptions.subscriber.phone": "رقم الهاتف",
"subscriptions.subscription.title": "الاشتراك",
"subscriptions.subscription.start": "تاريخ البدء",
"subscriptions.subscription.end": "تاريخ الانتهاء",
"subscriptions.subscription.days_remaining": "أيام متبقية",
"subscriptions.subscription.renew": "تجديد الاشتراك",
"subscriptions.subscription.cancel": "إلغاء الاشتراك",
"subscriptions.subscription.amount_paid": "المبلغ المدفوع",
"operator.entry.subscribed_banner": "مشترك ✓",
"operator.entry.subscription_expires": "ينتهي الاشتراك",
"operator.entry.subscription_expired_warning": "انتهى الاشتراك — سيتم الحساب بالساعة",
"operator.exit.subscription_confirm_button": "تأكيد الخروج (اشتراك)",
"receipt.subscription_title": "إيصال اشتراك",
"receipt.subscription_plan": "الخطة",
"receipt.subscription_end_date": "تاريخ انتهاء الاشتراك",
"admin.dashboard.expiring_soon": "اشتراكات تنتهي قريباً",
"admin.dashboard.expired_unrenewed": "اشتراكات منتهية غير مجددة",
"errors.plan_label_exists": "اسم الخطة موجود بالفعل",
"errors.plan_not_active": "هذه الخطة غير متاحة",
"errors.subscriber_plate_exists": "رقم اللوحة مسجل بالفعل",
"errors.subscriber_already_subscribed": "المشترك لديه اشتراك نشط بالفعل",
"errors.subscription_not_active": "الاشتراك غير نشط",
"errors.subscription_daily_limit": "تم الوصول للحد الأقصى من الدخولات اليومية"
```

---

### 3.11 App Startup Lifespan Event

| ID | Requirement |
|---|---|
| FR-LIFE-001 | In `main.py`, replace the current `@app.on_event("startup")` pattern (if any) with a `@asynccontextmanager` lifespan function. |
| FR-LIFE-002 | The lifespan function calls `await SubscriptionService.expire_overdue_subscriptions(db)` then `await SubscriptionService.activate_pending_subscriptions(db)` on every app startup, before serving requests. |
| FR-LIFE-003 | If either bulk operation raises an exception, it is caught, logged at `CRITICAL` level, and the app continues starting. The bulk operation failure must not prevent the app from serving requests. |
| FR-LIFE-004 | The lifespan writes a single audit log: `action="SUBSCRIPTIONS_BULK_EXPIRED"` with `payload_after={"expired_count": N, "activated_count": M}`. |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID | Requirement |
|---|---|
| NFR-PERF-401 | `SubscriptionService.get_active_for_card` must complete in under **50ms** on LAN. It is called on every entry scan. The index on `subscriptions(card_id)` and `subscriptions(status)` must exist. |
| NFR-PERF-402 | The entry scan response time (including subscription check) must remain under **800ms** total — the same SLA as Phase 2. The subscription check adds at most one additional DB query. |
| NFR-PERF-403 | The startup lifespan bulk expiry operation must complete in under **2 seconds** for up to 10,000 subscriptions using a single bulk UPDATE, not a row-by-row loop. |
| NFR-PERF-404 | `get_filtered` for subscribers supports up to 10,000 rows with pagination. Indexes on `subscribers(plate_number)` and `subscriptions(subscriber_id, status)` must exist. |
| NFR-PERF-405 | Dashboard subscription stats are fetched concurrently with existing live stats using `asyncio.gather`. They add at most 3 additional queries, all on indexed columns. |

---

### 4.2 Data Integrity

| ID | Requirement |
|---|---|
| NFR-INT-401 | The constraint "one active subscription per subscriber" is enforced at the **service layer** via an explicit check before INSERT. No unique DB constraint is used (it would complicate the PENDING state). |
| NFR-INT-402 | `amount_paid_piastres` and `plan_price_snapshot` are both stored as integers. No float arithmetic is performed on monetary values. The `price_egp` input field is a float that is immediately converted to piastres via `round(value * 100)` in the Pydantic schema validator. |
| NFR-INT-403 | When a subscription is cancelled or expires, the associated card's `status` must be set to `AVAILABLE` in the **same transaction** as the subscription status update. Both changes commit together or neither does. |
| NFR-INT-404 | `is_subscribed = TRUE` sessions always have `amount_charged = 0` and `pricing_rule_id = NULL`. This is enforced at the service layer. A database CHECK constraint is added: `CHECK (is_subscribed = FALSE OR amount_charged = 0)`. |
| NFR-INT-405 | `end_date` is always `start_date + plan.duration_days` — computed once at creation and stored. It is never recomputed. Changing the plan's duration after subscription creation does not affect existing subscriptions. |
| NFR-INT-406 | `plate_number` on `subscriptions` is a snapshot of `subscriber.plate_number` at creation time. It is stored redundantly for audit purposes. |

---

### 4.3 Security

| ID | Requirement |
|---|---|
| NFR-SEC-401 | All subscription management endpoints (`/api/v1/subscriptions/*`, `/ui/admin/subscribers/*`, `/ui/admin/plans/*`) require `role = 'admin'`. |
| NFR-SEC-402 | The operator entry/exit flow does not expose subscription details in the API response beyond what is needed for the confirmation screen (subscriber name, plan label, expiry date). Phone number is never shown on the operator screen. |
| NFR-SEC-403 | Cancellation requires an explicit confirmation — the `cancel_subscription` endpoint must not be callable with an accidental GET or without a request body (even if `cancel_reason` is optional). |
| NFR-SEC-404 | All audit log entries for subscription events include the `admin_id` as `actor_id`. No subscription mutation occurs without an audit log entry. |

---

### 4.4 Usability (Gate Workstations & Operator Screens)

| ID | Requirement |
|---|---|
| NFR-UX-401 | On Gate 1 (Entry PC Station), the subscribed entry confirmation screen must be visually distinct from the regular entry confirmation screen. It displays a green background card with the "مشترك ✓" banner in large font, showing subscriber name and expiration date. |
| NFR-UX-402 | On Gate 2 (Exit PC Station), the zero-amount exit confirmation must make it immediately clear to the operator that no payment is needed. The amount "٠٫٠٠ ج.م" is displayed in a large green font at least `2rem` in size with a single "تأكيد الخروج (اشتراك)" button. |
| NFR-UX-403 | When a subscription is expired at entry time, the operator screen displays a clear amber warning banner before proceeding with the normal paid hourly flow. |
| NFR-UX-404 | The subscription receipt printed on the Gate 2 thermal printer must be clearly different from a paid receipt at a glance on 58mm thermal paper: header "إيصال اشتراك", subscriber and plate details, subscription expiry date, zero fee, and omitting pricing breakdowns. |

---

### 4.5 Maintainability

| ID | Requirement |
|---|---|
| NFR-MNT-401 | `SubscriptionService`, `SubscriptionPlanService`, and `SubscriberService` are three separate classes in three separate files. No class exceeds 200 lines. |
| NFR-MNT-402 | The modification to `SessionService.open_session` and `SessionService.close_session` must be implemented as a clean branch (`if subscription:` / `else:`). No existing logic is deleted or rearranged. |
| NFR-MNT-403 | The `days_remaining` computed field on `SubscriptionResponse` is a Pydantic `@computed_field` — it is not stored in the database. |
| NFR-MNT-404 | All new services are covered by unit tests. `get_active_for_card` is tested for all four status values and the date boundary condition. |

---

## 5. Edge Cases

### 5.1 Entry Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SUB-001 | Card scanned on entry but subscription expired yesterday | `get_active_for_card` returns `None` (date filter excludes it). Entry proceeds as paid. Amber warning shown: `t("operator.entry.subscription_expired_warning")`. |
| EC-SUB-002 | Card scanned on entry, subscription `PENDING` and `start_date = today` | `get_active_for_card` includes `PENDING` with `start_date <= today`. Treated as active. Entry free. |
| EC-SUB-003 | Card scanned on entry, subscription `PENDING` and `start_date = tomorrow` | `start_date > today` so not returned by `get_active_for_card`. Entry proceeds as paid. |
| EC-SUB-004 | `max_entries_per_day = 1` and vehicle already entered today | `check_daily_limit` returns `False`. Entry blocked with `409` and code `SUBSCRIPTION_DAILY_LIMIT_REACHED`. Arabic message: `t("errors.subscription_daily_limit")`. |
| EC-SUB-005 | `max_entries_per_day = NULL` (unlimited) | `check_daily_limit` always returns `True`. No count query is executed. |
| EC-SUB-006 | Subscribed vehicle is inside the garage when subscription expires overnight | The open session was created with `is_subscribed = TRUE`. It closes as free regardless of when the subscription expired. The session's `is_subscribed` flag is immutable after creation. |
| EC-SUB-007 | Same plate enters twice simultaneously (race condition) | The session-level `SELECT FOR UPDATE` on the card prevents two simultaneous sessions. Second scan gets `CARD_ALREADY_ACTIVE`. |

### 5.2 Subscription Lifecycle Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SUB-010 | Admin creates a subscription for a subscriber who already has an active one | `409` with code `SUBSCRIBER_ALREADY_HAS_ACTIVE_SUBSCRIPTION`. |
| EC-SUB-011 | Admin tries to assign a card that is already `IN_USE` to a new subscription | `409` with code `CARD_NOT_AVAILABLE`. The card must be `AVAILABLE` to be assigned. |
| EC-SUB-012 | Admin renews before expiry — new start date is old end date | New subscription created with `status = PENDING`, `start_date = old.end_date`. Old subscription remains `ACTIVE`. When `start_date` arrives, the lifespan event activates the new one and expires the old one. |
| EC-SUB-013 | Admin renews an already-expired subscription | New subscription created with `start_date = cairo_today`. Old subscription `status` is already `EXPIRED`. New one is `ACTIVE` immediately. A new card assignment is optional — the old card should be re-available; admin confirms which card. |
| EC-SUB-014 | Plan is deactivated while subscriptions are running on it | Existing subscriptions continue normally. Only new subscriptions cannot use the deactivated plan. |
| EC-SUB-015 | `amount_paid_egp` is less than `plan.price_egp` (discount applied) | Valid — both `amount_paid_piastres` and `plan_price_snapshot` are stored. The discrepancy is visible in reports. No validation error. |
| EC-SUB-016 | `amount_paid_egp = 0` (complimentary subscription) | Valid. Stored as `amount_paid_piastres = 0`. No error. |
| EC-SUB-017 | Startup lifespan runs and finds 0 overdue subscriptions | Both bulk operations return `0`. A single audit log is written with `expired_count=0, activated_count=0`. No error. |
| EC-SUB-018 | Subscriber's plate normalized differently on lookup vs creation | All plate comparisons use `PlateService.normalize` on both sides. Eastern numerals in lookup are converted before DB query. |
| EC-SUB-019 | Admin cancels a subscription while the vehicle is currently parked (ACTIVE session open) | Subscription cancelled. Card freed. The open session continues and closes normally as `is_subscribed = TRUE` (zero charge). The cancelled subscription does not block the session close. |

### 5.3 Reporting Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-SUB-020 | Revenue report for a period with zero subscriptions created | Returns `total_subscriptions = 0`, `total_revenue_piastres = 0`. No division-by-zero error. `by_plan` is an empty list. |
| EC-SUB-021 | Dashboard subscription stats when no subscriptions exist at all | All three counts are `0`. No error. Dashboard renders with `٠` values. |
| EC-SUB-022 | Subscriber has both a completed (expired) and a new active subscription | `get_by_subscriber` returns both. The `active_subscription` field on `SubscriberResponse` shows only the currently `ACTIVE` or `PENDING` one. |

---

## 6. Defined Error Codes

All error responses: `{"detail": "<Arabic message>", "code": "<CODE>"}`.

### 6.1 Plan Errors

| Code | HTTP | Trigger |
|---|---|---|
| `PLAN_LABEL_ALREADY_EXISTS` | 409 | Duplicate plan label on creation or update |
| `PLAN_NOT_FOUND` | 404 | Plan ID does not exist |
| `PLAN_NOT_ACTIVE` | 409 | Creating a subscription under a deactivated plan |
| `PLAN_DURATION_IMMUTABLE` | 422 | Attempting to update `duration_days` |

### 6.2 Subscriber Errors

| Code | HTTP | Trigger |
|---|---|---|
| `SUBSCRIBER_NOT_FOUND` | 404 | Subscriber ID does not exist |
| `SUBSCRIBER_PLATE_ALREADY_EXISTS` | 409 | Duplicate plate number on creation |
| `SUBSCRIBER_PLATE_IMMUTABLE` | 422 | Attempting to update `plate_number` |

### 6.3 Subscription Errors

| Code | HTTP | Trigger |
|---|---|---|
| `SUBSCRIPTION_NOT_FOUND` | 404 | Subscription ID does not exist |
| `SUBSCRIPTION_NOT_ACTIVE` | 409 | Cancel/renew on a non-ACTIVE subscription |
| `SUBSCRIBER_ALREADY_HAS_ACTIVE_SUBSCRIPTION` | 409 | Creating a subscription when one is already ACTIVE or PENDING |
| `SUBSCRIPTION_DAILY_LIMIT_REACHED` | 409 | Entry scan but daily entry count at max |
| `CARD_NOT_AVAILABLE` | 409 | Card is not AVAILABLE for subscription assignment |

### 6.4 General

| Code | HTTP | Trigger |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing or invalid JWT |
| `INSUFFICIENT_PERMISSIONS` | 403 | Non-admin accesses admin endpoint |
| `INVALID_DATE_RANGE` | 422 | `start_date > end_date` in report filters |
| `DATABASE_UNAVAILABLE` | 503 | DB unreachable |
| `INTERNAL_ERROR` | 500 | Unhandled exception |

---

## 7. File Structure Additions for Phase 4

pgms/
├── models/
│   ├── subscription_plan.py        # SubscriptionPlan model
│   ├── subscriber.py               # Subscriber model (with company_name & card_code)
│   └── subscription.py             # Subscription model + SubscriptionStatus enum
├── schemas/
│   └── subscriptions.py            # All Phase 4 Pydantic schemas
├── repositories/
│   ├── subscription_plan_repo.py
│   ├── subscriber_repo.py
│   └── subscription_repo.py
├── services/
│   ├── subscription_plan_service.py
│   ├── subscriber_service.py
│   ├── subscription_service.py
│   └── excel_import_service.py     # Bulk onboarding parser & atomic executor
├── routes/
│   ├── subscriptions_api.py        # /api/v1/subscriptions/* JSON endpoints
│   └── ui_subscriptions.py         # Admin UI subscriber/plan/subscription pages & Excel import
├── templates/
│   ├── admin/
│   │   ├── plans.html
│   │   ├── subscribers.html
│   │   ├── subscriber_new.html
│   │   ├── subscribers_import.html # Drag-and-drop Excel & CSV import
│   │   ├── subscriber_detail.html
│   │   ├── subscriber_subscribe.html
│   │   ├── subscriber_renew.html
│   │   └── subscriptions.html
│   ├── operator/
│   │   ├── entry_confirm.html      # MODIFIED: adds subscription banner
│   │   └── exit_confirm.html       # MODIFIED: adds zero-amount subscription view
│   └── receipts/
│       └── thermal_subscription.html # Subscription thermal receipt
├── tests/
│   ├── unit/
│   │   ├── test_subscription_schemas.py
│   │   ├── test_subscription_repos.py
│   │   ├── test_subscription_plan_service.py
│   │   ├── test_subscription_service.py
│   │   ├── test_subscription_services.py
│   │   ├── test_session_subscription.py
│   │   ├── test_subscription_api.py
│   │   └── test_excel_import.py
│   └── integration/
│       ├── test_subscription_routes.py
│       ├── test_ui_operator_subscriptions.py
│       └── test_ui_subscriptions.py
└── alembic/versions/
    └── 1004_phase4_subscriptions.py # Migration script


---

## 8. Out of Scope for Phase 4

The following are explicitly deferred and must not be implemented:

- Online payment gateway (Fawry, Paymob, etc.) for subscription fees.
- Automated SMS or WhatsApp notifications for expiry reminders.
- Subscriber self-service portal or mobile app.
- Fleet subscriptions (one subscription covering multiple plates).
- Family plans (multiple plates under one subscriber account).
- Automatic subscription renewal with pre-authorized payment.
- Prorated refunds on cancellation.
- Subscription pause/freeze functionality.
- Time-restricted subscriptions (e.g., weekdays only, daytime only).
- QR code generation for subscriber cards.
- Barcode printing for subscriber cards from the system.
- Integration with external CRM or accounting systems.
- Subscription gifting or transfer between subscribers.
- Grace period after expiry (free entry for N days after end date).
- Multi-tier pricing (different rates for different hours within a subscription).

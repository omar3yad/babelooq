# Phase 2 — Atomic Coding Task Checklist

> **Version:** 1.0
> **Scope:** All coding tasks required to complete Phase 2 as specified in
> `spec_phase2.md`.
> **Execution order is mandatory within each group.** All of Group 1 must be
> complete before Group 2 begins, and so on.
> **Each task is atomic:** one file, one class, one method, or one migration block
> per task.
> **All code must pass:** `black`, `ruff`, and `mypy --strict` before a task is
> marked complete.

---

## Group 1 — Database Models & Alembic Migrations

### 1a — Enums

- [ ] **Task 1.1:** Open `models/parking_card.py` (create if absent). Define a
  `CardStatus` Python `enum.Enum` with exactly four values:
  `AVAILABLE = "available"`, `IN_USE = "in_use"`, `LOST = "lost"`,
  `DAMAGED = "damaged"`. Add `__all__ = ["CardStatus"]`. No other code in this
  task.

- [ ] **Task 1.2:** Open `models/parking_session.py` (create if absent). Define a
  `SessionStatus` Python `enum.Enum` with exactly three values:
  `ACTIVE = "ACTIVE"`, `COMPLETED = "COMPLETED"`, `LOST_CARD = "LOST_CARD"`.
  Define a `PaymentMethod` Python `enum.Enum` with one value: `CASH = "cash"`.
  Add both to `__all__`. No other code in this task.

### 1b — ParkingCard Model

- [ ] **Task 1.3:** In `models/parking_card.py`, import `Base` from `database` and
  `TimestampMixin` from `models/mixins.py`. Define the `ParkingCard` class
  inheriting from `Base` and `TimestampMixin`. Set `__tablename__ = "parking_cards"`.
  Add only these columns:
  - `id: Mapped[int]` — primary key, autoincrement.
  - `card_code: Mapped[str]` — `VARCHAR(50)`, unique, not nullable, indexed.

- [ ] **Task 1.4:** In `models/parking_card.py`, add the remaining columns to
  `ParkingCard`:
  - `status: Mapped[CardStatus]` — `SQLAlchemy Enum(CardStatus)`, not nullable,
    `server_default="available"`.
  - `last_seen_at: Mapped[datetime | None]` — `TIMESTAMP`, nullable.
  Add `__all__ = ["CardStatus", "ParkingCard"]` at the bottom of the file.

### 1c — ParkingSession Model Updates

- [ ] **Task 1.5:** Open `models/parking_session.py`. Ensure the `ParkingSession`
  class inherits from `Base` and `TimestampMixin`. Add or verify these columns
  exist with exact types:
  - `id: Mapped[int]` — primary key, autoincrement.
  - `card_id: Mapped[int]` — `Integer`, FK → `parking_cards.id`, not nullable,
    indexed.
  - `card_code: Mapped[str]` — `VARCHAR(50)`, not nullable. Snapshot of card code
    at session open time.
  - `status: Mapped[SessionStatus]` — `SQLAlchemy Enum(SessionStatus)`, not
    nullable, `server_default="ACTIVE"`, indexed.

- [ ] **Task 1.6:** In `models/parking_session.py`, add these columns to
  `ParkingSession`:
  - `gate_number: Mapped[int]` — `SMALLINT`, not nullable.
  - `shift_id: Mapped[int]` — FK → `shifts.id`, not nullable, indexed.
  - `operator_id: Mapped[int]` — FK → `users.id`, not nullable.
  - `entry_time: Mapped[datetime]` — `TIMESTAMP`, not nullable.
  - `exit_time: Mapped[datetime | None]` — `TIMESTAMP`, nullable.
  - `plate_number: Mapped[str | None]` — `VARCHAR(30)`, nullable.

- [ ] **Task 1.7:** In `models/parking_session.py`, add these columns to
  `ParkingSession`:
  - `duration_minutes: Mapped[int | None]` — `INTEGER`, nullable.
  - `pricing_rule_id: Mapped[int | None]` — FK → `pricing_rules.id`, nullable.
  - `amount_charged: Mapped[int | None]` — `INTEGER`, nullable. Stored in
    piastres. Must never be a float.
  - `is_lost_card: Mapped[bool]` — `BOOLEAN`, not nullable,
    `server_default="0"`.
  - `lost_card_penalty_applied: Mapped[int | None]` — `INTEGER`, nullable.
    Snapshot of penalty at close time in piastres.

- [ ] **Task 1.8:** In `models/parking_session.py`, add the final columns to
  `ParkingSession`:
  - `payment_method: Mapped[PaymentMethod]` — `SQLAlchemy Enum(PaymentMethod)`,
    not nullable, `server_default="cash"`.
  - `is_paid: Mapped[bool]` — `BOOLEAN`, not nullable, `server_default="0"`.
  - `exit_operator_id: Mapped[int | None]` — FK → `users.id`, nullable.
  - `exit_shift_id: Mapped[int | None]` — FK → `shifts.id`, nullable.
  - `receipt_printed_at: Mapped[datetime | None]` — `TIMESTAMP`, nullable.
  - `admin_override_by: Mapped[int | None]` — FK → `users.id`, nullable.
  - `admin_override_note: Mapped[str | None]` — `TEXT`, nullable.
  - `is_deleted: Mapped[bool]` — `BOOLEAN`, not nullable, `server_default="0"`.
  - `notes: Mapped[str | None]` — `TEXT`, nullable.
  Add `__all__ = ["SessionStatus", "PaymentMethod", "ParkingSession"]`.

### 1d — PricingRule Model Updates

- [ ] **Task 1.9:** Open `models/pricing_rule.py`. Add one new column to
  `PricingRule` if not already present:
  - `lost_card_penalty: Mapped[int]` — `INTEGER`, not nullable,
    `server_default="0"`. Stored in piastres.
  Verify all other columns from `plan.md` Section 2.2 exist. Update `__all__`.

### 1e — Models `__init__.py`

- [ ] **Task 1.10:** Update `models/__init__.py` to import and re-export all of:
  `CardStatus`, `ParkingCard`, `SessionStatus`, `PaymentMethod`,
  `ParkingSession`, `PricingRule`, `Shift`, `User`, `UserRole`, `AuditLog`.
  Replace the entire file content. Ensure `__all__` lists every export.

### 1f — Alembic Migration

- [ ] **Task 1.11:** Generate a new Alembic migration by running:
  `alembic revision --autogenerate -m "phase2_cards_sessions_pricing_updates"`.
  Open the generated file. Verify `upgrade()` contains in this order:
  1. Create `parking_cards` table with all columns and the unique index on
     `card_code`.
  2. Add `status` column (as `SessionStatus` enum) and index to
     `parking_sessions`.
  3. Add `card_id`, `card_code`, `gate_number`, `shift_id`, `operator_id`,
     `entry_time`, `exit_time`, `plate_number` to `parking_sessions`.
  4. Add `duration_minutes`, `pricing_rule_id`, `amount_charged`, `is_lost_card`,
     `lost_card_penalty_applied`, `payment_method`, `is_paid`,
     `exit_operator_id`, `exit_shift_id`, `receipt_printed_at`,
     `admin_override_by`, `admin_override_note`, `is_deleted`, `notes` to
     `parking_sessions`.
  5. Add `lost_card_penalty` column to `pricing_rules`.
  Verify `downgrade()` reverses all steps cleanly. Do not edit logic — only
  verify and commit.

- [ ] **Task 1.12:** Run `alembic upgrade head` against the local SQLite dev
  database. Confirm all tables and columns exist using `sqlite3` CLI or a DB
  browser. Fix any migration errors before marking complete. Delete any
  `test_verify.db` artifact after verification. Commit no source changes in
  this task.

---

## Group 2 — Pydantic Schemas

- [ ] **Task 2.1:** Create `schemas/parking_card.py`. Define the following Pydantic
  models, all with `model_config = ConfigDict(from_attributes=True)`:
  - `ParkingCardCreate`: field `card_code: str` —
    `Field(min_length=1, max_length=50)`.
  - `ParkingCardBulkCreate`: field `card_codes: list[str]` —
    `Field(min_length=1, max_items=500)`.
  - `ParkingCardResponse`: fields `id: int`, `card_code: str`,
    `status: CardStatus`, `last_seen_at: datetime | None`, `created_at: datetime`,
    `updated_at: datetime`.
  - `ParkingCardStatusUpdate`: field `status: CardStatus`.
  Add `__all__` and import `CardStatus` from `models`.

- [ ] **Task 2.2:** Create `schemas/parking_session.py`. Define:
  - `SessionOpenRequest`: fields `card_code: str` — `Field(min_length=1,
    max_length=50)`, `plate_number: str | None = None`.
  - `SessionExitRequest`: no fields (exit is triggered by session ID in URL;
    amounts are computed server-side). Keep as an empty model for forward
    compatibility.
  - `SessionLostCardRequest`: fields `plate_number: str` —
    `Field(min_length=1, max_length=30)`, `notes: str | None = None`.
  All with `model_config = ConfigDict(from_attributes=True)`.

- [ ] **Task 2.3:** In `schemas/parking_session.py`, define:
  - `PriceBreakdownResponse`: fields `duration_minutes: int`,
    `billable_minutes: int`, `billable_hours: int`, `rate_per_hour: int`,
    `grace_period_mins: int`, `minimum_charge: int`, `base_amount: int`,
    `penalty_amount: int`, `total_amount: int`, `pricing_rule_id: int`,
    `is_grace_period: bool`, `is_lost_card: bool`.
    All integers are piastres. No floats. `model_config =
    ConfigDict(from_attributes=False)` (this is a plain dataclass schema).

- [ ] **Task 2.4:** In `schemas/parking_session.py`, define:
  - `SessionResponse`: all fields from `ParkingSession` model except
    `is_deleted`, `admin_override_note`. Include: `id`, `card_id`, `card_code`,
    `status: SessionStatus`, `gate_number`, `shift_id`, `operator_id`,
    `entry_time`, `exit_time`, `plate_number`, `duration_minutes`,
    `pricing_rule_id`, `amount_charged`, `is_lost_card`,
    `lost_card_penalty_applied`, `payment_method`, `is_paid`,
    `exit_operator_id`, `exit_shift_id`, `receipt_printed_at`, `notes`,
    `created_at`. Set `model_config = ConfigDict(from_attributes=True)`.
  - `SessionLookupResponse`: fields `session: SessionResponse`,
    `price_breakdown: PriceBreakdownResponse`. Used by the exit lookup endpoint.
  Add `__all__` listing all three response schemas.

- [ ] **Task 2.5:** Create `schemas/shift.py`. Define:
  - `ShiftOpenRequest`: field `opening_cash_egp: int` — `Field(ge=0)`. Value
    is in piastres.
  - `ShiftCloseRequest`: field `closing_cash_egp: int` — `Field(ge=0)`.
  - `ShiftResponse`: fields `id`, `operator_id`, `gate_number`, `started_at`,
    `ended_at`, `opening_cash_egp`, `closing_cash_egp`, `notes`, `created_at`,
    `updated_at`. `model_config = ConfigDict(from_attributes=True)`.
  - `ShiftSummaryResponse`: fields `shift_id: int`, `operator_id: int`,
    `gate_number: int`, `started_at: datetime`, `ended_at: datetime | None`,
    `total_sessions: int`, `completed_sessions: int`, `lost_card_sessions: int`,
    `active_sessions: int`, `computed_total_piastres: int`,
    `closing_cash_piastres: int | None`, `discrepancy_piastres: int | None`.
    All monetary fields in piastres, integers only.
  Add `__all__`.

- [ ] **Task 2.6:** Create `schemas/pricing_rule.py`. Define:
  - `PricingRuleCreate`: fields `label: str` — `Field(max_length=100)`,
    `rate_per_hour: int` — `Field(gt=0)`, `minimum_charge: int` — `Field(ge=0)`,
    `grace_period_mins: int` — `Field(ge=0)`, `lost_card_penalty: int` —
    `Field(ge=0)`, `effective_from: datetime`, `effective_until: datetime | None
    = None`.
  - `PricingRuleResponse`: all fields from `PricingRule` model including `id`,
    `label`, `rate_per_hour`, `minimum_charge`, `grace_period_mins`,
    `lost_card_penalty`, `is_active`, `created_by`, `effective_from`,
    `effective_until`, `created_at`, `updated_at`.
    `model_config = ConfigDict(from_attributes=True)`.
  Add `__all__`.

- [ ] **Task 2.7:** Create `schemas/receipt.py`. Define:
  - `ReceiptData`: a Pydantic model (not `from_attributes`) holding all data
    needed to render the receipt template without hitting the DB again: `session_id:
    int`, `card_code: str`, `plate_number: str | None`, `gate_number: int`,
    `operator_name: str`, `entry_time: datetime`, `exit_time: datetime`,
    `duration_minutes: int`, `duration_display: str`, `pricing_rule_label: str`,
    `rate_per_hour: int`, `grace_period_mins: int`, `base_amount: int`,
    `penalty_amount: int`, `total_amount: int`, `total_display: str`,
    `payment_method: str`, `is_lost_card: bool`, `is_grace_period: bool`,
    `garage_name: str`.
  Add `__all__ = ["ReceiptData"]`.

- [ ] **Task 2.8:** Update `schemas/__init__.py` to import and re-export everything
  from `schemas/parking_card.py`, `schemas/parking_session.py`,
  `schemas/shift.py`, `schemas/pricing_rule.py`, and `schemas/receipt.py`.
  Rebuild `__all__` to list every export. Ensure no circular imports.

---

## Group 3 — Pure Services & Domain Logic

### 3a — Domain Exceptions

- [x] **Task 3.1:** Create `services/exceptions.py`. Define the following exception
  classes, each inheriting from `Exception` with an optional `message: str`
  parameter and storing it as `self.message`:
  - `CardNotFoundError`
  - `CardNotAvailableError`
  - `CardAlreadyActiveError`
  - `CardHasNoActiveSessionError`
  - `InvalidBarcodeFormatError`
  - `BulkCardConflictError` — additionally stores `conflicting_codes: list[str]`
  - `SessionNotActiveError`
  - `SessionNotFoundError`
  - `ShiftAlreadyOpenError`
  - `NoActiveShiftError`
  - `ShiftNotFoundError`
  - `ShiftNotOwnedError`
  - `NoPricingRuleError`
  Add `__all__` listing all exceptions.

### 3b — PlateService

- [x] **Task 3.2:** Create `services/plate_service.py`. Define a `PlateService`
  class with no `__init__` parameters (stateless). Add method:
```python
  def normalize(self, plate: str) -> str
```
  Implementation: strip leading/trailing whitespace; replace each Eastern
  Arabic-Indic digit (٠=0, ١=1, ٢=2, ٣=3, ٤=4, ٥=5, ٦=6, ٧=7, ٨=8, ٩=9)
  with its Western equivalent using `str.translate`; collapse multiple internal
  spaces to a single space; return the result. Must not raise on empty string —
  returns empty string.

- [x] **Task 3.3:** In `services/plate_service.py`, add method:
```python
  def validate(self, plate: str) -> bool
```
  Normalizes the plate first. Then checks: the result matches the pattern
  `^[\u0600-\u06FF]{1,3} \d{1,4}$` using `re.match`. Returns `True` or
  `False`. Never raises.

- [x] **Task 3.4:** In `services/plate_service.py`, add method:
```python
  def search_normalized(self, plate: str) -> str
```
  Calls `self.normalize(plate)`, then applies
  `unicodedata.normalize('NFKD', result)` and removes all combining characters
  (Unicode category `'Mn'`) using a list comprehension. Returns the result.
  Used for DB search comparison only — never for storage. Add
  `__all__ = ["PlateService"]`.

### 3c — Pricing Helpers (Pure Functions)

- [x] **Task 3.5:** Create `services/pricing_helpers.py`. Define a pure function:
```python
  def format_duration(minutes: int) -> str
```
  Converts integer minutes to an Arabic string. Rules (use Arabic-Indic numerals
  via a helper — see Task 3.6):
  - `0` → `"٠ دقائق"`
  - `1` → `"دقيقة واحدة"`
  - `2` → `"دقيقتان"`
  - `3–10` → `"N دقائق"` (Arabic plural)
  - `11–59` → `"N دقيقة"`
  - `60` → `"ساعة واحدة"`
  - `120` → `"ساعتان"`
  - `61–119, 121–179, ...` (non-exact hours) → `"N ساعة و M دقيقة"` or
    `"ساعة واحدة و M دقيقة"` or `"ساعتان و M دقيقة"` depending on hour count.
  - Exact multiples of 60 from 180 upward → `"N ساعات"`.
  - Non-exact hours ≥ 180 min → `"N ساعات و M دقيقة"`.
  This function has zero imports from the project — only stdlib. No I/O.

- [x] **Task 3.6:** In `services/pricing_helpers.py`, define a pure helper:
```python
  def to_arabic_indic(n: int) -> str
```
  Converts a non-negative integer to its Arabic-Indic numeral string by mapping
  each digit: `{'0':'٠','1':'١','2':'٢','3':'٣','4':'٤','5':'٥','6':'٦',
  '7':'٧','8':'٨','9':'٩'}`. Returns the converted string. Used internally by
  `format_duration` and `format_egp`.

- [x] **Task 3.7:** In `services/pricing_helpers.py`, define a pure function:
```python
  def format_egp(piastres: int) -> str
```
  Converts an integer piastres value to a display string with Arabic-Indic
  numerals and two decimal places. Algorithm: `egp = piastres // 100`,
  `fils = piastres % 100`. Format as `f"{egp}.{fils:02d}"`. Convert all digits
  to Arabic-Indic via `to_arabic_indic` applied character by character (preserve
  the `.`). Append ` ج.م`. Example: `2500` → `"٢٥٫٠٠ ج.م"`. The decimal
  point `"."` is replaced with `"٫"` (Arabic decimal separator U+066B). No
  floats used anywhere. Add `__all__ = ["format_duration", "format_egp",
  "to_arabic_indic"]`.

### 3d — PriceCalculation Dataclass

- [ ] **Task 3.8:** Create `services/pricing_calculation.py`. Define a Python
  `dataclasses.dataclass` (frozen=True) named `PriceCalculation` with fields:
  `duration_minutes: int`, `billable_minutes: int`, `billable_hours: int`,
  `rate_per_hour: int`, `grace_period_mins: int`, `minimum_charge: int`,
  `base_amount: int`, `penalty_amount: int`, `total_amount: int`,
  `pricing_rule_id: int`, `is_grace_period: bool`, `is_lost_card: bool`.
  All integer fields represent piastres where monetary. No SQLAlchemy imports.
  No Pydantic imports. Add `__all__ = ["PriceCalculation"]`.

### 3e — ShiftSummary Dataclass

- [ ] **Task 3.9:** Create `services/shift_summary.py`. Define a Python
  `dataclasses.dataclass` (frozen=True) named `ShiftSummary` with fields:
  `shift_id: int`, `operator_id: int`, `gate_number: int`,
  `started_at: datetime`, `ended_at: datetime | None`, `total_sessions: int`,
  `completed_sessions: int`, `lost_card_sessions: int`, `active_sessions: int`,
  `computed_total_piastres: int`, `closing_cash_piastres: int | None`,
  `discrepancy_piastres: int | None`. No SQLAlchemy imports. No Pydantic imports.
  Add `__all__ = ["ShiftSummary"]`.

### 3f — PricingService

- [x] **Task 3.10:** Create `services/pricing_service.py`. Define a `PricingService`
  class with `__init__(self, db: AsyncSession)`. Add method:
```python
  async def get_active_rule(self) -> PricingRule
```
  Executes `SELECT * FROM pricing_rules WHERE is_active = TRUE LIMIT 1`.
  Returns the `PricingRule`. Raises `NoPricingRuleError("No active pricing rule")`
  if the query returns no result.

- [x] **Task 3.11:** In `services/pricing_service.py`, add method:
```python
  def calculate(
      self,
      session: ParkingSession,
      rule: PricingRule,
      exit_time: datetime,
  ) -> PriceCalculation
```
  This method is **synchronous and pure** (no DB calls — rule is passed in).
  Algorithm using only integer arithmetic and `math.ceil`:
  1. `total_seconds = (exit_time - session.entry_time).total_seconds()`
  2. `duration_minutes = math.ceil(total_seconds / 60)` — minimum 0.
  3. If `duration_minutes <= rule.grace_period_mins`: `is_grace_period = True`,
     `billable_minutes = 0`, `billable_hours = 0`,
     `base_amount = rule.minimum_charge`.
  4. Else: `is_grace_period = False`,
     `billable_minutes = duration_minutes - rule.grace_period_mins`,
     `billable_hours = math.ceil(billable_minutes / 60)`,
     `raw = billable_hours * rule.rate_per_hour`,
     `base_amount = max(raw, rule.minimum_charge)`.
  5. `penalty_amount = 0`, `total_amount = base_amount`.
  Returns `PriceCalculation(...)`. No floats anywhere.

- [x] **Task 3.12:** In `services/pricing_service.py`, add method:
```python
  def calculate_lost_card(
      self,
      session: ParkingSession,
      rule: PricingRule,
      exit_time: datetime,
  ) -> PriceCalculation
```
  Calls `self.calculate(session, rule, exit_time)` to get the base calculation.
  Returns a new `PriceCalculation` identical to the base but with:
  `penalty_amount = rule.lost_card_penalty`,
  `total_amount = base_calc.base_amount + rule.lost_card_penalty`,
  `is_lost_card = True`. Does not mutate the base dataclass (it is frozen).

- [x] **Task 3.13:** In `services/pricing_service.py`, add method:
```python
  async def preview(self, entry_time: datetime) -> PriceCalculation
```
  Calls `await self.get_active_rule()`, then calls
  `self.calculate(mock_session, rule, utcnow())` where `mock_session` is a
  minimal `SimpleNamespace(entry_time=entry_time)` (not a DB object). Returns
  the `PriceCalculation`. Add `__all__ = ["PricingService"]`.

### 3g — CardService

- [x] **Task 3.14:** Create `services/card_service.py`. Define a `CardService`
  class with `__init__(self, db: AsyncSession)`. Add method:
```python
  def normalize_code(self, raw: str) -> str
```
  Strips all whitespace (`raw.strip()`), uppercases (`upper()`). If the result
  is empty or does not match `^[A-Z0-9\-_]{1,50}$`, raises
  `InvalidBarcodeFormatError(f"Invalid barcode: '{raw[:20]}'")`. Returns the
  normalized string. This method is synchronous.

- [x] **Task 3.15:** In `services/card_service.py`, add method:
```python
  async def get_by_code(self, card_code: str) -> ParkingCard
```
  Normalizes `card_code` via `self.normalize_code`. Queries
  `SELECT * FROM parking_cards WHERE card_code = :code LIMIT 1`. Raises
  `CardNotFoundError(f"Card '{card_code}' not found")` if no result. Returns
  the `ParkingCard`.

- [x] **Task 3.16:** In `services/card_service.py`, add method:
```python
  async def validate_for_entry(self, card_code: str) -> ParkingCard
```
  Calls `await self.get_by_code(card_code)`. If `card.status ==
  CardStatus.IN_USE`, raises `CardAlreadyActiveError`. If `card.status` is
  `CardStatus.LOST` or `CardStatus.DAMAGED`, raises `CardNotAvailableError`.
  Returns the card only if `status == CardStatus.AVAILABLE`.

- [x] **Task 3.17:** In `services/card_service.py`, add method:
```python
  async def validate_for_exit(self, card_code: str, session_repo) -> ParkingSession
```
  Calls `await self.get_by_code(card_code)`. Then calls
  `await session_repo.get_active_by_card_id(card.id)`. Raises
  `CardHasNoActiveSessionError` if `None`. Returns the `ParkingSession`.

- [x] **Task 3.18:** In `services/card_service.py`, add method:
```python
  async def set_status(
      self, card: ParkingCard, status: CardStatus
  ) -> ParkingCard
```
  Sets `card.status = status` and `card.last_seen_at = datetime.utcnow()`.
  Calls `self.db.flush()`. Does **not** commit (caller is responsible). Returns
  the updated card. Add `__all__ = ["CardService"]`.

### 3h — ShiftService

- [x] **Task 3.19:** Create `services/shift_service.py`. Define a `ShiftService`
  class with `__init__(self, db: AsyncSession, audit_service: AuditService)`.
  Add method:
```python
  async def get_active_shift(self, operator_id: int) -> Shift | None
```
  Queries `SELECT * FROM shifts WHERE operator_id = :id AND ended_at IS NULL
  LIMIT 1`. Returns the `Shift` or `None`.

- [x] **Task 3.20:** In `services/shift_service.py`, add method:
```python
  async def require_active_shift(self, operator_id: int) -> Shift
```
  Calls `await self.get_active_shift(operator_id)`. Raises `NoActiveShiftError`
  if `None`. Returns the `Shift`.

- [x] **Task 3.21:** In `services/shift_service.py`, add method:
```python
  async def open_shift(
      self, operator_id: int, gate_number: int, opening_cash_egp: int
  ) -> Shift
```
  Calls `await self.get_active_shift(operator_id)`. Raises
  `ShiftAlreadyOpenError` if a shift is returned. Creates a new `Shift` with
  `operator_id`, `gate_number`, `opening_cash_egp`, `started_at=utcnow()`.
  Adds to `self.db`, flushes, commits. Calls `audit_service.log(...)` with
  action `"SHIFT_OPENED"`, `entity_type="shift"`, `entity_id=shift.id`. Returns
  the shift.

- [x] **Task 3.22:** In `services/shift_service.py`, add method:
```python
  async def close_shift(
      self,
      shift_id: int,
      operator_id: int,
      closing_cash_piastres: int,
  ) -> ShiftSummary
```
  Fetches shift by `shift_id`. Raises `ShiftNotFoundError` if absent. Raises
  `ShiftNotOwnedError` if `shift.operator_id != operator_id`. Sets
  `shift.ended_at = utcnow()`, `shift.closing_cash_egp = closing_cash_piastres`.
  Calls `await self._compute_summary(shift, closing_cash_piastres)`. Flushes and
  commits. Calls `audit_service.log(...)` with action `"SHIFT_CLOSED"`. Returns
  the `ShiftSummary`.

- [x] **Task 3.23:** In `services/shift_service.py`, add private method:
```python
  async def _compute_summary(
      self, shift: Shift, closing_cash_piastres: int | None
  ) -> ShiftSummary
```
  Queries `parking_sessions` where `shift_id = shift.id`. Counts: `total` (all),
  `completed` (`status = COMPLETED`), `lost_card` (`status = LOST_CARD`),
  `active` (`status = ACTIVE`). Sums `amount_charged` for COMPLETED and
  LOST_CARD sessions (ignoring `NULL`). Computes
  `discrepancy = closing_cash_piastres - computed_total` if
  `closing_cash_piastres` is not `None`, else `None`. Returns `ShiftSummary(...)`.
  Add `__all__ = ["ShiftService"]`.

### 3i — Services `__init__.py`

- [x] **Task 3.24:** Update `services/__init__.py` to import and re-export:
  `PlateService`, `PricingService`, `PriceCalculation`, `CardService`,
  `ShiftService`, `ShiftSummary`, `format_duration`, `format_egp`,
  `to_arabic_indic`, and all exceptions from `services/exceptions.py`. Rebuild
  `__all__`.

---

## Group 4 — Repositories & Data Access

### 4a — ParkingCard Repository

- [x] **Task 4.1:** Create `repositories/card_repo.py`. Define a
  `ParkingCardRepository` class with `__init__(self, db: AsyncSession)`. Add
  method:
```python
  async def get_by_code(self, card_code: str) -> ParkingCard | None
```
  `SELECT * FROM parking_cards WHERE card_code = :code LIMIT 1`. Returns the
  object or `None`. No normalization here — caller must normalize first.

- [x] **Task 4.2:** In `repositories/card_repo.py`, add method:
```python
  async def create(self, card_code: str) -> ParkingCard
```
  Creates `ParkingCard(card_code=card_code, status=CardStatus.AVAILABLE)`. Adds
  to session, flushes. Does not commit. Returns the card.

- [x] **Task 4.3:** In `repositories/card_repo.py`, add method:
```python
  async def bulk_create(self, card_codes: list[str]) -> list[ParkingCard]
```
  Creates a `ParkingCard` object for each code. Adds all to session in a single
  `self.db.add_all(cards)` call. Flushes once. Returns the list. Does not
  commit. Caller checks for duplicates before calling this method.

- [x] **Task 4.4:** In `repositories/card_repo.py`, add method:
```python
  async def get_all(
      self,
      status: CardStatus | None = None,
      page: int = 1,
      size: int = 20,
  ) -> tuple[list[ParkingCard], int]
```
  Builds a `select(ParkingCard)` query. Applies `WHERE status = :status` if
  provided. Returns `(cards, total_count)` using a separate count query with
  the same filter. Uses `offset((page-1)*size).limit(size)`.

- [x] **Task 4.5:** In `repositories/card_repo.py`, add method:
```python
  async def get_existing_codes(self, codes: list[str]) -> list[str]
```
  Queries `SELECT card_code FROM parking_cards WHERE card_code IN (:codes)`.
  Returns the list of codes that already exist in the DB. Used for bulk
  duplicate checking. Add `__all__ = ["ParkingCardRepository"]`.

### 4b — ParkingSession Repository

- [x] **Task 4.6:** Create `repositories/session_repo.py`. Define a
  `ParkingSessionRepository` class with `__init__(self, db: AsyncSession)`.
  Add method:
```python
  async def get_active_by_card_id(
      self, card_id: int
  ) -> ParkingSession | None
```
  `SELECT * FROM parking_sessions WHERE card_id = :id AND status = 'ACTIVE'
  LIMIT 1`. Returns session or `None`.

- [x] **Task 4.7:** In `repositories/session_repo.py`, add method:
```python
  async def get_by_id_for_update(self, session_id: int) -> ParkingSession | None
```
  For PostgreSQL: uses `SELECT ... FOR UPDATE` via SQLAlchemy
  `.with_for_update()`. For SQLite (detected by dialect): uses a regular
  `SELECT` (SQLite's file-level locking provides sufficient isolation for
  single-server deployments). Returns the session or `None`. This is the **only**
  method used when closing or resolving a session to prevent race conditions.

- [x] **Task 4.8:** In `repositories/session_repo.py`, add method:
```python
  async def create(
      self,
      card_id: int,
      card_code: str,
      gate_number: int,
      shift_id: int,
      operator_id: int,
      plate_number: str | None,
  ) -> ParkingSession
```
  Creates `ParkingSession(...)` with `status=SessionStatus.ACTIVE`,
  `entry_time=datetime.utcnow()`, `is_paid=False`, `is_lost_card=False`.
  Adds to session, flushes. Does not commit. Returns the session.

- [x] **Task 4.9:** In `repositories/session_repo.py`, add method:
```python
  async def get_active_by_plate(
      self, plate_normalized: str
  ) -> list[ParkingSession]
```
  Queries `SELECT * FROM parking_sessions WHERE status = 'ACTIVE' AND
  plate_number = :plate`. Returns a list (may be empty or multiple rows). Caller
  provides the normalized plate string.

- [x] **Task 4.10:** In `repositories/session_repo.py`, add method:
```python
  async def get_by_shift(
      self, shift_id: int, page: int = 1, size: int = 10
  ) -> tuple[list[ParkingSession], int]
```
  Returns sessions for a shift ordered by `entry_time DESC`, paginated. Uses a
  separate count query with the same `shift_id` filter.

- [x] **Task 4.11:** In `repositories/session_repo.py`, add method:
```python
  async def get_by_id(self, session_id: int) -> ParkingSession | None
```
  Standard `SELECT * WHERE id = :id`. Returns session or `None`. This is the
  **read-only** variant; use `get_by_id_for_update` when intending to mutate.

- [x] **Task 4.12:** In `repositories/session_repo.py`, add method:
```python
  async def count_by_shift_and_status(
      self, shift_id: int, status: SessionStatus | None = None
  ) -> int
```
  `SELECT COUNT(*) FROM parking_sessions WHERE shift_id = :id [AND status =
  :status]`. Returns integer count. Add `__all__ = ["ParkingSessionRepository"]`.

### 4c — PricingRule Repository

- [x] **Task 4.13:** Create `repositories/rate_repo.py`. Define a
  `PricingRuleRepository` class with `__init__(self, db: AsyncSession)`. Add
  methods:
```python
  async def get_active(self) -> PricingRule | None
  async def get_by_id(self, rule_id: int) -> PricingRule | None
  async def get_all(self, page: int = 1, size: int = 20) -> tuple[list[PricingRule], int]
  async def create(self, **kwargs) -> PricingRule
  async def set_active(self, rule_id: int) -> PricingRule
```
  `set_active` must: first set `is_active = FALSE` on all rules (single UPDATE),
  then set `is_active = TRUE` on the target rule. Both in one transaction, single
  flush. Add `__all__ = ["PricingRuleRepository"]`.

### 4d — Shift Repository

- [x] **Task 4.14:** Create `repositories/shift_repo.py`. Define a
  `ShiftRepository` class with `__init__(self, db: AsyncSession)`. Add methods:
```python
  async def get_by_id(self, shift_id: int) -> Shift | None
  async def get_active_for_operator(self, operator_id: int) -> Shift | None
  async def create(self, **kwargs) -> Shift
  async def get_all(
      self,
      operator_id: int | None = None,
      gate_number: int | None = None,
      page: int = 1,
      size: int = 20,
  ) -> tuple[list[Shift], int]
```
  All methods flush but do not commit. Add `__all__ = ["ShiftRepository"]`.

### 4e — Repositories `__init__.py`

- [x] **Task 4.15:** Update `repositories/__init__.py` to import and re-export:
  `ParkingCardRepository`, `ParkingSessionRepository`, `PricingRuleRepository`,
  `ShiftRepository`, `UserRepository`, `AuditLogRepository`. Rebuild `__all__`.

---

## Group 5 — Session Service & Core Business Logic

- [x] **Task 5.1:** Create `services/session_service.py`. Define a `SessionService`
  class with:
```python
  def __init__(
      self,
      db: AsyncSession,
      card_service: CardService,
      session_repo: ParkingSessionRepository,
      pricing_service: PricingService,
      shift_service: ShiftService,
      audit_service: AuditService,
      plate_service: PlateService,
  )
```
  Store all seven as instance attributes. No logic in `__init__`.

- [x] **Task 5.2:** In `services/session_service.py`, add method:
```python
  async def open_session(
      self,
      card_code: str,
      operator_id: int,
      plate_number: str | None = None,
  ) -> ParkingSession
```
  Step-by-step implementation:
  1. `shift = await self.shift_service.require_active_shift(operator_id)` —
     raises `NoActiveShiftError` if absent.
  2. `card = await self.card_service.validate_for_entry(card_code)` — raises
     `CardAlreadyActiveError`, `CardNotAvailableError`, or `CardNotFoundError`.
  3. If `plate_number` is not `None`: normalize via
     `self.plate_service.normalize(plate_number)`; if result is empty string,
     set `plate_number = None`.
  4. `session = await self.session_repo.create(card_id=card.id,
     card_code=card.card_code, gate_number=shift.gate_number,
     shift_id=shift.id, operator_id=operator_id, plate_number=plate_number)`.
  5. `await self.card_service.set_status(card, CardStatus.IN_USE)`.
  6. `await self.db.commit()`.
  7. `await self.audit_service.log(actor_id=operator_id,
     action="SESSION_OPENED", entity_type="parking_session",
     entity_id=session.id, before=None, after={"card_code": card.card_code,
     "gate_number": shift.gate_number})`.
  8. Return `session`.
  If any step raises after step 4 (after session is flushed), the `await
  self.db.rollback()` is called in a `try/except` block. The entire operation
  is atomic.

- [x] **Task 5.3:** In `services/session_service.py`, add method:
```python
  async def close_session(
      self,
      session_id: int,
      exit_operator_id: int,
  ) -> tuple[ParkingSession, PriceCalculation]
```
  Step-by-step implementation:
  1. `exit_shift = await self.shift_service.require_active_shift(exit_operator_id)`.
  2. `session = await self.session_repo.get_by_id_for_update(session_id)`.
     Raises `SessionNotFoundError` if `None`.
  3. If `session.status != SessionStatus.ACTIVE`: raises `SessionNotActiveError`.
  4. `rule = await self.pricing_service.get_active_rule()`.
  5. `exit_time = datetime.utcnow()`.
  6. `calc = self.pricing_service.calculate(session, rule, exit_time)`.
  7. Update session fields: `status=SessionStatus.COMPLETED`,
     `exit_time=exit_time`, `exit_operator_id=exit_operator_id`,
     `exit_shift_id=exit_shift.id`, `duration_minutes=calc.duration_minutes`,
     `amount_charged=calc.total_amount`, `pricing_rule_id=rule.id`,
     `is_paid=True`.
  8. `await self.card_service.set_status(card, CardStatus.AVAILABLE)` — fetch
     card via `card_id` on session.
  9. `await self.db.commit()`.
  10. `await self.audit_service.log(...)` with action `"SESSION_CLOSED"`.
  11. Return `(session, calc)`.

- [x] **Task 5.4:** In `services/session_service.py`, add method:
```python
  async def resolve_lost_card(
      self,
      session_id: int,
      operator_id: int,
      notes: str | None = None,
  ) -> tuple[ParkingSession, PriceCalculation]
```
  Step-by-step implementation:
  1. `shift = await self.shift_service.require_active_shift(operator_id)`.
  2. `session = await self.session_repo.get_by_id_for_update(session_id)`.
     Raises `SessionNotFoundError` if `None`.
  3. If `session.status != SessionStatus.ACTIVE`: raises `SessionNotActiveError`.
  4. `rule = await self.pricing_service.get_active_rule()`.
  5. `exit_time = datetime.utcnow()`.
  6. `calc = self.pricing_service.calculate_lost_card(session, rule, exit_time)`.
  7. Update session: `status=SessionStatus.LOST_CARD`, `exit_time=exit_time`,
     `is_lost_card=True`, `exit_operator_id=operator_id`,
     `exit_shift_id=shift.id`, `duration_minutes=calc.duration_minutes`,
     `amount_charged=calc.total_amount`, `pricing_rule_id=rule.id`,
     `lost_card_penalty_applied=rule.lost_card_penalty`, `is_paid=True`,
     `notes=notes`.
  8. Fetch card by `session.card_id`, call `await self.card_service.set_status
     (card, CardStatus.LOST)`.
  9. `await self.db.commit()`.
  10. `await self.audit_service.log(...)` with action `"LOST_CARD_RESOLVED"`.
  11. Return `(session, calc)`.

- [x] **Task 5.5:** In `services/session_service.py`, add method:
```python
  async def find_active_by_plate(
      self, plate: str
  ) -> list[ParkingSession]
```
  Normalizes via `self.plate_service.normalize(plate)`. Calls
  `await self.session_repo.get_active_by_plate(normalized)`. Returns the list
  (empty list is a valid return — not an error).

- [x] **Task 5.6:** In `services/session_service.py`, add method:
```python
  async def mark_receipt_printed(self, session_id: int) -> None
```
  Fetches session by ID (read-only `get_by_id`). If `session.receipt_printed_at
  is None`: sets `session.receipt_printed_at = datetime.utcnow()`, flushes,
  commits. If already set: does nothing (idempotent). Add
  `__all__ = ["SessionService"]`.

- [x] **Task 5.7:** Update `services/__init__.py` to add `SessionService` to imports
  and `__all__`.

---

## Group 6 — API Routes

### 6a — Cards API

- [x] **Task 6.1:** Create `routes/cards.py`. Define `router = APIRouter(prefix=
  "/api/v1/cards", tags=["cards"])`. Add `POST /` endpoint:
  - Auth: `Depends(require_admin)`.
  - Body: `ParkingCardCreate`.
  - Calls `CardService.normalize_code(data.card_code)`. Checks for existing card
    via `ParkingCardRepository.get_by_code`. Raises `HTTPException(409,
    code="CARD_CODE_ALREADY_EXISTS")` if found.
  - Calls `ParkingCardRepository.create(normalized_code)`. Commits.
  - Returns `{"data": ParkingCardResponse(...)}` with status `201`.

- [x] **Task 6.2:** In `routes/cards.py`, add `POST /bulk` endpoint:
  - Auth: `Depends(require_admin)`.
  - Body: `ParkingCardBulkCreate`.
  - Normalizes all codes via `CardService.normalize_code`.
  - Calls `ParkingCardRepository.get_existing_codes(codes)` — if any exist,
    raises `HTTPException(409, code="BULK_CARD_CONFLICT", detail=
    f"Duplicate codes: {conflicting}")`.
  - Calls `ParkingCardRepository.bulk_create(codes)`. Commits.
  - Returns `{"data": [ParkingCardResponse(...)], "created": len(cards)}` with
    status `201`.

- [x] **Task 6.3:** In `routes/cards.py`, add `GET /` endpoint:
  - Auth: `Depends(require_admin)`.
  - Query params: `status: CardStatus | None = None`, `page: int = Query(1,
    ge=1)`, `size: int = Query(20, ge=1, le=100)`.
  - Returns `PaginatedResponse[ParkingCardResponse]`.

- [x] **Task 6.4:** In `routes/cards.py`, add `GET /{card_code}` endpoint:
  - Auth: `Depends(require_any_role)`.
  - Normalizes `card_code` via `CardService.normalize_code`. Raises
    `HTTPException(422, code="INVALID_BARCODE_FORMAT")` on
    `InvalidBarcodeFormatError`.
  - Calls `ParkingCardRepository.get_by_code`. Raises `HTTPException(404,
    code="CARD_NOT_FOUND")` if absent.
  - Returns `{"data": ParkingCardResponse(...)}`.

- [x] **Task 6.5:** In `routes/cards.py`, add `PATCH /{card_code}/status`
  endpoint:
  - Auth: `Depends(require_admin)`.
  - Body: `ParkingCardStatusUpdate`.
  - Fetches card, updates `status`, commits. Returns updated card.
  - Raises `HTTPException(404, code="CARD_NOT_FOUND")` if card absent.
  - Logs `"CARD_STATUS_CHANGED"` in audit log.

### 6b — Sessions API

- [x] **Task 6.6:** Create `routes/sessions.py`. Define `router = APIRouter(
  prefix="/api/v1/sessions", tags=["sessions"])`. Add `POST /` endpoint:
  - Auth: `Depends(require_operator)`.
  - Body: `SessionOpenRequest`.
  - Instantiates all required services. Calls `SessionService.open_session(
    data.card_code, current_user.id, data.plate_number)`.
  - Maps service exceptions to HTTP exceptions:
    - `InvalidBarcodeFormatError` → `422` `INVALID_BARCODE_FORMAT`
    - `CardNotFoundError` → `404` `CARD_NOT_FOUND`
    - `CardAlreadyActiveError` → `409` `CARD_ALREADY_ACTIVE`
    - `CardNotAvailableError` → `409` `CARD_NOT_AVAILABLE`
    - `NoActiveShiftError` → `403` `NO_ACTIVE_SHIFT`
  - Returns `{"data": SessionResponse(...)}` with status `201`.

- [x] **Task 6.7:** In `routes/sessions.py`, add `GET /active` endpoint:
  - Auth: `Depends(require_admin)`.
  - Queries all sessions with `status = ACTIVE` via `ParkingSessionRepository`.
  - Supports pagination: `page`, `size` query params.
  - Returns `PaginatedResponse[SessionResponse]`.

- [x] **Task 6.8:** In `routes/sessions.py`, add `GET /{session_id}` endpoint:
  - Auth: `Depends(require_any_role)`.
  - Fetches via `ParkingSessionRepository.get_by_id`. Raises `HTTPException(404,
    code="SESSION_NOT_FOUND")` if absent.
  - Returns `{"data": SessionResponse(...)}`.

- [x] **Task 6.9:** In `routes/sessions.py`, add `PATCH /{session_id}/exit`
  endpoint:
  - Auth: `Depends(require_operator)`.
  - No request body.
  - Calls `SessionService.close_session(session_id, current_user.id)`.
  - Maps exceptions:
    - `SessionNotFoundError` → `404` `SESSION_NOT_FOUND`
    - `SessionNotActiveError` → `409` `SESSION_NOT_ACTIVE`
    - `NoActiveShiftError` → `403` `NO_ACTIVE_SHIFT`
    - `NoPricingRuleError` → `503` `NO_ACTIVE_PRICING_RULE`
  - Returns `{"data": SessionResponse(...), "price_breakdown":
    PriceBreakdownResponse(...)}` with status `200`.

- [x] **Task 6.10:** In `routes/sessions.py`, add `PATCH /{session_id}/lost-card`
  endpoint:
  - Auth: `Depends(require_operator)`.
  - Body: `SessionLostCardRequest` (plate_number, notes).
  - Calls `SessionService.resolve_lost_card(session_id, current_user.id,
    data.notes)`.
  - Maps same exceptions as Task 6.9.
  - Returns `{"data": SessionResponse(...), "price_breakdown":
    PriceBreakdownResponse(...)}` with status `200`.

- [x] **Task 6.11:** In `routes/sessions.py`, add `GET /{session_id}/receipt`
  endpoint:
  - Auth: `Depends(require_any_role)`.
  - Fetches session, fetches operator name, fetches pricing rule label.
  - Calls `SessionService.mark_receipt_printed(session_id)`.
  - Builds and returns `{"data": ReceiptData(...)}`.
  - Raises `HTTPException(404)` if session absent.

### 6c — Shifts API

- [x] **Task 6.12:** Create `routes/shifts.py`. Define `router = APIRouter(
  prefix="/api/v1/shifts", tags=["shifts"])`. Add `POST /` endpoint:
  - Auth: `Depends(require_operator)`.
  - Body: `ShiftOpenRequest`.
  - Calls `ShiftService.open_shift(current_user.id, current_user.gate_number,
    data.opening_cash_egp)`.
  - Maps `ShiftAlreadyOpenError` → `HTTPException(409, code=
    "SHIFT_ALREADY_OPEN")`.
  - Returns `{"data": ShiftResponse(...)}` with status `201`.

- [x] **Task 6.13:** In `routes/shifts.py`, add `GET /active` endpoint:
  - Auth: `Depends(require_any_role)`.
  - For operators: calls `ShiftService.get_active_shift(current_user.id)`.
  - For admins: query param `operator_id: int` required; uses that ID.
  - Raises `HTTPException(404, code="SHIFT_NOT_FOUND")` if none found.
  - Returns `{"data": ShiftResponse(...)}`.

- [x] **Task 6.14:** In `routes/shifts.py`, add `PATCH /{shift_id}/close`
  endpoint:
  - Auth: `Depends(require_operator)`.
  - Body: `ShiftCloseRequest`.
  - Calls `ShiftService.close_shift(shift_id, current_user.id,
    data.closing_cash_egp)`.
  - Maps `ShiftNotOwnedError` → `403`, `ShiftNotFoundError` → `404`.
  - Returns `{"data": ShiftSummaryResponse(...)}`.

- [x] **Task 6.15:** In `routes/shifts.py`, add `GET /{shift_id}/summary`
  endpoint:
  - Auth: `Depends(require_any_role)`.
  - Fetches shift, calls `ShiftService._compute_summary(shift,
    shift.closing_cash_egp)`.
  - Returns `{"data": ShiftSummaryResponse(...)}`.

- [x] **Task 6.16:** In `routes/shifts.py`, add `GET /{shift_id}/sessions`
  endpoint:
  - Auth: `Depends(require_any_role)`.
  - Calls `ParkingSessionRepository.get_by_shift(shift_id, page, size)`.
  - Returns `PaginatedResponse[SessionResponse]`.

### 6d — Rates API

- [x] **Task 6.17:** Create `routes/rates.py`. Define `router = APIRouter(
  prefix="/api/v1/rates", tags=["rates"])`. Add these endpoints:
  - `GET /active` — auth: `require_any_role`. Returns active rule or `503`
    with `NO_ACTIVE_PRICING_RULE`.
  - `GET /preview` — auth: `require_any_role`. Query param:
    `entry_time: datetime`. Calls `PricingService.preview(entry_time)`. Returns
    `{"data": PriceBreakdownResponse(...)}`.
  - `GET /` — auth: `require_admin`. Paginated list of all rules.
  - `POST /` — auth: `require_admin`. Body: `PricingRuleCreate`. Creates rule
    with `created_by=current_user.id`. Returns `201`.
  - `PATCH /{rule_id}/activate` — auth: `require_admin`. Calls
    `PricingRuleRepository.set_active(rule_id)`. Logs `"RATE_ACTIVATED"`. Returns
    updated rule.

### 6e — Router Registration

- [x] **Task 6.18:** In `main.py`, import the four new routers from `routes/cards.py`,
  `routes/sessions.py`, `routes/shifts.py`, and `routes/rates.py`. Add four
  `app.include_router(...)` calls after the existing Phase 1 routers. No other
  changes to `main.py` in this task.

---

## Group 7 — Jinja2 Filters, Helpers & Static Assets

### 7a — Jinja2 Filters

- [x] **Task 7.1:** Open `utils/jinja.py`. Add a `format_egp_filter` function:
```python
  def format_egp_filter(piastres: int | None) -> str
```
  If `piastres is None`: returns `"—"`. Calls `format_egp(piastres)` from
  `services/pricing_helpers.py`. Returns the result. This is the function
  registered as the `format_egp` Jinja2 filter.

- [x] **Task 7.2:** In `utils/jinja.py`, add a `format_duration_filter` function:
```python
  def format_duration_filter(minutes: int | None) -> str
```
  If `minutes is None`: returns `"—"`. Calls `format_duration(minutes)` from
  `services/pricing_helpers.py`. Returns the result. Registered as
  `format_duration` Jinja2 filter.

- [x] **Task 7.3:** In `utils/jinja.py`, add a `format_datetime_filter` function:
```python
  def format_datetime_filter(dt: datetime | None) -> str
```
  If `dt is None`: returns `"—"`. Converts UTC `dt` to Cairo local time
  (`Africa/Cairo`, UTC+2) using `datetime + timedelta(hours=2)` (no external
  timezone library required in Phase 2; use stdlib only). Formats as
  `DD/MM/YYYY HH:mm` using Arabic-Indic digits via `to_arabic_indic`.
  Returns the string.

- [x] **Task 7.4:** In `utils/jinja.py`, update `create_jinja2_environment` to
  register the three new filters on the `Jinja2Templates` environment:
  - `templates.env.filters["format_egp"] = format_egp_filter`
  - `templates.env.filters["format_duration"] = format_duration_filter`
  - `templates.env.filters["format_datetime"] = format_datetime_filter`
  Also register `format_duration` and `format_egp` as globals for use without
  pipe syntax. No other changes to this function.

### 7b — Translations

- [x] **Task 7.5:** Update `translations/ar.json`. Add the following keys with
  Arabic values:
  `"operator.dashboard.title"`, `"operator.dashboard.entry_button"` (`"دخول"`)
  , `"operator.dashboard.exit_button"` (`"خروج"`),
  `"operator.dashboard.lost_card_button"` (`"كرت مفقود"`),
  `"operator.dashboard.no_shift_banner"` (`"افتح شيفتك أولاً"`),
  `"operator.entry.title"` (`"مسح كرت الدخول"`),
  `"operator.entry.scan_label"` (`"امسح الكرت"`),
  `"operator.entry.success_title"` (`"تم تسجيل الدخول"`),
  `"operator.exit.title"` (`"مسح كرت الخروج"`),
  `"operator.exit.scan_label"` (`"امسح الكرت للخروج"`),
  `"operator.exit.confirm_button"` (`"تأكيد الدفع وطباعة الإيصال"`),
  `"operator.lost_card.title"` (`"تذكرة مفقودة"`),
  `"operator.lost_card.warning"` (`"سيتم تطبيق غرامة الكرت المفقود"`),
  `"operator.shift.start_button"` (`"ابدأ الشيفت"`),
  `"operator.shift.end_button"` (`"أنهِ الشيفت"`),
  `"receipt.title"` (`"إيصال وقوف سيارات"`),
  `"receipt.lost_card_title"` (`"إيصال كرت مفقود"`),
  `"receipt.footer"` (`"شكراً لزيارتكم"`),
  `"errors.card_already_active"` (`"تم ادخال هذا الكارت بالفعل"`),
  `"errors.card_not_found"` (`"هذا الكارت غير مسجل في النظام"`),
  `"errors.card_not_available"` (`"الكرت ده متعطل — تواصل مع الإدارة"`),
  `"errors.no_active_session"` (`"مفيش جلسة مفتوحة لهذا الكرت"`),
  `"errors.no_active_shift"` (`"افتح شيفتك الأول قبل ما تبدأ"`),
  `"errors.no_pricing_rule"` (`"لا توجد تعريفة سعرية نشطة — تواصل مع الإدارة"`).

### 7c — Print CSS

- [x] **Task 7.6:** Create `static/print.css`. This file contains **only**
  `@media print` rules. Content:
```css
  @media print {
    @page {
      size: 58mm auto;
      margin: 2mm;
    }
    body {
      width: 58mm;
      font-family: 'Courier New', Courier, monospace;
      font-size: 10pt;
      direction: rtl;
      margin: 0;
      padding: 0;
    }
    .no-print {
      display: none !important;
    }
    .receipt-body {
      display: block !important;
    }
  }
```
  No non-print styles in this file. The `.no-print` class is applied to all
  non-receipt UI in templates.

### 7d — Scan JavaScript

- [x] **Task 7.7:** Create `static/js/scan.js`. This file contains exactly one
  IIFE (immediately invoked function expression) with the following logic:
  1. On `DOMContentLoaded`: find the element with id `"scan-input"` and call
     `.focus()`.
  2. Listen for `keydown` on `#scan-input`. On `Enter` (key `"Enter"` or
     `keyCode 13`): check if last submit was more than 100ms ago (debounce using
     a module-level `let lastSubmit = 0`). If so: update `lastSubmit =
     Date.now()`, call `document.getElementById("scan-form").requestSubmit()`.
  3. After any form submission result (page reload): on `DOMContentLoaded`,
     if `#scan-input` exists, call `.focus()` and set `.value = ""`.
  No external dependencies. Vanilla JS only. Total file size under 1KB.

### 7e — Dashboard Auto-Refresh & Clock JS

- [x] **Task 7.8:** Create `static/js/dashboard.js`. Contains two functions:
  1. `startClock()`: Updates the element with id `"live-clock"` every 1000ms
     with the current Cairo time. Cairo time = `new Date()` adjusted by
     `+2 * 60 * 60 * 1000` milliseconds (UTC+2). Formats as `HH:mm:ss` using
     Arabic-Indic digit substitution via a lookup object `{0:'٠',1:'١',...}`.
  2. `startSessionRefresh(url)`: calls `fetch(url)` every 60000ms and updates
     the element with id `"session-count"` with the `total` field from the JSON
     response. Silently ignores fetch errors (no alert, no redirect).
  Both are called at the bottom of the file without wrapping in DOMContentLoaded
  (scripts are placed at end of `<body>`). Total file under 2KB.

### 7f — Tailwind Rebuild

- [x] **Task 7.9:** Run `make css` (from Task 17.1 in Phase 1 tasks) to rebuild
  `static/css/tailwind.min.css` including any new classes used in Phase 2
  templates (to be added in Group 8). This task must be re-run after all Group 8
  template tasks are complete. Mark this task complete only after all Group 8
  tasks are done and the CSS build succeeds with zero purge warnings.

---

## Group 8 — Operator UI Routes & Jinja2 Templates

### 8a — UI Shift Routes

- [x] **Task 8.1:** Create `routes/ui_operator.py`. Define `router = APIRouter(
  prefix="/ui/operator", tags=["ui-operator"])`. Add `GET /shift/start`:
  - Auth: `Depends(require_operator)`.
  - Checks `ShiftService.get_active_shift(current_user.id)`. If shift is open,
    redirects to `/ui/operator/dashboard` with status `303`.
  - Returns `TemplateResponse("operator/shift_start.html", {"request": request,
    "user": current_user})`.

- [x] **Task 8.2:** In `routes/ui_operator.py`, add `POST /shift/start`:
  - Auth: `Depends(require_operator)`.
  - Form fields: `opening_cash_egp: int = Form(...)` (value in piastres; the
    form sends the value multiplied by 100 via a hidden field, or the template
    displays EGP and server converts: accept `opening_cash_egp_egp: int =
    Form(...)` in EGP and multiply by 100 server-side).
  - Calls `ShiftService.open_shift(...)`. On `ShiftAlreadyOpenError`: redirects
    to `/ui/operator/dashboard`.
  - On success: redirects to `/ui/operator/dashboard` with status `303`.

- [x] **Task 8.3:** In `routes/ui_operator.py`, add `GET /shift/end`:
  - Auth: `Depends(require_operator)`.
  - Calls `ShiftService.require_active_shift(current_user.id)`. On
    `NoActiveShiftError`: redirects to `/ui/operator/dashboard`.
  - Calls `ShiftService._compute_summary(shift, None)` for the live preview.
  - Returns `TemplateResponse("operator/shift_end.html", {"request": request,
    "user": current_user, "shift": shift, "summary": summary})`.

- [x] **Task 8.4:** In `routes/ui_operator.py`, add `POST /shift/end`:
  - Auth: `Depends(require_operator)`.
  - Form field: `closing_cash_egp: int = Form(...)` (EGP; server multiplies
    by 100).
  - Calls `ShiftService.close_shift(shift_id, current_user.id,
    closing_cash_piastres)`.
  - On success: redirects to `/ui/login` with status `303` (logout implied by
    spec; clears cookie as well by calling the logout logic inline).

### 8b — UI Dashboard Route

- [x] **Task 8.5:** In `routes/ui_operator.py`, add `GET /dashboard`:
  - Auth: `Depends(require_operator)`.
  - Calls `ShiftService.get_active_shift(current_user.id)` — `shift` may be
    `None`.
  - If `shift` is not `None`: calls `ParkingSessionRepository.get_by_shift(
    shift.id, page=1, size=10)` to get the last 10 sessions.
  - Calls `PricingRuleRepository.get_active()` — `active_rule` may be `None`.
  - Returns `TemplateResponse("operator/dashboard.html", {"request": request,
    "user": current_user, "shift": shift, "sessions": sessions,
    "session_total": total, "active_rule": active_rule})`.

### 8c — UI Entry Routes

- [x] **Task 8.6:** In `routes/ui_operator.py`, add `GET /entry`:
  - Auth: `Depends(require_operator)`.
  - Returns `TemplateResponse("operator/entry.html", {"request": request,
    "user": current_user, "error": None})`.

- [x] **Task 8.7:** In `routes/ui_operator.py`, add `POST /entry`:
  - Auth: `Depends(require_operator)`.
  - Form field: `card_code: str = Form(...)`, `plate_number: str = Form("")`.
  - Calls `SessionService.open_session(card_code, current_user.id,
    plate_number or None)`.
  - On success: redirects to `GET /ui/operator/entry/confirm/{session.id}` with
    status `303`.
  - On any service exception: re-renders `operator/entry.html` with
    `{"error": t("errors.<code>")}` where the translation key matches the
    exception type.

- [x] **Task 8.8:** In `routes/ui_operator.py`, add `GET /entry/confirm/
  {session_id}`:
  - Auth: `Depends(require_operator)`.
  - Fetches session via `ParkingSessionRepository.get_by_id`. Raises redirect
    to dashboard if not found.
  - Returns `TemplateResponse("operator/entry_confirm.html", {"request":
    request, "session": session})`.

### 8d — UI Exit Routes

- [x] **Task 8.9:** In `routes/ui_operator.py`, add `GET /exit`:
  - Auth: `Depends(require_operator)`.
  - Returns `TemplateResponse("operator/exit_scan.html", {"request": request,
    "user": current_user, "error": None})`.

- [x] **Task 8.10:** In `routes/ui_operator.py`, add `POST /exit/lookup`:
  - Auth: `Depends(require_operator)`.
  - Form field: `card_code: str = Form(...)`.
  - Calls `CardService.validate_for_exit(card_code, session_repo)` to get the
    active session.
  - Calls `PricingService.preview(session.entry_time)` using `utcnow()` as
    exit time (live estimate).
  - On success: returns `TemplateResponse("operator/exit_confirm.html",
    {"request": request, "session": session, "calc": calc, "rule": rule})`.
  - On any service exception: re-renders `operator/exit_scan.html` with error.

- [x] **Task 8.11:** In `routes/ui_operator.py`, add `POST /exit/{session_id}/
  confirm`:
  - Auth: `Depends(require_operator)`.
  - Calls `SessionService.close_session(session_id, current_user.id)`.
  - On success: redirects to `/ui/operator/receipt/{session_id}` with status
    `303`.
  - On `SessionNotActiveError`: redirects to `/ui/operator/exit` with a query
    param `error=SESSION_NOT_ACTIVE`.
  - On `NoPricingRuleError`: re-renders exit scan with error message.

### 8e — UI Lost Card Routes

- [x] **Task 8.12:** In `routes/ui_operator.py`, add `GET /lost-card`:
  - Auth: `Depends(require_operator)`.
  - Returns `TemplateResponse("operator/lost_card.html", {"request": request,
    "user": current_user, "error": None, "sessions": None})`.

- [x] **Task 8.13:** In `routes/ui_operator.py`, add `POST /lost-card`:
  - Auth: `Depends(require_operator)`.
  - Form fields: `plate_number: str = Form(...)`, `notes: str = Form("")`.
  - Calls `SessionService.find_active_by_plate(plate_number)`.
  - If empty list: re-renders `operator/lost_card.html` with
    `error=t("errors.no_active_session_for_plate")`.
  - If one result: redirects to `GET /ui/operator/lost-card/confirm/
    {session.id}` with status `303`.
  - If multiple results: re-renders `operator/lost_card.html` with
    `{"sessions": sessions}` for the operator to choose.

- [x] **Task 8.14:** In `routes/ui_operator.py`, add `GET /lost-card/confirm/
  {session_id}`:
  - Auth: `Depends(require_operator)`.
  - Fetches session. Fetches active pricing rule. Calls
    `PricingService.calculate_lost_card(session, rule, utcnow())` for preview.
  - Returns `TemplateResponse("operator/lost_card_confirm.html", {"request":
    request, "session": session, "calc": calc, "rule": rule})`.

- [x] **Task 8.15:** In `routes/ui_operator.py`, add `POST /lost-card/confirm/
  {session_id}`:
  - Auth: `Depends(require_operator)`.
  - Form field: `notes: str = Form("")`.
  - Calls `SessionService.resolve_lost_card(session_id, current_user.id,
    notes or None)`.
  - On success: redirects to `/ui/operator/receipt/{session_id}` with status
    `303`.

### 8f — UI Receipt Route

- [x] **Task 8.16:** In `routes/ui_operator.py`, add `GET /receipt/{session_id}`:
  - Auth: `Depends(require_operator)`.
  - Fetches session. If absent: redirect to dashboard.
  - Calls `SessionService.mark_receipt_printed(session_id)`.
  - Fetches operator name by `session.operator_id`. Fetches pricing rule by
    `session.pricing_rule_id`.
  - Builds `ReceiptData(...)` with all fields populated. Calls
    `format_duration(session.duration_minutes)` and `format_egp(
    session.amount_charged)` for display fields.
  - Returns `TemplateResponse("receipts/thermal.html", {"request": request,
    "receipt": receipt_data, "garage_name": settings.APP_NAME})`.

### 8g — Register UI Router

- [x] **Task 8.17:** In `main.py`, import `router` from `routes/ui_operator.py`
  as `ui_operator_router`. Add `app.include_router(ui_operator_router)`. No
  other changes.

### 8h — HTML Templates

- [x] **Task 8.18:** Create `templates/operator/dashboard.html` extending
  `templates/base.html`. Must include:
  - If `shift is None`: a full-width amber banner with text from
    `t("operator.dashboard.no_shift_banner")`. Entry and Exit buttons rendered
    with `disabled` attribute and 50% opacity.
  - If `shift is not None`: Entry and Exit buttons enabled. Each button:
    `min-height: 120px`, `width: calc(50% - 0.5rem)`, inline-flex, font-size
    `1.5rem`. Amber "كرت مفقود" button full-width `min-height: 60px` below.
  - Shift info bar: operator name, gate number, shift start time (via
    `format_datetime` filter), session count today.
  - Element `<span id="live-clock"></span>` for the JS clock.
  - Element `<span id="session-count">{{ session_total }}</span>`.
  - At bottom of `<body>` (inside `{% block scripts %}`): load
    `/static/js/dashboard.js` and call `startClock();
    startSessionRefresh('/api/v1/shifts/active');`.
  - Compact session table (last 10): card code, entry time, exit time or
    "داخل", amount (via `format_egp` filter).

- [x] **Task 8.19:** Create `templates/operator/entry.html` extending `base.html`.
  Must include:
  - Override `{% block nav %}` to show only a back link to dashboard (no full
    nav on scan screens).
  - A single centred card containing: Arabic heading from
    `t("operator.entry.scan_label")`, one `<input id="scan-input" type="text"
    inputmode="none" autocomplete="off" autocorrect="off" autocapitalize="off"
    spellcheck="false" autofocus name="card_code">` inside a `<form
    id="scan-form" method="POST" action="/ui/operator/entry">`.
  - Hidden CSRF token field (if CSRF middleware is added; use `{{ csrf_token }}`
    placeholder for now).
  - CSS pulse animation on `#scan-input` border using `@keyframes pulse` defined
    inline in a `<style>` tag in `{% block head %}`.
  - If `error` in context: full-width red error card above the input with the
    error message and a "حاول تاني" message.
  - Load `/static/js/scan.js` in `{% block scripts %}`.

- [x] **Task 8.20:** Create `templates/operator/entry_confirm.html` extending
  `base.html`. Must include:
  - Override `{% block nav %}` — empty.
  - A green success card (full screen height on mobile): inline SVG checkmark
    (simple `<svg>` path, no external file), card code in large monospace font,
    entry time via `format_datetime` filter.
  - `<script>setTimeout(() => { window.location.href='/ui/operator/dashboard';
    }, 3000);</script>` in `{% block scripts %}`.

- [x] **Task 8.21:** Create `templates/operator/exit_scan.html` extending
  `base.html`. Identical structure to `entry.html` with:
  - Heading from `t("operator.exit.scan_label")`.
  - Form action: `/ui/operator/exit/lookup`.
  - Error display identical to entry template.
  - Same scan JS loaded.

- [x] **Task 8.22:** Create `templates/operator/exit_confirm.html` extending
  `base.html`. Must include:
  - Card code in monospace.
  - Entry time and current exit time via `format_datetime`.
  - Duration via `format_duration` filter.
  - Pricing breakdown: grace period status, billable hours, rate per hour
    (via `format_egp`), base amount, penalty (if `calc.penalty_amount > 0`).
  - **Total amount in large bold font** via `format_egp` filter.
  - Active pricing rule label.
  - Confirm button: `min-height: 64px`, full-width, green background.
  - Cancel link to `/ui/operator/exit` (does NOT close the session).
  - Form action: `POST /ui/operator/exit/{{ session.id }}/confirm`.

- [x] **Task 8.23:** Create `templates/operator/lost_card.html` extending
  `base.html`. Must include:
  - Full-width amber warning banner with text from
    `t("operator.lost_card.warning")`.
  - A `<form method="POST" action="/ui/operator/lost-card">` with:
    - `plate_number` input: required, `dir="rtl"`, `inputmode="text"`,
      `min-height: 48px`, full-width.
    - `notes` textarea: optional, `rows="2"`, full-width.
    - Submit button: `min-height: 56px`, full-width, red background.
  - If `sessions` in context (multiple matches): a list below the form with one
    card per session showing card code, gate, entry time. Each card has a
    "اختر" link to `/ui/operator/lost-card/confirm/{{ s.id }}`.
  - If `error` in context: error block above the form.

- [x] **Task 8.24:** Create `templates/operator/lost_card_confirm.html` extending
  `base.html`. Must include:
  - Session details (card code, entry time, current duration estimate via
    `format_duration`).
  - Penalty breakdown: base amount, penalty amount, total.
  - Total in large bold.
  - Confirm form `POST /ui/operator/lost-card/confirm/{{ session.id }}` with
    hidden `notes` field.
  - Confirm button: red, full-width, `min-height: 64px`.
  - Cancel link to `/ui/operator/dashboard`.

- [x] **Task 8.25:** Create `templates/operator/shift_start.html` extending
  `base.html`. Must include:
  - One numeric input: `opening_cash_egp` labelled "الكاش الافتتاحي (بالجنيه)",
    `type="number"`, `min="0"`, `step="1"`, `min-height: 48px`, full-width.
    (`value * 100` conversion happens in the route handler.)
  - Submit button from `t("operator.shift.start_button")`: full-width,
    `min-height: 56px`, green.

- [x] **Task 8.26:** Create `templates/operator/shift_end.html` extending
  `base.html`. Must include:
  - Read-only summary card: total sessions, computed total (via `format_egp`),
    active (unresolved) sessions count.
  - One numeric input: `closing_cash_egp` labelled "الكاش الختامي (بالجنيه)".
  - Live discrepancy display: element `<span id="discrepancy-display">` updated
    by inline JS: `input.addEventListener('input', () => { const diff =
    parseInt(input.value || 0) * 100 - {{ summary.computed_total_piastres }};
    el.textContent = formatEgp(diff); })`. Positive diff = green, negative =
    red.
  - `formatEgp` JS helper defined inline (converts piastres int to display
    string with 2 decimal places — Latin numerals acceptable in JS).
  - Submit button from `t("operator.shift.end_button")`: full-width,
    `min-height: 56px`, amber.

- [x] **Task 8.27:** Create `templates/receipts/thermal.html`. This file does
  **NOT** extend `base.html`. It is a standalone HTML file. Structure:
```html
  <!DOCTYPE html>
  <html lang="ar" dir="rtl">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>إيصال</title>
    <link rel="stylesheet" href="/static/print.css">
    <style>
      body { width: 58mm; font-family: 'Courier New', monospace;
             font-size: 10pt; direction: rtl; margin: 0; padding: 4mm; }
      .sep { white-space: pre; }
      .lbl { font-size: 9pt; }
      .val { font-weight: bold; }
      .total-line { font-size: 13pt; font-weight: bold; }
    </style>
  </head>
  <body class="receipt-body">
    <!-- Content defined in Task 8.28 -->
  </body>
  </html>
```

- [x] **Task 8.28:** In `templates/receipts/thermal.html`, add the receipt body
  content inside `<body>`:
  1. Garage name `{{ receipt.garage_name }}` — centred, bold.
  2. Separator: `<p class="sep">--------------------------------</p>`
  3. Receipt type: `{{ t("receipt.lost_card_title") if receipt.is_lost_card else
     t("receipt.title") }}`.
  4. Session ID: `{{ receipt.session_id | string | zfill(8) }}` — use a Jinja2
     filter `zfill` registered in `create_jinja2_environment` as
     `lambda s, w: s.zfill(w)`.
  5. Card code, plate number (or `"غير مسجل"` if `None`), gate number,
     operator name.
  6. Separator.
  7. Entry time: `{{ receipt.entry_time | format_datetime }}`.
  8. Exit time: `{{ receipt.exit_time | format_datetime }}`.
  9. Duration: `{{ receipt.duration_minutes | format_duration }}`.
  10. Separator.
  11. Pricing rule label, rate per hour (`{{ receipt.rate_per_hour |
      format_egp }}`), grace period.
  12. If `receipt.is_grace_period`: single line "ضمن فترة السماح".
  13. Base amount: `{{ receipt.base_amount | format_egp }}`.
  14. If `receipt.penalty_amount > 0`: penalty line with
      `{{ receipt.penalty_amount | format_egp }}`.
  15. Separator.
  16. Total line with class `total-line`: `{{ receipt.total_amount |
      format_egp }}`.
  17. Payment method: "نقداً".
  18. Separator.
  19. Footer: `{{ t("receipt.footer") }}`.
  20. `<script>` block per FR-RCPT-008:
      `window.addEventListener('load', () => { window.print();
      setTimeout(() => { window.location.href='/ui/operator/dashboard'; },
      2000); });`
  - Non-print page also shows a `<div class="no-print">` preview of all fields
    and a "طباعة مرة أخرى" button calling `window.print()`.

---

## Group 9 — Unit Tests

### 9a — Pricing Helpers

- [x] **Task 9.1:** Create `tests/unit/test_pricing_helpers.py`. Write tests for
  `to_arabic_indic`:
  - `test_zero`: `to_arabic_indic(0)` → `"٠"`.
  - `test_single_digit`: `to_arabic_indic(5)` → `"٥"`.
  - `test_multi_digit`: `to_arabic_indic(2025)` → `"٢٠٢٥"`.

- [x] **Task 9.2:** In `tests/unit/test_pricing_helpers.py`, write tests for
  `format_egp`:
  - `test_zero_piastres`: `format_egp(0)` → `"٠٫٠٠ ج.م"`.
  - `test_round_egp`: `format_egp(100)` → `"١٫٠٠ ج.م"`.
  - `test_partial_egp`: `format_egp(2550)` → `"٢٥٫٥٠ ج.م"`.
  - `test_no_float_used`: inspects `format_egp` source to assert `"float"` is
    not a substring (use `inspect.getsource`).
  - `test_arabic_decimal_separator`: asserts `"٫"` (U+066B) appears in result.

- [x] **Task 9.3:** In `tests/unit/test_pricing_helpers.py`, write tests for
  `format_duration`:
  - `test_zero_minutes` → `"٠ دقائق"`.
  - `test_one_minute` → `"دقيقة واحدة"`.
  - `test_two_minutes` → `"دقيقتان"`.
  - `test_five_minutes` → `"٥ دقائق"`.
  - `test_fifteen_minutes` → `"١٥ دقيقة"`.
  - `test_sixty_minutes` → `"ساعة واحدة"`.
  - `test_ninety_minutes` → `"ساعة واحدة و٣٠ دقيقة"`.
  - `test_one_twenty_minutes` → `"ساعتان"`.
  - `test_one_twenty_five_minutes` → `"ساعتان و٥ دقائق"` or
    `"ساعتان و٥ دقيقة"` (verify actual Arabic grammar rule applied).
  - `test_two_hundred_minutes` → assert contains `"ساعات"` and `"٢٠"`.
  - `test_exact_three_hours` → assert contains `"ساعات"` and no `"دقيقة"`.

### 9b — PlateService

- [x] **Task 9.4:** Create `tests/unit/test_plate_service.py`. Instantiate
  `plate = PlateService()`. Write tests for `normalize`:
  - `test_strips_whitespace`: `normalize("  أ ب ج 123  ")` → `"أ ب ج 123"`.
  - `test_eastern_to_western_numerals`: `normalize("أ ب ج ١٢٣")` → `"أ ب ج 123"`.
  - `test_collapses_spaces`: `normalize("أ  ب   ج 1")` → `"أ ب ج 1"`.
  - `test_empty_string`: `normalize("")` → `""`.
  - `test_mixed_numerals`: `normalize("ن ي ش ١٥٩")` → `"ن ي ش 159"`.

- [x] **Task 9.5:** In `tests/unit/test_plate_service.py`, write tests for
  `validate`:
  - `test_valid_plate`: `validate("ن ي ش 159")` → `True`.
  - `test_one_letter`: `validate("أ 1")` → `True`.
  - `test_three_letters_four_digits`: `validate("أ ب ج 1234")` → `True`.
  - `test_no_space`: `validate("أبج123")` → `False`.
  - `test_latin_letters`: `validate("ABC 123")` → `False`.
  - `test_empty`: `validate("")` → `False`.

- [x] **Task 9.6:** In `tests/unit/test_plate_service.py`, write tests for
  `search_normalized`:
  - `test_removes_diacritics`: assert the result of `search_normalized("أَحْمَد")`
    does not contain any combining characters (check with `unicodedata.category`).
  - `test_normalizes_first`: assert `search_normalized("ن ي ش ١٥٩")` equals
    `search_normalized("ن ي ش 159")`.

### 9c — PricingService

- [x] **Task 9.7:** Create `tests/unit/test_pricing_service.py`. Import
  `PricingService`, `PriceCalculation`, and `PricingRule`. Create a helper
  `make_rule(**overrides)` that returns a mock `PricingRule` object (using
  `SimpleNamespace`) with defaults: `id=1`, `rate_per_hour=1000`,
  `minimum_charge=0`, `grace_period_mins=15`, `lost_card_penalty=2000`.
  Create a helper `make_session(entry_time)` returning a `SimpleNamespace` with
  `entry_time=entry_time`. Instantiate `service = PricingService(db=None)`.

- [x] **Task 9.8:** Write tests for `PricingService.calculate` (all synchronous):
  - `test_zero_duration`: entry and exit same time → `duration_minutes=0`,
    `is_grace_period=True`, `total_amount=minimum_charge`.
  - `test_within_grace_period`: 10 minutes → `is_grace_period=True`,
    `total=minimum_charge`.
  - `test_exactly_grace_period`: 15 minutes → `is_grace_period=True`.
  - `test_one_minute_over_grace`: 16 minutes → `is_grace_period=False`,
    `billable_minutes=1`, `billable_hours=1`,
    `base_amount=rate_per_hour`.
  - `test_ninety_minutes`: 90 min, grace=15 → `billable_minutes=75`,
    `billable_hours=ceil(75/60)=2`, `base_amount=2000`.
  - `test_minimum_charge_applied`: rate=100, min_charge=500, 1h above grace →
    `base_amount=500`.
  - `test_no_floats_in_result`: assert all fields of returned `PriceCalculation`
    that should be `int` are indeed `int` (use `dataclasses.fields`).

- [x] **Task 9.9:** Write tests for `PricingService.calculate_lost_card`:
  - `test_adds_penalty`: base = 1000, penalty = 2000 → `total_amount=3000`,
    `penalty_amount=2000`, `is_lost_card=True`.
  - `test_penalty_on_grace_period_session`: within grace + penalty →
    `total_amount = minimum_charge + lost_card_penalty`.
  - `test_zero_penalty`: `lost_card_penalty=0` →
    `total_amount == base_amount`, `penalty_amount=0`.

### 9d — CardService

- [x] **Task 9.10:** Create `tests/unit/test_card_service.py`. Write tests for
  `CardService.normalize_code` (instantiate with `db=None`):
  - `test_strips_whitespace`: `normalize_code("  CARD-001  ")` → `"CARD-001"`.
  - `test_uppercases`: `normalize_code("card-001")` → `"CARD-001"`.
  - `test_empty_raises`: `normalize_code("")` raises `InvalidBarcodeFormatError`.
  - `test_invalid_chars_raises`: `normalize_code("CARD@001")` raises
    `InvalidBarcodeFormatError`.
  - `test_arabic_raises`: `normalize_code("كرت-001")` raises
    `InvalidBarcodeFormatError`.
  - `test_too_long_raises`: `normalize_code("A" * 51)` raises
    `InvalidBarcodeFormatError`.
  - `test_valid_with_underscore`: `normalize_code("CARD_001")` → `"CARD_001"`.
  - `test_valid_with_dash`: `normalize_code("CARD-0042")` → `"CARD-0042"`.

### 9e — ShiftService

- [x] **Task 9.11:** Create `tests/unit/test_shift_service.py`. Use the
  `db_session` and `audit_service` fixtures from `tests/conftest.py`. Write test
  `test_open_shift_success` (async): creates an operator user, calls
  `ShiftService.open_shift(operator_id, gate_number=1, opening_cash_egp=50000)`.
  Asserts returned shift has `ended_at=None` and `gate_number=1`.

- [x] **Task 9.12:** Write test `test_open_shift_already_open` (async): opens a
  shift, then calls `open_shift` again for the same operator. Asserts
  `ShiftAlreadyOpenError` is raised.

- [x] **Task 9.13:** Write test `test_require_active_shift_no_shift` (async):
  calls `require_active_shift` for an operator with no open shift. Asserts
  `NoActiveShiftError` is raised.

- [x] **Task 9.14:** Write test `test_close_shift_success` (async): opens a shift,
  closes it with `closing_cash_egp=60000`. Asserts `ShiftSummary` returned has
  `ended_at` not `None` and `closing_cash_piastres=60000`.

- [x] **Task 9.15:** Write test `test_close_shift_not_owned` (async): creates two
  operators, opens a shift for operator 1, tries to close with operator 2's ID.
  Asserts `ShiftNotOwnedError`.

- [x] **Task 9.16:** Write test `test_compute_summary_counts` (async): opens shift,
  creates 2 COMPLETED and 1 ACTIVE session records directly in the DB, calls
  `_compute_summary`. Asserts `completed_sessions=2`, `active_sessions=1`.

### 9f — SessionService

- [x] **Task 9.17:** Create `tests/unit/test_session_service.py`. Use all fixtures.
  Write `test_open_session_success` (async): seeds a card (`AVAILABLE`), operator,
  and open shift. Calls `SessionService.open_session("CARD-0001", operator_id)`.
  Asserts returned session has `status=ACTIVE` and `card.status=IN_USE` in DB.

- [x] **Task 9.18:** Write `test_open_session_no_shift` (async): no open shift.
  Asserts `NoActiveShiftError`.

- [x] **Task 9.19:** Write `test_open_session_card_already_active` (async): card
  already has an ACTIVE session. Asserts `CardAlreadyActiveError`. Asserts no
  new session is created.

- [x] **Task 9.20:** Write `test_open_session_card_not_found` (async): scans
  unknown code. Asserts `CardNotFoundError`. Asserts no session row in DB.

- [x] **Task 9.21:** Write `test_open_session_atomicity` (async): patches
  `CardService.set_status` to raise an exception. Calls `open_session`. Asserts
  no `ParkingSession` row was committed to the DB (rollback verification).

- [x] **Task 9.22:** Write `test_close_session_success` (async): seeds ACTIVE
  session and active pricing rule. Calls `close_session(session_id,
  exit_operator_id)`. Asserts session `status=COMPLETED`, `is_paid=True`,
  `amount_charged` is an integer, card `status=AVAILABLE`.

- [x] **Task 9.23:** Write `test_close_session_not_active` (async): session is
  `COMPLETED`. Asserts `SessionNotActiveError`.

- [x] **Task 9.24:** Write `test_close_session_no_pricing_rule` (async): no active
  pricing rule. Asserts `NoPricingRuleError`. Asserts session remains `ACTIVE`.

- [x] **Task 9.25:** Write `test_resolve_lost_card_success` (async): seeds ACTIVE
  session, active rule with `lost_card_penalty=2000`. Calls
  `resolve_lost_card(session_id, operator_id)`. Asserts `status=LOST_CARD`,
  `is_lost_card=True`, `lost_card_penalty_applied=2000`, card `status=LOST`.

- [x] **Task 9.26:** Write `test_mark_receipt_printed_idempotent` (async): calls
  `mark_receipt_printed(id)` twice. Asserts `receipt_printed_at` in DB is the
  same timestamp after both calls (second call does not update).

- [x] **Task 9.27:** Write `test_find_active_by_plate_normalizes` (async): seeds
  session with `plate_number="ن ي ش 159"`. Calls
  `find_active_by_plate("ن ي ش ١٥٩")` (Eastern numerals). Asserts the session
  is returned (normalization happens before lookup).

---

## Group 10 — Integration Tests & End-to-End Verification

### 10a — Card API Integration Tests

- [ ] **Task 10.1:** Create `tests/integration/test_card_routes.py`. Write
  `test_create_card_as_admin` (async): POST to `/api/v1/cards/` with
  `{"card_code": "CARD-TEST-001"}`. Asserts status `201` and response contains
  `data.card_code == "CARD-TEST-001"`.

- [ ] **Task 10.2:** Write `test_create_card_duplicate` (async): creates card,
  tries to create again with same code. Asserts `409` and `code ==
  "CARD_CODE_ALREADY_EXISTS"`.

- [ ] **Task 10.3:** Write `test_create_card_invalid_barcode` (async): sends
  `card_code = "كرت-001"`. Asserts `422` and `code == "INVALID_BARCODE_FORMAT"`.

- [ ] **Task 10.4:** Write `test_bulk_create_cards` (async): POST `/api/v1/cards/
  bulk` with 5 unique codes. Asserts `201` and `created == 5`.

- [ ] **Task 10.5:** Write `test_bulk_create_conflict` (async): pre-creates one
  card, includes that code in bulk request. Asserts `409` and `code ==
  "BULK_CARD_CONFLICT"`.

- [ ] **Task 10.6:** Write `test_get_card_by_code` (async): creates card, GETs
  `/api/v1/cards/CARD-TEST-001`. Asserts `200` and `data.status == "available"`.

- [ ] **Task 10.7:** Write `test_get_card_normalizes_code` (async): creates card
  `"CARD-001"`, GETs `/api/v1/cards/card-001` (lowercase). Asserts `200`
  (normalization in route).

- [ ] **Task 10.8:** Write `test_update_card_status` (async): creates card, PATCHes
  status to `"damaged"`. Asserts `200` and `data.status == "damaged"`.

### 10b — Session API Integration Tests

- [ ] **Task 10.9:** Create `tests/integration/test_session_routes.py`. Write
  `test_open_session_happy_path` (async): seeds card, operator with open shift,
  active pricing rule. POST `/api/v1/sessions/` with
  `{"card_code": "CARD-0001"}`. Asserts `201`, `data.status == "ACTIVE"`.

- [ ] **Task 10.10:** Write `test_open_session_no_shift` (async): operator has no
  open shift. Asserts `403` and `code == "NO_ACTIVE_SHIFT"`.

- [ ] **Task 10.11:** Write `test_open_session_card_already_active` (async): card
  has open session. Asserts `409` and `code == "CARD_ALREADY_ACTIVE"`.

- [ ] **Task 10.12:** Write `test_open_session_card_not_found` (async). Asserts
  `404` and `code == "CARD_NOT_FOUND"`.

- [ ] **Task 10.13:** Write `test_exit_session_happy_path` (async): seeds ACTIVE
  session and active pricing rule. PATCH `/api/v1/sessions/{id}/exit`. Asserts
  `200`, `data.status == "COMPLETED"`, `data.amount_charged` is an integer ≥ 0,
  `data.is_paid == True`.

- [ ] **Task 10.14:** Write `test_exit_session_grace_period` (async): seeds session
  with `entry_time = utcnow() - timedelta(minutes=5)`, grace = 15 min. PATCHes
  exit. Asserts `price_breakdown.is_grace_period == True` and
  `data.amount_charged == minimum_charge`.

- [ ] **Task 10.15:** Write `test_exit_session_not_active` (async): session already
  `COMPLETED`. Asserts `409` and `code == "SESSION_NOT_ACTIVE"`.

- [ ] **Task 10.16:** Write `test_exit_no_pricing_rule` (async): no active rule.
  Asserts `503` and `code == "NO_ACTIVE_PRICING_RULE"`.

- [ ] **Task 10.17:** Write `test_lost_card_happy_path` (async): seeds ACTIVE
  session, rule with `lost_card_penalty=2000`. PATCH `/api/v1/sessions/{id}/
  lost-card` with `{"plate_number": "أ ب ج 123", "notes": "test"}`. Asserts
  `200`, `data.status == "LOST_CARD"`, `data.is_lost_card == True`,
  `data.lost_card_penalty_applied == 2000`.

- [ ] **Task 10.18:** Write `test_amount_not_accepted_from_client` (async): sends
  `{"card_code": "CARD-0001", "amount_charged": 99999}` on session open. Asserts
  `201` and the DB record's `amount_charged` is `NULL` (not `99999`). Verifies
  the API ignores client-supplied monetary fields.

### 10c — Shift API Integration Tests

- [ ] **Task 10.19:** Create `tests/integration/test_shift_routes.py`. Write
  `test_open_shift` (async): POST `/api/v1/shifts/` as operator with
  `{"opening_cash_egp": 50000}`. Asserts `201` and `data.ended_at == None`.

- [ ] **Task 10.20:** Write `test_open_shift_already_open` (async): opens shift,
  tries again. Asserts `409` and `code == "SHIFT_ALREADY_OPEN"`.

- [ ] **Task 10.21:** Write `test_close_shift_with_summary` (async): opens shift,
  creates 2 completed sessions via the API, closes shift with
  `closing_cash_egp=100000`. Asserts `200` and `data.completed_sessions == 2`
  and `data.discrepancy_piastres` is an integer.

- [ ] **Task 10.22:** Write `test_close_shift_not_owned` (async): operator A opens
  shift; operator B tries to close it. Asserts `403` and `code ==
  "SHIFT_NOT_OWNED"`.

- [ ] **Task 10.23:** Write `test_shift_sessions_list` (async): opens shift, opens
  3 sessions. GET `/api/v1/shifts/{id}/sessions`. Asserts `total == 3`.

### 10d — Rates API Integration Tests

- [ ] **Task 10.24:** Create `tests/integration/test_rate_routes.py`. Write
  `test_get_active_rule` (async): seeds active rule. GET `/api/v1/rates/active`.
  Asserts `200` and `data.is_active == True`.

- [ ] **Task 10.25:** Write `test_get_active_rule_none` (async): no active rule.
  Asserts `503` and `code == "NO_ACTIVE_PRICING_RULE"`.

- [ ] **Task 10.26:** Write `test_preview_price` (async): seeds active rule. GET
  `/api/v1/rates/preview?entry_time=<ISO_datetime_60_min_ago>`. Asserts `200`
  and `data.duration_minutes >= 60`.

### 10e — Full Flow Integration Tests

- [ ] **Task 10.27:** Create `tests/integration/test_full_flow.py`. Write
  `test_complete_entry_to_exit_flow` (async):
  1. Create operator, open shift.
  2. Create card `CARD-FLOW-001` (available).
  3. POST session open → assert `ACTIVE`, card `IN_USE`.
  4. PATCH session exit → assert `COMPLETED`, card `AVAILABLE`,
     `amount_charged >= 0`, `duration_minutes >= 0`.
  5. GET receipt data → assert all required receipt fields present and non-null
     (except `plate_number`).

- [ ] **Task 10.28:** Write `test_complete_lost_card_flow` (async):
  1. Open shift, create card, open session.
  2. PATCH lost-card → assert `LOST_CARD`, card `LOST`,
     `lost_card_penalty_applied == rule.lost_card_penalty`.
  3. GET receipt data → assert `is_lost_card == True` and
     `penalty_amount == rule.lost_card_penalty`.

- [ ] **Task 10.29:** Write `test_race_condition_double_exit` (async): opens one
  session. Fires two concurrent PATCH exit requests using `asyncio.gather`.
  Asserts exactly one returns `200` (COMPLETED) and the other returns `409`
  (SESSION_NOT_ACTIVE). Asserts only one `COMPLETED` session exists in the DB.

- [ ] **Task 10.30:** Write `test_race_condition_double_entry_same_card` (async):
  fires two concurrent POST session-open requests for the same card using
  `asyncio.gather`. Asserts exactly one returns `201` and the other returns
  `409` (`CARD_ALREADY_ACTIVE`). Asserts only one `ACTIVE` session in DB.

### 10f — UI Integration Tests

- [ ] **Task 10.31:** Create `tests/integration/test_ui_operator_routes.py`. Write
  `test_dashboard_renders` (async): log in as operator, GET
  `/ui/operator/dashboard`. Asserts `200`, content-type `text/html`, Arabic
  text `"دخول"` in body.

- [ ] **Task 10.32:** Write `test_dashboard_no_shift_shows_banner` (async): operator
  has no shift. GET dashboard. Asserts `"افتح شيفتك أولاً"` in body.

- [ ] **Task 10.33:** Write `test_entry_page_renders` (async): GET
  `/ui/operator/entry`. Asserts `200` and `"scan-input"` in body.

- [ ] **Task 10.34:** Write `test_entry_post_success_redirects` (async): seeds card
  and open shift. POST `/ui/operator/entry` with `card_code=CARD-0001`. Asserts
  `303` redirect to `/ui/operator/entry/confirm/`.

- [ ] **Task 10.35:** Write `test_entry_post_card_not_found_rerenders` (async):
  POST entry with unknown `card_code`. Asserts `200` (re-render) and Arabic
  error message in body.

- [ ] **Task 10.36:** Write `test_exit_scan_page_renders` (async): GET
  `/ui/operator/exit`. Asserts `200` and `"scan-form"` in body.

- [ ] **Task 10.37:** Write `test_exit_lookup_success` (async): seeds ACTIVE session.
  POST `/ui/operator/exit/lookup` with `card_code`. Asserts `200` and Arabic
  text `"تأكيد الدفع"` in body.

- [ ] **Task 10.38:** Write `test_receipt_page_triggers_print` (async): seeds
  COMPLETED session. GET `/ui/operator/receipt/{id}`. Asserts `200` and
  `"window.print()"` in body.

- [ ] **Task 10.39:** Write `test_receipt_sets_printed_at` (async): GET receipt
  page. Query DB for session. Asserts `receipt_printed_at` is not `None`.

- [ ] **Task 10.40:** Write `test_receipt_idempotent_printed_at` (async): GET
  receipt page twice. Asserts `receipt_printed_at` timestamp is the same both
  times (first value not overwritten).

### 10g — Coverage & Quality Gate

- [ ] **Task 10.41:** Run `pytest --cov=services --cov-report=term-missing`. Confirm:
  - `services/pricing_helpers.py`: 100% coverage.
  - `services/plate_service.py`: 100% coverage.
  - `services/pricing_service.py`: 100% coverage.
  - `services/card_service.py`: 100% coverage.
  - `services/shift_service.py`: 100% coverage.
  - `services/session_service.py`: 100% coverage.
  Fix any gaps before marking complete. Do not mark complete with any uncovered
  lines in the above files.

- [ ] **Task 10.42:** Run `black . && ruff check . && mypy .` on the entire project.
  Fix all formatting errors, lint warnings, and type errors. Zero issues must
  remain. Do not mark complete with any tool reporting warnings or errors.

- [ ] **Task 10.43:** Run `make css` to rebuild Tailwind with all new template
  classes included. Verify the built `static/css/tailwind.min.css` is under
  150KB. Update `Makefile` if the build command changed. Commit the rebuilt CSS.

- [ ] **Task 10.44:** Perform manual QA on a physical Sunmi V2 device using the
  checklist from `spec_phase2.md` Section 6.3. Complete every checkbox on the
  manual QA checklist. Record the QA result in `QA_LOG.md` with: date, tester
  name, device firmware version, and pass/fail per checklist item.
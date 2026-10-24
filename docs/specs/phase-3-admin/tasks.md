# Phase 3 — Atomic Coding Task Checklist

> **Version:** 1.0
> **Scope:** All coding tasks required to complete Phase 3 as specified in
> `docs/specs/phase-3-admin/spec.md`.
> **Execution order is mandatory within each group.** Complete all tasks in a
> group before starting the next group.
> **Each task is atomic:** one file, one class, one method, or one migration
> block per task.
> **All code must pass:** `black`, `ruff`, and `mypy --strict` before any task
> is marked complete.

---

## Group 1 — Models, Migrations & Indexes

### 1a — Model Updates

- [x] **Task 1.1:** Open `models/shift.py`. Add one column to the `Shift` class
  if not already present:
  - `admin_override_note: Mapped[str | None]` — `TEXT`, nullable.
  Verify all other columns from `plan.md` Section 2.2 still exist. Update
  `__all__`. Do not change any other model file in this task.

- [x] **Task 1.2:** Open `models/__init__.py`. Verify that `Shift` is exported.
  No new imports needed — this task is a verification step only. If `Shift` is
  missing from `__all__`, add it. Commit no logic changes.

### 1b — Alembic Migration

- [x] **Task 1.3:** Generate a new Alembic migration by running:
  `alembic revision --autogenerate -m "phase3_shift_admin_override_note"`.
  Open the generated file. Verify `upgrade()` adds the
  `admin_override_note TEXT NULL` column to the `shifts` table. Verify
  `downgrade()` drops the column. Do not edit logic — only verify and commit.

- [x] **Task 1.4:** Generate a second Alembic migration manually (not autogenerate)
  with message `"phase3_performance_indexes"`. In `upgrade()`, add the following
  indexes using `op.create_index` — skip any that already exist by checking
  `op.get_bind().dialect.has_table` or using `if_not_exists=True` where
  supported:
  - `ix_parking_sessions_exit_time` on `parking_sessions(exit_time)`.
  - `ix_parking_sessions_entry_time` on `parking_sessions(entry_time)`.
  - `ix_parking_sessions_status` on `parking_sessions(status)` — verify this
    does not duplicate the index created in Phase 2.
  - `ix_shifts_started_at` on `shifts(started_at)`.
  - `ix_shifts_ended_at` on `shifts(ended_at)`.
  In `downgrade()`, drop all five indexes. Commit the migration file.

- [x] **Task 1.5:** Run `alembic upgrade head` against the local SQLite dev
  database. Confirm all columns and indexes exist. Fix any migration errors.
  Delete any `test_verify.db` artifact. Commit no source changes in this task.

---

## Group 2 — Utility Modules

### 2a — Cairo Time Utilities

- [x] **Task 2.1:** Create `utils/time.py`. Define the following pure functions
  using only Python stdlib (`datetime`, `timedelta`). No external timezone
  libraries. All functions are synchronous:

```python
  def cairo_now() -> datetime:
```
  Returns `datetime.utcnow() + timedelta(hours=2)`. Represents current Cairo
  local time as a naive datetime.

```python
  def cairo_today_start() -> datetime:
```
  Returns the UTC datetime corresponding to midnight Cairo time today.
  Algorithm: `cairo_now().replace(hour=0, minute=0, second=0, microsecond=0)
  - timedelta(hours=2)`.

```python
  def cairo_date_to_utc_start(d: date) -> datetime:
```
  Converts a `datetime.date` to the UTC datetime of Cairo midnight on that
  date. Algorithm: `datetime(d.year, d.month, d.day, 0, 0, 0) -
  timedelta(hours=2)`.

```python
  def cairo_date_to_utc_end(d: date) -> datetime:
```
  Returns the UTC datetime of Cairo midnight at the end of that date (start of
  next day). Algorithm: `cairo_date_to_utc_start(d) + timedelta(days=1)`.

```python
  def utc_to_cairo(dt: datetime) -> datetime:
```
  Adds 2 hours to a UTC datetime. Returns Cairo local time as a naive datetime.

```python
  def cairo_date_str(dt: datetime) -> str:
```
  Converts a UTC datetime to a Cairo local date string `"YYYY-MM-DD"`. Calls
  `utc_to_cairo(dt).strftime("%Y-%m-%d")`.

  Add `__all__` listing all six functions.

- [x] **Task 2.2:** Create `tests/unit/test_time_utils.py`. Write the following
  tests using `freezegun.freeze_time`:

  - `test_cairo_now_is_utc_plus_2`: freezes UTC at `2024-08-15 22:00:00`.
    Asserts `cairo_now()` equals `2024-08-16 00:00:00`.
  - `test_cairo_today_start_returns_utc`: freezes Cairo time at midnight (UTC
    `22:00` previous day). Asserts `cairo_today_start()` returns the correct
    UTC boundary.
  - `test_cairo_date_to_utc_start`: `date(2024, 8, 15)` →
    `datetime(2024, 8, 14, 22, 0, 0)`.
  - `test_cairo_date_to_utc_end`: `date(2024, 8, 15)` →
    `datetime(2024, 8, 15, 22, 0, 0)`.
  - `test_cairo_date_str`: UTC `datetime(2024, 8, 15, 23, 30)` → `"2024-08-16"`
    (Cairo is already next day).
  - `test_utc_to_cairo_adds_two_hours`: UTC `10:00` → Cairo `12:00`.

### 2b — CSV Export Utilities

- [x] **Task 2.3:** Create `utils/csv_export.py`. Add the following at the top
  of the file:
  - Import `csv`, `io`, `codecs`, `asyncio` from stdlib.
  - Define a module-level constant `CSV_BOM = "\ufeff"` (UTF-8 BOM).
  - Define a pure helper:
```python
    def _piastres_to_egp_str(piastres: int | None) -> str:
```
    If `None`: returns `""`. Else: returns `f"{piastres / 100:.2f}"` (Latin
    digits, dot separator). Uses float division for display only — the stored
    value is always integer. Add `# display only — not stored` comment.

- [x] **Task 2.4:** In `utils/csv_export.py`, define an async generator:
```python
  async def generate_sessions_csv(
      sessions_iter: AsyncIterator[ParkingSession],
      operator_names: dict[int, str],
  ) -> AsyncIterator[str]
```
  Yields strings (not bytes — `StreamingResponse` handles encoding). Algorithm:
  1. Yield `CSV_BOM`.
  2. Yield a header row using `csv.writer` writing to a `io.StringIO` buffer.
     Headers (in order): `"رقم الجلسة"`, `"رمز الكرت"`, `"رقم اللوحة"`,
     `"البوابة"`, `"العامل"`, `"وقت الدخول"`, `"وقت الخروج"`,
     `"المدة (دقيقة)"`, `"الحالة"`, `"المبلغ (جنيه)"`, `"كرت مفقود"`,
     `"طريقة الدفع"`.
  3. Async-iterate `sessions_iter`. For each session, yield one CSV row string.
     Use `operator_names.get(session.operator_id, "")` for the operator column.
     Use `cairo_date_str_full(dt)` (format `"YYYY-MM-DD HH:mm"`) for datetimes.
     Booleans: `"نعم"` / `"لا"`. `None` values: `""`.
  4. Between every 100 rows, yield `await asyncio.sleep(0)` to yield control
     to the event loop (prevents blocking). This is a no-op string — insert it
     via `asyncio.sleep(0)` and continue (do not yield the coroutine result as
     a string row).

  Add a private helper inside the file:
```python
  def _row_to_str(row: list) -> str:
```
  Writes a single CSV row to a `StringIO` buffer and returns the string
  (including the line terminator).

- [x] **Task 2.5:** In `utils/csv_export.py`, define a second async generator:
```python
  async def generate_shifts_csv(
      shifts_iter: AsyncIterator[Shift],
      operator_names: dict[int, str],
      session_totals: dict[int, int],
  ) -> AsyncIterator[str]
```
  Same pattern as Task 2.4. Headers: `"رقم الشيفت"`, `"العامل"`, `"البوابة"`,
  `"بداية الشيفت"`, `"نهاية الشيفت"`, `"عدد الجلسات"`,
  `"الإجمالي المحسوب (جنيه)"`, `"الكاش الختامي (جنيه)"`,
  `"الفرق (جنيه)"`.
  `session_totals` is a `dict[shift_id, total_piastres]` pre-fetched by the
  caller. Discrepancy = `closing_cash_egp - computed_total` if both non-None,
  else `""`. Add `__all__ = ["generate_sessions_csv", "generate_shifts_csv"]`
  at the bottom of the file.

- [x] **Task 2.6:** Update `utils/__init__.py` to import and re-export all
  public names from `utils/time.py` and `utils/csv_export.py`. Rebuild `__all__`.

---
## Group 3 — Pydantic Schemas

- [x] **Task 3.1:** Create `schemas/admin_reports.py`. Define the following
  Pydantic models. All use `model_config = ConfigDict(from_attributes=False)`
  unless noted. No SQLAlchemy imports:

```python
  class LiveStatsResponse(BaseModel):
      active_sessions: int
      total_capacity: int
      occupancy_pct: int
      revenue_today_piastres: int
      open_shifts: int
```

```python
  class GateStatusResponse(BaseModel):
      gate_number: int
      operator_name: str | None
      operator_id: int | None
      shift_start: datetime | None
      active_sessions: int
```

- [x] **Task 3.2:** In `schemas/admin_reports.py`, add:

```python
  class RevenueSummaryResponse(BaseModel):
      total_sessions: int
      total_revenue_piastres: int
      avg_duration_minutes: int
      avg_revenue_piastres: int
```

```python
  class GateRevenueResponse(BaseModel):
      gate_number: int
      session_count: int
      total_piastres: int
```

```python
  class OperatorRevenueResponse(BaseModel):
      operator_id: int
      operator_name: str
      session_count: int
      total_piastres: int
```

```python
  class DailyRevenueResponse(BaseModel):
      date_str: str  # "YYYY-MM-DD" Cairo local
      session_count: int
      total_piastres: int
```

- [x] **Task 3.3:** In `schemas/admin_reports.py`, add:

```python
  class ReportFilters(BaseModel):
      start_date: date | None = None
      end_date: date | None = None
      gate_number: int | None = Field(None, ge=1, le=5)
      operator_id: int | None = None
      status: SessionStatus | None = None
      card_code: str | None = Field(None, max_length=50)
      plate_number: str | None = Field(None, max_length=30)
      long_stay: bool = False

      @model_validator(mode="after")
      def validate_date_range(self) -> "ReportFilters":
          if self.start_date and self.end_date:
              if self.start_date > self.end_date:
                  raise ValueError("start_date must be <= end_date")
          return self
```

  Import `SessionStatus` from `models`. Import `date` from `datetime`.

- [x] **Task 3.4:** In `schemas/admin_reports.py`, add:

```python
  class ShiftFilters(BaseModel):
      operator_id: int | None = None
      gate_number: int | None = Field(None, ge=1, le=5)
      status: Literal["open", "closed"] | None = None
      start_date: date | None = None
      end_date: date | None = None
      overdue: bool = False

      @model_validator(mode="after")
      def validate_date_range(self) -> "ShiftFilters":
          if self.start_date and self.end_date:
              if self.start_date > self.end_date:
                  raise ValueError("start_date must be <= end_date")
          return self
```

```python
  class ForceCloseShiftRequest(BaseModel):
      closing_cash_egp: int | None = Field(None, ge=0)
      admin_note: str | None = Field(None, max_length=500)
```

- [x] **Task 3.5:** In `schemas/admin_reports.py`, add:

```python
  class AdminSessionDetail(BaseModel):
      model_config = ConfigDict(from_attributes=True)
      # All fields from SessionResponse (import and re-use)
      id: int
      card_id: int
      card_code: str
      status: SessionStatus
      gate_number: int
      shift_id: int
      operator_id: int
      entry_time: datetime
      exit_time: datetime | None
      plate_number: str | None
      duration_minutes: int | None
      pricing_rule_id: int | None
      amount_charged: int | None
      is_lost_card: bool
      lost_card_penalty_applied: int | None
      payment_method: PaymentMethod
      is_paid: bool
      exit_operator_id: int | None
      exit_shift_id: int | None
      receipt_printed_at: datetime | None
      admin_override_by: int | None
      admin_override_note: str | None
      notes: str | None
      created_at: datetime
      audit_logs: list[AuditLogResponse] = []
```

  Import `AuditLogResponse` from `schemas.audit_log`, `PaymentMethod` from
  `models`.

- [x] **Task 3.6:** In `schemas/admin_reports.py`, add `ServiceTypeRevenueResponse`:
```python
  class ServiceTypeRevenueResponse(BaseModel):
      model_config = ConfigDict(from_attributes=False)

      service_type: str
      label: str
      session_count: int
      total_piastres: int
      percentage: float = 0.0
```

- [x] **Task 3.7:** In `schemas/parking_session.py`, add `SessionAdminOverrideCloseRequest`:
```python
  class SessionAdminOverrideCloseRequest(BaseModel):
      model_config = ConfigDict(from_attributes=True)
      amount_charged_egp: float = Field(0.0, ge=0)
      override_note: str | None = None
```

- [x] **Task 3.8:** In `schemas/admin_reports.py` and `schemas/parking_session.py`, verify `__all__` lists all schemas. Update `schemas/__init__.py` to import and re-export all names from `schemas/admin_reports.py` and `schemas/parking_session.py`. Rebuild `schemas/__init__.py` `__all__`.

---

## Group 4 — Repositories

### 4a — Report Repository

- [x] **Task 4.1:** Create `repositories/report_repo.py`. Define a
  `ReportRepository` class with `__init__(self, db: AsyncSession)`. Add method:
```python
  async def count_active_sessions(self) -> int
```
  Executes: `SELECT COUNT(*) FROM parking_sessions WHERE status = 'ACTIVE'`.
  Returns integer. Uses `scalar_one_or_none()` with fallback to `0`.

- [x] **Task 4.2:** In `repositories/report_repo.py`, add method:
```python
  async def count_total_card_capacity(self) -> int
```
  Executes: `SELECT COUNT(*) FROM parking_cards WHERE status != 'damaged'`.
  Returns integer with fallback to `0`.

- [x] **Task 4.3:** In `repositories/report_repo.py`, add method:
```python
  async def sum_revenue_today(
      self, start_utc: datetime, end_utc: datetime
  ) -> int
```
  Executes:
```sql
  SELECT COALESCE(SUM(amount_charged), 0)
  FROM parking_sessions
  WHERE status IN ('COMPLETED', 'LOST_CARD')
    AND exit_time >= :start_utc
    AND exit_time < :end_utc
```
  Returns integer piastres.

- [x] **Task 4.4:** In `repositories/report_repo.py`, add method:
```python
  async def count_open_shifts(self) -> int
```
  Executes: `SELECT COUNT(*) FROM shifts WHERE ended_at IS NULL`.
  Returns integer.

- [x] **Task 4.5:** In `repositories/report_repo.py`, add method:
```python
  async def get_gate_panel(self) -> list[dict]
```
  Executes a single JOIN query:
```sql
  SELECT
      s.gate_number,
      u.full_name AS operator_name,
      u.id AS operator_id,
      s.started_at AS shift_start,
      COUNT(ps.id) FILTER (WHERE ps.status = 'ACTIVE') AS active_sessions
FROM shifts s
  JOIN users u ON s.operator_id = u.id
  LEFT JOIN parking_sessions ps ON ps.shift_id = s.id
  WHERE s.ended_at IS NULL
  GROUP BY s.gate_number, u.full_name, u.id, s.started_at
  ORDER BY s.gate_number
```
  Returns a list of dicts with keys: `gate_number`, `operator_name`,
  `operator_id`, `shift_start`, `active_sessions`. Uses `db.execute` with
  `text()`. For gates with no open shift, they will be absent from the result;
  the service layer fills in the missing gates.

  **SQLite compatibility note:** SQLite does not support `FILTER (WHERE ...)`.
  Use a `CASE WHEN` expression instead:
  `SUM(CASE WHEN ps.status = 'ACTIVE' THEN 1 ELSE 0 END)`.
  Detect dialect via `db.bind.dialect.name` and use the appropriate expression.

- [x] **Task 4.6:** In `repositories/report_repo.py`, add method:
```python
  async def count_long_stay_sessions(
      self, threshold_utc: datetime
  ) -> int
```
  Executes:
```sql
  SELECT COUNT(*) FROM parking_sessions
  WHERE status = 'ACTIVE' AND entry_time < :threshold_utc
```
  Returns integer.

- [x] **Task 4.7:** In `repositories/report_repo.py`, add method:
```python
  async def count_overdue_shifts(self, threshold_utc: datetime) -> int
```
  Executes:
```sql
  SELECT COUNT(*) FROM shifts
  WHERE ended_at IS NULL AND started_at < :threshold_utc
```
  Returns integer.

- [x] **Task 4.8:** In `repositories/report_repo.py`, add method:
```python
  async def get_revenue_summary(
      self,
      start_utc: datetime | None,
      end_utc: datetime | None,
      gate_number: int | None,
      operator_id: int | None,
  ) -> dict
```
  Builds a SELECT with `COALESCE(SUM(amount_charged), 0)`,
  `COUNT(*)`, `COALESCE(SUM(duration_minutes), 0)` from `parking_sessions`
  where `status IN ('COMPLETED', 'LOST_CARD')`. Applies filters for
  `exit_time >= start_utc`, `exit_time < end_utc`, `gate_number`, `operator_id`
  when each is not `None`. Returns dict with keys: `total_sessions`,
  `total_revenue`, `total_duration`. Uses `text()` with named bind params.

- [x] **Task 4.9:** In `repositories/report_repo.py`, add method:
```python
  async def get_revenue_by_gate(
      self,
      start_utc: datetime | None,
      end_utc: datetime | None,
      operator_id: int | None,
  ) -> list[dict]
```
  Executes:
```sql
  SELECT gate_number,
         COUNT(*) AS session_count,
         COALESCE(SUM(amount_charged), 0) AS total_piastres
  FROM parking_sessions
  WHERE status IN ('COMPLETED', 'LOST_CARD')
    [AND exit_time >= :start_utc]
    [AND exit_time < :end_utc]
    [AND operator_id = :operator_id]
  GROUP BY gate_number
  ORDER BY gate_number
```
  Returns list of dicts with keys: `gate_number`, `session_count`,
  `total_piastres`.

- [x] **Task 4.10:** In `repositories/report_repo.py`, add method:
```python
  async def get_revenue_by_operator(
      self,
      start_utc: datetime | None,
      end_utc: datetime | None,
      gate_number: int | None,
  ) -> list[dict]
```
  Joins `parking_sessions` with `users` on `operator_id = users.id`. Groups by
  `operator_id`, `users.full_name`. Returns list of dicts: `operator_id`,
  `operator_name`, `session_count`, `total_piastres`.

- [x] **Task 4.10b:** In `repositories/report_repo.py`, add method:
```python
  async def get_revenue_by_service_type(
      self,
      start_utc: datetime | None,
      end_utc: datetime | None,
      gate_number: int | None,
  ) -> list[dict]
```
  Executes aggregation query grouping completed and lost-card sessions by service type
  (regular tickets, lost card penalties, and subscriptions). Returns list of dicts with keys:
  `service_type`, `session_count`, `total_piastres`.

- [x] **Task 4.11:** In `repositories/report_repo.py`, add method:
```python
  async def get_daily_revenue_raw(
      self,
      start_utc: datetime,
      end_utc: datetime,
      gate_number: int | None,
      operator_id: int | None,
  ) -> list[dict]
```
  Groups sessions by Cairo calendar date. Since SQLite and PostgreSQL handle
  date functions differently, use a portable approach:

  For **PostgreSQL** (`dialect.name == 'postgresql'`):
```sql
  SELECT
    DATE((exit_time + INTERVAL '2 hours')) AS cairo_date,
    COUNT(*) AS session_count,
    COALESCE(SUM(amount_charged), 0) AS total_piastres
  FROM parking_sessions
  WHERE status IN ('COMPLETED', 'LOST_CARD')
    AND exit_time >= :start_utc AND exit_time < :end_utc
    [AND gate_number = :gate_number]
    [AND operator_id = :operator_id]
  GROUP BY cairo_date
  ORDER BY cairo_date
```

  For **SQLite** (`dialect.name == 'sqlite'`):
```sql
  SELECT
    DATE(exit_time, '+2 hours') AS cairo_date,
    COUNT(*) AS session_count,
    COALESCE(SUM(amount_charged), 0) AS total_piastres
  FROM parking_sessions
  WHERE status IN ('COMPLETED', 'LOST_CARD')
    AND exit_time >= :start_utc AND exit_time < :end_utc
    [AND gate_number = :gate_number]
    [AND operator_id = :operator_id]
  GROUP BY cairo_date
  ORDER BY cairo_date
```

  Returns list of dicts: `cairo_date` (string `"YYYY-MM-DD"`),
  `session_count`, `total_piastres`.

- [x] **Task 4.12:** In `repositories/report_repo.py`, add method:
```python
  async def get_sessions_filtered(
      self,
      filters: ReportFilters,
      page: int,
      size: int,
  ) -> tuple[list[ParkingSession], int]
```
  Builds a dynamic `select(ParkingSession)` query. For each filter field,
  appends a WHERE clause only when the field is not `None` / not `False`:
  - `start_date` → `exit_time >= cairo_date_to_utc_start(start_date)`.
  - `end_date` → `exit_time < cairo_date_to_utc_end(end_date)`.
  - `gate_number` → `gate_number = :gate_number`.
  - `operator_id` → `operator_id = :operator_id`.
  - `status` → `status = :status`.
  - `card_code` → `card_code LIKE :pattern` where `pattern =
    f"%{escape_like(card_code)}%"`.
  - `plate_number` → `plate_number LIKE :pattern` where pattern uses
    `PlateService().search_normalized(plate_number)`.
  - `long_stay=True` → `status = 'ACTIVE' AND entry_time < :threshold` where
    `threshold = utcnow() - timedelta(hours=24)`.
  Returns `(sessions, total_count)`. Uses two queries: one for rows
  (with LIMIT/OFFSET), one for total COUNT with the same filters.

- [x] **Task 4.13:** In `repositories/report_repo.py`, add method:
```python
  async def get_sessions_for_export(
      self,
      filters: ReportFilters,
      chunk_size: int = 500,
  ) -> AsyncIterator[ParkingSession]
```
  Uses the same filter logic as Task 4.12 but yields sessions in chunks via
  `LIMIT/OFFSET` pagination. After yielding each chunk, calls
  `await asyncio.sleep(0)` to yield control. No full result set is loaded into
  memory. Implemented as an `async def` with `yield`.

- [x] **Task 4.14:** In `repositories/report_repo.py`, add a private static
  method:
```python
  @staticmethod
  def _escape_like(value: str) -> str:
```
  Replaces `%` with `\%` and `_` with `\_` in the input string. Returns the
  escaped string. Used internally before constructing LIKE patterns. Add
  `__all__ = ["ReportRepository"]`.

### 4b — Admin Shift Repository

- [x] **Task 4.15:** Create `repositories/admin_shift_repo.py`. Define an
  `AdminShiftRepository` class with `__init__(self, db: AsyncSession)`. Add
  method:
```python
  async def get_shifts_filtered(
      self,
      filters: ShiftFilters,
      page: int,
      size: int,
  ) -> tuple[list[Shift], int]
```
  Builds a dynamic `select(Shift)` query. Filter conditions:
  - `operator_id` → `operator_id = :val`.
  - `gate_number` → `gate_number = :val`.
  - `status='open'` → `ended_at IS NULL`.
  - `status='closed'` → `ended_at IS NOT NULL`.
  - `start_date` → `started_at >= cairo_date_to_utc_start(start_date)`.
  - `end_date` → `started_at < cairo_date_to_utc_end(end_date)`.
  - `overdue=True` → `ended_at IS NULL AND started_at 
    utcnow() - timedelta(hours=12)`.
  Returns `(shifts, total_count)` ordered by `started_at DESC`.

- [x] **Task 4.16:** In `repositories/admin_shift_repo.py`, add method:
```python
  async def get_shift_session_totals(
      self, shift_ids: list[int]
  ) -> dict[int, int]
```
  Executes:
```sql
  SELECT shift_id, COALESCE(SUM(amount_charged), 0) AS total
  FROM parking_sessions
  WHERE shift_id IN :ids
    AND status IN ('COMPLETED', 'LOST_CARD')
  GROUP BY shift_id
```
  Returns `dict[shift_id, total_piastres]`. Missing shift IDs default to `0`.

- [x] **Task 4.17:** In `repositories/admin_shift_repo.py`, add method:
```python
  async def get_shift_session_counts(
      self, shift_id: int
  ) -> dict[str, int]
```
  Returns counts by status for a single shift:
```sql
  SELECT status, COUNT(*) FROM parking_sessions
  WHERE shift_id = :shift_id
  GROUP BY status
```
  Returns `{"ACTIVE": n, "COMPLETED": n, "LOST_CARD": n}`. Missing statuses
  default to `0`. Add `__all__ = ["AdminShiftRepository"]`.

### 4c — Repositories `__init__.py`

- [x] **Task 4.18:** Update `repositories/__init__.py` to import and re-export
  `ReportRepository` and `AdminShiftRepository`. Rebuild `__all__`.

---

## Group 5 — Services

### 5a — Service Exceptions

- [x] **Task 5.1:** Open `services/exceptions.py`. Add the following new exception
  classes (same pattern as existing ones — inherit from `Exception`, store
  `message`):
  - `ShiftAlreadyClosedError`
  - `PricingRuleNotFoundError`
  - `RateLabelAlreadyExistsError`
  - `InvalidDateRangeError`
  - `InvalidReportTypeError`
  - `ShiftIdRequiredForPrintError`
  Update `__all__` to include all six new exceptions. Update
  `services/__init__.py` to re-export them.

### 5b — ReportService

- [x] **Task 5.2:** Create `services/report_service.py`. Define a `ReportService`
  class with:
```python
  def __init__(self, db: AsyncSession, report_repo: ReportRepository)
```
  Store both as instance attributes. No logic in `__init__`.

- [x] **Task 5.3:** In `services/report_service.py`, add method:
```python
  async def get_live_stats(self) -> LiveStatsResponse
```
  Fires five coroutines **concurrently** using `asyncio.gather` with
  `return_exceptions=True`:
  1. `self.report_repo.count_active_sessions()`
  2. `self.report_repo.count_total_card_capacity()`
  3. `self.report_repo.sum_revenue_today(cairo_today_start(),
     cairo_date_to_utc_end(cairo_now().date()))`
  4. `self.report_repo.count_open_shifts()`
  5. `self.report_repo.count_long_stay_sessions(
     datetime.utcnow() - timedelta(hours=24))`

  For each result: if it is an `Exception`, log at `ERROR` level and use `0`
  as the fallback value. Compute `occupancy_pct =
  round(active * 100 / max(capacity, 1))`. Return `LiveStatsResponse(...)`.
  Import `asyncio` at the top of the file.

- [x] **Task 5.4:** In `services/report_service.py`, add method:
```python
  async def get_gate_panel(self) -> list[GateStatusResponse]
```
  Calls `await self.report_repo.get_gate_panel()` to get open-shift gates.
  Builds a full list for gates 1–5: for each gate number, look up the result
  from the repo; if absent, create a `GateStatusResponse` with all fields
  `None`/`0`. Returns the list sorted by `gate_number` ascending.

- [x] **Task 5.5:** In `services/report_service.py`, add method:
```python
  async def get_alert_counts(self) -> dict[str, int]
```
  Calls two repo methods concurrently via `asyncio.gather`:
  - `count_long_stay_sessions(utcnow() - timedelta(hours=24))`
  - `count_overdue_shifts(utcnow() - timedelta(hours=12))`
  Returns `{"long_stay": n, "overdue_shifts": n}`. On exception for either,
  uses `0`.

- [x] **Task 5.6:** In `services/report_service.py`, add method:
```python
  async def get_revenue_summary(
      self, filters: ReportFilters
  ) -> RevenueSummaryResponse
```
  Resolves UTC boundaries from `filters.start_date` and `filters.end_date`
  (using `cairo_date_to_utc_start` / `cairo_date_to_utc_end`; `None` if not
  provided). Calls `report_repo.get_revenue_summary(...)`. Computes
  `avg_duration_minutes = total_duration // max(total_sessions, 1)` and
  `avg_revenue_piastres = total_revenue // max(total_sessions, 1)`. No floats.
  Returns `RevenueSummaryResponse(...)`.

- [x] **Task 5.7:** In `services/report_service.py`, add method:
```python
  async def get_revenue_by_gate(
      self, filters: ReportFilters
  ) -> list[GateRevenueResponse]
```
  Resolves UTC boundaries. Calls `report_repo.get_revenue_by_gate(...)`.
  Returns `list[GateRevenueResponse]`.

- [x] **Task 5.8:** In `services/report_service.py`, add method:
```python
  async def get_revenue_by_operator(
      self, filters: ReportFilters
  ) -> list[OperatorRevenueResponse]
```
  Resolves UTC boundaries. Calls `report_repo.get_revenue_by_operator(...)`.
  Returns `list[OperatorRevenueResponse]`.

- [x] **Task 5.8b:** In `services/report_service.py`, add method:
```python
  async def get_revenue_by_service_type(
      self, filters: ReportFilters
  ) -> list[ServiceTypeRevenueResponse]
```
  Resolves UTC boundaries from `filters.start_date` and `filters.end_date`. Calls
  `report_repo.get_revenue_by_service_type(...)`. Computes percentage breakdown
  and returns `list[ServiceTypeRevenueResponse]`.

- [x] **Task 5.9:** In `services/report_service.py`, add method:
```python
  async def get_daily_revenue(
      self, filters: ReportFilters
  ) -> list[DailyRevenueResponse]
```
  Requires both `filters.start_date` and `filters.end_date` to be set.
  If either is `None`, defaults to today's Cairo date for both. Calls
  `report_repo.get_daily_revenue_raw(...)`. Then fills in missing days in
  Python: iterates from `start_date` to `end_date` inclusive (using
  `timedelta(days=1)`); for each day, if absent from DB results, inserts a
  `DailyRevenueResponse(date_str=..., session_count=0, total_piastres=0)`.
  Returns the complete list ordered by `date_str` ascending.

- [x] **Task 5.10:** In `services/report_service.py`, add method:
```python
  async def get_sessions_filtered(
      self,
      filters: ReportFilters,
      page: int,
      size: int,
  ) -> tuple[list[ParkingSession], int]
```
  Delegates directly to `self.report_repo.get_sessions_filtered(filters, page,
  size)`. Returns the tuple unchanged. Add `__all__ = ["ReportService"]`.

### 5c — Admin Shift Service Extension

- [x] **Task 5.11:** Open `services/shift_service.py`. Add a new method to
  `ShiftService`:
```python
  async def force_close_shift(
      self,
      shift_id: int,
      admin_id: int,
      closing_cash_piastres: int | None,
      admin_note: str | None,
  ) -> ShiftSummary
```
  Implementation:
  1. Fetch shift via `self.db.get(Shift, shift_id)`. Raises `ShiftNotFoundError`
     if `None`.
  2. If `shift.ended_at IS NOT NULL`: raises `ShiftAlreadyClosedError`.
  3. Capture `before_state = {"ended_at": None, "closing_cash_egp":
     shift.closing_cash_egp}`.
  4. Set `shift.ended_at = datetime.utcnow()`.
  5. If `closing_cash_piastres is not None`: set `shift.closing_cash_egp =
     closing_cash_piastres`.
  6. If `admin_note is not None`: set `shift.admin_override_note = admin_note`.
  7. Flush.
  8. Compute summary via `await self._compute_summary(shift,
     shift.closing_cash_egp)`.
  9. Commit.
  10. Call `await self.audit_service.log(actor_id=admin_id,
      action="SHIFT_FORCE_CLOSED", entity_type="shift", entity_id=shift_id,
      before=before_state, after={"ended_at": shift.ended_at.isoformat(),
      "closing_cash_egp": shift.closing_cash_egp, "admin_note": admin_note})`.
  11. Return the `ShiftSummary`.

  The audit log write is called after commit (per spec FR-AUDIT-005). If the
  audit write fails, log at `ERROR` level but do not re-raise.

### 5c2 — Admin Session Service Extension

- [x] **Task 5.11b:** Open `services/session_service.py`. Add method to `SessionService`:
```python
  async def admin_override_close_session(
      self,
      session_id: int,
      admin_id: int,
      amount_charged_egp: float = 0.0,
      override_note: str | None = None,
  ) -> ParkingSession
```
  Implementation:
  1. Fetch session via `session_repo.get_by_id(session_id)`. Raises `SessionNotFoundError` if absent.
  2. If `session.status != SessionStatus.ACTIVE`: raises `SessionNotActiveError`.
  3. Closes session: sets `exit_time = datetime.utcnow()`, `status = SessionStatus.COMPLETED`,
     `is_paid = True`, `amount_charged = int(round(amount_charged_egp * 100))`,
     `payment_method = PaymentMethod.CASH`, `admin_override_by = admin_id`,
     `admin_override_note = override_note`.
  4. Releases associated card status to `AVAILABLE`.
  5. Commits changes and writes audit log with action `"SESSION_ADMIN_OVERRIDE_CLOSE"`.
  6. Returns the updated session.

### 5d — Admin Pricing Service Extension

- [x] **Task 5.12:** Open `services/pricing_service.py`. Add method to
  `PricingService`:
```python
  async def create_rule(
      self,
      data: PricingRuleCreate,
      admin_id: int,
      rate_repo: PricingRuleRepository,
      audit_service: AuditService,
  ) -> PricingRule
```
  Implementation:
  1. Check for duplicate label via `rate_repo.get_by_label(data.label)`. Raises
     `RateLabelAlreadyExistsError` if found.
  2. Convert EGP float fields to piastres using `round(value * 100)` (already
     done in schema validator — verify and trust `data` fields are integers).
  3. Call `rate_repo.create(label=data.label, rate_per_hour=data.rate_per_hour,
     minimum_charge=data.minimum_charge, grace_period_mins=
     data.grace_period_mins, lost_card_penalty=data.lost_card_penalty,
     effective_from=data.effective_from or datetime.utcnow(),
     effective_until=data.effective_until, created_by=admin_id,
     is_active=False)`.
  4. Commit.
  5. Call `audit_service.log(...)` with action `"RATE_CREATED"`.
  6. Return the rule.

- [x] **Task 5.13:** Open `repositories/rate_repo.py`. Add method to
  `PricingRuleRepository`:
```python
  async def get_by_label(self, label: str) -> PricingRule | None
```
  `SELECT * FROM pricing_rules WHERE label = :label LIMIT 1`. Returns the rule
  or `None`. Update `__all__`.

- [x] **Task 5.14:** Update `schemas/pricing_rule.py`. Modify `PricingRuleCreate`
  to accept EGP float inputs and convert to piastres in validators:
  - Change `rate_per_hour: int` → `rate_per_hour_egp: float = Field(ge=0)`.
  - Change `minimum_charge: int` → `minimum_charge_egp: float = Field(ge=0)`.
  - Change `lost_card_penalty: int` → `lost_card_penalty_egp: float =
     Field(ge=0)`.
  - Add computed properties (or a `model_validator(mode="after")`) that sets:
    `rate_per_hour: int = round(rate_per_hour_egp * 100)`,
    `minimum_charge: int = round(minimum_charge_egp * 100)`,
    `lost_card_penalty: int = round(lost_card_penalty_egp * 100)`.
  Ensure `grace_period_mins: int` remains an integer input (minutes, not EGP).
  Update `__all__` and `schemas/__init__.py`.

### 5e — Services `__init__.py`

- [x] **Task 5.15:** Update `services/__init__.py` to import and re-export
  `ReportService`. Rebuild `__all__`. Verify all six new exceptions from
  Task 5.1 are exported.

---

## Group 6 — Jinja2 Filters & Admin Static Assets

### 6a — New Jinja2 Filters

- [x] **Task 6.1:** Open `utils/jinja.py`. Add the following filter function:
```python
  def discrepancy_class_filter(
      discrepancy_piastres: int | None,
      computed_total: int = 0,
  ) -> str:
```
  Logic:
  - If `discrepancy_piastres is None`: return `"text-gray-400"`.
  - If `discrepancy_piastres == 0`: return `"text-green-600"`.
  - If `abs(discrepancy_piastres) / max(computed_total, 1) <= 0.05`: return
    `"text-amber-500"`.
  - Else: return `"text-red-600"`.
  This is a pure function. No imports from the project.

- [x] **Task 6.2:** In `utils/jinja.py`, add filter:
```python
  def cairo_date_filter(dt: datetime | None) -> str:
```
  If `dt is None`: returns `"—"`. Else: calls `cairo_date_str(dt)` from
  `utils/time.py`. Returns the `"YYYY-MM-DD"` string.

- [x] **Task 6.3:** In `utils/jinja.py`, add filter:
```python
  def session_status_label_filter(status: str) -> str:
```
  Returns: `"ACTIVE"` → `"داخل"`, `"COMPLETED"` → `"خرج"`,
  `"LOST_CARD"` → `"كرت مفقود"`. Any other value → `status` unchanged.

- [x] **Task 6.4:** In `utils/jinja.py`, add filter:
```python
  def shift_status_label_filter(ended_at: datetime | None) -> str:
```
  Returns `"مفتوح"` if `ended_at is None`, else `"مغلق"`.

- [x] **Task 6.5:** In `utils/jinja.py`, update `create_jinja2_environment` to
  register all four new filters:
  - `"discrepancy_class"` → `discrepancy_class_filter`
  - `"cairo_date"` → `cairo_date_filter`
  - `"session_status_label"` → `session_status_label_filter`
  - `"shift_status_label"` → `shift_status_label_filter`
  Also verify `"zfill"` is registered (from Phase 2 tasks). No other changes to
  this function in this task.

### 6b — Admin Translations

- [x] **Task 6.6:** Open `translations/ar.json`. Add all keys listed in
  `spec.md` Section 2.12. Do not remove any existing keys. Validate the JSON is
  syntactically correct after editing (run `python -c "import json;
  json.load(open('translations/ar.json'))"`).

### 6c — Admin Print CSS

- [x] **Task 6.7:** Create `static/admin_print.css`. This file contains both
  screen and print styles for the A4 print template:
```css
  /* Screen preview styles */
  body {
    font-family: 'Arial', sans-serif;
    font-size: 11pt;
    direction: rtl;
    margin: 20px auto;
    max-width: 210mm;
    padding: 15mm;
    background: white;
  }

  .no-print {
    margin-bottom: 16px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th, td {
    border: 1px solid #ccc;
    padding: 6px 8px;
    text-align: right;
  }

  th {
    background-color: #f0f0f0;
    font-weight: bold;
  }

  /* Print-only styles */
  @media print {
    @page {
      size: A4;
      margin: 15mm;
    }

    body {
      margin: 0;
      padding: 0;
      font-size: 10pt;
    }

    .no-print {
      display: none !important;
    }

    table {
      page-break-inside: auto;
    }

    tr {
      page-break-inside: avoid;
    }

    thead {
      display: table-header-group;
    }
  }
```

### 6d — Admin Dashboard JS

- [x] **Task 6.8:** Create `static/js/admin_dashboard.js`. Contains three
  functions:
```javascript
  async function refreshLiveStats(statsUrl, gatesUrl) { ... }
```
  Calls `fetch(statsUrl)` and `fetch(gatesUrl)` concurrently via
  `Promise.all`. On success, updates DOM elements by ID:
  `"stat-active-sessions"`, `"stat-occupancy"`, `"stat-revenue-today"`,
  `"stat-open-shifts"`. Updates the gate panel rows by finding elements with
  `data-gate` attributes. On fetch error: logs to `console.error` and does not
  update DOM (stale values remain).

```javascript
  function startAutoRefresh(statsUrl, gatesUrl, intervalMs = 30000) { ... }
```
  Calls `refreshLiveStats` once immediately, then sets `setInterval` for
  `intervalMs`. Returns the interval ID.

```javascript
  function convertToArabicIndic(numStr) { ... }
```
  Replaces each Latin digit with its Arabic-Indic equivalent using a lookup
  object. Returns the converted string. Used to update stat values in the DOM
  after fetch.

  Total file size under 3KB. No external dependencies. Vanilla JS only.

---

## Group 7 — Admin API Routes

- [x] **Task 7.1:** Create `routes/admin_api.py`. Define `router = APIRouter(
  prefix="/api/v1/admin", tags=["admin"])`. All routes in this file use
  `Depends(require_admin)`. Add `GET /stats/live` endpoint:
  - Instantiates `ReportRepository(db)` and `ReportService(db, repo)`.
  - Calls `await report_service.get_live_stats()`.
  - Returns `{"data": LiveStatsResponse(...).model_dump()}` with status `200`.

- [x] **Task 7.2:** In `routes/admin_api.py`, add `GET /stats/gates` endpoint:
  - Calls `await report_service.get_gate_panel()`.
  - Returns `{"data": [GateStatusResponse(...).model_dump() for g in gates]}`
    with status `200`.

- [x] **Task 7.3:** In `routes/admin_api.py`, add `GET /sessions` endpoint:
  - Query params parsed into `ReportFilters` using `Depends` with a
    `get_report_filters` dependency function defined in this file. The
    dependency reads individual query params and constructs `ReportFilters`,
    raising `HTTPException(422, code="INVALID_DATE_RANGE")` on
    `ValueError` from the validator.
  - Pagination: `page: int = Query(1, ge=1)`, `size: int = Query(20, ge=1,
    le=100)`.
  - Calls `report_service.get_sessions_filtered(filters, page, size)`.
  - Returns `PaginatedResponse[SessionResponse]`.

- [x] **Task 7.4:** In `routes/admin_api.py`, add `GET /sessions/{session_id}`
  endpoint:
  - Fetches session via `ParkingSessionRepository.get_by_id`. Raises
    `HTTPException(404, code="SESSION_NOT_FOUND")` if absent.
  - Fetches all `AuditLog` rows where `entity_type='parking_session'` and
    `entity_id=session_id`, ordered by `created_at ASC`, via a direct query.
  - Builds and returns `{"data": AdminSessionDetail(...).model_dump()}`.

- [x] **Task 7.4b:** In `routes/admin_api.py`, add `POST /sessions/{session_id}/override-close` endpoint:
  - Accepts `payload: SessionAdminOverrideCloseRequest`.
  - Calls `session_service.admin_override_close_session(...)`.
  - Maps `SessionNotFoundError` → `404` with `X-Error-Code: SESSION_NOT_FOUND`.
  - Maps `SessionNotActiveError` → `409` with `X-Error-Code: SESSION_NOT_ACTIVE`.
  - Returns `{"success": True, "message": "تم إغلاق الجلسة وتحرير الكرت بنجاح", "data": {...}}`.

- [x] **Task 7.5:** In `routes/admin_api.py`, add
  `GET /sessions/export/csv` endpoint:
  - Same filter parsing as Task 7.3 (reuse `get_report_filters` dependency).
  - Fetches all operator IDs from sessions, loads their names in one query.
  - Calls `report_repo.get_sessions_for_export(filters)` to get the async
    iterator.
  - Constructs `generate_sessions_csv(sessions_iter, operator_names)`.
  - Returns `StreamingResponse(generator, media_type="text/csv",
    headers={"Content-Disposition":
    f'attachment; filename="pgms_sessions_{cairo_date_str(utcnow())}.csv"})`.

- [x] **Task 7.6:** In `routes/admin_api.py`, add `GET /shifts` endpoint:
  - Query params parsed into `ShiftFilters` using a `get_shift_filters`
    dependency function. Raises `HTTPException(422, code="INVALID_DATE_RANGE")`
    on date range errors.
  - Calls `AdminShiftRepository.get_shifts_filtered(filters, page, size)`.
  - Fetches session totals via `get_shift_session_totals(shift_ids)`.
  - Returns `PaginatedResponse[ShiftResponse]`.

- [x] **Task 7.7:** In `routes/admin_api.py`, add `GET /shifts/{shift_id}`
  endpoint:
  - Fetches shift by ID. Raises `HTTPException(404)` if absent.
  - Calls `ShiftService._compute_summary(shift, shift.closing_cash_egp)`.
  - Fetches paginated sessions for the shift via
    `ParkingSessionRepository.get_by_shift(shift_id, page=1, size=10)`.
  - Returns `{"data": {"shift": ShiftResponse(...), "summary":
    ShiftSummaryResponse(...), "sessions": [SessionResponse(...)],
    "session_total": total}}`.

- [x] **Task 7.8:** In `routes/admin_api.py`, add
  `GET /shifts/{shift_id}/export/csv` endpoint:
  - Fetches all sessions for the shift via async iterator (chunk size 500).
  - Fetches operator names. Fetches session totals via
    `get_shift_session_totals([shift_id])`.
  - Streams `generate_sessions_csv(...)`.
  - Returns `StreamingResponse` with filename
    `pgms_shift_{shift_id}_{cairo_date}.csv`.

- [x] **Task 7.9:** In `routes/admin_api.py`, add
  `PATCH /shifts/{shift_id}/force-close` endpoint:
  - Body: `ForceCloseShiftRequest` (optional).
  - Calls `ShiftService.force_close_shift(shift_id, current_user.id,
    data.closing_cash_egp, data.admin_note)`.
  - Maps `ShiftNotFoundError` → `404`, `ShiftAlreadyClosedError` → `409` with
    code `"SHIFT_ALREADY_CLOSED"`.
  - Returns `{"data": ShiftSummaryResponse(...).model_dump()}`.

- [x] **Task 7.10:** In `routes/admin_api.py`, add `GET /reports/revenue`
  endpoint:
  - Same filter parsing as Task 7.3.
  - Calls four service methods concurrently via `asyncio.gather`:
    `get_revenue_summary`, `get_revenue_by_gate`, `get_revenue_by_operator`,
    `get_daily_revenue`.
  - Returns:
```json
    {
      "data": {
        "summary": {...},
        "by_gate": [...],
        "by_operator": [...],
        "daily": [...]
      }
    }
```

- [x] **Task 7.10b:** In `routes/admin_api.py`, add subscription reporting endpoints:
  - `GET /stats/subscriptions`: Uses `SubscriptionService` to fetch subscriber metrics (`total_subscribers`, `active_subscribers`, `expiring_soon`).
  - `GET /reports/subscriptions`: Uses `SubscriptionRepository` to fetch paginated subscriptions ledger with filtering.

- [x] **Task 7.11:** In `routes/admin_api.py`, add `GET /reports/export/csv`
  endpoint:
  - Same filter + streaming pattern as Task 7.5.
  - Filename: `pgms_report_{start}_{end}.csv` where `start` and `end` are
    Cairo date strings from the filter (or `"all"` if not provided).

- [x] **Task 7.12:** Register `admin_api.router` in `main.py`. Import `router`
  from `routes/admin_api.py` as `admin_api_router`. Add
  `app.include_router(admin_api_router)` after existing routers. No other
  changes to `main.py`.

---

## Group 8 — Admin UI Routes & Jinja2 Templates

### 8a — Admin UI Router

- [x] **Task 8.1:** Create `routes/ui_admin.py`. Define `router = APIRouter(
  prefix="/ui/admin", tags=["ui-admin"])`. All routes use
  `Depends(require_admin)`. Add a module-level dependency override: unauthenticated
  or non-admin access redirects to `/ui/login?next={request.url.path}` with
  status `303`. Implement this via a shared `require_admin_ui` dependency that
  catches `HTTPException(403)` and issues the redirect instead of returning JSON.

- [x] **Task 8.2:** In `routes/ui_admin.py`, add `GET /dashboard` endpoint:
  - Calls `report_service.get_live_stats()` and `report_service.get_gate_panel()`
    concurrently via `asyncio.gather`.
  - Calls `report_service.get_alert_counts()`.
  - Returns `TemplateResponse("admin/dashboard.html", {"request": request,
    "user": current_user, "stats": stats, "gates": gates,
    "long_stay_count": alerts["long_stay"],
    "overdue_shift_count": alerts["overdue_shifts"]})`.

- [x] **Task 8.3:** In `routes/ui_admin.py`, add `GET /shifts` endpoint:
  - Parses `ShiftFilters` from query params using `get_shift_filters` dependency.
  - Pagination: `page`, `size` (default 20).
  - Calls `AdminShiftRepository.get_shifts_filtered(filters, page, size)`.
  - Fetches operator names for all returned shifts (one query via `WHERE id IN`).
  - Fetches session totals via `get_shift_session_totals(shift_ids)`.
  - Returns `TemplateResponse("admin/shifts.html", {...})`.

- [x] **Task 8.4:** In `routes/ui_admin.py`, add `GET /shifts/{shift_id}`
  endpoint:
  - Fetches shift. Raises redirect to `/ui/admin/shifts` if not found.
  - Computes summary via `ShiftService._compute_summary(...)`.
  - Fetches paginated sessions (page 1, size 10).
  - Returns `TemplateResponse("admin/shift_detail.html", {...})`.

- [x] **Task 8.5:** In `routes/ui_admin.py`, add `GET /sessions` endpoint:
  - Parses `ReportFilters` from query params.
  - Calls `report_service.get_sessions_filtered(filters, page, size)`.
  - Fetches operator names for all returned sessions.
  - Returns `TemplateResponse("admin/sessions.html", {...})`.

- [x] **Task 8.6:** In `routes/ui_admin.py`, add `GET /sessions/{session_id}`
  endpoint:
  - Fetches session and audit logs (same logic as API Task 7.4).
  - Fetches operator name, exit operator name, pricing rule label.
  - Returns `TemplateResponse("admin/session_detail.html", {...})`.

- [x] **Task 8.6b:** In `routes/ui_admin.py`, add camera image serving endpoints:
  - `GET /sessions/{session_id}/plate-image`: Resolves entry ANPR plate photo via `PlateCaptureService.resolve_image(...)`. Returns `FileResponse` with caching headers, or 404.
  - `GET /sessions/{session_id}/exit-image`: Resolves exit camera photo via `PlateCaptureService.resolve_image(...)`. Returns `FileResponse` with caching headers, or 404.

- [x] **Task 8.7:** In `routes/ui_admin.py`, add `GET /reports/revenue` endpoint:
  - Parses `ReportFilters`. Defaults `start_date` and `end_date` to today if
    absent.
  - Calls all four report service methods (as in API Task 7.10).
  - Fetches all operators and gates for the filter dropdowns.
  - Returns `TemplateResponse("admin/reports/revenue.html", {...})`.

- [x] **Task 8.8:** In `routes/ui_admin.py`, add `GET /reports/print` endpoint:
  - Query params: `report_type: str`, `shift_id: int | None = None`, plus all
    filter params.
  - Validates `report_type` is one of `"revenue"`, `"sessions"`, `"shift"`.
    Raises `HTTPException(422, code="INVALID_REPORT_TYPE")` if invalid.
  - If `report_type="shift"` and `shift_id is None`: raises `HTTPException(422,
    code="SHIFT_ID_REQUIRED_FOR_PRINT")`.
  - Fetches the appropriate data (up to 500 rows for sessions/revenue, full
    shift detail for shift type). If row count > 500, sets
    `truncated=True` in context.
  - Returns `TemplateResponse("admin/reports/print.html", {"request": request,
    "report_type": report_type, "data": ..., "filters": filters,
    "generated_at": cairo_now(), "garage_name": settings.APP_NAME,
    "truncated": truncated})`. This route renders a standalone template.

- [x] **Task 8.9:** In `routes/ui_admin.py`, add `GET /rates` endpoint:
  - Fetches all pricing rules ordered by `created_at DESC` via
    `PricingRuleRepository.get_all(page=1, size=100)`.
  - Returns `TemplateResponse("admin/rates.html", {"request": request,
    "user": current_user, "rules": rules})`.

- [x] **Task 8.10:** In `routes/ui_admin.py`, add `GET /operators` endpoint:
  - Fetches all users via `UserRepository.get_all(page=1, size=200)`.
  - For each operator, fetches their active shift status via a single
    `get_active_shift` batch query (or one query per operator — note the
    10-operator scale makes N+1 acceptable here).
  - Returns `TemplateResponse("admin/operators.html", {...})`.

- [x] **Task 8.10b:** In `routes/ui_admin.py`, add `GET /cards` endpoint:
  - Fetches card inventory and counters by status (`total`, `available`, `in_use`, `lost`, `damaged`).
  - Returns `TemplateResponse("admin/cards.html", {"request": request, "user": current_user, "cards": cards, ...})`.

- [x] **Task 8.11:** Register `ui_admin.router` in `main.py`. Import as
  `ui_admin_router`. Add `app.include_router(ui_admin_router)`. No other
  changes.

### 8b — Admin Base Template

- [x] **Task 8.12:** Create `templates/admin/base_admin.html`. This file does
  **NOT** extend any other template. Complete structure:
```html
  <!DOCTYPE html>
  <html lang="ar" dir="rtl">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ t("admin.dashboard.title") }}{% endblock %} — PGMS</title>
    <link rel="stylesheet" href="/static/css/tailwind.min.css">
    {% block head %}{% endblock %}
  </head>
  <body class="bg-gray-100 min-h-screen">
    <!-- Sidebar -->
    <aside id="sidebar" class="...">
      <nav>
        <a href="/ui/admin/dashboard">{{ t("admin.nav.dashboard") }}</a>
        <a href="/ui/admin/shifts">{{ t("admin.nav.shifts") }}</a>
        <a href="/ui/admin/sessions">{{ t("admin.nav.sessions") }}</a>
        <a href="/ui/admin/reports/revenue">{{ t("admin.nav.reports") }}</a>
        <a href="/ui/admin/rates">{{ t("admin.nav.rates") }}</a>
        <a href="/ui/admin/operators">{{ t("admin.nav.operators") }}</a>
        <form method="POST" action="/ui/logout">
          <button type="submit">{{ t("admin.nav.logout") }}</button>
        </form>
      </nav>
    </aside>
    <!-- Main content -->
    <main class="...">
      <header class="...">
        <button id="sidebar-toggle" class="...">☰</button>
        <span>{{ user.full_name if user else "" }}</span>
      </header>
      {% block content %}{% endblock %}
    </main>
    <script>
      // Sidebar collapse with localStorage
      const sidebar = document.getElementById('sidebar');
      const toggle = document.getElementById('sidebar-toggle');
      const STORAGE_KEY = 'pgms_sidebar_collapsed';
      if (localStorage.getItem(STORAGE_KEY) === 'true') {
        sidebar.classList.add('collapsed');
      }
      toggle.addEventListener('click', () => {
        const collapsed = sidebar.classList.toggle('collapsed');
        localStorage.setItem(STORAGE_KEY, collapsed);
      });
    </script>
    {% block scripts %}{% endblock %}
  </body>
  </html>
```
  Use Tailwind utility classes throughout. Sidebar width: `w-64` expanded,
  `w-0 overflow-hidden` collapsed. Main content margin adjusts accordingly.

### 8c — Admin Dashboard Template

- [x] **Task 8.13:** Create `templates/admin/dashboard.html` extending
  `templates/admin/base_admin.html`. Must include:
  - If `long_stay_count > 0`: amber alert banner with count and link to
    `/ui/admin/sessions?status=ACTIVE&long_stay=true`.
  - If `overdue_shift_count > 0`: red alert banner with count and link to
    `/ui/admin/shifts?status=open&overdue=true`.
  - Four KPI cards in a 2×2 grid (`grid grid-cols-2 gap-4`). Each card:
    `rounded-lg bg-white shadow p-4`. Labels from `t(...)`. Values with IDs:
    `stat-active-sessions`, `stat-occupancy`, `stat-revenue-today`,
    `stat-open-shifts`. Values pre-populated from server-side `stats` context
    using `format_egp` / `to_arabic_indic` as appropriate.
  - Gate panel table below KPIs: columns — gate number, operator, shift start,
    active sessions, status badge. Each row has `data-gate="{{ g.gate_number }}"`.
    Clicking a row navigates to `/ui/admin/shifts?gate_number={{ g.gate_number }}`.
  - At bottom of `{% block scripts %}`: loads `/static/js/admin_dashboard.js`
    and calls `startAutoRefresh('/api/v1/admin/stats/live',
    '/api/v1/admin/stats/gates', 30000)`.

### 8d — Shift List Template

- [x] **Task 8.14:** Create `templates/admin/shifts.html` extending
  `base_admin.html`. Must include:
  - Filter bar: `<form method="GET">` with inputs for `start_date`, `end_date`
    (`type="date"`), `gate_number` (dropdown 1–5 + "الكل"), `operator_id`
    (dropdown + "الكل"), `status` (dropdown: open/closed/كل), `overdue`
    (checkbox). Submit button: `t("admin.filter.submit")`.
  - Results count: `t("admin.pagination.showing")` with values via
    `to_arabic_indic`.
  - Table: `shift_id | operator | gate | start | end | sessions | computed total
    | closing cash | discrepancy | status`. Discrepancy cell uses
    `discrepancy_class` filter for colour. Status badge uses `shift_status_label`
    filter.
  - Pagination controls below the table. Page numbers with current page
    highlighted.
  - Each row links to `/ui/admin/shifts/{{ shift.id }}`.

### 8e — Shift Detail Template

- [x] **Task 8.15:** Create `templates/admin/shift_detail.html` extending
  `base_admin.html`. Must include:
  - Header card: operator name, gate, start time (`format_datetime`), end time
    or "مفتوح", duration.
  - Financial summary card: all `ShiftSummary` fields rendered with `format_egp`.
    Discrepancy in colour using `discrepancy_class` filter.
  - If `shift.ended_at is None`: "Admin Override: Force Close Shift" button
    that opens a `<dialog>` modal (HTML5 `<dialog>` element). Modal contains a
    form with optional closing cash input and notes textarea. Form POSTs to
    `PATCH /api/v1/admin/shifts/{{ shift.id }}/force-close` via `fetch` in an
    inline script. On success: reloads the page.
  - Sessions table (paginated 10 per page): session ID (zfill 8), card code,
    plate, entry time, exit time, duration, amount.
  - Two buttons: "Export Sessions CSV" (links to
    `/api/v1/admin/shifts/{{ shift.id }}/export/csv`) and "طباعة" (links to
    `/ui/admin/reports/print?report_type=shift&shift_id={{ shift.id }}`).

### 8f — Session List Template

- [x] **Task 8.16:** Create `templates/admin/sessions.html` extending
  `base_admin.html`. Must include:
  - Filter bar with: `start_date`, `end_date`, `gate_number`, `operator_id`,
    `status` (dropdown with all three status options), `card_code` text input,
    `plate_number` text input, `long_stay` checkbox.
  - Results count line.
  - Table: session ID (zfill 8), card code, plate (or "—"), gate, operator,
    status badge (`session_status_label`), entry time, exit time, duration,
    amount (`format_egp`).
  - Each row clickable → `/ui/admin/sessions/{{ session.id }}`.
  - "Export CSV" button → `/api/v1/admin/sessions/export/csv` with current
    filters appended as query params.
  - Pagination controls.

- [x] **Task 8.16b:** In `templates/admin/sessions.html`, add inline Admin Override modal:
  - Add quick settlement action button per active session row.
  - Dialog modal allowing input of settled amount and required override note.
  - Submits to `POST /api/v1/admin/sessions/{session_id}/override-close` via `fetch` and refreshes table without full reload.

### 8g — Session Detail Template

- [x] **Task 8.17:** Create `templates/admin/session_detail.html` extending
  `base_admin.html`. Must include:
  - Two-column detail card: all session fields rendered in a `<dl>` definition
    list. Monetary fields via `format_egp`. Datetime fields via `format_datetime`.
    Booleans as "نعم" / "لا".
  - Audit log section: a table of all audit log entries for this session:
    timestamp (`format_datetime`), actor, action, before/after (truncated to 80
    chars per cell with `title` attribute showing full text).
  - A "رجوع" link to `/ui/admin/sessions`.

- [x] **Task 8.17b:** In `templates/admin/session_detail.html`, add ANPR Camera Plate section & Admin Override Action Box:
  - Displays entry and exit camera photo snapshots served by `/ui/admin/sessions/{id}/plate-image` and `/exit-image`.
  - Visual Egyptian license plate badge ("مـصـر / EGYPT" with Arabic letters and numerals).
  - Admin Override Action Box (displayed if `session.status == 'ACTIVE'`), providing amount input and override reason note, submitting to `/api/v1/admin/sessions/{id}/override-close`.

### 8h — Revenue Report Template

- [x] **Task 8.18:** Create `templates/admin/reports/revenue.html` extending
  `base_admin.html`. Must include:
  - Filter bar (same structure as sessions, without `status`, `card_code`,
    `plate_number`, `long_stay`). Default `start_date` and `end_date` to today
    (pre-populated server-side).
  - Summary card: four KPI values from `RevenueSummaryResponse`.
  - "By Gate" table: gate number, session count, total revenue.
  - "By Operator" table: operator name, session count, total revenue.
  - "Daily Revenue" table: date, session count, total revenue. Days with zero
    sessions rendered with grey text.
  - "Export CSV" and "طباعة" buttons.
  - All monetary values via `format_egp`. All numbers via `to_arabic_indic`.

### 8i — Rates Management Template

- [x] **Task 8.19:** Create `templates/admin/rates.html` extending
  `base_admin.html`. Must include:
  - "إنشاء تعريفة جديدة" button that shows/hides an inline `<div>` form via
    a toggle. The form uses `fetch` to POST to `/api/v1/rates/` with JSON body.
    On success: inserts the new rule at the top of the table without page reload.
    On error: shows Arabic error message inside the form.
  - Form fields: `label` (text), `rate_per_hour_egp` (number, step `"0.01"`),
    `grace_period_mins` (number, min `"0"`), `minimum_charge_egp` (number,
    step `"0.01"`), `lost_card_penalty_egp` (number, step `"0.01"`),
    `effective_from` (datetime-local).
  - Client-side JS: prevents negative values in all number inputs via
    `input.addEventListener('input', () => { if (val < 0) input.value = 0; })`.
  - Rules table (newest first): ID, label, rate/hr, grace, min charge, penalty,
    effective from, active badge. "تفعيل" button (disabled on active rule) calls
    `PATCH /api/v1/rates/{id}/activate` via `fetch`. On success: updates badges
    in the table without reload.

### 8j — Operators Template

- [x] **Task 8.20:** Create `templates/admin/operators.html` extending
  `base_admin.html`. Must include:
  - Table: full name, username, gate, is_active badge, current shift status,
    last shift date (or "لا يوجد").
  - Per-row action buttons: "تعطيل" (POST to `PATCH /api/v1/users/{id}/deactivate`
    via `fetch`), "إعادة كلمة المرور" (opens a modal with a password input,
    POSTs to `PATCH /api/v1/users/{id}/reset-password`).
  - "إنشاء عامل جديد" button that shows an inline form (same toggle pattern
    as rates page). Form fields: `full_name`, `username`, `password`, `role`
    (select), `gate_number` (1–5, shown only when role = operator). POSTs to
    `POST /api/v1/users/`.

- [x] **Task 8.20b:** Create `templates/admin/cards.html` extending `base_admin.html`:
  - Cards inventory management table with status filter badges (`available`, `in_use`, `lost`, `damaged`).
  - Single card add form and bulk barcode generation modal with range specifications.
  - Barcode printable sheet layout for thermal/sticker printing.

### 8k — A4 Print Template

- [x] **Task 8.21:** Create `templates/admin/reports/print.html`. This is a
  **standalone** HTML file — does NOT extend any base template. Structure:
```html
  <!DOCTYPE html>
  <html lang="ar" dir="rtl">
  <head>
    <meta charset="UTF-8">
    <title>{{ t("admin.reports.print_title") }}</title>
    <link rel="stylesheet" href="/static/admin_print.css">
  </head>
  <body>
    <div class="no-print">
      <a href="javascript:history.back()">{{ t("admin.nav.dashboard") }} ← رجوع</a>
      <button onclick="window.print()">{{ t("admin.print.button") }}</button>
    </div>
    <h1>{{ garage_name }}</h1>
    <h2>{{ t("admin.reports.print_title") }} — {{ report_type }}</h2>
    <p>
      {% if filters.start_date %}من: {{ filters.start_date }}{% endif %}
      {% if filters.end_date %} إلى: {{ filters.end_date }}{% endif %}
      {% if filters.gate_number %} | البوابة: {{ filters.gate_number | to_arabic_indic }}{% endif %}
    </p>
    <p>تاريخ الطباعة: {{ generated_at | format_datetime }}</p>
    <hr>
    {% if truncated %}
    <p><strong>ملاحظة: يتم عرض أول ٥٠٠ نتيجة فقط</strong></p>
    {% endif %}
    {% block report_content %}{% endblock %}
    <script>
      window.addEventListener('load', () => window.print());
    </script>
  </body>
  </html>
```
  The `{% block report_content %}` is populated in the route by passing the
  pre-rendered data. Since the print template is standalone, the route renders
  the data inline using Jinja2 `include` of a partial. Define three partials:
  - `templates/admin/reports/_print_sessions.html`
  - `templates/admin/reports/_print_revenue.html`
  - `templates/admin/reports/_print_shift.html`
  The main print template uses `{% if report_type == "sessions" %}{% include
  "admin/reports/_print_sessions.html" %}{% endif %}` etc.

- [x] **Task 8.22:** Create `templates/admin/reports/_print_sessions.html`
  (partial, no extends). Renders a full `<table>` of session rows using the
  same columns as the session list page. All monetary values via `format_egp`.
  All datetimes via `format_datetime`. No pagination — all rows are rendered.

- [x] **Task 8.23:** Create `templates/admin/reports/_print_revenue.html`
  (partial). Renders: summary card as a `<table>`, then "by gate" table, then
  "by operator" table, then "daily" table. All on one scrollable/printable page.

- [x] **Task 8.24:** Create `templates/admin/reports/_print_shift.html`
  (partial). Renders the shift header, financial summary, and full sessions
  table for the selected shift.

### 8l — Tailwind Rebuild

- [x] **Task 8.25:** Run `make css` to rebuild `static/css/tailwind.min.css`
  including all new admin template classes. Verify the built file is under
  300KB (admin templates add more classes than operator templates). Update
  `tailwind.config.js` to include `"templates/admin/**/*.html"` in the
  `content` array if not already present. Mark complete only after a successful
  build with no purge warnings.

---

## Group 9 — Unit Tests

### 9a — Cairo Time Utils Tests (extended)

- [x] **Task 9.1:** Open `tests/unit/test_time_utils.py` (created in Task 2.2).
  Add the following tests:
  - `test_cairo_date_to_utc_end_is_next_midnight`: `cairo_date_to_utc_end(
    date(2024, 8, 15))` equals `cairo_date_to_utc_start(date(2024, 8, 16))`.
  - `test_utc_to_cairo_midnight_crossing`: UTC `2024-08-15 23:30` → Cairo
    `2024-08-16 01:30` (next calendar day).
  - `test_cairo_date_str_midnight_utc`: UTC `2024-08-15 22:00:00` → `"2024-08-16"`.

### 9b — ReportService Unit Tests

- [x] **Task 9.2:** Create `tests/unit/test_report_service.py`. Define a
  `MockReportRepo` class (plain Python, no DB) that returns hardcoded values
  for all repo methods. Instantiate
  `service = ReportService(db=None, report_repo=MockReportRepo())`.

  Write test `test_get_live_stats_success`: mock returns `active=3`,
  `capacity=10`, `revenue=5000`, `open_shifts=2`. Asserts
  `stats.active_sessions == 3`, `stats.occupancy_pct == 30`,
  `stats.revenue_today_piastres == 5000`.

- [x] **Task 9.3:** Write test `test_get_live_stats_exception_fallback`: mock
  raises `Exception` for `count_open_shifts`. Asserts no exception propagates
  to the caller and `stats.open_shifts == 0`.

- [x] **Task 9.4:** Write test `test_get_daily_revenue_fills_missing_days`:
  mock `get_daily_revenue_raw` returns only `[{"cairo_date": "2024-08-15",
  "session_count": 3, "total_piastres": 3000}]`. Call `get_daily_revenue`
  with `filters` spanning `2024-08-14` to `2024-08-16`. Asserts result has
  3 items. Asserts `2024-08-14` has `session_count=0` and
  `total_piastres=0`. Asserts `2024-08-15` has correct values.

- [x] **Task 9.5:** Write test `test_revenue_summary_no_floats`: mock returns
  `total_sessions=3`, `total_revenue=7777`, `total_duration=100`. Asserts all
  fields of `RevenueSummaryResponse` are of type `int` (use `isinstance`).

- [x] **Task 9.6:** Write test `test_revenue_summary_zero_sessions_no_div_error`:
  mock returns `total_sessions=0`, `total_revenue=0`, `total_duration=0`.
  Asserts `avg_duration_minutes=0` and `avg_revenue_piastres=0` (no
  `ZeroDivisionError`).

- [x] **Task 9.7:** Write test `test_gate_panel_fills_missing_gates`: mock
  `get_gate_panel` returns data for gates 1, 3, 5 only. Asserts returned list
  has exactly 5 items. Asserts gates 2 and 4 have `operator_name=None` and
  `active_sessions=0`.

- [x] **Task 9.8:** Write test `test_get_alert_counts_both_succeed`: mock returns
  `long_stay=2`, `overdue=1`. Asserts `{"long_stay": 2, "overdue_shifts": 1}`.

### 9c — ReportFilters Validation Tests

- [x] **Task 9.9:** Create `tests/unit/test_report_filters.py`. Write tests:
  - `test_valid_filters`: constructs `ReportFilters(start_date=date(2024,1,1),
    end_date=date(2024,1,31))`. Asserts no exception.
  - `test_invalid_date_range_raises`: `start_date=date(2024,2,1),
    end_date=date(2024,1,1)`. Asserts `ValidationError` is raised.
  - `test_same_start_end_date_valid`: `start_date == end_date`. Asserts valid.
  - `test_gate_number_out_of_range`: `gate_number=6`. Asserts `ValidationError`.
  - `test_gate_number_zero`: `gate_number=0`. Asserts `ValidationError`.
  - `test_card_code_too_long`: `card_code="A" * 51`. Asserts `ValidationError`.
  - `test_all_none_is_valid`: `ReportFilters()` with no params. Asserts valid.

- [x] **Task 9.10:** Create `tests/unit/test_shift_filters.py`. Write tests:
  - `test_valid_shift_filters`: `ShiftFilters(status="open", gate_number=3)`.
    Asserts valid.
  - `test_invalid_status`: `ShiftFilters(status="pending")`. Asserts
    `ValidationError`.
  - `test_invalid_date_range`: `start_date > end_date`. Asserts `ValidationError`.
  - `test_overdue_default_false`: `ShiftFilters()`. Asserts `overdue=False`.

### 9d — Jinja2 Filter Unit Tests

- [x] **Task 9.11:** Create `tests/unit/test_admin_filters.py`. Write tests for
  `discrepancy_class_filter`:
  - `test_zero_discrepancy` → `"text-green-600"`.
  - `test_none_discrepancy` → `"text-gray-400"`.
  - `test_small_discrepancy_within_5pct`: `discrepancy=50, computed_total=1000`
    (5%) → `"text-amber-500"`.
  - `test_large_discrepancy`: `discrepancy=200, computed_total=1000` (20%) →
    `"text-red-600"`.
  - `test_zero_computed_total_no_div_error`: `discrepancy=100, computed_total=0`
    → `"text-red-600"` (not a ZeroDivisionError).

- [x] **Task 9.12:** In `tests/unit/test_admin_filters.py`, write tests for
  `session_status_label_filter`:
  - `"ACTIVE"` → `"داخل"`.
  - `"COMPLETED"` → `"خرج"`.
  - `"LOST_CARD"` → `"كرت مفقود"`.
  - `"UNKNOWN"` → `"UNKNOWN"` (passthrough).

- [x] **Task 9.13:** In `tests/unit/test_admin_filters.py`, write tests for
  `shift_status_label_filter`:
  - `None` → `"مفتوح"`.
  - `datetime(2024, 1, 1)` → `"مغلق"`.

- [x] **Task 9.14:** In `tests/unit/test_admin_filters.py`, write tests for
  `cairo_date_filter`:
  - `None` → `"—"`.
  - `datetime(2024, 8, 15, 23, 0, 0)` (UTC) → `"2024-08-16"` (Cairo next day).

### 9e — PricingRuleCreate Schema Tests

- [x] **Task 9.15:** Create `tests/unit/test_pricing_rule_schema.py`. Write tests:
  - `test_egp_converted_to_piastres`: `PricingRuleCreate(
    rate_per_hour_egp=10.0, ...)`. Asserts `rate_per_hour == 1000`.
  - `test_fractional_egp_rounded`: `rate_per_hour_egp=5.555`. Asserts
    `rate_per_hour == 556`.
  - `test_zero_rate_valid`: `rate_per_hour_egp=0.0`. Asserts no error and
    `rate_per_hour == 0`.
  - `test_negative_rate_invalid`: `rate_per_hour_egp=-1.0`. Asserts
    `ValidationError`.
  - `test_lost_card_penalty_conversion`: `lost_card_penalty_egp=25.50`. Asserts
    `lost_card_penalty == 2550`.

### 9f — CSV Export Unit Tests

- [x] **Task 9.16:** Create `tests/unit/test_csv_export.py`. Write tests for
  `_piastres_to_egp_str`:
  - `None` → `""`.
  - `0` → `"0.00"`.
  - `2550` → `"25.50"`.
  - `100` → `"1.00"`.

- [x] **Task 9.17:** In `tests/unit/test_csv_export.py`, write an async test
  for `generate_sessions_csv`:
```python
  async def test_csv_starts_with_bom():
```
  Creates a mock async iterator of one `SimpleNamespace` session object.
  Collects all yielded strings from the generator. Asserts the first yielded
  string equals `"\ufeff"`.

- [x] **Task 9.18:** In `tests/unit/test_csv_export.py`, write test:
```python
  async def test_csv_header_row_is_arabic():
```
  Collects CSV output. Asserts the second yielded chunk contains `"رقم الجلسة"`.

- [x] **Task 9.19:** In `tests/unit/test_csv_export.py`, write test:
```python
  async def test_none_values_render_as_empty_string():
```
  Creates a session with `plate_number=None` and `amount_charged=None`. Asserts
  the data row does not contain the strings `"None"` or `"null"`.

---

## Group 10 — Integration Tests & End-to-End Verification

### 10a — Admin API Auth Tests

- [x] **Task 10.1:** Create `tests/integration/test_admin_auth.py`. Write tests:
  - `test_admin_stats_requires_auth` (async): GET `/api/v1/admin/stats/live`
    with no cookie. Asserts `401`.
  - `test_admin_stats_requires_admin_role` (async): log in as operator, GET
    `/api/v1/admin/stats/live`. Asserts `403` and `code ==
    "INSUFFICIENT_PERMISSIONS"`.
  - `test_admin_stats_succeeds_as_admin` (async): log in as admin. Asserts `200`.
  - `test_all_admin_routes_reject_operator`: parametrize a list of at least 8
    admin route paths (`GET /api/v1/admin/sessions`,
    `GET /api/v1/admin/shifts`, `GET /api/v1/admin/reports/revenue`, etc.).
    For each, assert operator gets `403`.

### 10b — Live Stats API Tests

- [x] **Task 10.2:** Create `tests/integration/test_admin_stats.py`. Write tests:
  - `test_live_stats_empty_db` (async): fresh DB. Asserts all counts are `0`,
    `occupancy_pct == 0`, `revenue_today_piastres == 0`.
  - `test_live_stats_with_active_sessions` (async): seeds 3 ACTIVE sessions.
    Asserts `active_sessions == 3`.
  - `test_live_stats_revenue_today` (async): seeds 2 COMPLETED sessions with
    `amount_charged=2500` each and `exit_time=utcnow()`. Asserts
    `revenue_today_piastres == 5000`.
  - `test_live_stats_revenue_excludes_yesterday` (async): seeds a COMPLETED
    session with `exit_time=utcnow() - timedelta(hours=25)`. Asserts it is not
    included in `revenue_today_piastres`.
  - `test_gate_panel_endpoint` (async): seeds one open shift for gate 2. GET
    `/api/v1/admin/stats/gates`. Asserts gate 2 has `operator_name` populated.
    Asserts other gates have `operator_name=null`.

### 10c — Report Filtering Tests

- [x] **Task 10.3:** Create `tests/integration/test_report_filters.py`. Write tests:
  - `test_session_filter_by_date_range` (async): seeds 3 sessions — one
    yesterday, one today, one tomorrow. Filters with `start_date=today&
    end_date=today`. Asserts `total == 1`.
  - `test_session_filter_by_gate` (async): seeds sessions on gates 1 and 2.
    Filters `gate_number=1`. Asserts only gate 1 sessions returned.
  - `test_session_filter_by_status_active` (async): seeds 2 ACTIVE, 1
    COMPLETED. Filters `status=ACTIVE`. Asserts `total == 2`.
  - `test_session_filter_by_card_code_partial` (async): seeds card `"CARD-0042"`.
    Filters `card_code=0042`. Asserts session returned (partial LIKE match).
  - `test_session_filter_card_code_sql_injection_safe` (async): filters
    `card_code=%`. Asserts no SQL error and returns empty result (literal `%`
    not treated as wildcard).
  - `test_session_filter_long_stay` (async): seeds one ACTIVE session with
    `entry_time = utcnow() - timedelta(hours=25)` and one recent ACTIVE session.
    Filters `long_stay=true`. Asserts only the old session returned.
  - `test_invalid_date_range_returns_422` (async): GET `/api/v1/admin/sessions?
    start_date=2024-08-31&end_date=2024-08-01`. Asserts `422` and `code ==
    "INVALID_DATE_RANGE"`.

### 10d — Revenue Report Tests

- [x] **Task 10.4:** Create `tests/integration/test_revenue_report.py`. Write tests:
  - `test_revenue_summary_correct_totals` (async): seeds 3 COMPLETED sessions
    with `amount_charged=1000` each and `duration_minutes=30` each. GET
    `/api/v1/admin/reports/revenue`. Asserts `total_revenue_piastres == 3000`,
    `avg_duration_minutes == 30`.
  - `test_revenue_excludes_active_sessions` (async): seeds 1 ACTIVE session
    with `amount_charged=NULL`. Asserts it is excluded from revenue totals.
  - `test_daily_revenue_fills_empty_days` (async): seeds sessions on day 1 and
    day 3 of a 3-day range. GET with `start_date` and `end_date` spanning all
    3 days. Asserts the `daily` array has 3 items. Asserts day 2 has
    `session_count=0`.
  - `test_revenue_by_gate_groups_correctly` (async): seeds 2 sessions on gate
    1 and 1 session on gate 2. Asserts `by_gate` has 2 entries with correct
    counts.

### 10e — Shift Admin Tests

- [x] **Task 10.5:** Create `tests/integration/test_admin_shifts.py`. Write tests:
  - `test_list_shifts_paginated` (async): seeds 25 shifts. GET
    `/api/v1/admin/shifts`. Asserts `total == 25` and `len(data) == 20`
    (default page size).
  - `test_filter_shifts_by_status_open` (async): seeds 2 open and 3 closed
    shifts. Filters `status=open`. Asserts `total == 2`.
  - `test_filter_shifts_overdue` (async): seeds 1 shift with `started_at =
    utcnow() - timedelta(hours=13)` (ended_at NULL) and 1 recent open shift.
    Filters `overdue=true`. Asserts only the old shift returned.
  - `test_force_close_shift_success` (async): seeds open shift. PATCH
    `/api/v1/admin/shifts/{id}/force-close` with `closing_cash_egp=50000`.
    Asserts `200`, shift `ended_at` is not null in DB.
  - `test_force_close_already_closed_returns_409` (async): seeds closed shift.
    Asserts `409` and `code == "SHIFT_ALREADY_CLOSED"`.
  - `test_force_close_creates_audit_log` (async): force-closes a shift. Queries
    `audit_logs` for `action="SHIFT_FORCE_CLOSED"`. Asserts one record exists.
  - `test_shift_export_csv_returns_bom` (async): seeds shift with 3 sessions.
    GET `/api/v1/admin/shifts/{id}/export/csv`. Reads first bytes of response.
    Asserts BOM `"\ufeff"` is present.

### 10f — Pricing Admin Tests

- [x] **Task 10.6:** Create `tests/integration/test_admin_rates.py`. Write tests:
  - `test_create_pricing_rule` (async): POST `/api/v1/rates/` with valid data
    (`rate_per_hour_egp=10.0`, `grace_period_mins=15`, etc.). Asserts `201` and
    `data.rate_per_hour == 1000` (converted to piastres).
  - `test_create_duplicate_label_returns_409` (async): creates rule with label
    "Test", creates again with same label. Asserts `409` and `code ==
    "RATE_LABEL_ALREADY_EXISTS"`.
  - `test_activate_rule` (async): creates 2 rules, activates rule 2. GET
    `/api/v1/rates/active`. Asserts `data.id == rule2.id`.
  - `test_activate_already_active_is_idempotent` (async): activates the active
    rule again. Asserts `200` and no error.
  - `test_fractional_egp_stored_as_piastres` (async): creates rule with
    `rate_per_hour_egp=5.555`. Queries DB directly. Asserts `rate_per_hour ==
    556`.

### 10g — CSV Export Tests

- [x] **Task 10.7:** Create `tests/integration/test_csv_export_routes.py`. Write:
  - `test_sessions_csv_content_type` (async): seeds 2 sessions. GET
    `/api/v1/admin/sessions/export/csv`. Asserts `Content-Type` header contains
    `text/csv`.
  - `test_sessions_csv_has_bom` (async): reads first 3 bytes of response.
    Asserts they equal `b"\xef\xbb\xbf"` (UTF-8 BOM).
  - `test_sessions_csv_header_in_arabic` (async): reads first 500 bytes. Asserts
    `"رقم الجلسة"` in decoded content.
  - `test_sessions_csv_empty_filter_returns_header_only` (async): GET with
    `start_date=1900-01-01&end_date=1900-01-02`. Asserts response is valid CSV
    with only BOM + header row. No data rows.
  - `test_sessions_csv_none_values_no_null_string` (async): seeds session with
    `plate_number=None`. Asserts decoded CSV does not contain `"None"`.
  - `test_sessions_csv_monetary_latin_digits` (async): seeds session with
    `amount_charged=2500`. Asserts decoded CSV contains `"25.00"` (Latin,
    not Arabic-Indic).

### 10h — Admin UI Route Tests

- [x] **Task 10.8:** Create `tests/integration/test_ui_admin_routes.py`. Write:
  - `test_dashboard_requires_admin` (async): GET `/ui/admin/dashboard` as
    operator. Asserts `303` redirect to `/ui/login?next=/ui/admin/dashboard`.
  - `test_dashboard_renders_as_admin` (async): GET as admin. Asserts `200`
    and `"لوحة التحكم"` in body.
  - `test_shifts_page_renders` (async): GET `/ui/admin/shifts`. Asserts `200`.
  - `test_sessions_page_renders` (async): GET `/ui/admin/sessions`. Asserts
    `200` and `"دخول وخروج"` in body.
  - `test_cards_page_renders` (async): GET `/ui/admin/cards`. Asserts `200`.
  - `test_admin_override_close_session` (async): POST
    `/api/v1/admin/sessions/{id}/override-close`. Asserts `200` and session status updated.
  - `test_revenue_report_renders` (async): GET `/ui/admin/reports/revenue`.
    Asserts `200` and `"تقرير الإيراد"` in body.
  - `test_print_view_shift_missing_shift_id` (async): GET
    `/ui/admin/reports/print?report_type=shift` (no `shift_id`). Asserts `422`.
  - `test_print_view_invalid_report_type` (async): GET
    `/ui/admin/reports/print?report_type=unknown`. Asserts `422`.
  - `test_print_view_sessions_renders` (async): seeds 2 sessions. GET
    `/ui/admin/reports/print?report_type=sessions`. Asserts `200` and
    `"window.print()"` in body.
  - `test_print_view_shift_renders` (async): seeds a shift. GET
    `/ui/admin/reports/print?report_type=shift&shift_id={id}`. Asserts `200`.
  - `test_rates_page_renders` (async): GET `/ui/admin/rates`. Asserts `200`
    and `"التعريفات السعرية"` in body.
  - `test_operators_page_renders` (async): GET `/ui/admin/operators`. Asserts
    `200`.
  - `test_dashboard_long_stay_banner_shown` (async): seeds ACTIVE session with
    `entry_time = utcnow() - timedelta(hours=25)`. GET dashboard. Asserts amber
    alert banner text appears in body.
  - `test_dashboard_no_banner_when_no_long_stay` (async): no long-stay sessions.
    GET dashboard. Asserts long-stay banner `div` is absent from body.

### 10i — Coverage & Quality Gate

- [x] **Task 10.9:** Run `pytest --cov=services/report_service
  --cov=utils/time --cov=utils/csv_export --cov-report=term-missing`.
  Confirm:
  - `services/report_service.py`: ≥ 95% coverage.
  - `utils/time.py`: 100% coverage.
  - `utils/csv_export.py`: ≥ 90% coverage.
  Fix any coverage gaps. Do not mark complete with any critical branch uncovered.

- [x] **Task 10.10:** Run `pytest --cov=repositories/report_repo
  --cov=repositories/admin_shift_repo --cov-report=term-missing`.
  Confirm ≥ 85% coverage on both repository files. The 15% tolerance allows for
  dialect-specific SQL branches that cannot be exercised in SQLite-only tests.

- [x] **Task 10.11:** Run `black . && ruff check . && mypy .` on the entire
  project. Fix all formatting, lint, and type errors. Zero issues must remain.
  Do not mark complete with any tool reporting warnings or errors.

- [x] **Task 10.12:** Run `make css` to rebuild Tailwind. Verify
  `static/css/tailwind.min.css` rebuilds successfully. Verify
  `tailwind.config.js` content array includes both `"templates/operator/**/*.html"`
  and `"templates/admin/**/*.html"`. Commit the rebuilt CSS file.

- [x] **Task 10.13:** Perform manual QA for Phase 3. Open a browser and verify:
  - [x] Admin dashboard loads and all 4 KPI cards show values.
  - [x] KPI cards update after 30 seconds without page reload.
  - [x] Long-stay alert banner appears when seeded appropriately.
  - [x] Shift list page filters by date range correctly.
  - [x] Shift detail page shows correct discrepancy in red/amber/green.
  - [x] Force-close modal submits and reloads correctly.
  - [x] Revenue report shows correct totals for a seeded date range.
  - [x] Daily revenue table has one row per day with zero-filled gaps.
  - [x] Session CSV export opens correctly in Excel with Arabic headers visible.
  - [x] A4 print view triggers `window.print()` on load.
  - [x] A4 print view "رجوع" link is visible on screen, hidden when printing.
  - [x] Rates page inline form creates a new rule without page reload.
  - [x] Activating a rate updates badges in the table without page reload.
  - [x] Sidebar collapse state persists across page navigations.
  - [x] All admin pages redirect to login when accessed as operator.
  Record QA results in `QA_LOG.md` with date and tester name.
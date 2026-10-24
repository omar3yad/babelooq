# Phase 4 — Atomic Coding Task Checklist

> **Version:** 1.0
> **Scope:** All coding tasks required to complete Phase 4 as specified in
> `docs/specs/phase-4-subscriptions/spec.md`.
> **Execution order is mandatory within each group.** Complete all tasks in a
> group before starting the next group.
> **Each task is atomic:** one file, one class, one method, or one migration
> block per task.
> **All code must pass:** `black`, `ruff`, and `mypy --strict` before any
> task is marked complete.

---

## Group 1 — Database Models

### 1a — Enums

- [x] **Task 1.1:** Create `models/subscription.py`. Define a
  `SubscriptionStatus` Python `enum.Enum` with exactly four values:
  `ACTIVE = "ACTIVE"`, `EXPIRED = "EXPIRED"`, `CANCELLED = "CANCELLED"`,
  `PENDING = "PENDING"`. Add `__all__ = ["SubscriptionStatus"]`. No other
  code in this task.

### 1b — SubscriptionPlan Model

- [x] **Task 1.2:** Create `models/subscription_plan.py`. Import `Base` from
  `database` and `TimestampMixin` from `models/mixins.py`. Define the
  `SubscriptionPlan` class inheriting from `Base` and `TimestampMixin`.
  Set `__tablename__ = "subscription_plans"`. Add these columns only:
  - `id: Mapped[int]` — primary key, autoincrement.
  - `label: Mapped[str]` — `VARCHAR(100)`, unique, not nullable, indexed.
  - `duration_days: Mapped[int]` — `SMALLINT`, not nullable.

- [x] **Task 1.3:** In `models/subscription_plan.py`, add remaining columns
  to `SubscriptionPlan`:
  - `price_piastres: Mapped[int]` — `INTEGER`, not nullable. Stored in
    piastres. Never a float.
  - `max_entries_per_day: Mapped[int | None]` — `SMALLINT`, nullable.
    `NULL` means unlimited.
  - `description: Mapped[str | None]` — `TEXT`, nullable.
  - `is_active: Mapped[bool]` — `BOOLEAN`, not nullable,
    `server_default="1"`.
  - `created_by: Mapped[int]` — `INTEGER`, FK → `users.id`, not nullable.
  Add `__all__ = ["SubscriptionPlan"]`.

### 1c — Subscriber Model

- [x] **Task 1.4:** Create `models/subscriber.py`. Import `Base` and
  `TimestampMixin`. Define the `Subscriber` class inheriting from both.
  Set `__tablename__ = "subscribers"`. Add these columns only:
  - `id: Mapped[int]` — primary key, autoincrement.
  - `full_name: Mapped[str]` — `VARCHAR(120)`, not nullable.
  - `phone_number: Mapped[str | None]` — `VARCHAR(20)`, nullable.

- [x] **Task 1.5:** In `models/subscriber.py`, add remaining columns:
  - `plate_number: Mapped[str]` — `VARCHAR(30)`, unique, not nullable,
    indexed.
  - `company_name: Mapped[str | None]` — `VARCHAR(150)`, nullable, indexed.
  - `card_code: Mapped[str | None]` — `VARCHAR(50)`, unique, nullable, indexed.
  - `notes: Mapped[str | None]` — `TEXT`, nullable.
  Add `__all__ = ["Subscriber"]`.

### 1d — Subscription Model

- [x] **Task 1.6:** In `models/subscription.py`, add imports for `Base`,
  `TimestampMixin`, and `SubscriptionStatus`. Define the `Subscription`
  class inheriting from `Base` and `TimestampMixin`.
  Set `__tablename__ = "subscriptions"`. Add these columns only:
  - `id: Mapped[int]` — primary key, autoincrement.
  - `subscriber_id: Mapped[int]` — `INTEGER`, FK → `subscribers.id`,
    not nullable, indexed.
  - `plan_id: Mapped[int]` — `INTEGER`, FK → `subscription_plans.id`,
    not nullable.
  - `card_id: Mapped[int]` — `INTEGER`, FK → `parking_cards.id`,
    not nullable, indexed.

- [x] **Task 1.7:** In `models/subscription.py`, add these columns to
  `Subscription`:
  - `plate_number: Mapped[str]` — `VARCHAR(30)`, not nullable. Snapshot
    at creation time.
  - `start_date: Mapped[date]` — `DATE`, not nullable.
  - `end_date: Mapped[date]` — `DATE`, not nullable, indexed.
  - `status: Mapped[SubscriptionStatus]` — `SQLAlchemy Enum(SubscriptionStatus)`,
    not nullable, `server_default="ACTIVE"`, indexed.

- [x] **Task 1.8:** In `models/subscription.py`, add these columns to
  `Subscription`:
  - `amount_paid_piastres: Mapped[int]` — `INTEGER`, not nullable.
  - `plan_price_snapshot: Mapped[int]` — `INTEGER`, not nullable. Snapshot
    of `plan.price_piastres` at subscription creation time.
  - `paid_at: Mapped[datetime | None]` — `TIMESTAMP`, nullable.
  - `collected_by: Mapped[int | None]` — `INTEGER`, FK → `users.id`,
    nullable.
  - `renewal_count: Mapped[int]` — `SMALLINT`, not nullable,
    `server_default="0"`.

- [x] **Task 1.9:** In `models/subscription.py`, add final columns to
  `Subscription`:
  - `previous_subscription_id: Mapped[int | None]` — `INTEGER`,
    FK → `subscriptions.id`, nullable. Self-referential for renewal chain.
  - `cancel_reason: Mapped[str | None]` — `TEXT`, nullable.
  - `ended_at: Mapped[datetime | None]` — `TIMESTAMP`, nullable.
  - `notes: Mapped[str | None]` — `TEXT`, nullable.
  Update `__all__ = ["SubscriptionStatus", "Subscription"]`.

### 1e — ParkingSession Model Additions

- [x] **Task 1.10:** Open `models/parking_session.py`. Add two new columns
  to the `ParkingSession` class. Do not alter any existing column:
  - `subscription_id: Mapped[int | None]` — `INTEGER`,
    FK → `subscriptions.id`, nullable.
  - `is_subscribed: Mapped[bool]` — `BOOLEAN`, not nullable,
    `server_default="0"`.
  Update `__all__` to include any new exports if needed.

### 1f — Models `__init__.py`

- [x] **Task 1.11:** Update `models/__init__.py` to import and re-export:
  `SubscriptionPlan`, `Subscriber`, `SubscriptionStatus`, `Subscription`.
  Add all four to `__all__`. Verify all previously exported names are still
  present. Do not remove any existing export.

---

## Group 2 — Alembic Migrations

- [x] **Task 2.1:** Generate a new Alembic migration by running:
  `alembic revision --autogenerate -m "phase4_subscriptions_initial"`.
  Open the generated file. Verify `upgrade()` creates tables in this exact
  order:
  1. `subscription_plans` — all columns, unique index on `label`.
  2. `subscribers` — all columns, unique index on `plate_number`.
  3. `subscriptions` — all columns, FK constraints, indexes on
     `subscriber_id`, `card_id`, `status`, `end_date`.
  Verify `downgrade()` drops all three tables in reverse order.
  Commit the migration file. Do not edit any logic.

- [x] **Task 2.2:** Generate a second migration manually with message
  `"phase4_parking_session_subscription_columns"`. In `upgrade()`:
  1. `op.add_column('parking_sessions', Column('subscription_id', Integer,
     ForeignKey('subscriptions.id'), nullable=True))`.
  2. `op.add_column('parking_sessions', Column('is_subscribed', Boolean,
     nullable=False, server_default='0'))`.
  3. `op.create_index('ix_parking_sessions_subscription_id',
     'parking_sessions', ['subscription_id'])`.
  In `downgrade()`: drop the index, then drop both columns. Commit.

- [x] **Task 2.3:** Generate a third migration manually with message
  `"phase4_subscriptions_check_constraint"`. In `upgrade()`, add a CHECK
  constraint to `parking_sessions`:
```python
  op.create_check_constraint(
      "ck_sessions_subscribed_zero_charge",
      "parking_sessions",
      "is_subscribed = 0 OR is_subscribed = FALSE OR amount_charged = 0 "
      "OR amount_charged IS NULL"
  )
```
  In `downgrade()`: drop the constraint by name. Commit.

- [x] **Task 2.4:** Generate a fourth migration manually with message
  `"phase4_subscriptions_performance_indexes"`. In `upgrade()`, add:
  - `ix_subscriptions_subscriber_id_status` on
    `subscriptions(subscriber_id, status)`.
  - `ix_subscriptions_card_id_status` on `subscriptions(card_id, status)`.
  - `ix_subscriptions_end_date_status` on `subscriptions(end_date, status)`.
  - `ix_subscribers_plate_number` — verify it was created in Task 2.1; skip
    if exists using `if_not_exists=True` or an existence check.
  In `downgrade()`: drop all added indexes. Commit.

- [x] **Task 2.5:** Run `alembic upgrade head` against the local SQLite dev
  database. Confirm all tables, columns, indexes, and the CHECK constraint
  exist. Fix any migration errors. Delete any `test_verify.db` artifact.
  Commit no source changes in this task.

---

## Group 3 — Pydantic Schemas

- [x] **Task 3.1:** Create `schemas/subscriptions.py`. Add at the top:
  imports from `pydantic` (`BaseModel`, `ConfigDict`, `Field`,
  `model_validator`, `computed_field`), from `datetime` (`date`, `datetime`),
  and `SubscriptionStatus` from `models`. Define:

```python
  class PlanCreate(BaseModel):
      label: str = Field(min_length=1, max_length=100)
      duration_days: int = Field(ge=1)
      price_egp: float = Field(ge=0)
      max_entries_per_day: int | None = Field(None, ge=1)
      description: str | None = None

      @model_validator(mode="after")
      def convert_price(self) -> "PlanCreate":
          self._price_piastres = round(self.price_egp * 100)
          return self

      @property
      def price_piastres(self) -> int:
          return round(self.price_egp * 100)
```

- [x] **Task 3.2:** In `schemas/subscriptions.py`, define:

```python
  class PlanUpdate(BaseModel):
      label: str | None = Field(None, min_length=1, max_length=100)
      price_egp: float | None = Field(None, ge=0)
      description: str | None = None
      max_entries_per_day: int | None = Field(None, ge=1)
      # duration_days intentionally excluded — immutable after creation
```

```python
  class PlanResponse(BaseModel):
      model_config = ConfigDict(from_attributes=True)
      id: int
      label: str
      duration_days: int
      price_piastres: int
      max_entries_per_day: int | None
      description: str | None
      is_active: bool
      created_by: int
      created_at: datetime
      updated_at: datetime
```

- [x] **Task 3.3:** In `schemas/subscriptions.py`, define:

```python
  class SubscriberCreate(BaseModel):
      full_name: str = Field(min_length=1, max_length=120)
      plate_number: str = Field(min_length=1, max_length=30)
      phone_number: str | None = Field(None, max_length=20)
      notes: str | None = None
```

```python
  class SubscriberUpdate(BaseModel):
      full_name: str | None = Field(None, min_length=1, max_length=120)
      phone_number: str | None = Field(None, max_length=20)
      company_name: str | None = Field(None, max_length=150)
      card_code: str | None = Field(None, max_length=50)
      notes: str | None = None
      # plate_number intentionally excluded — immutable after creation
```

- [x] **Task 3.4:** In `schemas/subscriptions.py`, define:

```python
  class SubscriptionCreate(BaseModel):
      subscriber_id: int
      plan_id: int | None = None
      card_id: int | None = None
      card_code: str | None = None
      duration_days: int | None = Field(None, ge=1)
      start_date: date
      end_date: date | None = None
      amount_paid_egp: float = Field(ge=0)
      notes: str | None = None

      @property
      def amount_paid_piastres(self) -> int:
          return round(self.amount_paid_egp * 100)
```

```python
  class SubscriptionRenewRequest(BaseModel):
      amount_paid_egp: float = Field(ge=0)
      notes: str | None = None

      @property
      def amount_paid_piastres(self) -> int:
          return round(self.amount_paid_egp * 100)
```

```python
  class SubscriptionCancelRequest(BaseModel):
      cancel_reason: str | None = Field(None, max_length=500)
```

- [x] **Task 3.5:** In `schemas/subscriptions.py`, define:

```python
  class SubscriptionResponse(BaseModel):
      model_config = ConfigDict(from_attributes=True)
      id: int
      subscriber_id: int
      plan_id: int
      card_id: int
      plate_number: str
      start_date: date
      end_date: date
      status: SubscriptionStatus
      amount_paid_piastres: int
      plan_price_snapshot: int
      paid_at: datetime | None
      collected_by: int | None
      renewal_count: int
      previous_subscription_id: int | None
      cancel_reason: str | None
      ended_at: datetime | None
      notes: str | None
      created_at: datetime

      @computed_field
      @property
      def days_remaining(self) -> int:
          from utils.time import cairo_now
          remaining = (self.end_date - cairo_now().date()).days
          return max(remaining, 0)
```

- [x] **Task 3.6:** In `schemas/subscriptions.py`, define:

```python
  class SubscriberResponse(BaseModel):
      model_config = ConfigDict(from_attributes=True)
      id: int
      full_name: str
      phone_number: str | None
      plate_number: str
      notes: str | None
      created_at: datetime
      updated_at: datetime
      active_subscription: SubscriptionResponse | None = None
```

```python
  class PlanRevenueResponse(BaseModel):
      plan_id: int
      plan_label: str
      subscription_count: int
      total_piastres: int
```

```python
  class SubscriptionRevenueSummary(BaseModel):
      total_subscriptions: int
      total_revenue_piastres: int
      avg_revenue_piastres: int
      by_plan: list[PlanRevenueResponse]
```

```python
  class SubscriptionDashboardStats(BaseModel):
      expiring_soon_count: int
      expired_unrenewed_count: int
      active_subscriptions_count: int
```

- [x] **Task 3.7:** Update `schemas/__init__.py` to import and re-export
  all names from `schemas/subscriptions.py`. Add all new schema class names
  to `__all__`. Verify no circular imports by running
  `python -c "from schemas import *"`.

---

## Group 4 — Repositories

### 4a — SubscriptionPlan Repository

- [x] **Task 4.1:** Create `repositories/subscription_plan_repo.py`. Define a
  `SubscriptionPlanRepository` class with `__init__(self, db: AsyncSession)`.
  Add method:
```python
  async def get_by_id(self, plan_id: int) -> SubscriptionPlan | None
```
  `SELECT * FROM subscription_plans WHERE id = :id LIMIT 1`. Returns the
  plan or `None`.

- [x] **Task 4.2:** In `repositories/subscription_plan_repo.py`, add method:
```python
  async def get_by_label(self, label: str) -> SubscriptionPlan | None
```
  `SELECT * FROM subscription_plans WHERE label = :label LIMIT 1`. Returns
  plan or `None`. Used for duplicate label check.

- [x] **Task 4.3:** In `repositories/subscription_plan_repo.py`, add method:
```python
  async def get_all(
      self,
      active_only: bool = False,
  ) -> list[SubscriptionPlan]
```
  Builds `select(SubscriptionPlan)`. Applies `WHERE is_active = TRUE` if
  `active_only=True`. Orders by `price_piastres ASC`. Returns full list
  (no pagination — plan count is bounded and small).

- [x] **Task 4.4:** In `repositories/subscription_plan_repo.py`, add method:
```python
  async def create(
      self,
      label: str,
      duration_days: int,
      price_piastres: int,
      max_entries_per_day: int | None,
      description: str | None,
      created_by: int,
  ) -> SubscriptionPlan
```
  Creates `SubscriptionPlan(...)` with `is_active=True`. Adds to session,
  flushes. Does not commit. Returns the plan.

- [x] **Task 4.5:** In `repositories/subscription_plan_repo.py`, add method:
```python
  async def update_fields(
      self, plan: SubscriptionPlan, **fields
  ) -> SubscriptionPlan
```
  Sets each key-value pair in `fields` as an attribute on `plan`. Flushes.
  Does not commit. Returns the updated plan. Add
  `__all__ = ["SubscriptionPlanRepository"]`.

### 4b — Subscriber Repository

- [x] **Task 4.6:** Create `repositories/subscriber_repo.py`. Define a
  `SubscriberRepository` class with `__init__(self, db: AsyncSession)`.
  Add method:
```python
  async def get_by_id(self, subscriber_id: int) -> Subscriber | None
```
  `SELECT * WHERE id = :id`. Returns subscriber or `None`.

- [x] **Task 4.7:** In `repositories/subscriber_repo.py`, add method:
```python
  async def get_by_plate(self, plate_normalized: str) -> Subscriber | None
```
  `SELECT * WHERE plate_number = :plate LIMIT 1`. Returns subscriber or
  `None`. Caller must normalize the plate before calling this method.

- [x] **Task 4.8:** In `repositories/subscriber_repo.py`, add method:
```python
  async def create(
      self,
      full_name: str,
      plate_number: str,
      phone_number: str | None,
      notes: str | None,
  ) -> Subscriber
```
  Creates `Subscriber(...)`. Adds, flushes. Does not commit. Returns the
  subscriber.

- [x] **Task 4.9:** In `repositories/subscriber_repo.py`, add method:
```python
  async def update_fields(
      self, subscriber: Subscriber, **fields
  ) -> Subscriber
```
  Sets each key-value pair as attribute. Flushes. Does not commit.

- [x] **Task 4.10:** In `repositories/subscriber_repo.py`, add method:
```python
  async def get_filtered(
      self,
      search: str | None,
      plan_id: int | None,
      page: int,
      size: int,
  ) -> tuple[list[Subscriber], int]
```
  Builds `select(Subscriber)`. Applies `ILIKE '%:search%'` on both
  `full_name` and `plate_number` (joined with `OR`) when `search` is not
  `None`. For SQLite uses `LIKE` (case-insensitive via `func.lower`). Does
  not filter by subscription status here — that join is handled by the service.
  Returns `(subscribers, total_count)` with `LIMIT/OFFSET`. Add
  `__all__ = ["SubscriberRepository"]`.

### 4c — Subscription Repository

- [x] **Task 4.11:** Create `repositories/subscription_repo.py`. Define a
  `SubscriptionRepository` class with `__init__(self, db: AsyncSession)`.
  Add method:
```python
  async def get_by_id(self, subscription_id: int) -> Subscription | None
```
  `SELECT * WHERE id = :id`. Returns subscription or `None`.

- [x] **Task 4.12:** In `repositories/subscription_repo.py`, add method:
```python
  async def get_active_for_card(
      self, card_id: int, today: date
  ) -> Subscription | None
```
  Executes:
```sql
  SELECT * FROM subscriptions
  WHERE card_id = :card_id
    AND status IN ('ACTIVE', 'PENDING')
    AND start_date <= :today
    AND end_date >= :today
  LIMIT 1
```
  Returns the subscription or `None`. This is the hot path — called on every
  entry scan. Must use the composite index `ix_subscriptions_card_id_status`.

- [x] **Task 4.13:** In `repositories/subscription_repo.py`, add method:
```python
  async def get_active_for_subscriber(
      self, subscriber_id: int
  ) -> Subscription | None
```
  Queries subscriptions where `subscriber_id = :id` and
  `status IN ('ACTIVE', 'PENDING')`. Returns one or `None`.

- [x] **Task 4.14:** In `repositories/subscription_repo.py`, add method:
```python
  async def create(
      self,
      subscriber_id: int,
      plan_id: int,
      card_id: int,
      plate_number: str,
      start_date: date,
      end_date: date,
      status: SubscriptionStatus,
      amount_paid_piastres: int,
      plan_price_snapshot: int,
      paid_at: datetime | None,
      collected_by: int | None,
      renewal_count: int,
      previous_subscription_id: int | None,
      notes: str | None,
  ) -> Subscription
```
  Creates `Subscription(...)`. Adds, flushes. Does not commit. Returns the
  subscription.

- [x] **Task 4.15:** In `repositories/subscription_repo.py`, add method:
```python
  async def update_fields(
      self, subscription: Subscription, **fields
  ) -> Subscription
```
  Sets each key-value pair as attribute. Flushes. Does not commit.

- [x] **Task 4.16:** In `repositories/subscription_repo.py`, add method:
```python
  async def count_daily_entries(
      self,
      subscription_id: int,
      day_start_utc: datetime,
      day_end_utc: datetime,
  ) -> int
```
  Executes:
```sql
  SELECT COUNT(*) FROM parking_sessions
  WHERE subscription_id = :subscription_id
    AND entry_time >= :day_start_utc
    AND entry_time < :day_end_utc
```
  Returns integer count.

- [x] **Task 4.17:** In `repositories/subscription_repo.py`, add method:
```python
  async def bulk_expire_overdue(self, today_cairo: date) -> int
```
  Executes a single bulk UPDATE:
```sql
  UPDATE subscriptions
  SET status = 'EXPIRED', ended_at = :now
  WHERE status = 'ACTIVE' AND end_date < :today_cairo
```
  Returns the row count affected. Also executes a second UPDATE to free
  the associated cards:
```sql
  UPDATE parking_cards
  SET status = 'available', updated_at = :now
  WHERE id IN (
      SELECT card_id FROM subscriptions
      WHERE status = 'EXPIRED'
        AND ended_at >= :now_minus_5s
  )
```
  Both UPDATEs are in the same transaction. Flushes but does not commit
  (caller commits).

- [x] **Task 4.18:** In `repositories/subscription_repo.py`, add method:
```python
  async def bulk_activate_pending(self, today_cairo: date) -> int
```
  Executes:
```sql
  UPDATE subscriptions
  SET status = 'ACTIVE', updated_at = :now
  WHERE status = 'PENDING' AND start_date <= :today_cairo
```
  Returns row count. Flushes, does not commit.

- [x] **Task 4.19:** In `repositories/subscription_repo.py`, add method:
```python
  async def get_expiring_soon(
      self, threshold_date: date
  ) -> list[Subscription]
```
  Queries:
```sql
  SELECT * FROM subscriptions
  WHERE status = 'ACTIVE'
    AND end_date <= :threshold_date
  ORDER BY end_date ASC
```
  Returns list.

- [x] **Task 4.20:** In `repositories/subscription_repo.py`, add method:
```python
  async def get_all_by_subscriber(
      self, subscriber_id: int
  ) -> list[Subscription]
```
  Returns all subscriptions for a subscriber ordered by `created_at DESC`.
  No pagination (subscriber subscription history is bounded and small).

- [x] **Task 4.21:** In `repositories/subscription_repo.py`, add method:
```python
  async def get_filtered(
      self,
      status: SubscriptionStatus | None,
      plan_id: int | None,
      page: int,
      size: int,
  ) -> tuple[list[Subscription], int]
```
  Applies `WHERE status = :status` and/or `WHERE plan_id = :plan_id` when
  not `None`. Orders by `created_at DESC`. Returns `(subscriptions, total)`.

- [x] **Task 4.22:** In `repositories/subscription_repo.py`, add method:
```python
  async def get_revenue_by_plan(
      self,
      start_utc: datetime | None,
      end_utc: datetime | None,
      plan_id: int | None,
  ) -> list[dict]
```
  Executes:
```sql
  SELECT s.plan_id, p.label AS plan_label,
         COUNT(*) AS subscription_count,
         COALESCE(SUM(s.amount_paid_piastres), 0) AS total_piastres
  FROM subscriptions s
  JOIN subscription_plans p ON s.plan_id = p.id
  WHERE s.status != 'CANCELLED'
    [AND s.paid_at >= :start_utc]
    [AND s.paid_at < :end_utc]
    [AND s.plan_id = :plan_id]
  GROUP BY s.plan_id, p.label
  ORDER BY total_piastres DESC
```
  Returns list of dicts: `plan_id`, `plan_label`, `subscription_count`,
  `total_piastres`. Add `__all__ = ["SubscriptionRepository"]`.

### 4d — Repositories `__init__.py`

- [x] **Task 4.23:** Update `repositories/__init__.py` to import and
  re-export `SubscriptionPlanRepository`, `SubscriberRepository`,
  `SubscriptionRepository`. Add all three to `__all__`. Rebuild the full
  `__all__` list to include all existing repositories.

---

## Group 5 — Service Exceptions

- [x] **Task 5.1:** Open `services/exceptions.py`. Add the following new
  exception classes using the same pattern as existing ones (inherit from
  `Exception`, store `message: str` in `__init__`):
  - `PlanNotFoundError`
  - `PlanNotActiveError`
  - `PlanLabelAlreadyExistsError`
  - `SubscriberNotFoundError`
  - `SubscriberPlateAlreadyExistsError`
  - `SubscriptionNotFoundError`
  - `SubscriptionNotActiveError`
  - `SubscriberAlreadyHasActiveSubscriptionError`
  - `SubscriptionDailyLimitReachedError`
  Update `__all__` to include all nine new exceptions. Update
  `services/__init__.py` to re-export them.

---

## Group 6 — Services

### 6a — SubscriptionPlanService

- [x] **Task 6.1:** Create `services/subscription_plan_service.py`. Define a
  `SubscriptionPlanService` class with:
```python
  def __init__(
      self,
      db: AsyncSession,
      plan_repo: SubscriptionPlanRepository,
      audit_service: AuditService,
  )
```
  Store all three as instance attributes.

- [x] **Task 6.2:** In `services/subscription_plan_service.py`, add method:
```python
  async def create_plan(
      self, data: PlanCreate, admin_id: int
  ) -> SubscriptionPlan
```
  1. Calls `plan_repo.get_by_label(data.label)`. Raises
     `PlanLabelAlreadyExistsError` if not `None`.
  2. Calls `plan_repo.create(label=data.label,
     duration_days=data.duration_days,
     price_piastres=data.price_piastres,
     max_entries_per_day=data.max_entries_per_day,
     description=data.description,
     created_by=admin_id)`.
  3. Commits `self.db`.
  4. Calls `audit_service.log(actor_id=admin_id, action="PLAN_CREATED",
     entity_type="subscription_plan", entity_id=plan.id,
     before=None, after={"label": plan.label,
     "price_piastres": plan.price_piastres})`.
  5. Returns plan.

- [x] **Task 6.3:** In `services/subscription_plan_service.py`, add method:
```python
  async def deactivate_plan(
      self, plan_id: int, admin_id: int
  ) -> SubscriptionPlan
```
  1. Fetches plan via `plan_repo.get_by_id`. Raises `PlanNotFoundError` if
     absent.
  2. Calls `plan_repo.update_fields(plan, is_active=False)`.
  3. Commits.
  4. Logs `"PLAN_DEACTIVATED"` with `before={"is_active": True}` and
     `after={"is_active": False}`.
  5. Returns plan.

- [x] **Task 6.4:** In `services/subscription_plan_service.py`, add method:
```python
  async def update_plan(
      self, plan_id: int, data: PlanUpdate, admin_id: int
  ) -> SubscriptionPlan
```
  1. Fetches plan. Raises `PlanNotFoundError` if absent.
  2. Captures `before_state = {"label": plan.label, "price_piastres":
     plan.price_piastres, ...}`.
  3. Builds `updates` dict from only non-`None` fields in `data`. Converts
     `price_egp` to piastres via `round(data.price_egp * 100)` if provided.
     Never includes `duration_days` in updates (it is excluded from the
     schema).
  4. If `"label"` in updates: checks for duplicate via `plan_repo.get_by_label`.
     Raises `PlanLabelAlreadyExistsError` if found and the found plan's ID
     differs from `plan_id`.
  5. Calls `plan_repo.update_fields(plan, **updates)`.
  6. Commits. Logs `"PLAN_UPDATED"`. Returns plan.
  Add `__all__ = ["SubscriptionPlanService"]`.

### 6b — SubscriberService

- [x] **Task 6.5:** Create `services/subscriber_service.py`. Define a
  `SubscriberService` class with:
```python
  def __init__(
      self,
      db: AsyncSession,
      subscriber_repo: SubscriberRepository,
      plate_service: PlateService,
      audit_service: AuditService,
  )
```

- [x] **Task 6.6:** In `services/subscriber_service.py`, add method:
```python
  async def create_subscriber(
      self, data: SubscriberCreate, admin_id: int
  ) -> Subscriber
```
  1. Normalizes `data.plate_number` via `self.plate_service.normalize(...)`.
  2. Checks uniqueness via `subscriber_repo.get_by_plate(normalized)`.
     Raises `SubscriberPlateAlreadyExistsError` if found.
  3. Calls `subscriber_repo.create(full_name=data.full_name,
     plate_number=normalized, phone_number=data.phone_number,
     notes=data.notes)`.
  4. Commits. Logs `"SUBSCRIBER_CREATED"`. Returns subscriber.

- [x] **Task 6.7:** In `services/subscriber_service.py`, add method:
```python
  async def update_subscriber(
      self, subscriber_id: int, data: SubscriberUpdate, admin_id: int
  ) -> Subscriber
```
  1. Fetches subscriber. Raises `SubscriberNotFoundError` if absent.
  2. Builds `updates` from non-`None` fields only. Never includes
     `plate_number`.
  3. Calls `subscriber_repo.update_fields(subscriber, **updates)`.
  4. Commits. Logs `"SUBSCRIBER_UPDATED"`. Returns subscriber.

- [x] **Task 6.8:** In `services/subscriber_service.py`, add method:
```python
  async def get_filtered(
      self,
      search: str | None,
      status_filter: str | None,
      plan_id: int | None,
      expiring_days: int | None,
      subscription_repo: SubscriptionRepository,
      page: int,
      size: int,
  ) -> tuple[list[Subscriber], int]
```
  1. Calls `subscriber_repo.get_filtered(search, plan_id, page, size)` to
     get the base paginated list.
  2. For each subscriber in the result, calls
     `subscription_repo.get_active_for_subscriber(subscriber.id)` to attach
     the active subscription. This is N+1 but acceptable at the page size
     of 20 subscribers per page.
  3. If `status_filter` is provided, post-filters the list by the
     subscription's `status` field (or `None` for no active sub = "expired"
     or "never subscribed").
  4. If `expiring_days` is provided, post-filters to subscribers whose active
     subscription's `end_date <= cairo_now().date() + timedelta(days=
     expiring_days)`.
  5. Returns the filtered list and the original total count (pre-filter).
  Add `__all__ = ["SubscriberService"]`.

### 6c — SubscriptionService

- [x] **Task 6.9:** Create `services/subscription_service.py`. Define a
  `SubscriptionService` class with:
```python
  def __init__(
      self,
      db: AsyncSession,
      subscription_repo: SubscriptionRepository,
      plan_repo: SubscriptionPlanRepository,
      card_service: CardService,
      audit_service: AuditService,
  )
```
  Store all five as instance attributes.

- [x] **Task 6.10:** In `services/subscription_service.py`, add method:
```python
  async def get_active_for_card(
      self, card_id: int
  ) -> Subscription | None
```
  Calls `self.subscription_repo.get_active_for_card(card_id,
  cairo_now().date())`. Returns the subscription or `None`. This method
  must not raise — it is called on every entry scan and must silently return
  `None` on any unexpected state.

- [x] **Task 6.11:** In `services/subscription_service.py`, add method:
```python
  async def check_daily_limit(
      self, subscription: Subscription
  ) -> bool
```
  1. Fetches the plan via `plan_repo.get_by_id(subscription.plan_id)`.
  2. If `plan.max_entries_per_day is None`: returns `True` immediately (no
     limit check, no DB query).
  3. Computes `day_start_utc = cairo_today_start()` and `day_end_utc =
     day_start_utc + timedelta(days=1)`.
  4. Calls `subscription_repo.count_daily_entries(subscription.id,
     day_start_utc, day_end_utc)`.
  5. Returns `count < plan.max_entries_per_day`.

- [x] **Task 6.12:** In `services/subscription_service.py`, add method:
```python
  async def create_subscription(
      self,
      data: SubscriptionCreate,
      admin_id: int,
  ) -> Subscription
```
  Step-by-step:
  1. Fetch plan via `plan_repo.get_by_id(data.plan_id)`. Raise
     `PlanNotFoundError` if absent.
  2. Raise `PlanNotActiveError` if `plan.is_active = False`.
  3. Fetch card via `card_service.get_by_code` — wait, card is identified
     by `card_id` here, not code. Use a direct DB get:
     `await self.db.get(ParkingCard, data.card_id)`. Raise
     `CardNotFoundError` if absent.
  4. Raise `CardNotAvailableError` if `card.status != CardStatus.AVAILABLE`.
  5. Check `subscription_repo.get_active_for_subscriber(data.subscriber_id)`.
     Raise `SubscriberAlreadyHasActiveSubscriptionError` if not `None`.
  6. Compute `end_date = data.start_date + timedelta(days=plan.duration_days)`.
  7. Determine `status`: if `data.start_date <= cairo_now().date()` then
     `ACTIVE` else `PENDING`.
  8. Call `subscription_repo.create(subscriber_id=data.subscriber_id,
     plan_id=data.plan_id, card_id=data.card_id,
     plate_number=subscriber.plate_number, start_date=data.start_date,
     end_date=end_date, status=status,
     amount_paid_piastres=data.amount_paid_piastres,
     plan_price_snapshot=plan.price_piastres,
     paid_at=datetime.utcnow(), collected_by=admin_id,
     renewal_count=0, previous_subscription_id=None,
     notes=data.notes)`.
     Note: fetch `subscriber.plate_number` via
     `await self.db.get(Subscriber, data.subscriber_id)` before this step.
  9. If `status == ACTIVE`: call `card_service.set_status(card,
     CardStatus.IN_USE)`.
  10. Commit `self.db`.
  11. Log `"SUBSCRIPTION_CREATED"`. Return subscription.

- [x] **Task 6.13:** In `services/subscription_service.py`, add method:
```python
  async def renew_subscription(
      self,
      subscription_id: int,
      data: SubscriptionRenewRequest,
      admin_id: int,
  ) -> Subscription
```
  Step-by-step:
  1. Fetch old subscription. Raise `SubscriptionNotFoundError` if absent.
  2. Raise `SubscriptionNotActiveError` if `old.status` is not `ACTIVE`.
  3. Fetch plan via `plan_repo.get_by_id(old.plan_id)`.
  4. Determine new `start_date`:
     - If `old.end_date >= cairo_now().date()` (not yet expired):
       `new_start = old.end_date` (seamless continuation).
     - Else (already expired): `new_start = cairo_now().date()`.
  5. `new_end = new_start + timedelta(days=plan.duration_days)`.
  6. Determine new `status`: if `new_start <= cairo_now().date()` then
     `ACTIVE` else `PENDING`.
  7. Call `subscription_repo.create(...)` for the new subscription with
     `renewal_count=old.renewal_count + 1`,
     `previous_subscription_id=old.id`, same `card_id`, `subscriber_id`.
  8. If new `status == ACTIVE` and old status was `ACTIVE`:
     call `subscription_repo.update_fields(old, status=SubscriptionStatus.
     EXPIRED, ended_at=datetime.utcnow())`.
  9. If new `status == PENDING`: old subscription stays `ACTIVE`.
  10. Commit. Log `"SUBSCRIPTION_RENEWED"` with
      `after={"old_id": old.id, "new_id": new_sub.id}`. Return new
      subscription.

- [x] **Task 6.14:** In `services/subscription_service.py`, add method:
```python
  async def cancel_subscription(
      self,
      subscription_id: int,
      cancel_reason: str | None,
      admin_id: int,
  ) -> Subscription
```
  1. Fetch subscription. Raise `SubscriptionNotFoundError` if absent.
  2. Raise `SubscriptionNotActiveError` if `status` not in
     (`ACTIVE`, `PENDING`).
  3. Capture `card = await self.db.get(ParkingCard, subscription.card_id)`.
  4. Call `subscription_repo.update_fields(subscription,
     status=SubscriptionStatus.CANCELLED,
     ended_at=datetime.utcnow(),
     cancel_reason=cancel_reason)`.
  5. Call `card_service.set_status(card, CardStatus.AVAILABLE)`.
  6. Both changes flush together. Commit once.
  7. Log `"SUBSCRIPTION_CANCELLED"`. Return subscription.

- [x] **Task 6.15:** In `services/subscription_service.py`, add method:
```python
  async def expire_overdue_subscriptions(self) -> int
```
  1. Calls `await self.subscription_repo.bulk_expire_overdue(
     cairo_now().date())`.
  2. Commits.
  3. Returns the count of expired rows.

- [x] **Task 6.16:** In `services/subscription_service.py`, add method:
```python
  async def activate_pending_subscriptions(self) -> int
```
  1. Calls `await self.subscription_repo.bulk_activate_pending(
     cairo_now().date())`.
  2. Commits.
  3. Returns the count of activated rows.

- [x] **Task 6.17:** In `services/subscription_service.py`, add method:
```python
  async def get_dashboard_stats(self) -> SubscriptionDashboardStats
```
  Fires three queries concurrently via `asyncio.gather`:
  1. `COUNT(*) WHERE status='ACTIVE'` — `active_subscriptions_count`.
  2. `subscription_repo.get_expiring_soon(cairo_now().date() +
     timedelta(days=7))` — length of result = `expiring_soon_count`.
  3. Count of subscriptions where `status='EXPIRED'` and no linked
     subscription has `status IN ('ACTIVE','PENDING')` via a subquery on
     `previous_subscription_id`.
  On any individual exception: use `0` as fallback. Returns
  `SubscriptionDashboardStats(...)`. Add
  `__all__ = ["SubscriptionService"]`.

### 6d — SessionService Modifications

- [x] **Task 6.18:** Open `services/session_service.py`. Add
  `SubscriptionService` as an optional dependency to `SessionService.__init__`:
```python
  def __init__(
      self,
      ...,  # existing params unchanged
      subscription_service: SubscriptionService | None = None,
  )
```
  Store as `self.subscription_service = subscription_service`. This is
  optional (`None`) so that existing Phase 2 tests do not break without
  modification.

- [x] **Task 6.19:** In `services/session_service.py`, modify
  `open_session` to add a subscription check **after** card validation and
  **before** creating the session. Insert these steps between the card
  validation step and the `session_repo.create` call:
  1. `subscription = None`
  2. If `self.subscription_service is not None`:
     a. `subscription = await self.subscription_service.get_active_for_card(
        card.id)`
     b. If `subscription is not None`:
        call `allowed = await self.subscription_service.check_daily_limit(
        subscription)`. If `not allowed`: raise
        `SubscriptionDailyLimitReachedError`.
  3. Pass `subscription_id=subscription.id if subscription else None` and
     `is_subscribed=subscription is not None` to `session_repo.create`.
  Return the `(session, subscription)` tuple instead of just `session`.
  Update the return type annotation to
  `tuple[ParkingSession, Subscription | None]`.

- [x] **Task 6.20:** In `services/session_service.py`, modify `close_session`
  to check `session.is_subscribed` before pricing. Immediately after fetching
  the session and verifying `status == ACTIVE`, insert:
```python
  if session.is_subscribed:
      exit_time = datetime.utcnow()
      session.exit_time = exit_time
      session.status = SessionStatus.COMPLETED
      session.amount_charged = 0
      session.is_paid = True
      session.pricing_rule_id = None
      session.exit_operator_id = exit_operator_id
      session.exit_shift_id = exit_shift.id
      session.duration_minutes = math.ceil(
          (exit_time - session.entry_time).total_seconds() / 60
      )
      await self.card_service.set_status(card, CardStatus.AVAILABLE)
      await self.db.commit()
      await self.audit_service.log(...)
      return (session, None)  # No PriceCalculation for subscribed sessions
```
  The existing pricing path runs only in the `else` branch. Update return
  type to `tuple[ParkingSession, PriceCalculation | None]`.

### 6e — ReportService Extension

- [x] **Task 6.21:** Open `services/report_service.py`. Add method:
```python
  async def get_subscription_revenue_summary(
      self,
      start_date: date | None,
      end_date: date | None,
      plan_id: int | None,
      subscription_repo: SubscriptionRepository,
  ) -> SubscriptionRevenueSummary
```
  Resolves UTC boundaries. Calls `subscription_repo.get_revenue_by_plan(
  start_utc, end_utc, plan_id)`. Computes totals: `total_subscriptions =
  sum(row["subscription_count"])`, `total_revenue_piastres =
  sum(row["total_piastres"])`, `avg_revenue_piastres = total_revenue //
  max(total_subscriptions, 1)`. Returns `SubscriptionRevenueSummary(...)`.

### 6f — App Startup Lifespan

- [x] **Task 6.22:** Open `main.py`. Replace any existing `@app.on_event(
  "startup")` decorator with a proper `@asynccontextmanager` lifespan
  function. If no startup event exists, add the lifespan from scratch.
  The lifespan function must:
  1. Open an `AsyncSession` from `AsyncSessionLocal`.
  2. Instantiate `SubscriptionRepository(db)` and
     `SubscriptionService(db, sub_repo, plan_repo=None, card_service=None,
     audit_service=AuditService(db))`.
  3. Call `expired_count = await sub_service.expire_overdue_subscriptions()`.
  4. Call `activated_count = await sub_service.activate_pending_subscriptions()`.
  5. Write a single audit log: `action="SUBSCRIPTIONS_BULK_EXPIRED"`,
     `actor_id=0` (system), `entity_type="system"`, `entity_id=0`,
     `payload_after={"expired_count": expired_count, "activated_count":
     activated_count}`. Commit.
  6. Wrap steps 3–5 in `try/except Exception as e: logger.critical(
     "Startup subscription lifecycle failed: %s", e)`. App continues
     starting even on failure.
  7. After `yield` (the app serves requests), close the session.
  Pass `lifespan=lifespan` to the `FastAPI(...)` constructor.

### 6g — Services `__init__.py`

- [x] **Task 6.23:** Update `services/__init__.py` to import and re-export
  `SubscriptionPlanService`, `SubscriberService`, `SubscriptionService`.
  Rebuild `__all__`. Verify all nine new exceptions from Task 5.1 are
  exported.

### 6h — Excel Import Service

- [x] **Task 6.24:** Create `services/excel_import_service.py`. Implement `ExcelImportService`:
  - `_normalize_string` & `_match_column_name` for intelligent Arabic & English column mapping.
  - `parse_file` supporting `.xlsx` and multi-encoding `.csv` (UTF-8, CP1256, Latin-1).
  - `generate_template` generating a formatted Excel template with styled Arabic headers.
  - `preview` validating rows, card code availability, duplicate plates/phones, and error reporting.
  - `execute_import` performing atomic batch import inside a single database transaction.

---
---

## Group 7 — Jinja2 Filters & Translations

### 7a — New Jinja2 Filters

- [x] **Task 7.1:** Open `utils/jinja.py`. Add filter function:
```python
  def days_remaining_filter(end_date: date | None) -> int:
```
  If `end_date is None`: returns `0`. Computes
  `(end_date - cairo_now().date()).days`. Returns `max(result, 0)`.

- [x] **Task 7.2:** In `utils/jinja.py`, add filter:
```python
  def subscription_status_label_filter(status: str) -> str:
```
  Returns: `"ACTIVE"` → `"نشط"`, `"EXPIRED"` → `"منتهي"`,
  `"CANCELLED"` → `"ملغي"`, `"PENDING"` → `"معلق"`. Any other value
  → returns `status` unchanged.

- [x] **Task 7.3:** In `utils/jinja.py`, add filter:
```python
  def subscription_status_class_filter(status: str) -> str:
```
  Returns Tailwind CSS class string:
  - `"ACTIVE"` → `"bg-green-100 text-green-800"`.
  - `"EXPIRED"` → `"bg-gray-100 text-gray-600"`.
  - `"CANCELLED"` → `"bg-red-100 text-red-700"`.
  - `"PENDING"` → `"bg-amber-100 text-amber-700"`.
  - Any other → `"bg-gray-100 text-gray-500"`.

- [x] **Task 7.4:** In `utils/jinja.py`, update `create_jinja2_environment`
  to register the three new filters:
  - `"days_remaining"` → `days_remaining_filter`
  - `"subscription_status_label"` → `subscription_status_label_filter`
  - `"subscription_status_class"` → `subscription_status_class_filter`
  No other changes to this function.

### 7b — Translations

- [x] **Task 7.5:** Open `translations/ar.json`. Add all translation keys
  listed in `spec.md` Section 3.10. Do not remove any existing key.
  Validate JSON syntax by running:
  `python -c "import json; json.load(open('translations/ar.json'))"`.

---

## Group 8 — API Routes

### 8a — Subscription Plans API

- [x] **Task 8.1:** Create `routes/subscriptions_api.py`. Define
  `router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])`.
  All routes in this file use `Depends(require_admin)` unless noted. Add
  `POST /plans` endpoint:
  - Body: `PlanCreate`.
  - Instantiates `SubscriptionPlanRepository(db)`, `AuditService(db)`,
    `SubscriptionPlanService(db, plan_repo, audit_service)`.
  - Calls `plan_service.create_plan(data, current_user.id)`.
  - Maps `PlanLabelAlreadyExistsError` → `HTTPException(409,
    code="PLAN_LABEL_ALREADY_EXISTS")`.
  - Returns `{"data": PlanResponse(...).model_dump()}` with status `201`.

- [x] **Task 8.2:** In `routes/subscriptions_api.py`, add `GET /plans`
  endpoint:
  - Query param: `active_only: bool = False`.
  - Calls `plan_repo.get_all(active_only=active_only)`.
  - Returns `{"data": [PlanResponse(...) for p in plans]}`.

- [x] **Task 8.3:** In `routes/subscriptions_api.py`, add
  `GET /plans/active` endpoint:
  - No auth restriction — uses `Depends(require_any_role)`.
  - Calls `plan_repo.get_all(active_only=True)`.
  - Returns list of `PlanResponse`. Used by subscription creation form
    dropdowns.

- [x] **Task 8.4:** In `routes/subscriptions_api.py`, add
  `PATCH /plans/{plan_id}` endpoint:
  - Body: `PlanUpdate`.
  - Calls `plan_service.update_plan(plan_id, data, current_user.id)`.
  - Maps `PlanNotFoundError` → `404`, `PlanLabelAlreadyExistsError` → `409`.
  - Returns `{"data": PlanResponse(...)}`.

- [x] **Task 8.5:** In `routes/subscriptions_api.py`, add
  `PATCH /plans/{plan_id}/deactivate` endpoint:
  - Calls `plan_service.deactivate_plan(plan_id, current_user.id)`.
  - Maps `PlanNotFoundError` → `404`.
  - Returns `{"data": PlanResponse(...)}`.

### 8b — Subscribers API

- [x] **Task 8.6:** In `routes/subscriptions_api.py`, add
  `POST /subscribers` endpoint:
  - Body: `SubscriberCreate`.
  - Instantiates all required services.
  - Calls `subscriber_service.create_subscriber(data, current_user.id)`.
  - Maps `SubscriberPlateAlreadyExistsError` → `HTTPException(409,
    code="SUBSCRIBER_PLATE_ALREADY_EXISTS")`.
  - Returns `{"data": SubscriberResponse(...)}` with status `201`.

- [x] **Task 8.7:** In `routes/subscriptions_api.py`, add
  `GET /subscribers` endpoint:
  - Query params: `search: str | None = None`,
    `status: str | None = None`, `plan_id: int | None = None`,
    `expiring_days: int | None = None`,
    `page: int = Query(1, ge=1)`,
    `size: int = Query(20, ge=1, le=100)`.
  - Calls `subscriber_service.get_filtered(...)`.
  - Returns `PaginatedResponse[SubscriberResponse]`.

- [x] **Task 8.8:** In `routes/subscriptions_api.py`, add
  `GET /subscribers/{subscriber_id}` endpoint:
  - Fetches subscriber via `subscriber_repo.get_by_id`. Raises `404` if
    absent.
  - Fetches active subscription via `subscription_repo.
    get_active_for_subscriber(subscriber_id)`.
  - Fetches all subscriptions via `subscription_repo.get_all_by_subscriber`.
  - Returns `{"data": SubscriberResponse(active_subscription=..., ...)}`.

- [x] **Task 8.9:** In `routes/subscriptions_api.py`, add
  `PATCH /subscribers/{subscriber_id}` endpoint:
  - Body: `SubscriberUpdate`.
  - Calls `subscriber_service.update_subscriber(subscriber_id, data,
    current_user.id)`.
  - Maps `SubscriberNotFoundError` → `404`.
  - Returns `{"data": SubscriberResponse(...)}`.

### 8c — Subscriptions API

- [x] **Task 8.10:** In `routes/subscriptions_api.py`, add `POST /`
  endpoint (creates subscription):
  - Body: `SubscriptionCreate`.
  - Calls `subscription_service.create_subscription(data, current_user.id)`.
  - Maps exceptions:
    - `PlanNotFoundError` → `404` `PLAN_NOT_FOUND`
    - `PlanNotActiveError` → `409` `PLAN_NOT_ACTIVE`
    - `CardNotAvailableError` → `409` `CARD_NOT_AVAILABLE`
    - `SubscriberAlreadyHasActiveSubscriptionError` → `409`
      `SUBSCRIBER_ALREADY_HAS_ACTIVE_SUBSCRIPTION`
  - Returns `{"data": SubscriptionResponse(...)}` with status `201`.

- [x] **Task 8.11:** In `routes/subscriptions_api.py`, add `GET /`
  endpoint (list subscriptions):
  - Query params: `status: SubscriptionStatus | None = None`,
    `plan_id: int | None = None`, `page`, `size`.
  - Calls `subscription_repo.get_filtered(status, plan_id, page, size)`.
  - Returns `PaginatedResponse[SubscriptionResponse]`.

- [x] **Task 8.12:** In `routes/subscriptions_api.py`, add
  `GET /{subscription_id}` endpoint:
  - Fetches subscription. Raises `404` if absent.
  - Returns `{"data": SubscriptionResponse(...)}`.

- [x] **Task 8.13:** In `routes/subscriptions_api.py`, add
  `POST /{subscription_id}/renew` endpoint:
  - Body: `SubscriptionRenewRequest`.
  - Calls `subscription_service.renew_subscription(subscription_id, data,
    current_user.id)`.
  - Maps `SubscriptionNotFoundError` → `404`,
    `SubscriptionNotActiveError` → `409` `SUBSCRIPTION_NOT_ACTIVE`.
  - Returns `{"data": SubscriptionResponse(...)}` with status `201`.

- [x] **Task 8.14:** In `routes/subscriptions_api.py`, add
  `PATCH /{subscription_id}/cancel` endpoint:
  - Body: `SubscriptionCancelRequest`.
  - Calls `subscription_service.cancel_subscription(subscription_id,
    data.cancel_reason, current_user.id)`.
  - Maps `SubscriptionNotFoundError` → `404`,
    `SubscriptionNotActiveError` → `409` `SUBSCRIPTION_NOT_ACTIVE`.
  - Returns `{"data": SubscriptionResponse(...)}`.

### 8d — Reporting API Extension

- [x] **Task 8.15:** Open `routes/admin_api.py`. Add endpoint
  `GET /reports/subscriptions`:
  - Auth: `Depends(require_admin)`.
  - Query params: `start_date: date | None`, `end_date: date | None`,
    `plan_id: int | None`.
  - Calls `report_service.get_subscription_revenue_summary(start_date,
    end_date, plan_id, subscription_repo)`.
  - Returns `{"data": SubscriptionRevenueSummary(...).model_dump()}`.

- [x] **Task 8.16:** Open `routes/admin_api.py`. Add endpoint
  `GET /stats/subscriptions`:
  - Auth: `Depends(require_admin)`.
  - Calls `subscription_service.get_dashboard_stats()`.
  - Returns `{"data": SubscriptionDashboardStats(...).model_dump()}`.

### 8e — Router Registration

- [x] **Task 8.17:** Open `main.py`. Import `router` from
  `routes/subscriptions_api.py` as `subscriptions_api_router`. Add
  `app.include_router(subscriptions_api_router)` after existing routers.
  No other changes to `main.py` in this task.

---

## Group 9 — Operator UI Modifications

- [x] **Task 9.1:** Open `routes/ui_operator.py`. Modify the `POST /entry`
  handler to:
  1. Pass `subscription_service` to `SessionService` when instantiating it.
  2. Unpack the returned `(session, subscription)` tuple from
     `session_service.open_session(...)`.
  3. Pass `subscription=subscription` in the redirect context to
     `GET /ui/operator/entry/confirm/{session_id}`.
  4. Map `SubscriptionDailyLimitReachedError` → re-render entry page with
     `error=t("errors.subscription_daily_limit")`.

- [x] **Task 9.2:** Open `routes/ui_operator.py`. Modify the
  `GET /entry/confirm/{session_id}` handler to:
  1. Also fetch the subscription for the session via
     `subscription_repo.get_by_id(session.subscription_id)` if
     `session.subscription_id` is not `None`.
  2. Fetch the subscriber name via
     `subscriber_repo.get_by_id(subscription.subscriber_id)` if subscription
     is not `None`.
  3. Pass `subscription=subscription` and `subscriber=subscriber` in the
     template context.

- [x] **Task 9.3:** Open `routes/ui_operator.py`. Modify the
  `POST /exit/lookup` handler to:
  1. Unpack `(session, subscription)` returned by `close_session` — wait,
     lookup does not close. Instead: after computing the price preview, also
     fetch `subscription = None` if `session.is_subscribed` is `False`, or
     `subscription_repo.get_by_id(session.subscription_id)` if `True`.
  2. Pass `is_subscribed=session.is_subscribed`,
     `subscription=subscription` to `exit_confirm.html`.

- [x] **Task 9.4:** Open `routes/ui_operator.py`. Modify the
  `POST /exit/{session_id}/confirm` handler to:
  1. Unpack `(session, calc)` from `close_session` — `calc` may be `None`
     for subscribed sessions.
  2. Redirect to `/ui/operator/receipt/{session_id}` regardless (same as
     before). No change to redirect target.

- [x] **Task 9.5:** Open `routes/ui_operator.py`. Modify the
  `GET /receipt/{session_id}` handler to:
  1. Check `session.is_subscribed`.
  2. If `True`: render `receipts/thermal_subscription.html` instead of
     `receipts/thermal.html`. Fetch subscriber name from DB.
  3. If `False`: existing logic unchanged.

---

## Group 10 — Operator Templates Modifications

- [x] **Task 10.1:** Open `templates/operator/entry_confirm.html`. Add a
  conditional block after the existing success card:
```jinja2
  {% if subscription %}
  <div class="bg-green-500 text-white rounded-lg p-4 mt-4 text-center">
    <p class="text-xl font-bold">{{ t("operator.entry.subscribed_banner") }}</p>
    <p class="text-sm mt-1">
      {{ subscriber.full_name if subscriber else "" }}
    </p>
    <p class="text-sm">
      {{ t("operator.entry.subscription_expires") }}:
      {{ subscription.end_date | cairo_date }}
    </p>
  </div>
  {% endif %}
```
  Do not alter any existing template structure outside of this addition.

- [x] **Task 10.2:** Open `templates/operator/exit_confirm.html`. Add a
  conditional block that replaces the pricing section when
  `is_subscribed=True`:
```jinja2
  {% if is_subscribed %}
  <div class="text-center my-6">
    <p class="text-gray-500 text-sm">{{ t("subscriptions.subscription.title") }}</p>
    <p class="text-green-600 font-bold" style="font-size: 2rem;">٠٫٠٠ ج.م</p>
    {% if subscription %}
    <p class="text-sm text-gray-500 mt-1">
      {{ t("subscriptions.subscription.end") }}:
      {{ subscription.end_date | cairo_date }}
    </p>
    {% endif %}
  </div>
  <form method="POST"
    action="/ui/operator/exit/{{ session.id }}/confirm">
    <button type="submit"
      class="w-full bg-green-600 text-white py-4 rounded-lg text-lg font-bold"
      style="min-height: 64px;">
      {{ t("operator.exit.subscription_confirm_button") }}
    </button>
  </form>
  {% else %}
  {# existing pricing section unchanged #}
  {% endif %}
```

---

## Group 11 — Subscription Receipt Template

- [x] **Task 11.1:** Create `templates/receipts/thermal_subscription.html`.
  This is a **standalone** HTML file — does NOT extend `base.html`.
  Structure mirrors `thermal.html` but with subscription-specific content:
```html
  <!DOCTYPE html>
  <html lang="ar" dir="rtl">
  <head>
    <meta charset="UTF-8">
    <title>إيصال اشتراك</title>
    <link rel="stylesheet" href="/static/print.css">
    <style>
      body { width: 58mm; font-family: 'Courier New', monospace;
             font-size: 10pt; direction: rtl; margin: 0; padding: 4mm; }
      .sep { white-space: pre; }
      .total-line { font-size: 13pt; font-weight: bold; }
    </style>
  </head>
  <body class="receipt-body">
    <!-- Content defined in Task 11.2 -->
  </body>
  </html>
```

- [x] **Task 11.2:** In `templates/receipts/thermal_subscription.html`, add
  the receipt body inside `<body>`. Required fields in order:
  1. Garage name (`{{ receipt.garage_name }}`), centred, bold.
  2. Separator: `<p class="sep">--------------------------------</p>`.
  3. Receipt type: `{{ t("receipt.subscription_title") }}` — "إيصال اشتراك".
  4. Session ID: `{{ receipt.session_id | zfill(8) }}`.
  5. Subscriber name: `{{ receipt.subscriber_name }}`.
  6. Card code, plate number (or "غير مسجل"), gate number, operator name.
  7. Separator.
  8. Entry time: `{{ receipt.entry_time | format_datetime }}`.
  9. Exit time: `{{ receipt.exit_time | format_datetime }}`.
  10. Duration: `{{ receipt.duration_minutes | format_duration }}`.
  11. Separator.
  12. Plan label: `{{ receipt.pricing_rule_label }}`.
  13. Subscription end date:
      `{{ t("receipt.subscription_end_date") }}: {{ receipt.subscription_end_date | cairo_date }}`.
  14. Separator.
  15. Amount line with class `total-line`: `٠٫٠٠ ج.م`.
  16. Separator.
  17. Footer: `{{ t("receipt.footer") }}`.
  18. `<script>` block:
      `window.addEventListener('load', () => { window.print();
      setTimeout(() => { window.location.href='/ui/operator/dashboard'; },
      2000); });`
  19. Non-print preview `<div class="no-print">` with a "طباعة مرة أخرى"
      button calling `window.print()`.

---

## Group 12 — Admin UI Routes & Templates

### 12a — Admin Subscription UI Router

- [x] **Task 12.2:** Create `routes/ui_subscriptions.py`. Define
  `router = APIRouter(prefix="/ui/admin", tags=["ui-subscriptions"])`.
  All routes use `Depends(require_admin)`. Add `GET /plans` endpoint:
  - Fetches all plans via `plan_repo.get_all(active_only=False)`.
  - Returns `TemplateResponse("admin/plans.html", {"request": request,
    "user": current_user, "plans": plans})`.

- [x] **Task 12.3:** In `routes/ui_subscriptions.py`, add
  `GET /subscribers` endpoint:
  - Parses `search`, `status`, `plan_id`, `expiring_days`, `page`, `size`
    from query params.
  - Calls `subscriber_service.get_filtered(...)`.
  - Fetches all active plans for the filter dropdown.
  - Returns `TemplateResponse("admin/subscribers.html", {...})`.

- [x] **Task 12.4:** In `routes/ui_subscriptions.py`, add
  `GET /subscribers/new` endpoint:
  - Returns `TemplateResponse("admin/subscriber_new.html", {"request":
    request, "user": current_user})`.

- [x] **Task 12.5:** In `routes/ui_subscriptions.py`, add
  `GET /subscribers/{subscriber_id}` endpoint:
  - Fetches subscriber. Redirects to `/ui/admin/subscribers` if absent.
  - Fetches active subscription and all historical subscriptions.
  - Fetches paginated sessions (page 1, size 10) via
    `session_repo.get_active_by_subscription` — add this method to
    `ParkingSessionRepository`: `SELECT * WHERE subscription_id IN
    (list of subscriber's subscription IDs) ORDER BY entry_time DESC
    LIMIT 10`.
  - Returns `TemplateResponse("admin/subscriber_detail.html", {...})`.

- [x] **Task 12.6:** In `routes/ui_subscriptions.py`, add
  `GET /subscribers/{subscriber_id}/subscribe` endpoint:
  - Fetches subscriber. Fetches active plans.
  - Fetches all available cards via `card_repo.get_all(status=
    CardStatus.AVAILABLE, page=1, size=200)`.
  - Returns `TemplateResponse("admin/subscriber_subscribe.html", {...})`.

- [x] **Task 12.7:** In `routes/ui_subscriptions.py`, add
  `GET /subscribers/{subscriber_id}/renew` endpoint:
  - Fetches subscriber and their active subscription.
  - If no active subscription: redirects to
    `/ui/admin/subscribers/{id}/subscribe`.
  - Returns `TemplateResponse("admin/subscriber_renew.html", {...})`.

- [x] **Task 12.8:** In `routes/ui_subscriptions.py`, add
  `GET /subscriptions` endpoint:
  - Parses `status`, `plan_id`, `page`, `size` from query params.
  - Calls `subscription_repo.get_filtered(status, plan_id, page, size)`.
  - For each subscription fetches subscriber name and plan label in one
    batch query each.
  - Returns `TemplateResponse("admin/subscriptions.html", {...})`.

- [x] **Task 12.9:** Register `ui_subscriptions.router` in `main.py`.
  Import as `ui_subscriptions_router`. Add
  `app.include_router(ui_subscriptions_router)`. No other changes.

### 12b — Dashboard Extension

- [x] **Task 12.10:** Open `routes/ui_admin.py`. Modify `GET /dashboard`
  to additionally call `subscription_service.get_dashboard_stats()`
  concurrently in the existing `asyncio.gather`. Pass
  `sub_stats: SubscriptionDashboardStats` in the template context. Update
  the `asyncio.gather` call to include the new coroutine.

- [x] **Task 12.11:** Open `templates/admin/dashboard.html`. Add a new
  alert card below the existing amber/red banners:
```jinja2
  {% if sub_stats.expiring_soon_count > 0 %}
  <div class="bg-amber-50 border border-amber-300 rounded-lg p-3 mb-4">
    <a href="/ui/admin/subscribers?status=expiring"
       class="text-amber-800 font-medium">
      ⚠ {{ sub_stats.expiring_soon_count | to_arabic_indic }}
      {{ t("admin.dashboard.expiring_soon") }}
    </a>
  </div>
  {% endif %}
  {% if sub_stats.expired_unrenewed_count > 0 %}
  <div class="bg-red-50 border border-red-300 rounded-lg p-3 mb-4">
    <a href="/ui/admin/subscribers?status=expired"
       class="text-red-800 font-medium">
      ❌ {{ sub_stats.expired_unrenewed_count | to_arabic_indic }}
      {{ t("admin.dashboard.expired_unrenewed") }}
    </a>
  </div>
  {% endif %}
```

### 12c — Admin Templates

- [x] **Task 12.12:** Create `templates/admin/plans.html` extending
  `templates/admin/base_admin.html`. Must include:
  - "إنشاء خطة جديدة" button that shows/hides an inline `<div>` form via
    a JavaScript toggle (`display: none` / `display: block`).
  - Inline form fields: `label` (text), `duration_days` (number, min 1),
    `price_egp` (number, step `"0.01"`, min 0), `grace_period_mins` —
    not applicable here; only `max_entries_per_day` (number, optional),
    `description` (textarea, optional). Submit POSTs to
    `POST /api/v1/subscriptions/plans` via `fetch`. On success: reloads
    the page. On error: shows Arabic error message inside the form.
  - Plans table (newest first): ID, label, duration (days), price
    (`format_egp`), max entries/day (or "غير محدود"), active badge.
  - Per-row "تعطيل" button (calls `PATCH /api/v1/subscriptions/plans/{id}/
    deactivate` via `fetch`, updates badge on success).
  - Deactivated plans show grey "غير نشط" badge; "تعطيل" button disabled.

- [x] **Task 12.13:** Create `templates/admin/subscribers.html` extending
  `base_admin.html`. Must include:
  - Filter bar: `search` text input, `status` dropdown
    (نشط/منتهي/ملغي/الكل), `plan_id` dropdown, `expiring_days` hidden
    param (filled by "Expiring soon" link). Submit button.
  - Results count.
  - Table: full name, phone, plate number, plan label (or "لا يوجد"),
    status badge (`subscription_status_class` filter), expiry date
    (`cairo_date` filter), days remaining (`days_remaining` filter).
  - Each row links to `/ui/admin/subscribers/{{ subscriber.id }}`.
  - "إضافة مشترك" button links to `/ui/admin/subscribers/new`.
  - Pagination controls.

- [x] **Task 12.14:** Create `templates/admin/subscriber_new.html` extending
  `base_admin.html`. Must include:
  - A `<form method="POST" action="/api/v1/subscriptions/subscribers">`
    (submits via `fetch`, redirects to new subscriber page on success).
  - Fields: `full_name` (text, required), `plate_number` (text, required,
    `dir="rtl"`), `phone_number` (text, optional), `notes` (textarea,
    optional).
  - Submit button: "إضافة المشترك", full-width, green.
  - On success: JavaScript redirects to
    `/ui/admin/subscribers/{new_id}/subscribe`.

- [x] **Task 12.15:** Create `templates/admin/subscriber_detail.html`
  extending `base_admin.html`. Must include:
  - Subscriber info card: full name, phone, plate number, notes.
  - Active subscription card (if any): plan label, start date, end date,
    days remaining (`days_remaining` filter in green/amber/red depending on
    value), card code, amount paid (`format_egp`), status badge.
  - "تجديد الاشتراك" button (links to
    `/ui/admin/subscribers/{{ subscriber.id }}/renew`) — shown when no
    active subscription OR when `days_remaining < 7`.
  - "إنشاء اشتراك جديد" button (links to
    `/ui/admin/subscribers/{{ subscriber.id }}/subscribe`) — shown only
    when no active subscription.
  - Recent sessions table (last 10): card code, entry time, exit time,
    duration, amount (shows "٠٫٠٠ ج.م" for subscribed sessions).
  - Past subscriptions list: plan label, start, end, status badge, amount
    paid.

- [x] **Task 12.16:** Create `templates/admin/subscriber_subscribe.html`
  extending `base_admin.html`. Must include:
  - Subscriber name and plate displayed at top (read-only).
  - Form submits to `POST /api/v1/subscriptions/` via `fetch`.
  - Fields:
    - `plan_id` (select from active plans; shows label, duration, and price).
    - `card_id` (scan input or select from available cards list).
    - `start_date` (date input, default today in Cairo).
    - `amount_paid_egp` (number, pre-filled from selected plan price via
      JavaScript `change` event on plan select).
    - `notes` (textarea, optional).
  - JavaScript: on plan selection change, fetch
    `GET /api/v1/subscriptions/plans/active` and update `amount_paid_egp`
    pre-fill and show computed `end_date` = start_date + duration_days.
  - Submit button: "إنشاء الاشتراك", green, full-width.
  - On success: redirect to `/ui/admin/subscribers/{{ subscriber.id }}`.

- [x] **Task 12.17:** Create `templates/admin/subscriber_renew.html`
  extending `base_admin.html`. Must include:
  - Current subscription info (plan label, current end date, days remaining).
  - New subscription preview: new start date (= current end date if not
    expired, else today), new end date, duration.
  - Fields: `amount_paid_egp` (pre-filled from plan price), `notes`.
  - Submit POSTs to `POST /api/v1/subscriptions/{{ subscription.id }}/renew`
    via `fetch`.
  - Submit button: "تجديد الاشتراك", amber, full-width.
  - On success: redirect to subscriber detail page.

- [x] **Task 12.18:** Create `templates/admin/subscriptions.html` extending
  `base_admin.html`. Must include:
  - Filter bar: `status` dropdown, `plan_id` dropdown, `page`, `size`.
  - Table: subscription ID, subscriber name, plate, plan label, start date,
    end date, days remaining, amount paid (`format_egp`), status badge.
  - Pagination controls.
  - Each row links to the subscriber detail page (not subscription detail).

### 12d — Sidebar Navigation Update

- [x] **Task 12.19:** Open `templates/admin/base_admin.html`. Add two new
  sidebar links:
  - `<a href="/ui/admin/subscribers">{{ t("subscriptions.subscriber.title") }}</a>`
  - `<a href="/ui/admin/plans">{{ t("subscriptions.plan.title") }}</a>`
  Place them after the "التعريفات" link and before "العمال". No other
  changes to `base_admin.html`.

---

### 12e — Excel Bulk Import UI & Template

- [x] **Task 12.20:** Open `routes/ui_subscriptions.py`. Add Excel import routes:
  - `GET /ui/admin/subscribers/import`: renders `admin/subscribers_import.html` with active plans.
  - `GET /ui/admin/subscribers/template-excel`: downloads styled `subscribers_template.xlsx`.
  - `POST /ui/admin/subscribers/import-preview`: receives file, calls `ExcelImportService.parse_file` and `preview()`, returns validation statistics.
  - `POST /ui/admin/subscribers/import-confirm`: executes `ExcelImportService.execute_import()`.

- [x] **Task 12.21:** Create `templates/admin/subscribers_import.html` extending `base_admin.html`.
  Includes drag-and-drop file upload, template download button, interactive preview table showing card code status (existing vs new), subscriber status, warning banners, and confirmation button.

---

## Group 13 — Tailwind Rebuild

- [x] **Task 13.1:** Run `make css` to rebuild `static/css/tailwind.min.css`
  including all new template classes from Group 12. Verify `tailwind.config.js`
  `content` array still includes both `"templates/operator/**/*.html"` and
  `"templates/admin/**/*.html"`. Mark complete only after a successful build
  with no purge warnings and the file size is under 350KB.

---

## Group 14 — Unit Tests

### 14a — Filter Tests

- [x] **Task 14.1:** Create `tests/unit/test_subscription_schemas.py`. Write
  tests for `PlanCreate`:
  - `test_price_egp_converts_to_piastres`: `PlanCreate(price_egp=10.0,
    ...)`. Asserts `plan.price_piastres == 1000`.
  - `test_fractional_price_rounds_correctly`: `price_egp=5.555`. Asserts
    `price_piastres == 556`.
  - `test_zero_price_valid`: `price_egp=0.0`. Asserts `price_piastres == 0`.
  - `test_negative_price_invalid`: `price_egp=-1.0`. Asserts
    `ValidationError`.
  - `test_duration_days_zero_invalid`: `duration_days=0`. Asserts
    `ValidationError`.

- [x] **Task 14.2:** In `tests/unit/test_subscription_schemas.py`, write
  tests for `SubscriberUpdate`:
  - `test_plate_number_not_in_schema`: asserts `"plate_number"` is not a
    field of `SubscriberUpdate` (use `model_fields`).
  - `test_all_fields_optional`: `SubscriberUpdate()` with no args. Asserts
    no `ValidationError`.

- [x] **Task 14.3:** In `tests/unit/test_subscription_schemas.py`, write
  tests for `SubscriptionResponse.days_remaining`:
  - `test_days_remaining_future`: freeze today, set `end_date = today + 5`.
    Asserts `days_remaining == 5`.
  - `test_days_remaining_expired`: `end_date = today - 1`. Asserts
    `days_remaining == 0` (not negative).
  - `test_days_remaining_today`: `end_date = today`. Asserts
    `days_remaining == 0`.

### 14b — Jinja2 Filter Tests

- [x] **Task 14.4:** Create `tests/unit/test_subscription_filters.py`. Write
  tests for `subscription_status_label_filter`:
  - `"ACTIVE"` → `"نشط"`.
  - `"EXPIRED"` → `"منتهي"`.
  - `"CANCELLED"` → `"ملغي"`.
  - `"PENDING"` → `"معلق"`.
  - `"UNKNOWN"` → `"UNKNOWN"` (passthrough).

- [x] **Task 14.5:** In `tests/unit/test_subscription_filters.py`, write
  tests for `subscription_status_class_filter`:
  - `"ACTIVE"` → asserts contains `"green"`.
  - `"EXPIRED"` → asserts contains `"gray"`.
  - `"CANCELLED"` → asserts contains `"red"`.
  - `"PENDING"` → asserts contains `"amber"`.

- [x] **Task 14.6:** In `tests/unit/test_subscription_filters.py`, write
  tests for `days_remaining_filter` using `freezegun.freeze_time`:
  - `None` → `0`.
  - `end_date = frozen_today + 7` → `7`.
  - `end_date = frozen_today - 1` → `0` (not `-1`).
  - `end_date = frozen_today` → `0`.

### 14c — SubscriptionPlanService Unit Tests

- [x] **Task 14.7:** Create `tests/unit/test_subscription_plan_service.py`.
  Use `db_session` and `audit_service` fixtures. Write test
  `test_create_plan_success` (async): calls `plan_service.create_plan(
  PlanCreate(label="شهري", duration_days=30, price_egp=150.0), admin_id=1)`.
  Asserts returned plan has `price_piastres == 15000` and `is_active == True`.

- [x] **Task 14.8:** Write test `test_create_plan_duplicate_label_raises`
  (async): creates a plan with label "شهري", then creates another with the
  same label. Asserts `PlanLabelAlreadyExistsError`.

- [x] **Task 14.9:** Write test `test_deactivate_plan_success` (async):
  creates a plan, deactivates it. Asserts `plan.is_active == False` in DB.

- [x] **Task 14.10:** Write test `test_update_plan_price` (async): creates
  plan with `price_egp=100.0`, updates with `price_egp=200.0`. Asserts
  `plan.price_piastres == 20000`.

- [x] **Task 14.11:** Write test `test_update_plan_duration_not_possible`
  (async): asserts `"duration_days"` is not a field in `PlanUpdate`
  (cannot be passed). Does not test service — tests the schema directly.

### 14d — SubscriptionService Unit Tests

- [x] **Task 14.12:** Create `tests/unit/test_subscription_service.py`.
  Use all fixtures. Write `test_get_active_for_card_found` (async): seeds
  a subscription with `status=ACTIVE`, `start_date=today`,
  `end_date=today+30`. Calls `get_active_for_card(card.id)`. Asserts the
  subscription is returned.

- [x] **Task 14.13:** Write `test_get_active_for_card_expired` (async):
  seeds subscription with `end_date=yesterday`. Calls
  `get_active_for_card`. Asserts `None` returned.

- [x] **Task 14.14:** Write `test_get_active_for_card_pending_future`
  (async): seeds subscription with `status=PENDING`,
  `start_date=tomorrow`. Calls `get_active_for_card`. Asserts `None`
  (future start not yet active).

- [x] **Task 14.15:** Write `test_get_active_for_card_pending_today`
  (async): seeds subscription with `status=PENDING`,
  `start_date=today`, `end_date=today+30`. Calls `get_active_for_card`.
  Asserts the subscription is returned.

- [x] **Task 14.16:** Write `test_check_daily_limit_no_limit` (async):
  plan has `max_entries_per_day=None`. Asserts `check_daily_limit` returns
  `True` without querying `parking_sessions` (mock `count_daily_entries`
  to verify it is NOT called).

- [x] **Task 14.17:** Write `test_check_daily_limit_within_limit` (async):
  plan has `max_entries_per_day=3`, existing entry count = 2. Asserts
  `check_daily_limit` returns `True`.

- [x] **Task 14.18:** Write `test_check_daily_limit_at_limit` (async):
  plan has `max_entries_per_day=3`, existing count = 3. Asserts
  `check_daily_limit` returns `False`.

- [x] **Task 14.19:** Write `test_create_subscription_success` (async):
  seeds subscriber, active plan, available card. Calls
  `create_subscription(...)`. Asserts subscription `status=ACTIVE`,
  card `status=IN_USE` in DB, audit log created.

- [x] **Task 14.20:** Write `test_create_subscription_card_not_available`
  (async): card has `status=IN_USE`. Asserts `CardNotAvailableError`.

- [x] **Task 14.21:** Write `test_create_subscription_duplicate_active`
  (async): subscriber already has `ACTIVE` subscription. Asserts
  `SubscriberAlreadyHasActiveSubscriptionError`.

- [x] **Task 14.22:** Write `test_cancel_subscription_success` (async):
  seeds ACTIVE subscription. Calls `cancel_subscription(...)`. Asserts
  `status=CANCELLED`, card `status=AVAILABLE`, `cancel_reason` stored.

- [x] **Task 14.23:** Write `test_cancel_subscription_not_active` (async):
  subscription already `EXPIRED`. Asserts `SubscriptionNotActiveError`.

- [x] **Task 14.24:** Write `test_renew_before_expiry` (async): active
  subscription ending in 5 days. Calls `renew_subscription(...)`. Asserts
  new subscription `status=PENDING`, `start_date = old.end_date`. Asserts
  old subscription stays `ACTIVE`.

- [x] **Task 14.25:** Write `test_renew_after_expiry` (async): subscription
  already `EXPIRED`. Calls `renew_subscription(...)`. Asserts new
  subscription `status=ACTIVE`, `start_date = today`.

- [x] **Task 14.26:** Write `test_expire_overdue_bulk` (async): seeds 3
  ACTIVE subscriptions with `end_date = yesterday` and 1 with
  `end_date = tomorrow`. Calls `expire_overdue_subscriptions()`. Asserts
  return value is `3`. Asserts 3 subscriptions have `status=EXPIRED` in DB.
  Asserts 1 subscription remains `ACTIVE`.

- [x] **Task 14.27:** Write `test_activate_pending_bulk` (async): seeds 2
  PENDING subscriptions with `start_date = today` and 1 with
  `start_date = tomorrow`. Calls `activate_pending_subscriptions()`.
  Asserts return value is `2`. Asserts 2 subscriptions `status=ACTIVE`.

### 14e — SessionService Subscription Integration Unit Tests

- [x] **Task 14.28:** Create `tests/unit/test_session_subscription.py`.
  Write `test_open_session_subscribed_sets_flag` (async): seeds card,
  operator, open shift, active plan, active subscription. Calls
  `session_service.open_session("CARD-0001", operator_id)`. Asserts
  returned session has `is_subscribed=True` and
  `subscription_id=subscription.id`.

- [x] **Task 14.29:** Write `test_open_session_not_subscribed_flag_false`
  (async): card has no subscription. Asserts returned session has
  `is_subscribed=False` and `subscription_id=None`.

- [x] **Task 14.30:** Write `test_open_session_daily_limit_blocks` (async):
  plan has `max_entries_per_day=1`, subscriber already entered today (seed
  one session with `subscription_id` set). Calls `open_session`. Asserts
  `SubscriptionDailyLimitReachedError`.

- [x] **Task 14.31:** Write `test_close_subscribed_session_zero_charge`
  (async): seeds ACTIVE subscribed session (is_subscribed=True), active
  pricing rule. Calls `close_session(...)`. Asserts `amount_charged=0`,
  `is_paid=True`, `pricing_rule_id=None`.

- [x] **Task 14.32:** Write `test_close_subscribed_returns_none_calc`
  (async): same setup as Task 14.31. Asserts the second element of the
  returned tuple is `None` (no `PriceCalculation` for subscribed sessions).

---

### 14h — Excel Import Unit Tests

- [x] **Task 14.33:** Create `tests/unit/test_excel_import.py`. Add unit tests:
  - `test_generate_template`: asserts generated bytes are valid openpyxl workbook with correct Arabic headers.
  - `test_parse_template`: parses the generated template and verifies row structures.
  - `test_parse_csv`: parses UTF-8 / CP1256 encoded CSV content.
  - `test_preview_and_execute_import`: verifies preview statistics, card auto-creation, subscriber creation, and subscription activation.

---

## Group 15 — Integration Tests

### 15a — Plan API Tests

- [x] **Task 15.1:** Create `tests/integration/test_subscription_plan_api.py`.
  Write `test_create_plan_as_admin` (async): POST
  `/api/v1/subscriptions/plans`. Asserts `201` and
  `data.price_piastres == 15000` for `price_egp=150.0`.

- [x] **Task 15.2:** Write `test_create_plan_duplicate_label` (async):
  creates plan twice with same label. Asserts `409` and
  `code == "PLAN_LABEL_ALREADY_EXISTS"`.

- [x] **Task 15.3:** Write `test_create_plan_as_operator_forbidden` (async):
  logs in as operator, POSTs plan. Asserts `403`.

- [x] **Task 15.4:** Write `test_deactivate_plan` (async): creates plan,
  deactivates. Asserts `200` and `data.is_active == False`.

- [x] **Task 15.5:** Write `test_active_plans_endpoint_excludes_inactive`
  (async): creates one active and one deactivated plan. GET
  `/api/v1/subscriptions/plans/active`. Asserts only the active plan
  is returned.

### 15b — Subscriber API Tests

- [x] **Task 15.6:** Create `tests/integration/test_subscriber_api.py`.
  Write `test_create_subscriber_success` (async): POST
  `/api/v1/subscriptions/subscribers` with valid data. Asserts `201` and
  `data.plate_number` is normalized.

- [x] **Task 15.7:** Write `test_create_subscriber_duplicate_plate` (async):
  creates subscriber, creates again with same plate. Asserts `409` and
  `code == "SUBSCRIBER_PLATE_ALREADY_EXISTS"`.

- [x] **Task 15.8:** Write `test_create_subscriber_plate_normalized` (async):
  POSTs `plate_number = "ن ي ش ١٥٩"` (Eastern numerals). Asserts stored
  `plate_number == "ن ي ش 159"` (Western numerals).

- [x] **Task 15.9:** Write `test_get_subscriber_detail` (async): creates
  subscriber and subscription. GET
  `/api/v1/subscriptions/subscribers/{id}`. Asserts `active_subscription`
  is populated.

- [x] **Task 15.10:** Write `test_update_subscriber_cannot_change_plate`
  (async): PATCH with `{"plate_number": "أ ب ج 999"}`. Asserts the stored
  plate number is unchanged (schema ignores the field).

### 15c — Subscription Lifecycle API Tests

- [x] **Task 15.11:** Create `tests/integration/test_subscription_api.py`.
  Write `test_create_subscription_full_flow` (async):
  1. Creates subscriber, active plan, available card.
  2. POST `/api/v1/subscriptions/` with valid data.
  3. Asserts `201`, `data.status == "ACTIVE"`.
  4. Queries DB: asserts card `status == "in_use"`.

- [x] **Task 15.12:** Write `test_create_subscription_inactive_plan` (async):
  deactivates plan, then tries to create subscription. Asserts `409`
  `PLAN_NOT_ACTIVE`.

- [x] **Task 15.13:** Write `test_create_subscription_card_in_use` (async):
  card `status=IN_USE`. Asserts `409` `CARD_NOT_AVAILABLE`.

- [x] **Task 15.14:** Write `test_renew_subscription_before_expiry` (async):
  creates subscription ending in 5 days. POST `.../renew`. Asserts new
  subscription `status=PENDING` and `start_date == old.end_date`.

- [x] **Task 15.15:** Write `test_cancel_subscription` (async): creates
  subscription, cancels. Asserts `data.status == "CANCELLED"`. Queries
  DB: asserts card `status == "available"`.

- [x] **Task 15.16:** Write `test_cancel_already_cancelled` (async):
  cancels twice. Asserts second call returns `409` `SUBSCRIPTION_NOT_ACTIVE`.

### 15d — Entry/Exit Subscription Integration Tests

- [x] **Task 15.17:** Create
  `tests/integration/test_subscription_entry_exit.py`. Write
  `test_subscribed_entry_sets_is_subscribed_true` (async):
  1. Seeds subscriber, active plan, subscription, card.
  2. POST `/api/v1/sessions/` with the subscribed card code.
  3. Asserts `201`, `data.is_subscribed == True`,
     `data.subscription_id == subscription.id`.

- [x] **Task 15.18:** Write `test_subscribed_exit_zero_charge` (async):
  1. Opens subscribed session (Task 15.17 flow).
  2. PATCH `/api/v1/sessions/{id}/exit`.
  3. Asserts `data.amount_charged == 0`, `data.is_paid == True`,
     `data.pricing_rule_id == None`.

- [x] **Task 15.19:** Write `test_expired_subscription_entry_paid` (async):
  seeds subscription with `end_date = yesterday`. POST session. Asserts
  `data.is_subscribed == False` (expired subscription not recognized as
  active).

- [x] **Task 15.20:** Write `test_daily_limit_blocks_second_entry` (async):
  plan has `max_entries_per_day=1`. Opens first session (close it). Opens
  second session same day. Asserts `409`
  `SUBSCRIPTION_DAILY_LIMIT_REACHED`.

- [x] **Task 15.21:** Write `test_unlimited_entries_allowed` (async): plan
  has `max_entries_per_day=None`. Opens and closes 3 sessions in sequence.
  All succeed with `is_subscribed=True`. No `409` error.

### 15e — Admin UI Subscription Tests

- [x] **Task 15.22:** Create
  `tests/integration/test_ui_subscription_routes.py`. Write:
  - `test_plans_page_renders` (async): GET `/ui/admin/plans`. Asserts `200`
    and `t("subscriptions.plan.title")` value in body.
  - `test_subscribers_page_renders` (async): GET `/ui/admin/subscribers`.
    Asserts `200`.
  - `test_subscriber_new_page_renders` (async): GET
    `/ui/admin/subscribers/new`. Asserts `200`.
  - `test_subscriber_detail_page_renders` (async): seeds subscriber. GET
    `/ui/admin/subscribers/{id}`. Asserts `200` and subscriber name in body.
  - `test_subscriber_subscribe_page_renders` (async): seeds subscriber and
    active plan. GET `/ui/admin/subscribers/{id}/subscribe`. Asserts `200`.
  - `test_subscriptions_list_page_renders` (async): GET
    `/ui/admin/subscriptions`. Asserts `200`.
  - `test_plans_page_requires_admin` (async): GET as operator. Asserts `303`
    redirect.

### 15f — Startup Lifespan Test

- [x] **Task 15.23:** Create
  `tests/integration/test_subscription_lifespan.py`. Write
  `test_lifespan_expires_overdue_subscriptions` (async):
  1. Seeds 2 ACTIVE subscriptions with `end_date = yesterday`.
  2. Seeds 1 ACTIVE subscription with `end_date = tomorrow`.
  3. Triggers the lifespan function directly (call
     `expire_overdue_subscriptions()` and
     `activate_pending_subscriptions()` on `SubscriptionService`).
  4. Queries DB. Asserts 2 subscriptions `status=EXPIRED`.
  5. Asserts 1 subscription remains `ACTIVE`.

- [x] **Task 15.24:** Write `test_lifespan_activates_pending` (async):
  1. Seeds 1 PENDING subscription with `start_date = today`.
  2. Seeds 1 PENDING subscription with `start_date = tomorrow`.
  3. Calls `activate_pending_subscriptions()`.
  4. Asserts the today subscription is `ACTIVE`.
  5. Asserts the tomorrow subscription remains `PENDING`.

### 15g — Coverage & Quality Gate

- [x] **Task 15.25:** Run `pytest --cov=services/subscription_service
  --cov=services/subscription_plan_service
  --cov=services/subscriber_service
  --cov-report=term-missing`. Confirm:
  - `services/subscription_service.py` ≥ 95% coverage.
  - `services/subscription_plan_service.py` ≥ 95% coverage.
  - `services/subscriber_service.py` ≥ 90% coverage.
  Fix any critical uncovered branches before marking complete.

- [x] **Task 15.26:** Run `pytest --cov=repositories/subscription_repo
  --cov=repositories/subscription_plan_repo
  --cov=repositories/subscriber_repo
  --cov-report=term-missing`. Confirm ≥ 85% coverage on all three
  repository files.

- [x] **Task 15.27:** Run `black . && ruff check . && mypy .` on the entire
  project. Fix all formatting, lint, and type errors. Zero issues must
  remain. Do not mark complete with any tool reporting warnings or errors.

- [x] **Task 15.28:** Run `make css` to rebuild Tailwind. Verify
  `static/css/tailwind.min.css` rebuilds successfully with all new
  subscription template classes included. Commit the rebuilt CSS.

- [x] **Task 15.29:** Perform manual QA. Verify:
  - [x] Creating a plan via the inline form works without page reload.
  - [x] Creating a subscriber and assigning a subscription works end-to-end.
  - [x] Scanning a subscribed card on the Gate 1 PC workstation shows green "مشترك ✓"
        banner.
  - [x] Exit scan shows zero amount in green for subscribed vehicles.
  - [x] Subscription receipt prints correctly on 58mm thermal paper.
  - [x] Renewing a subscription creates the correct start/end dates.
  - [x] Cancelling a subscription frees the card (status → available).
  - [x] Dashboard shows expiring soon and expired unrenewed alert cards.
  - [x] Startup lifespan expires overdue subscriptions on app restart.
  Record results in `QA_LOG.md` with date and tester name.
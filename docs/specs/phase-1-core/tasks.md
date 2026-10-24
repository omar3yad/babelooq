# Phase 1 — Atomic Coding Task Checklist

> **Version:** 1.0
> **Scope:** All coding tasks required to complete Phase 1 as specified in `spec.md`.
> **Execution order is mandatory.** No task may be started until all tasks above it in the
> same group are checked. No task may skip a layer (models → schemas → repositories →
> services → routes).
> **Each task is atomic:** one file, one class, one function, or one config block per task.

---

## Group 0 — Project Scaffold & Tooling

- [x] **Task 0.1:** Create the root project directory structure exactly as specified in
  `constitution.md` Section 3. Create every folder listed with a `.gitkeep` file so the
  structure is committed. Folders: `models/`, `schemas/`, `routes/`, `services/`,
  `repositories/`, `templates/auth/`, `templates/receipts/`, `static/`, `tests/unit/`,
  `tests/integration/`, `translations/`, `alembic/`.

- [x] **Task 0.2:** Create `pyproject.toml` in the project root. Add the following tool
  sections only — do not add any dependencies here:
  - `[tool.black]` with `line-length = 88`.
  - `[tool.ruff]` with `line-length = 88` and `select = ["E", "F", "W", "C90"]`.
  - `[tool.mypy]` with `strict = true` and `ignore_missing_imports = true`.
  - `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` and
    `testpaths = ["tests"]`.

- [x] **Task 0.3:** Create `requirements.txt` with exact pinned versions for:
  `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `aiosqlite`, `asyncpg`,
  `alembic`, `pydantic`, `pydantic-settings`, `python-jose[cryptography]`, `bcrypt`,
  `python-multipart`, `jinja2`, `httpx`, `pytest`, `pytest-asyncio`, `freezegun`.
  Use the latest stable version of each package available as of mid-2025.

- [x] **Task 0.4:** Create `.env.example` in the project root with the following keys,
  each with a placeholder value and an inline comment explaining its purpose:
  `DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`, `JWT_EXPIRE_HOURS`, `JWT_ALGORITHM`,
  `DEBUG`, `APP_NAME`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `CORS_ORIGINS`,
  `SEED_ADMIN_USERNAME`, `SEED_ADMIN_PASSWORD`, `SEED_ADMIN_FULL_NAME`,
  `SEED_OP_1_USERNAME`, `SEED_OP_1_PASSWORD`, `SEED_OP_1_FULL_NAME`,
  `SEED_OP_2_USERNAME`, `SEED_OP_2_PASSWORD`, `SEED_OP_2_FULL_NAME`,
  `SEED_OP_3_USERNAME`, `SEED_OP_3_PASSWORD`, `SEED_OP_3_FULL_NAME`,
  `SEED_OP_4_USERNAME`, `SEED_OP_4_PASSWORD`, `SEED_OP_4_FULL_NAME`,
  `SEED_OP_5_USERNAME`, `SEED_OP_5_PASSWORD`, `SEED_OP_5_FULL_NAME`.

- [x] **Task 0.5:** Create `.gitignore` ignoring: `.env`, `__pycache__/`, `*.pyc`,
  `*.pyo`, `.mypy_cache/`, `.pytest_cache/`, `htmlcov/`, `.coverage`, `dist/`,
  `*.egg-info/`, `node_modules/`, `*.db`, `*.sqlite3`.

- [x] **Task 0.6:** Create `translations/ar.json` with the following keys and Arabic
  string values:
  `"login.title"`, `"login.username_label"`, `"login.password_label"`,
  `"login.submit_button"`, `"login.error_invalid_credentials"`,
  `"login.error_account_inactive"`, `"login.error_username_required"`,
  `"login.error_password_required"`, `"nav.logout"`, `"errors.unauthorized"`,
  `"errors.forbidden"`, `"errors.not_found"`, `"errors.server_error"`,
  `"errors.db_unavailable"`.

---

## Group 1 — Configuration (`config.py`)

- [x] **Task 1.1:** Create `config.py` in the project root. Define a `Settings` class
  inheriting from `pydantic_settings.BaseSettings`. Add only these fields with their
  types and defaults:
  - `DATABASE_URL: str` — no default (required).
  - `SECRET_KEY: str` — no default (required).
  - `ENVIRONMENT: Literal["development", "staging", "production"]` — no default
    (required).
  - `DEBUG: bool = False`.
  - `APP_NAME: str = "PGMS"`.

- [x] **Task 1.2:** Add the following optional fields to the `Settings` class in
  `config.py`:
  - `JWT_EXPIRE_HOURS: int = 8`.
  - `JWT_ALGORITHM: str = "HS256"`.
  - `DB_POOL_SIZE: int = 5`.
  - `DB_MAX_OVERFLOW: int = 10`.
  - `CORS_ORIGINS: list[str] = []`.

- [x] **Task 1.3:** Add a Pydantic `model_validator(mode="after")` to the `Settings`
  class in `config.py` that:
  - Raises `ValueError` with the message `"SECRET_KEY must be at least 32 characters"`
    if `len(SECRET_KEY) < 32`.
  - Raises `ValueError` with the message `"DEBUG must not be True in production"` if
    `ENVIRONMENT == "production"` and `DEBUG is True`.
  - Raises `ValueError` if `JWT_EXPIRE_HOURS < 1`.

- [x] **Task 1.4:** Add a `model_config = SettingsConfigDict(env_file=".env",
  env_file_encoding="utf-8", case_sensitive=True)` attribute to the `Settings` class.
  Then add a module-level `get_settings` function decorated with
  `@functools.lru_cache()` that instantiates and returns `Settings()`. Add
  `__all__ = ["Settings", "get_settings"]`.

---

## Group 2 — Database Layer (`database.py`)

- [x] **Task 2.1:** Create `database.py` in the project root. Import `get_settings`.
  Create an `engine` using `sqlalchemy.ext.asyncio.create_async_engine` with the URL
  from `settings.DATABASE_URL`. For SQLite URLs (detected by checking if the URL
  starts with `"sqlite"`), add `connect_args={"check_same_thread": False}` and use
  `poolclass=StaticPool`. For all other URLs, pass `pool_size` and `max_overflow` from
  settings.

- [x] **Task 2.2:** In `database.py`, add a SQLAlchemy connection event listener using
  `@sqlalchemy.event.listens_for(engine.sync_engine, "connect")` that executes
  `PRAGMA foreign_keys=ON` on every new SQLite connection. This listener must be
  registered only when the database URL starts with `"sqlite"`.

- [x] **Task 2.3:** In `database.py`, create `AsyncSessionLocal` using
  `sqlalchemy.ext.asyncio.async_sessionmaker` with `bind=engine`,
  `class_=AsyncSession`, `expire_on_commit=False`, and `autoflush=False`.

- [x] **Task 2.4:** In `database.py`, create a `Base` declarative class using
  `sqlalchemy.orm.DeclarativeBase`. Add `__all__ = ["engine", "AsyncSessionLocal",
  "Base", "get_db"]`.

- [x] **Task 2.5:** In `database.py`, create an async generator function `get_db`
  that yields one `AsyncSession` from `AsyncSessionLocal`. The session must be closed
  in a `finally` block regardless of whether an exception occurred. Annotate the return
  type as `AsyncGenerator[AsyncSession, None]`.

---

## Group 3 — SQLAlchemy Models

### 3a — Timestamp Mixin

- [x] **Task 3.1:** Create `models/__init__.py` as an empty file.

- [x] **Task 3.2:** Create `models/mixins.py`. Define a `TimestampMixin` class (not
  inheriting from `Base`) with two `MappedColumn` attributes:
  - `created_at: Mapped[datetime]` with
    `server_default=func.now()` and `nullable=False`.
  - `updated_at: Mapped[datetime]` with `server_default=func.now()`,
    `onupdate=func.now()`, and `nullable=False`.
  Both columns store UTC. Import `datetime` from the standard library.

### 3b — User Model

- [x] **Task 3.3:** Create `models/user.py`. Define a `UserRole` Python `enum.Enum`
  with values `ADMIN = "admin"` and `OPERATOR = "operator"`. Do not add any methods.

- [x] **Task 3.4:** In `models/user.py`, define a `User` class inheriting from `Base`
  and `TimestampMixin`. Set `__tablename__ = "users"`. Add the following mapped columns
  only — no relationships yet:
  - `id: Mapped[int]` — primary key, autoincrement.
  - `full_name: Mapped[str]` — `VARCHAR(120)`, not nullable.
  - `username: Mapped[str]` — `VARCHAR(60)`, unique, not nullable, indexed.
  - `hashed_password: Mapped[str]` — `VARCHAR(255)`, not nullable.

- [x] **Task 3.5:** In `models/user.py`, add the remaining columns to the `User` model:
  - `role: Mapped[UserRole]` — SQLAlchemy `Enum(UserRole)`, not nullable.
  - `gate_number: Mapped[int | None]` — `SMALLINT`, nullable.
  - `is_active: Mapped[bool]` — not nullable, `server_default="1"`.

- [x] **Task 3.6:** In `models/user.py`, add a `__table_args__` to the `User` model
  containing one `sqlalchemy.CheckConstraint`:
```
(role = 'operator' AND gate_number IS NOT NULL AND gate_number BETWEEN 1 AND 5)
OR
(role = 'admin' AND gate_number IS NULL)
```
Name the constraint `"ck_users_role_gate_consistency"`.

### 3c — PricingRule Model (stub)

- [x] **Task 3.7:** Create `models/pricing_rule.py`. Define a `PricingRule` class
  inheriting from `Base` and `TimestampMixin`. Set `__tablename__ = "pricing_rules"`.
  Add all columns exactly as defined in `master-plan.md` Section 2.2 for `pricing_rules`:
  `id`, `label`, `rate_per_hour`, `minimum_charge`, `grace_period_mins`, `is_active`,
  `created_by` (FK to `users.id`), `effective_from`, `effective_until`.
  Use `Mapped` annotations throughout. No relationships in this task.

### 3d — Shift Model (stub)

- [x] **Task 3.8:** Create `models/shift.py`. Define a `Shift` class inheriting from
  `Base` and `TimestampMixin`. Set `__tablename__ = "shifts"`. Add all columns exactly
  as defined in `master-plan.md` Section 2.2 for `shifts`:
  `id`, `operator_id` (FK to `users.id`), `gate_number`, `started_at`, `ended_at`,
  `opening_cash_egp`, `closing_cash_egp`, `notes`.
  Use `Mapped` annotations throughout. No relationships in this task.

### 3e — ParkingSession Model (stub)

- [x] **Task 3.9:** Create `models/parking_session.py`. Define a `PaymentMethod`
  `enum.Enum` with value `CASH = "cash"`. Then define a `ParkingSession` class
  inheriting from `Base` and `TimestampMixin`. Set `__tablename__ = "parking_sessions"`.
  Add all columns exactly as defined in `master-plan.md` Section 2.2:
  `id`, `ticket_number` (unique, indexed), `card_barcode` (indexed), `plate_number` (nullable),
  `gate_number`, `shift_id` (FK), `operator_id` (FK), `entry_time`, `exit_time`,
  `duration_minutes`, `pricing_rule_id` (FK), `amount_charged`, `payment_method`,
  `is_paid`, `exit_operator_id` (FK nullable), `exit_shift_id` (FK nullable),
  `receipt_printed_at`, `is_deleted`, `notes`.
  Use Mapped annotations throughout. No relationships in this task.

### 3f — AuditLog Model

- [x] **Task 3.10:** Create `models/audit_log.py`. Define an `AuditLog` class
  inheriting from `Base` only (no `TimestampMixin` — it has only `created_at`).
  Set `__tablename__ = "audit_logs"`. Add columns:
  - `id: Mapped[int]` — primary key, autoincrement.
  - `actor_id: Mapped[int]` — FK to `users.id`, not nullable, indexed.
  - `action: Mapped[str]` — `VARCHAR(80)`, not nullable, indexed.
  - `entity_type: Mapped[str]` — `VARCHAR(40)`, not nullable.
  - `entity_id: Mapped[int]` — not nullable.
  - `payload_before: Mapped[str | None]` — `TEXT`, nullable.
  - `payload_after: Mapped[str | None]` — `TEXT`, nullable.
  - `created_at: Mapped[datetime]` — not nullable, `server_default=func.now()`.
  No `updated_at` column on this model.

- [x] **Task 3.11:** Update `models/__init__.py` to import and re-export:
  `UserRole`, `User`, `PricingRule`, `Shift`, `ParkingSession`, `PaymentMethod`,
  `AuditLog`. Add `__all__` listing all exports.

---

## Group 4 — Alembic Migrations

- [x] **Task 4.1:** Run `alembic init alembic` in the project root. Then update
  `alembic/env.py` to:
  - Import `get_settings` and set `config.set_main_option("sqlalchemy.url",
    get_settings().DATABASE_URL)`.
  - Import `Base` from `database` and set `target_metadata = Base.metadata`.
  - Replace the `run_migrations_online` function with an async version using
    `AsyncEngine` and `AsyncConnection` compatible with SQLAlchemy 2.x async.

- [x] **Task 4.2:** Generate the initial migration by running
  `alembic revision --autogenerate -m "create initial schema"`. Then open the generated
  file and verify that all five tables appear in the `upgrade()` function in this exact
  order: `users`, `pricing_rules`, `shifts`, `parking_sessions`, `audit_logs`. Verify
  that `downgrade()` drops them in reverse order. Do not edit any logic — only verify
  and commit the file.

- [x] **Task 4.3:** Run `alembic upgrade head` against a local SQLite test database
  (set `DATABASE_URL=sqlite+aiosqlite:///./test_verify.db` temporarily). Confirm all
  five tables exist using a SQLite browser or `sqlite3` CLI. Delete `test_verify.db`
  after verification. Commit no changes in this task — it is a verification step only.

---

## Group 5 — Pydantic Schemas

- [x] **Task 5.1:** Create `schemas/__init__.py` as an empty file.

- [x] **Task 5.2:** Create `schemas/common.py`. Define:
  - `PaginatedResponse` — generic Pydantic model with fields `data: list[T]`,
    `total: int`, `page: int`, `size: int` using `Generic[T]`.
  - `ErrorResponse` — Pydantic model with fields `detail: str` and `code: str`.
  Both models must have `model_config = ConfigDict(from_attributes=True)`.

### 5a — User Schemas

- [x] **Task 5.3:** Create `schemas/user.py`. Define `UserBase` as a Pydantic
  `BaseModel` with fields:
  - `full_name: str` — `Field(min_length=1, max_length=120)`.
  - `username: str` — `Field(min_length=1, max_length=60,
    pattern=r"^[a-zA-Z0-9_]+$")`.
  - `role: UserRole`.
  - `gate_number: int | None = None` — `Field(None, ge=1, le=5)`.
  Add a `model_validator(mode="after")` that raises `ValueError` if `role ==
  UserRole.OPERATOR and gate_number is None` or if `role == UserRole.ADMIN and
  gate_number is not None`.

- [x] **Task 5.4:** In `schemas/user.py`, define `UserCreate` inheriting from
  `UserBase` with one additional field:
  - `password: str` — `Field(min_length=8, max_length=128)`.

- [x] **Task 5.5:** In `schemas/user.py`, define `UserResponse` inheriting from
  `UserBase` with additional fields:
  - `id: int`.
  - `is_active: bool`.
  - `created_at: datetime`.
  - `updated_at: datetime`.
  Set `model_config = ConfigDict(from_attributes=True)`. `hashed_password` must not
  appear anywhere in this schema.

- [x] **Task 5.6:** In `schemas/user.py`, define `UserUpdatePassword` as a standalone
  Pydantic model (not inheriting `UserBase`) with one field:
  - `new_password: str` — `Field(min_length=8, max_length=128)`.

- [x] **Task 5.7:** Update `schemas/__init__.py` to import and re-export all schemas
  from `schemas/user.py` and `schemas/common.py`. Add `__all__`.

### 5b — Auth Schemas

- [x] **Task 5.8:** Create `schemas/auth.py`. Define:
  - `LoginRequest` — Pydantic model with `username: str` and `password: str`, both
    required, no defaults. Add `Field(min_length=1)` to each.
  - `LoginResponse` — Pydantic model with `user_id: int`, `role: UserRole`,
    `full_name: str`.
  - `TokenPayload` — Pydantic model with `sub: str`, `role: str`, `iat: int`,
    `exp: int`. Used internally for JWT decode validation only.
  Import `UserRole` from `models`. Add all three to `schemas/__init__.py`.

### 5c — AuditLog Schemas

- [x] **Task 5.9:** Create `schemas/audit_log.py`. Define `AuditLogResponse` as a
  Pydantic model with fields: `id: int`, `actor_id: int`, `action: str`,
  `entity_type: str`, `entity_id: int`, `payload_before: str | None`,
  `payload_after: str | None`, `created_at: datetime`.
  Set `model_config = ConfigDict(from_attributes=True)`. Add to `schemas/__init__.py`.

---

## Group 6 — Repositories

- [x] **Task 6.1:** Create `repositories/__init__.py` as an empty file.

### 6a — User Repository

- [x] **Task 6.2:** Create `repositories/user_repo.py`. Define a `UserRepository`
  class with `__init__(self, db: AsyncSession)` storing `self.db = db`. Add one method
  only:
```python
  async def get_by_id(self, user_id: int) -> User | None
```
  Uses `db.get(User, user_id)`. Returns the `User` or `None`.

- [x] **Task 6.3:** In `repositories/user_repo.py`, add:
```python
  async def get_by_username(self, username: str) -> User | None
```
  Uses `select(User).where(User.username == username)`. Returns the first result or
  `None`.

- [x] **Task 6.4:** In `repositories/user_repo.py`, add:
```python
  async def create(self, **kwargs) -> User
```
  Creates a `User(**kwargs)`, adds to session, flushes (does not commit), and returns
  the user. The caller is responsible for committing.

- [x] **Task 6.5:** In `repositories/user_repo.py`, add:
```python
  async def get_all(
      self,
      role: UserRole | None = None,
      is_active: bool | None = None,
      gate_number: int | None = None,
      page: int = 1,
      size: int = 20,
  ) -> tuple[list[User], int]
```
  Builds a `select(User)` query, applies filters for each non-None parameter, uses
  `offset((page-1)*size).limit(size)`. Returns `(users, total_count)` where
  `total_count` comes from a separate `select(func.count()).select_from(User)` with
  the same filters applied.

- [x] **Task 6.6:** In `repositories/user_repo.py`, add:
```python
  async def update_fields(self, user: User, **fields) -> User
```
  Sets each key-value pair in `fields` as an attribute on the `user` object, flushes
  the session, and returns the updated user. Does not commit.

- [x] **Task 6.7:** Update `repositories/__init__.py` to import and re-export
  `UserRepository`. Add `__all__`.

### 6b — AuditLog Repository

- [x] **Task 6.8:** Create `repositories/audit_log_repo.py`. Define an
  `AuditLogRepository` class with `__init__(self, db: AsyncSession)`. Add one method:
```python
  async def create(
      self,
      actor_id: int,
      action: str,
      entity_type: str,
      entity_id: int,
      payload_before: str | None = None,
      payload_after: str | None = None,
  ) -> AuditLog
```
  Creates an `AuditLog(...)`, adds to session, flushes, returns the log entry. Does
  not commit. Add `AuditLogRepository` to `repositories/__init__.py`.

---

## Group 7 — Services

- [x] **Task 7.1:** Create `services/__init__.py` as an empty file.

### 7a — Auth Service

- [x] **Task 7.2:** Create `services/auth_service.py`. Define a custom exception class
  `AuthenticationError(Exception)` at the top of the file. It takes an optional
  `message: str = "Invalid credentials"` in `__init__`. No other attributes.

- [x] **Task 7.3:** In `services/auth_service.py`, define an `AuthService` class with
  `__init__(self, settings: Settings)` storing `self.settings = settings`. Add one
  method:
```python
  def hash_password(self, plain: str) -> str
```
  Uses `bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12))`. Returns the
  decoded hash string. The plaintext value must not persist after this call.

- [x] **Task 7.4:** In `services/auth_service.py`, add:
```python
  def verify_password(self, plain: str, hashed: str) -> bool
```
  Uses `bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))`. Returns the
  boolean result. Must not short-circuit before `checkpw` completes.

- [x] **Task 7.5:** In `services/auth_service.py`, add:
```python
  def create_access_token(self, user_id: int, role: str) -> str
```
  Builds a payload dict: `{"sub": str(user_id), "role": role, "iat": utcnow_ts,
  "exp": utcnow_ts + timedelta(hours=settings.JWT_EXPIRE_HOURS)}`. Signs with
  `jose.jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)`.
  Returns the token string.

- [x] **Task 7.6:** In `services/auth_service.py`, add:
```python
  def decode_token(self, token: str) -> TokenPayload
```
  Calls `jose.jwt.decode(token, settings.SECRET_KEY,
  algorithms=[settings.JWT_ALGORITHM])`. Validates the result against `TokenPayload`
  schema. Raises `AuthenticationError("Token is invalid or expired")` on any
  `JWTError` or Pydantic validation failure.

- [x] **Task 7.7:** In `services/auth_service.py`, add:
```python
  async def authenticate_user(
      self, username: str, password: str, user_repo: UserRepository
  ) -> User
```
  Calls `user_repo.get_by_username(username.strip())`. If the user is not found, still
  calls `self.verify_password("dummy", DUMMY_HASH)` (constant-time), then raises
  `AuthenticationError`. If user found, calls `verify_password`; if False, raises
  `AuthenticationError`. If `user.is_active` is False, raises `AuthenticationError`.
  Returns the `User` on success. Define `DUMMY_HASH` as a module-level constant
  pre-computed bcrypt hash of the string `"__dummy__"`.

- [x] **Task 7.8:** Add `__all__ = ["AuthService", "AuthenticationError"]` to
  `services/auth_service.py`. Update `services/__init__.py` to import and re-export
  both.

### 7b — Audit Service

- [x] **Task 7.9:** Create `services/audit_service.py`. Define an `AuditService`
  class with `__init__(self, db: AsyncSession)`. Add one method:
```python
  async def log(
      self,
      actor_id: int,
      action: str,
      entity_type: str,
      entity_id: int,
      before: dict | None = None,
      after: dict | None = None,
  ) -> None
```
  Serializes `before` and `after` dicts to JSON strings (using `json.dumps`, removing
  any key named `"hashed_password"` before serialization). Instantiates
  `AuditLogRepository(self.db)` and calls its `create` method. Wraps the call in a
  `try/except Exception` that logs the error using Python `logging.getLogger(__name__)`
  at `ERROR` level but does not re-raise. Does not commit — the caller commits.

- [x] **Task 7.10:** Add `__all__ = ["AuditService"]` to `services/audit_service.py`.
  Update `services/__init__.py`.

### 7c — User Service

- [x] **Task 7.11:** Create `services/user_service.py`. Define a `UserService` class
  with:
```python
  def __init__(
      self,
      db: AsyncSession,
      user_repo: UserRepository,
      auth_service: AuthService,
      audit_service: AuditService,
  )
```
  Store all four as instance attributes. No logic in `__init__`.

- [x] **Task 7.12:** In `services/user_service.py`, add:
```python
  async def create_user(self, data: UserCreate) -> User
```
  Checks for an existing user with the same username via `user_repo.get_by_username`.
  If found, raises `HTTPException(409, detail="...", headers={"X-Error-Code":
  "USERNAME_ALREADY_EXISTS"})`. Hashes the password via `auth_service.hash_password`.
  Calls `user_repo.create(...)` with all fields except the raw `password`, using
  `hashed_password` instead. Calls `audit_service.log(actor_id=new_user.id,
  action="USER_CREATED", entity_type="user", entity_id=new_user.id, before=None,
  after={...})`. Commits `self.db`. Returns the created `User`.

- [x] **Task 7.13:** In `services/user_service.py`, add:
```python
  async def deactivate_user(self, user_id: int, actor_id: int) -> User
```
  Raises `HTTPException(403, code="CANNOT_DEACTIVATE_SELF")` if `user_id == actor_id`.
  Fetches user via `user_repo.get_by_id`; raises `HTTPException(404,
  code="USER_NOT_FOUND")` if not found. Raises `HTTPException(409,
  code="USER_ALREADY_INACTIVE")` if `user.is_active` is already `False`. Calls
  `user_repo.update_fields(user, is_active=False)`. Calls `audit_service.log` with
  action `"USER_DEACTIVATED"`. Commits. Returns the updated user.

- [x] **Task 7.14:** In `services/user_service.py`, add:
```python
  async def reset_password(
      self, user_id: int, new_password: str, actor_id: int
  ) -> User
```
  Fetches user; raises `HTTPException(404)` if not found. Calls
  `auth_service.hash_password(new_password)`. Calls `user_repo.update_fields(user,
  hashed_password=new_hash)`. Calls `audit_service.log` with action
  `"USER_PASSWORD_RESET"`, `before=None`, `after={"user_id": user_id}` (never log the
  password). Commits. Returns the updated user.

- [x] **Task 7.15:** In `services/user_service.py`, add:
```python
  async def get_all_users(
      self,
      role: UserRole | None,
      is_active: bool | None,
      gate_number: int | None,
      page: int,
      size: int,
  ) -> tuple[list[User], int]
```
  Delegates directly to `user_repo.get_all(...)` and returns the result unchanged.

- [x] **Task 7.16:** Add `__all__ = ["UserService"]` to `services/user_service.py`.
  Update `services/__init__.py`.

---

## Group 8 — FastAPI Dependencies

- [x] **Task 8.1:** Create `dependencies.py` in the project root. Define:
```python
  async def get_current_user(
      request: Request, db: AsyncSession = Depends(get_db)
  ) -> User
```
  Reads the `pgms_token` cookie from `request.cookies`. If absent, raises
  `HTTPException(401, code="UNAUTHORIZED")`. Instantiates `AuthService(get_settings())`
  and calls `decode_token`. If `AuthenticationError` is raised, raises
  `HTTPException(401, code="UNAUTHORIZED")`. Fetches the user from DB by `int(payload.
  sub)`. If user not found or `is_active` is False, raises `HTTPException(401,
  code="UNAUTHORIZED")`. Returns the `User`.

- [x] **Task 8.2:** In `dependencies.py`, define:
```python
  async def require_operator(
      user: User = Depends(get_current_user),
  ) -> User
```
  Raises `HTTPException(403, code="INSUFFICIENT_PERMISSIONS")` if
  `user.role != UserRole.OPERATOR`. Returns `user`.

- [x] **Task 8.3:** In `dependencies.py`, define:
```python
  async def require_admin(
      user: User = Depends(get_current_user),
  ) -> User
```
  Raises `HTTPException(403, code="INSUFFICIENT_PERMISSIONS")` if
  `user.role != UserRole.ADMIN`. Returns `user`.

- [x] **Task 8.4:** In `dependencies.py`, define:
```python
  async def require_any_role(
      user: User = Depends(get_current_user),
  ) -> User
```
  Returns `user` unconditionally (any authenticated user passes). Add
  `__all__ = ["get_current_user", "require_operator", "require_admin",
  "require_any_role"]`.

---

## Group 9 — Routes

- [x] **Task 9.1:** Create `routes/__init__.py` as an empty file.

### 9a — Auth API Routes

- [x] **Task 9.2:** Create `routes/auth.py`. Define `router = APIRouter(prefix=
  "/api/v1/auth", tags=["auth"])`. Add the `POST /login` endpoint:
  - Accepts `username: str = Form(...)` and `password: str = Form(...)`.
  - Instantiates `AuthService`, `UserRepository`, and `AuditService`.
  - Calls `auth_service.authenticate_user(username, password, user_repo)`.
  - On `AuthenticationError`, returns `JSONResponse(status_code=401,
    content={"detail": "...", "code": "INVALID_CREDENTIALS"})`.
  - On success, calls `auth_service.create_access_token`, creates a `JSONResponse`
    with `{"data": LoginResponse(...).model_dump()}`, and sets the `pgms_token` cookie
    (`httponly=True`, `samesite="strict"`, `secure` based on environment,
    `max_age=settings.JWT_EXPIRE_HOURS * 3600`).
  - Calls `audit_service.log` with action `"USER_LOGIN"`, commits `db`, returns
    response.

- [x] **Task 9.3:** In `routes/auth.py`, add the `POST /logout` endpoint:
  - Requires no authentication (public endpoint).
  - Creates a `JSONResponse({"data": "logged out"})`.
  - Deletes `pgms_token` cookie by setting `max_age=0`.
  - Returns the response.

- [x] **Task 9.4:** In `routes/auth.py`, add the `GET /me` endpoint:
  - Uses `Depends(require_any_role)` to get the current user.
  - Returns `{"data": UserResponse.model_validate(user).model_dump()}` with status
    `200`.

### 9b — User Management API Routes

- [x] **Task 9.5:** Create `routes/users.py`. Define `router = APIRouter(prefix=
  "/api/v1/users", tags=["users"])`. Add `POST /` endpoint:
  - Uses `Depends(require_admin)`.
  - Accepts `data: UserCreate` as JSON body.
  - Instantiates `UserService` with all dependencies.
  - Calls `user_service.create_user(data)`.
  - Returns `{"data": UserResponse.model_validate(user).model_dump()}` with status
    `201`.

- [x] **Task 9.6:** In `routes/users.py`, add `GET /` endpoint:
  - Uses `Depends(require_admin)`.
  - Query params: `role: UserRole | None = None`, `is_active: bool | None = None`,
    `gate_number: int | None = None`, `page: int = Query(1, ge=1)`,
    `size: int = Query(20, ge=1, le=100)`.
  - Calls `user_service.get_all_users(...)`.
  - Returns `PaginatedResponse[UserResponse]` with `data`, `total`, `page`, `size`.

- [x] **Task 9.7:** In `routes/users.py`, add `GET /{user_id}` endpoint:
  - Uses `Depends(require_admin)`.
  - Fetches user via `UserRepository.get_by_id`.
  - Returns `{"data": UserResponse(...)}` or `HTTPException(404,
    code="USER_NOT_FOUND")`.

- [x] **Task 9.8:** In `routes/users.py`, add `PATCH /{user_id}/deactivate` endpoint:
  - Uses `Depends(require_admin)`.
  - Calls `user_service.deactivate_user(user_id, actor_id=current_user.id)`.
  - Returns `{"data": UserResponse(...)}` with status `200`.

- [x] **Task 9.9:** In `routes/users.py`, add `PATCH /{user_id}/reset-password`
  endpoint:
  - Uses `Depends(require_admin)`.
  - Accepts `data: UserUpdatePassword` as JSON body.
  - Calls `user_service.reset_password(user_id, data.new_password,
    actor_id=current_user.id)`.
  - Returns `{"data": UserResponse(...)}` with status `200`.

### 9c — UI Auth Routes

- [x] **Task 9.10:** Create `routes/ui_auth.py`. Define `router = APIRouter(
  prefix="/ui", tags=["ui-auth"])`. Add `GET /login` endpoint:
  - Checks for a valid `pgms_token` cookie silently (no dependency injection — manual
    check to avoid raising exceptions).
  - If valid token found: redirect operators to `/ui/operator/dashboard`, admins to
    `/ui/admin/dashboard`.
  - If no valid token: returns `TemplateResponse("auth/login.html", {"request":
    request, "error": None})`.

- [x] **Task 9.11:** In `routes/ui_auth.py`, add `POST /login` endpoint:
  - Accepts form fields `username: str = Form(...)` and `password: str = Form(...)`.
  - Calls `authenticate_user`; on failure, re-renders `auth/login.html` with the
    Arabic error message from `translations/ar.json` key
    `"login.error_invalid_credentials"` passed as `{"error": "..."}` in the template
    context.
  - On success, sets the JWT cookie and returns `RedirectResponse` to
    `/ui/operator/dashboard` (operator) or `/ui/admin/dashboard` (admin) with status
    code `303`.

- [x] **Task 9.12:** In `routes/ui_auth.py`, add `POST /logout` endpoint:
  - Clears the `pgms_token` cookie.
  - Returns `RedirectResponse("/ui/login", status_code=303)`.

---

## Group 10 — Templates

- [x] **Task 10.1:** Create `templates/base.html`. It must:
  - Set `<html lang="ar" dir="rtl">`.
  - Load Tailwind CSS from a local built file at `/static/css/tailwind.min.css` (not
    a CDN).
  - Define blocks: `{% block title %}`, `{% block head %}`, `{% block nav %}`,
    `{% block content %}`, `{% block scripts %}`.
  - Include a `{% block nav %}` with a logout form (POST to `/ui/logout`) rendered as
    a button. Hide nav on the login page by leaving `{% block nav %}` empty there.
  - Use only CSS logical properties (`margin-inline-start`, not `margin-left`) in any
    inline styles.
  - Set `<meta name="viewport" content="width=device-width, initial-scale=1.0">`.

- [x] **Task 10.2:** Create `templates/auth/login.html` extending `base.html`. It
  must:
  - Override `{% block nav %}` with an empty block (no nav on login page).
  - Render a centered card containing: page title from `ar.json` key `"login.title"`,
    a `<form method="POST" action="/ui/login">`, username input, password input, submit
    button.
  - All input fields: `min-height: 48px`, `font-size: 16px`, `width: 100%`.
  - Submit button: `min-height: 48px`, `width: 100%`.
  - If `error` is present in the template context, render an error block above the form
    displaying the `error` string in a visually distinct red/warning block.
  - Total rendered page must not require any resource from an external domain.

- [x] **Task 10.3:** Create a minimal `templates/operator/dashboard.html` extending
  `base.html`. This is a placeholder only for Phase 1. It must render:
  - A heading with the operator's `full_name`.
  - The operator's assigned `gate_number`.
  - A message in Arabic: "لا توجد بيانات بعد" (No data yet).
  This template is accessed after login redirect and must not error.

---

## Group 11 — Jinja2 Template Utilities

- [x] **Task 11.1:** Create `utils/__init__.py` as an empty file.

- [x] **Task 11.2:** Create `utils/templates.py`. Define a function
  `load_translations(path: str = "translations/ar.json") -> dict` that reads and
  returns the JSON file as a Python dict. Cache the result with `@functools.lru_cache`.

- [x] **Task 11.3:** In `utils/templates.py`, define a Jinja2 filter function
  `translate_filter(key: str, translations: dict) -> str`:
  - Returns `translations[key]` if the key exists.
  - In development: returns `f"[[{key}]]"`.
  - In production: raises `KeyError` (startup validation will catch missing keys
    separately).

- [x] **Task 11.4:** Create `utils/jinja.py`. Define a function
  `create_jinja2_environment(settings: Settings) -> Jinja2Templates`:
  - Instantiates `Jinja2Templates(directory="templates")`.
  - Adds the `t` global function that wraps `translate_filter` with the loaded
    translations dict pre-bound (partial application), so templates can call
    `{{ t("login.title") }}`.
  - Returns the configured `Jinja2Templates` instance. This function is called once at
    app startup.

---

## Group 12 — Application Entry Point (`main.py`)

- [x] **Task 12.1:** Create `main.py` in the project root. Import `FastAPI`,
  `get_settings`, and all four routers (`auth`, `users`, `ui_auth`). Instantiate the
  app:
```python
  app = FastAPI(
      title=settings.APP_NAME,
      docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
      redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
  )
```

- [x] **Task 12.2:** In `main.py`, add `CORSMiddleware` to the app using
  `app.add_middleware(CORSMiddleware, ...)`. Read allowed origins from
  `settings.CORS_ORIGINS`. At startup, if `settings.ENVIRONMENT == "production"` and
  `"*"` is in `settings.CORS_ORIGINS`, raise `RuntimeError("Wildcard CORS origin
  forbidden in production")`.

- [x] **Task 12.3:** In `main.py`, mount the `StaticFiles` directory:
  `app.mount("/static", StaticFiles(directory="static"), name="static")`.
  Also call `create_jinja2_environment(settings)` and store the result as a module-
  level `templates` variable to be imported by route files.

- [x] **Task 12.4:** In `main.py`, include all routers:
```python
  app.include_router(auth_router)
  app.include_router(users_router)
  app.include_router(ui_auth_router)
```
  Add a root redirect: `GET /` → `RedirectResponse("/ui/login")`.

- [x] **Task 12.5:** In `main.py`, add a global exception handler for
  `HTTPException` that returns a `JSONResponse` with `{"detail": exc.detail, "code":
  getattr(exc, "code", "ERROR")}`. Add a generic `Exception` handler that logs the
  error at `ERROR` level and returns `{"detail": "Internal server error", "code":
  "INTERNAL_ERROR"}` with status `500` (detail is sanitized in non-development
  environments).

- [x] **Task 12.6:** In `main.py`, add a database availability check as an
  `@app.middleware("http")` or lifespan event. On startup, attempt a simple `SELECT 1`
  via the async engine. If it fails, log `CRITICAL` but allow the app to start. For
  each request to a DB-dependent route, if the DB is unreachable, return
  `JSONResponse(status_code=503, content={"detail": "...", "code":
  "DATABASE_UNAVAILABLE"})`.

---

## Group 13 — Seed Script

- [x] **Task 13.1:** Create `seed.py` in the project root. Add an `async def main()`
  function guarded by `if __name__ == "__main__": asyncio.run(main())`. At the start
  of `main()`: run `alembic upgrade head` programmatically using the Alembic `Config`
  and `command.upgrade` API. If tables do not exist after upgrade, print an error and
  exit.

- [x] **Task 13.2:** In `seed.py`, implement `seed_admin_user(db, settings,
  auth_service) -> dict` as a standalone async function. It:
  - Reads `SEED_ADMIN_USERNAME`, `SEED_ADMIN_PASSWORD`, `SEED_ADMIN_FULL_NAME` from
    settings (add these as optional fields to `Settings` with `default=None`).
  - Checks if a user with that username already exists.
  - If not: creates the user with `role=UserRole.ADMIN`, `gate_number=None`.
  - Returns `{"created": True}` or `{"created": False, "reason": "already exists"}`.

- [x] **Task 13.3:** In `seed.py`, implement `seed_operator_user(db, settings,
  auth_service, gate: int) -> dict` as a standalone async function. It:
  - Reads `SEED_OP_{gate}_USERNAME`, `SEED_OP_{gate}_PASSWORD`,
    `SEED_OP_{gate}_FULL_NAME` from environment directly using `os.environ.get`.
  - Checks for existing username; skips if found.
  - Creates the operator with `role=UserRole.OPERATOR`, `gate_number=gate`.
  - Returns result dict.

- [x] **Task 13.4:** In `seed.py`, implement `seed_default_pricing_rule(db) -> dict`
  that creates one `PricingRule` with: `label="السعر الافتراضي"`,
  `rate_per_hour=500`, `minimum_charge=0`, `grace_period_mins=15`, `is_active=True`,
  `effective_from=utcnow()`, `effective_until=None`, `created_by=<admin_user_id>`.
  Skips if any pricing rule with `label="السعر الافتراضي"` already exists.

- [x] **Task 13.5:** In `seed.py`'s `main()`, call all three seed functions (admin +
  five operator gates + pricing rule), collect their result dicts, and print a
  formatted summary table to stdout showing each entity, its status (created / skipped),
  and any reason. Commit once after all seeds complete. Rollback and print an error if
  any exception occurs.

---

## Group 14 — Tests: Configuration

- [x] **Task 14.1:** Create `tests/__init__.py` and `tests/unit/__init__.py` and
  `tests/integration/__init__.py` as empty files.

- [x] **Task 14.2:** Create `tests/conftest.py`. Define a `settings_override` pytest
  fixture (scope `"session"`) that returns a `Settings` instance with:
  `DATABASE_URL="sqlite+aiosqlite:///:memory:"`, `SECRET_KEY="a" * 32`,
  `ENVIRONMENT="development"`, `DEBUG=True`, `JWT_EXPIRE_HOURS=1`.

- [x] **Task 14.3:** In `tests/conftest.py`, define an `engine` fixture (scope
  `"session"`) that creates an async SQLAlchemy engine from the test `DATABASE_URL`.
  Define a `db_tables` fixture (scope `"session"`, `autouse=True`) that runs
  `Base.metadata.create_all(engine.sync_engine)` once and drops all tables after the
  session.

- [x] **Task 14.4:** In `tests/conftest.py`, define a `db_session` fixture (scope
  `"function"`) that opens a new `AsyncSession`, wraps it in a `SAVEPOINT`-based nested
  transaction (for rollback isolation between tests), yields the session, then rolls
  back after each test. This ensures each test starts with a clean database state.

- [x] **Task 14.5:** In `tests/conftest.py`, define an `auth_service` fixture that
  returns `AuthService(settings_override)`. Define a `user_repo` fixture that returns
  `UserRepository(db_session)`. Define an `audit_service` fixture that returns
  `AuditService(db_session)`.

- [x] **Task 14.6:** In `tests/conftest.py`, define an `async_client` fixture (scope
  `"function"`) using `httpx.AsyncClient(app=app, base_url="http://test")`. Override
  the `get_db` dependency on the `app` to yield the `db_session` fixture's session.
  Override `get_settings` to return `settings_override`.

---

## Group 15 — Tests: Unit Tests

### 15a — AuthService Unit Tests

- [x] **Task 15.1:** Create `tests/unit/test_auth_service.py`. Write test
  `test_hash_password_returns_string`: calls `auth_service.hash_password("secret123")`
  and asserts the result is a non-empty string not equal to `"secret123"`.

- [x] **Task 15.2:** Add test `test_hash_password_different_hashes_for_same_input`:
  hashes the same password twice and asserts the two hashes are not equal (bcrypt
  salting).

- [x] **Task 15.3:** Add test `test_verify_password_correct`: hashes a password, then
  calls `verify_password(plain, hashed)` and asserts `True`.

- [x] **Task 15.4:** Add test `test_verify_password_wrong_password`: hashes
  `"correct"`, then calls `verify_password("wrong", hashed)` and asserts `False`.

- [x] **Task 15.5:** Add test `test_create_access_token_returns_string`: calls
  `create_access_token(user_id=1, role="operator")` and asserts the result is a
  non-empty string containing two `.` characters (JWT structure).

- [x] **Task 15.6:** Add test `test_decode_token_valid`: creates a token, decodes it,
  asserts `payload.sub == "1"` and `payload.role == "operator"`.

- [x] **Task 15.7:** Add test `test_decode_token_expired`: uses `freezegun.freeze_time`
  to set the clock 9 hours in the future after creating a 1-hour token. Asserts
  `AuthenticationError` is raised.

- [x] **Task 15.8:** Add test `test_decode_token_tampered`: modifies one character of
  a valid token string and asserts `AuthenticationError` is raised.

- [x] **Task 15.9:** Add test `test_authenticate_user_success` (async): creates a
  `User` record in `db_session` with a hashed password, calls
  `authenticate_user("username", "plain", user_repo)`, asserts the returned user's
  `id` matches.

- [x] **Task 15.10:** Add test `test_authenticate_user_wrong_password` (async):
  asserts `AuthenticationError` raised when password is wrong.

- [x] **Task 15.11:** Add test `test_authenticate_user_not_found` (async): asserts
  `AuthenticationError` raised when username does not exist.

- [x] **Task 15.12:** Add test `test_authenticate_user_inactive` (async): creates an
  inactive user (`is_active=False`) and asserts `AuthenticationError` raised.

### 15b — AuditService Unit Tests

- [x] **Task 15.13:** Create `tests/unit/test_audit_service.py`. Write test
  `test_log_creates_record` (async): calls `audit_service.log(actor_id=1,
  action="USER_CREATED", entity_type="user", entity_id=1, before=None,
  after={"name": "x"})`. Queries `AuditLog` from `db_session`. Asserts one record
  exists with the correct `action` and `entity_id`.

- [x] **Task 15.14:** Add test `test_log_strips_hashed_password` (async): calls `log`
  with `after={"hashed_password": "secret", "name": "Ahmed"}`. Queries the log record.
  Parses `payload_after` JSON. Asserts `"hashed_password"` is not present in the parsed
  dict and `"name"` is present.

- [x] **Task 15.15:** Add test `test_log_does_not_raise_on_db_error` (async): patches
  `AuditLogRepository.create` to raise `Exception("DB error")`. Calls
  `audit_service.log(...)`. Asserts no exception propagates to the caller.

### 15c — UserService Unit Tests

- [x] **Task 15.16:** Create `tests/unit/test_user_service.py`. Write test
  `test_create_user_success` (async): calls `user_service.create_user(UserCreate(...))`
  with valid data. Asserts returned user has the correct `username`, `role`, and that
  `hashed_password` differs from the plaintext input.

- [x] **Task 15.17:** Add test `test_create_user_duplicate_username` (async): creates
  a user, then calls `create_user` again with the same username. Asserts
  `HTTPException` with status `409` is raised.

- [x] **Task 15.18:** Add test `test_deactivate_user_success` (async): creates an
  active user, calls `deactivate_user(user.id, actor_id=admin.id)`. Asserts
  `user.is_active` is `False`.

- [x] **Task 15.19:** Add test `test_deactivate_user_self` (async): asserts
  `HTTPException(403)` when `user_id == actor_id`.

- [x] **Task 15.20:** Add test `test_deactivate_user_already_inactive` (async):
  creates an inactive user, calls `deactivate_user`, asserts `HTTPException(409)`.

- [x] **Task 15.21:** Add test `test_reset_password_success` (async): resets password,
  then calls `auth_service.verify_password(new_plain, user.hashed_password)` and
  asserts `True`.

---

## Group 16 — Tests: Integration Tests

### 16a — Auth Endpoint Integration Tests

- [x] **Task 16.1:** Create `tests/integration/test_auth_routes.py`. Write test
  `test_login_success` (async): POSTs valid credentials to `/api/v1/auth/login`.
  Asserts status `200`, response body contains `data.role`, and `pgms_token` cookie is
  set.

- [x] **Task 16.2:** Add test `test_login_wrong_password` (async): POSTs wrong
  password. Asserts status `401` and `code == "INVALID_CREDENTIALS"`.

- [x] **Task 16.3:** Add test `test_login_unknown_username` (async): POSTs unknown
  username. Asserts status `401` and `code == "INVALID_CREDENTIALS"`.

- [x] **Task 16.4:** Add test `test_login_inactive_user` (async): creates an inactive
  user, POSTs their credentials. Asserts `401`.

- [x] **Task 16.5:** Add test `test_logout_clears_cookie` (async): logs in, then POSTs
  to `/api/v1/auth/logout`. Asserts status `200` and `pgms_token` cookie `max-age` is
  `0` or the cookie is absent.

- [x] **Task 16.6:** Add test `test_logout_without_session` (async): POSTs to
  `/api/v1/auth/logout` with no cookie. Asserts status `200` (idempotent).

- [x] **Task 16.7:** Add test `test_get_me_authenticated` (async): logs in, then GETs
  `/api/v1/auth/me`. Asserts status `200` and response contains `user_id`.

- [x] **Task 16.8:** Add test `test_get_me_unauthenticated` (async): GETs
  `/api/v1/auth/me` with no cookie. Asserts status `401`.

- [x] **Task 16.9:** Add test `test_get_me_expired_token` (async): creates a token with
  `exp` set to the past using `freezegun`. Sets it as cookie. GETs `/api/v1/auth/me`.
  Asserts `401`.

### 16b — User Management Integration Tests

- [x] **Task 16.10:** Create `tests/integration/test_user_routes.py`. Write test
  `test_create_user_as_admin` (async): logs in as admin, POSTs to `/api/v1/users/`
  with valid operator data. Asserts status `201` and response contains `id`.

- [x] **Task 16.11:** Add test `test_create_user_as_operator_forbidden` (async): logs
  in as operator, POSTs to `/api/v1/users/`. Asserts status `403`.

- [x] **Task 16.12:** Add test `test_create_user_duplicate_username` (async): creates
  a user, then creates another with the same username. Asserts `409` with code
  `USERNAME_ALREADY_EXISTS`.

- [x] **Task 16.13:** Add test `test_create_operator_without_gate` (async): POSTs
  operator with `gate_number=null`. Asserts `422`.

- [x] **Task 16.14:** Add test `test_create_operator_invalid_gate` (async): POSTs
  `gate_number=6`. Asserts `422`.

- [x] **Task 16.15:** Add test `test_create_admin_with_gate` (async): POSTs admin with
  `gate_number=1`. Asserts `422`.

- [x] **Task 16.16:** Add test `test_list_users_as_admin` (async): creates 3 users,
  GETs `/api/v1/users/`. Asserts status `200` and `total >= 3`.

- [x] **Task 16.17:** Add test `test_list_users_filter_by_role` (async): creates one
  operator and one admin, GETs `/api/v1/users/?role=operator`. Asserts all returned
  users have `role == "operator"`.

- [x] **Task 16.18:** Add test `test_get_user_by_id` (async): creates a user, GETs
  `/api/v1/users/{id}`. Asserts `200` and matching `username`.

- [x] **Task 16.19:** Add test `test_get_user_not_found` (async): GETs
  `/api/v1/users/99999`. Asserts `404` and `code == "USER_NOT_FOUND"`.

- [x] **Task 16.20:** Add test `test_deactivate_user` (async): creates an active user,
  PATCHes `/api/v1/users/{id}/deactivate`. Asserts `200` and `is_active == false`.

- [x] **Task 16.21:** Add test `test_deactivate_self_forbidden` (async): admin tries
  to deactivate their own account. Asserts `403`.

- [x] **Task 16.22:** Add test `test_deactivate_already_inactive` (async): PATCHes
  deactivate twice. Asserts second call returns `409`.

- [x] **Task 16.23:** Add test `test_reset_password` (async): resets a user's password,
  then attempts login with the new password. Asserts login returns `200`.

- [x] **Task 16.24:** Add test `test_hashed_password_never_in_response` (async):
  creates a user and checks that the string `"hashed_password"` does not appear anywhere
  in the response body of `POST /api/v1/users/`, `GET /api/v1/users/`,
  `GET /api/v1/users/{id}`, or `GET /api/v1/auth/me`.

### 16c — UI Route Integration Tests

- [x] **Task 16.25:** Create `tests/integration/test_ui_auth_routes.py`. Write test
  `test_login_page_renders` (async): GETs `/ui/login`. Asserts status `200` and
  response content-type is `text/html`. Asserts the Arabic string for `"login.title"`
  appears in the response body.

- [x] **Task 16.26:** Add test `test_ui_login_success_operator_redirect` (async): POSTs
  to `/ui/login` with valid operator credentials. Asserts redirect to
  `/ui/operator/dashboard` (status `303` and `Location` header).

- [x] **Task 16.27:** Add test `test_ui_login_failure_rerenders_form` (async): POSTs
  to `/ui/login` with wrong password. Asserts status `200` (re-render) and Arabic
  error message appears in response body.

- [x] **Task 16.28:** Add test `test_ui_logout_redirects_to_login` (async): POSTs to
  `/ui/logout`. Asserts redirect to `/ui/login` with status `303`.

- [x] **Task 16.29:** Add test `test_protected_ui_route_redirects_unauthenticated`
  (async): GETs `/ui/operator/dashboard` with no cookie. Asserts redirect to
  `/ui/login`.

---

## Group 17 — Static Assets & Final Verification

- [x] **Task 17.1:** Install Tailwind CSS CLI locally. Create `tailwind.config.js`
  with `content: ["./templates/**/*.html"]`. Run `tailwind build -o
  static/css/tailwind.min.css --minify`. Commit the output file. Add the build command
  to a `Makefile` target named `css`.

- [x] **Task 17.2:** Create a `Makefile` in the project root with the following
  targets:
  - `install`: `pip install -r requirements.txt`.
  - `css`: Tailwind build command from Task 17.1.
  - `migrate`: `alembic upgrade head`.
  - `seed`: `python seed.py`.
  - `run`: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`.
  - `test`: `pytest -v --tb=short`.
  - `lint`: `ruff check . && black --check .`.
  - `typecheck`: `mypy .`.

- [x] **Task 17.3:** Run the full test suite with `pytest -v`. Confirm all tests pass.
  Confirm coverage of `services/auth_service.py` is 100% by running
  `pytest --cov=services/auth_service --cov-report=term-missing`. Fix any failures
  before marking this task complete.

- [x] **Task 17.4:** Run `black .` and `ruff check .` on the entire project. Fix all
  formatting and lint errors. Run `mypy .` and fix all type errors. No warnings or
  errors may remain when this task is checked.

- [x] **Task 17.5:** Manually start the server with `make run`. Open
  `http://localhost:8000/ui/login` in a browser resized to 360px width. Verify:
  - Page renders in Arabic RTL with no horizontal scrollbar.
  - All text is visible and not clipped.
  - The submit button is at least 48px tall and full width.
  - Submitting with wrong credentials shows the Arabic error message.
  - Submitting with correct credentials redirects to the dashboard.
  - Logout button appears on dashboard and clears the session.
  Record this as a manual QA pass in a `QA_LOG.md` file with date and tester name.
# Phase 1 Specification — Foundation: Database, Config & Authentication

> **Version:** 1.0
> **Scope:** User stories, functional requirements, non-functional requirements, and edge cases
> covering database setup, environment configuration, and the authentication system.
> **Prerequisite reading:** `constitution.md`, `master-plan.md`
> **Out of scope for this phase:** Parking sessions, shift management, pricing, receipts, admin
> dashboard, and all operator UI beyond the login screen.

---

## 1. User Stories

### 1.1 System Administrator (DevOps / Deployer)

---

**US-001 — Environment Configuration**
> *As a system deployer, I want all configuration values (database URL, secret key, environment
> name) to be read from environment variables, so that I can deploy the same codebase to
> development, staging, and production without modifying any source files.*

**Acceptance Criteria:**
- All config values are declared in a single `config.py` using `pydantic-settings`.
- A `.env.example` file lists every required key with a placeholder value and an inline comment.
- The app refuses to start if any required variable is missing, printing a clear error message
  identifying the missing key.
- No connection string, secret, or credential appears anywhere in source code or migration files.

---

**US-002 — Database Initialization**
> *As a system deployer, I want to run a single command to create all database tables and seed
> essential data, so that the system is ready to use immediately after deployment.*

**Acceptance Criteria:**
- Running `alembic upgrade head` creates all five tables cleanly on both SQLite and PostgreSQL.
- Running `python seed.py` creates one admin account, five operator accounts (one per gate), and
  one default pricing rule without errors.
- Running the seed script a second time does not create duplicate records; it is idempotent.
- All seeded passwords are read from environment variables, not hardcoded.

---

**US-003 — Database Portability**
> *As a system deployer, I want to switch between SQLite (development) and PostgreSQL (production)
> by changing only the `DATABASE_URL` environment variable, so that local development requires
> no external services.*

**Acceptance Criteria:**
- The full test suite passes against both SQLite and PostgreSQL with no code changes.
- The Alembic migration chain produces identical schemas on both engines.
- `BOOLEAN`, `TIMESTAMP`, and `VARCHAR` columns behave identically on both engines as validated
  by integration tests.

---

### 1.2 Admin

---

**US-004 — Admin Account Creation (Seeded)**
> *As an admin, I want a pre-created admin account available after initial setup, so that I can
> log in immediately and create operator accounts without a bootstrapping problem.*

**Acceptance Criteria:**
- The seed script creates exactly one admin account with `role = 'admin'` and `gate_number = NULL`.
- The admin account credentials are set via `SEED_ADMIN_USERNAME` and `SEED_ADMIN_PASSWORD`
  environment variables.
- The admin can log in through the login page and receive a valid JWT session.
- The admin account is marked `is_active = TRUE`.

---

**US-005 — Create Operator Account**
> *As an admin, I want to create operator accounts and assign each to a specific gate number,
> so that each physical gate has a dedicated login credential.*

**Acceptance Criteria:**
- `POST /api/v1/users/` accepts `full_name`, `username`, `password`, `role`, `gate_number`.
- `gate_number` is required when `role = 'operator'` and must be an integer between 1 and 5.
- `gate_number` must be `null` when `role = 'admin'`.
- The endpoint rejects duplicate `username` values with `409 Conflict` and code
  `USERNAME_ALREADY_EXISTS`.
- The created user is returned in the response with `hashed_password` excluded.
- The action is recorded in `audit_logs` with action `USER_CREATED`.

---

**US-006 — Deactivate Operator Account**
> *As an admin, I want to deactivate an operator's account without deleting it, so that I
> preserve their historical records while revoking access immediately.*

**Acceptance Criteria:**
- `PATCH /api/v1/users/{id}/deactivate` sets `is_active = FALSE` on the target user.
- A deactivated user's JWT (if currently held) is rejected on the next request.
- The admin cannot deactivate their own account.
- The action is recorded in `audit_logs` with action `USER_DEACTIVATED`.
- Attempting to deactivate an already-inactive user returns `409 Conflict` with code
  `USER_ALREADY_INACTIVE`.

---

**US-007 — View All Users**
> *As an admin, I want to list all users in the system with their role, gate, and active status,
> so that I can manage the team and spot unauthorized accounts.*

**Acceptance Criteria:**
- `GET /api/v1/users/` returns a paginated list of all users.
- Each entry includes: `id`, `full_name`, `username`, `role`, `gate_number`, `is_active`,
  `created_at`. Never includes `hashed_password`.
- Supports filtering via query params: `role`, `is_active`, `gate_number`.
- Accessible only to users with `role = 'admin'`.

---

### 1.3 Operator

---

**US-008 — Operator Login**
> *As an operator, I want to log in with my username and password on the Gate Workstation PC,
> so that I can access the gate application and begin my shift.*

**Acceptance Criteria:**
- `GET /ui/login` renders a mobile-first Arabic RTL login form.
- `POST /api/v1/auth/login` accepts `username` and `password`.
- On success, a `HttpOnly`, `SameSite=Strict` cookie named `pgms_token` is set containing
  a signed JWT.
- The operator is redirected to `/ui/operator/dashboard` after successful login.
- On failure, the login page re-renders with a generic Arabic error message. The specific
  reason (wrong username vs wrong password) is never disclosed.
- A locked-out (inactive) operator sees an account-disabled message and cannot log in.
- Successful login is recorded in `audit_logs` with action `USER_LOGIN`.

---

**US-009 — Operator Logout**
> *As an operator, I want a clearly visible logout button on every page, so that I can
> end my session securely when handing over the terminal.*

**Acceptance Criteria:**
- `POST /api/v1/auth/logout` clears the `pgms_token` cookie.
- After logout, all protected routes redirect to `/ui/login`.
- The logout button is present in the base template navigation on every authenticated page.
- Logout does not close or affect any open shift; shift management is a separate action.

---

**US-010 — Session Persistence on Workstation PC**
> *As an operator, I want my session to remain active for a full 8-hour shift without requiring
> re-authentication, so that I am not interrupted during busy periods.*

**Acceptance Criteria:**
- JWT tokens have an expiry of exactly 8 hours from issuance.
- Requests made with an expired token return `401` and redirect to `/ui/login`.
- There is no automatic token refresh in Phase 1.
- Token expiry time is configurable via `JWT_EXPIRE_HOURS` env variable (default: `8`).

---

**US-011 — View Own Profile**
> *As an operator, I want to see my name, assigned gate, and current role displayed on
> the dashboard, so that I can confirm I am logged in with the correct account.*

**Acceptance Criteria:**
- `GET /api/v1/auth/me` returns `id`, `full_name`, `username`, `role`, `gate_number`.
- The operator dashboard renders `full_name` and `gate_number` prominently in Arabic.
- The endpoint returns `401` if no valid token is present.

---

## 2. Functional Requirements

### 2.1 Configuration & Environment (`config.py`)

| ID | Requirement |
|---|---|
| FR-CFG-001 | All settings are declared as fields on a single `Settings` class inheriting `pydantic_settings.BaseSettings`. |
| FR-CFG-002 | The following variables are required (app fails to start if absent): `DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT`. |
| FR-CFG-003 | The following variables are optional with defaults: `JWT_EXPIRE_HOURS=8`, `JWT_ALGORITHM="HS256"`, `DEBUG=False`, `APP_NAME="garage4u"`, `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10`, `CORS_ORIGINS=[]`. |
| FR-CFG-004 | `DEBUG=True` is only permitted when `ENVIRONMENT=development` or `staging`. If `ENVIRONMENT=production` and `DEBUG=True`, the app raises a `ValueError` on startup (`"DEBUG must not be True in production"`). |
| FR-CFG-005 | `SECRET_KEY` must be at least 32 characters, and `JWT_EXPIRE_HOURS` must be at least 1. The app raises `ValueError` on startup if violated. |
| FR-CFG-006 | A single `get_settings()` function returns a cached `Settings` instance (using `@lru_cache`). |
| FR-CFG-007 | `.env.example` is committed to the repository and stays synchronized with all `Settings` fields. |

---

### 2.2 Database Layer (`database.py`)

| ID | Requirement |
|---|---|
| FR-DB-001 | The async SQLAlchemy engine is created from `settings.DATABASE_URL` exclusively. |
| FR-DB-002 | `AsyncSession` is the only session type used. Synchronous sessions are forbidden. |
| FR-DB-003 | A `get_db()` async generator is provided as a FastAPI dependency; it yields one `AsyncSession` per request and closes it on exit regardless of exceptions. |
| FR-DB-004 | A declarative `Base` class is defined in `database.py` and imported by all models. |
| FR-DB-005 | Connection pool settings are configurable via env vars: `DB_POOL_SIZE` (default 5), `DB_MAX_OVERFLOW` (default 10). For SQLite, `StaticPool` is used with a connection listener setting `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=DELETE`, `PRAGMA synchronous=NORMAL`, and `PRAGMA busy_timeout=10000`. |

---

### 2.3 Database Models

#### Base Mixin — All Models

| ID | Requirement |
|---|---|
| FR-MDL-001 | Every model inherits a `TimestampMixin` providing `created_at` and `updated_at` columns. |
| FR-MDL-002 | `created_at` is set to `utcnow()` on insert and never modified thereafter. |
| FR-MDL-003 | `updated_at` is set to `utcnow()` on insert and auto-updated on every subsequent update via SQLAlchemy `onupdate`. |
| FR-MDL-004 | All timestamp columns are stored as UTC in the database. Conversion to local time is a display-layer concern only. |

#### `User` Model

| ID | Requirement |
|---|---|
| FR-MDL-010 | `id` — Integer, primary key, autoincrement. |
| FR-MDL-011 | `full_name` — VARCHAR(120), not nullable. |
| FR-MDL-012 | `username` — VARCHAR(60), unique, not nullable, indexed. |
| FR-MDL-013 | `hashed_password` — VARCHAR(255), not nullable. Plaintext password is never persisted. |
| FR-MDL-014 | `role` — Enum restricted to `'admin'` and `'operator'`; not nullable. |
| FR-MDL-015 | `gate_number` — SMALLINT, nullable. Must be between 1 and 5 inclusive when set. |
| FR-MDL-016 | `is_active` — BOOLEAN, not nullable, default `TRUE`. |
| FR-MDL-017 | A database-level `CHECK` constraint enforces: if `role = 'operator'` then `gate_number IS NOT NULL`; if `role = 'admin'` then `gate_number IS NULL`. |

#### `Shift` Model (stub — full spec in Phase 2)

| ID | Requirement |
|---|---|
| FR-MDL-020 | The `shifts` table is created in the Phase 1 migration with all columns defined in `master-plan.md`. |
| FR-MDL-021 | Foreign key `operator_id → users.id` is enforced at database level. |
| FR-MDL-022 | No service logic for shifts is implemented in Phase 1; the table exists for relational integrity. |

#### `PricingRule` Model (stub — full spec in Phase 2)

| ID | Requirement |
|---|---|
| FR-MDL-030 | The `pricing_rules` table is created in the Phase 1 migration with all columns defined in `master-plan.md`. |
| FR-MDL-031 | `rate_per_hour` and `minimum_charge` are stored as INTEGER (piastres). No FLOAT or DECIMAL columns for money. |
| FR-MDL-032 | The seed script inserts one default pricing rule: label `"السعر الافتراضي"`, `rate_per_hour = 1000` (10.00 EGP/hr), `first_hour_charge = 2000` (20.00 EGP), `subsequent_hour_charge = 1000` (10.00 EGP/hr), `minimum_charge = 0`, `grace_period_mins = 5`, `is_active = TRUE`. |

#### `ParkingSession` Model (stub — full spec in Phase 2)

| ID | Requirement |
|---|---|
| FR-MDL-040 | The `parking_sessions` table is created in the Phase 1 migration with all columns defined in `master-plan.md`. |
| FR-MDL-041 | Foreign keys `shift_id → shifts.id`, `operator_id → users.id`, `pricing_rule_id → pricing_rules.id` are enforced at database level. |
| FR-MDL-042 | No service or route logic for sessions is implemented in Phase 1. |

#### `AuditLog` Model

| ID | Requirement |
|---|---|
| FR-MDL-050 | `id` — Integer, primary key, autoincrement. |
| FR-MDL-051 | `actor_id` — Integer, FK → `users.id`, not nullable, indexed. |
| FR-MDL-052 | `action` — VARCHAR(80), not nullable, indexed. |
| FR-MDL-053 | `entity_type` — VARCHAR(40), not nullable. |
| FR-MDL-054 | `entity_id` — INTEGER, not nullable. |
| FR-MDL-055 | `payload_before` — TEXT (JSON-serialized), nullable. |
| FR-MDL-056 | `payload_after` — TEXT (JSON-serialized), nullable. |
| FR-MDL-057 | `created_at` — TIMESTAMP, not nullable, set on insert, never updated. No `updated_at` on this model. |
| FR-MDL-058 | No UPDATE or DELETE statement is ever issued against `audit_logs` by the application. |

---

### 2.4 Migrations (Alembic)

| ID | Requirement |
|---|---|
| FR-MIG-001 | Alembic is initialized with `alembic init alembic` and configured to use the async engine. |
| FR-MIG-002 | The initial migration creates all five tables in dependency order: `users` → `pricing_rules` → `shifts` → `parking_sessions` → `audit_logs`. |
| FR-MIG-003 | Each migration file has a descriptive `message` string (e.g., `"create initial schema"`). |
| FR-MIG-004 | `alembic upgrade head` completes without error on a fresh SQLite database. |
| FR-MIG-005 | `alembic downgrade base` cleanly drops all tables in reverse order. |
| FR-MIG-006 | Migration files are never edited after they have been applied to any shared environment. New changes always produce a new migration file. |

---

### 2.5 Seed Script (`seed.py`)

| ID | Requirement |
|---|---|
| FR-SEED-001 | The script is executable as `python seed.py` from the project root. It automatically runs `alembic upgrade head` prior to seeding. |
| FR-SEED-002 | Creates one admin user from env vars `SEED_ADMIN_USERNAME` (default `"Mohamed_abdou"`), `SEED_ADMIN_PASSWORD` (default `"198245"`), `SEED_ADMIN_FULL_NAME` (default `"محمد عبده"`). |
| FR-SEED-003 | Creates operator users for gates 1–5. Gate 1 default is `op_entry` ("عامل الدخول"), Gate 2 default is `op_exit` ("عامل الخروج"), Gates 3–5 defaults are `op3`–`op5`. Credentials are read from env vars `SEED_OP_{N}_USERNAME`, `SEED_OP_{N}_PASSWORD`, `SEED_OP_{N}_FULL_NAME`. |
| FR-SEED-004 | Creates one default `PricingRule` (values per FR-MDL-032). |
| FR-SEED-005 | The script checks for existing records by `username` / unique fields before inserting; it skips (not duplicates) any record that already exists. |
| FR-SEED-006 | On completion, the script prints a formatted summary table of created vs skipped records to stdout. |
| FR-SEED-007 | All seeded passwords are passed through `AuthService.hash_password()` before persistence. |

---

### 2.6 Authentication Service (`AuthService`)

| ID | Requirement |
|---|---|
| FR-AUTH-001 | `hash_password(plain: str) -> str` uses `bcrypt` with a work factor of 12. Plaintext password is zeroed/deleted from local scope immediately (`del plain`). |
| FR-AUTH-002 | `verify_password(plain: str, hashed: str) -> bool` uses `bcrypt.checkpw`. When a username is not found during authentication, `verify_password` is still executed against a dummy hash (`DUMMY_HASH`) to ensure constant-time execution and prevent timing attacks. Plaintext password is deleted (`del plain`). |
| FR-AUTH-003 | `create_access_token(user_id: int, role: str) -> str` generates a JWT signed with `SECRET_KEY` using `JWT_ALGORITHM`. Payload includes: `sub` (user_id as string), `role`, `iat` (issued-at), `exp` (expiry). |
| FR-AUTH-004 | `decode_token(token: str) -> TokenPayload` validates signature and expiry. Raises `AuthenticationError` for invalid or expired tokens. |
| FR-AUTH-005 | `authenticate_user(username: str, password: str, user_repo) -> User` fetches the user by username, verifies the password, and checks `is_active`. Returns the `User` object on success. |
| FR-AUTH-006 | `authenticate_user` raises `AuthenticationError` — not distinct errors per failure mode — for: user not found, wrong password, or inactive user. Error message is generic (`"Invalid credentials"`). |
| FR-AUTH-007 | No authentication logic lives in route handlers. Routes call `AuthService` methods only. |

---

### 2.7 Authentication Routes

| ID | Requirement |
|---|---|
| FR-AROUTE-001 | `POST /api/v1/auth/login` accepts `application/x-www-form-urlencoded` body with fields `username` and `password`. |
| FR-AROUTE-002 | On success, sets `pgms_token` cookie: `HttpOnly=True`, `SameSite=Strict`, `Secure=True` in staging and production, `Max-Age = JWT_EXPIRE_HOURS * 3600`. |
| FR-AROUTE-003 | On success, returns `{"data": {"user_id": ..., "role": ..., "full_name": ...}}` with status `200`. |
| FR-AROUTE-004 | On failure, returns `{"detail": "Invalid credentials", "code": "INVALID_CREDENTIALS"}` with status `401`. |
| FR-AROUTE-005 | `POST /api/v1/auth/logout` deletes the `pgms_token` cookie (sets `Max-Age=0`) and returns `200`. |
| FR-AROUTE-006 | `GET /api/v1/auth/me` reads token from `pgms_token` cookie or `Authorization: Bearer <token>` header, decodes JWT, fetches user from DB, and returns `UserResponse` (no `hashed_password`). Returns `401` if token is absent or invalid. |
| FR-AROUTE-007 | `GET /ui/login` renders `templates/auth/login.html`. If a valid token is already present, redirects to `/ui/operator/dashboard` (operators) or `/ui/admin/dashboard` (admins) with status `303`. |
| FR-AROUTE-008 | `POST /ui/login` (HTML form submission) calls `AuthService.authenticate_user`, sets the cookie, and redirects with `303`; on failure, re-renders the login page with Arabic error message. |
| FR-AROUTE-009 | `POST /ui/logout` clears the `pgms_token` cookie (`Max-Age=0`, `HttpOnly=True`, `SameSite=Strict`) and redirects to `/ui/login` with status `303`. |

---

### 2.8 Authorization Dependencies

| ID | Requirement |
|---|---|
| FR-AUTHZ-001 | `get_current_user(request)` — FastAPI dependency. Reads `pgms_token` cookie or `Authorization: Bearer <token>` header, decodes JWT, fetches and returns active `User`. Raises `HTTPException(401)` with header `X-Error-Code: UNAUTHORIZED` if token is missing, invalid, expired, or user is inactive. |
| FR-AUTHZ-002 | `require_operator(user: User = Depends(get_current_user))` — verifies user role is in (`UserRole.OPERATOR`, `UserRole.ADMIN`). Raises `HTTPException(403)` with header `X-Error-Code: INSUFFICIENT_PERMISSIONS` if user has neither role. |
| FR-AUTHZ-003 | `require_admin(user: User = Depends(get_current_user))` — raises `HTTPException(403)` with header `X-Error-Code: INSUFFICIENT_PERMISSIONS` if `user.role != UserRole.ADMIN`. |
| FR-AUTHZ-004 | `require_any_role` — accepts any authenticated user; used for endpoints shared between operators and admins (e.g., `GET /api/v1/auth/me`). |
| FR-AUTHZ-005 | All `/ui/operator/*` routes use `require_operator`. All `/api/v1/users/*` and `/ui/admin/*` routes use `require_admin`. |
| FR-AUTHZ-006 | Unauthorized access to a `/ui/` route returns a redirect to `/ui/login` with status `303` (with optional `?next=` query for admin routes), not a bare 401 JSON response. |
| FR-AUTHZ-007 | Unauthorized access to an `/api/v1/` route returns `{"detail": "...", "code": "..."}` with status `401` or `403` as appropriate. |

---

### 2.9 User Management Routes (Admin)

| ID | Requirement |
|---|---|
| FR-UROUTE-001 | `POST /api/v1/users/` creates a user; see US-005 for acceptance criteria. |
| FR-UROUTE-002 | `GET /api/v1/users/` returns paginated user list; requires `role = 'admin'`. Supports filtering by `role`, `is_active`, and `gate_number`. |
| FR-UROUTE-003 | `GET /api/v1/users/{id}` returns single user detail; requires `role = 'admin'`. |
| FR-UROUTE-004 | `PATCH /api/v1/users/{id}/deactivate` soft-deactivates user; see US-006. |
| FR-UROUTE-005 | `PATCH /api/v1/users/{id}/reset-password` accepts `{"new_password": "..."}`, hashes it, updates the record, and logs `USER_PASSWORD_RESET` in audit log. |
| FR-UROUTE-006 | `PATCH /api/v1/users/{id}` accepts `UserUpdate` (`full_name`, `username`, `role`, `gate_number`, `is_active`), enforces role-gate consistency, updates record, and logs `USER_UPDATED` in audit log. |

---

### 2.10 Login UI Template

| ID | Requirement |
|---|---|
| FR-UI-001 | `templates/auth/login.html` extends `templates/base.html`. |
| FR-UI-002 | `base.html` sets `<html lang="ar" dir="rtl">`. All layout uses CSS logical properties. |
| FR-UI-003 | The login form contains: username field (`type="text"`, `inputmode="text"`), password field (`type="password"`), and a submit button. All labels are in Arabic. |
| FR-UI-004 | The submit button is at minimum `48px` tall and spans the full input width. |
| FR-UI-005 | Form fields are at minimum `48px` tall with a font size of at least `16px` (prevents iOS/Android auto-zoom). |
| FR-UI-006 | Error messages (wrong credentials, inactive account) are displayed in Arabic above the form in a visually distinct error block. |
| FR-UI-007 | No external resources are loaded (no CDN fonts, no CDN CSS). Tailwind must be built locally. |
| FR-UI-008 | Total page size (HTML + CSS + JS) must not exceed 150 KB. |
| FR-UI-009 | The page renders correctly at 360px viewport width with no horizontal scroll. |

---

### 2.11 Audit Logging

| ID | Requirement |
|---|---|
| FR-AUDIT-001 | `AuditService.log(actor_id, action, entity_type, entity_id, before, after, db)` is the sole entry point for writing audit records. |
| FR-AUDIT-002 | `before` and `after` are Python dicts; the service serializes them to JSON strings before storage. Sensitive fields (`hashed_password`) are stripped before serialization. |
| FR-AUDIT-003 | Phase 1 actions that must be logged: `USER_CREATED`, `USER_DEACTIVATED`, `USER_PASSWORD_RESET`, `USER_LOGIN`. |
| FR-AUDIT-004 | `USER_LOGIN` log entry uses `entity_type = 'user'`, `entity_id = user.id`, `before = null`, `after = {"username": ..., "role": ...}`. |
| FR-AUDIT-005 | Audit log writes must not block or fail the primary operation. If the audit write fails, the error is logged to the application logger at `ERROR` level but does not cause the HTTP response to fail. |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement |
|---|---|
| NFR-PERF-001 | The login endpoint (`POST /api/v1/auth/login`) must respond within 800ms under normal conditions on the target hardware. bcrypt hashing time accounts for most of this budget. |
| NFR-PERF-002 | `GET /api/v1/auth/me` must respond within 100ms (no bcrypt; JWT decode + single DB read). |
| NFR-PERF-003 | The login HTML page (`GET /ui/login`) must deliver a fully rendered page within 300ms on LAN. |
| NFR-PERF-004 | All database queries generated in Phase 1 must use indexed columns for WHERE clauses. `username` and `actor_id` must be indexed. |
| NFR-PERF-005 | The application must handle 10 concurrent authenticated requests without degradation (5 operators + 5 admin page loads). |

---

### 3.2 Security

| ID | Requirement |
|---|---|
| NFR-SEC-001 | Passwords are hashed with bcrypt, work factor 12. The plaintext password must be zeroed from memory as soon as hashing completes (do not retain in local variables beyond the call). |
| NFR-SEC-002 | JWT tokens are signed with `HS256` using a `SECRET_KEY` of at least 32 random bytes. |
| NFR-SEC-003 | `pgms_token` cookie is always `HttpOnly` and `SameSite=Strict`. It is `Secure` in `ENVIRONMENT=production`. |
| NFR-SEC-004 | The login endpoint must not reveal whether a username exists in the system. When a username does not exist, verification is executed against a dummy bcrypt hash so response time and error messages are identical to a wrong-password attempt. |
| NFR-SEC-005 | All SQL queries are parameterized via SQLAlchemy ORM. No string interpolation into query text anywhere in the codebase. |
| NFR-SEC-006 | `DEBUG=True` must never be reachable in production (enforced at startup, per FR-CFG-004). |
| NFR-SEC-007 | Stack traces and internal error details are never returned in HTTP responses in non-development environments. FastAPI exception handlers must sanitize 500 responses. |
| NFR-SEC-008 | CORS: allowed origins are configured explicitly via `CORS_ORIGINS` env var. Wildcard `*` is rejected in production at startup. |
| NFR-SEC-009 | `hashed_password` is excluded from all Pydantic response schemas and all audit log payloads unconditionally. |

---

### 3.3 Reliability & Data Integrity

| ID | Requirement |
|---|---|
| NFR-REL-001 | Every database write in Phase 1 occurs within an explicit transaction. The session is committed only after all writes succeed; it is rolled back on any exception. |
| NFR-REL-002 | The `CHECK` constraint on `users.gate_number` (FR-MDL-017) must be enforced at database level, not only at application level. |
| NFR-REL-003 | The application must start and serve the login page even if the database is temporarily unreachable, returning a `503 Service Unavailable` with an Arabic error message rather than crashing. |
| NFR-REL-004 | All foreign key constraints must be explicitly enabled. For SQLite this requires `PRAGMA foreign_keys = ON` on every connection, set via a SQLAlchemy connection event listener. |

---

### 3.4 Maintainability

| ID | Requirement |
|---|---|
| NFR-MNT-001 | Cyclomatic complexity of any single function must not exceed 10 (enforced by Ruff). |
| NFR-MNT-002 | All `services/` functions have Google-style docstrings describing parameters, return values, and exceptions raised. |
| NFR-MNT-003 | No function exceeds 50 lines of code. Logic that would exceed this limit must be extracted into a helper. |
| NFR-MNT-004 | All Pydantic schemas have field-level descriptions (used for auto-generated OpenAPI docs). |
| NFR-MNT-005 | The OpenAPI docs (`/docs`) must be disabled in `ENVIRONMENT=production`. |

---

### 3.5 Localization & Accessibility

| ID | Requirement |
|---|---|
| NFR-L10N-001 | All Arabic strings displayed in the UI are stored in `translations/ar.json`; none are hardcoded in templates. |
| NFR-L10N-002 | All datetime values stored in the database are UTC. The display layer converts to `Africa/Cairo` (UTC+2, no DST) for all user-facing output. |
| NFR-L10N-003 | The login page must render correctly in RTL without any horizontal overflow at 360px viewport width. |
| NFR-L10N-004 | Touch targets on the login page meet WCAG 2.1 AA minimum size of 44×44px. |
| NFR-L10N-005 | Input font size is at minimum 16px to ensure high legibility and prevent unwanted zooming across browser engines. |

---

### 3.6 Testability

| ID | Requirement |
|---|---|
| NFR-TEST-001 | Unit test coverage for `services/auth_service.py` must be 100%. |
| NFR-TEST-002 | Unit test coverage for `services/audit_service.py` must be 100%. |
| NFR-TEST-003 | Integration tests cover every route defined in Phase 1 (happy path + at least two failure paths per route). |
| NFR-TEST-004 | Tests use an isolated in-memory SQLite database; no test ever touches a development or production database. |
| NFR-TEST-005 | The full test suite must complete in under 60 seconds on CI hardware. |
| NFR-TEST-006 | All tests are deterministic: no dependency on system time (use `freezegun` or dependency injection for timestamps), no dependency on external services. |

---

## 4. Edge Cases

### 4.1 Authentication Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-AUTH-001 | Login with correct username but wrong password | `401` with generic `INVALID_CREDENTIALS` code; no indication which field was wrong |
| EC-AUTH-002 | Login with username that does not exist | Identical response to EC-AUTH-001; same response time (constant-time comparison must still occur to prevent timing oracle) |
| EC-AUTH-003 | Login with an inactive (`is_active = FALSE`) account | `401` with generic `INVALID_CREDENTIALS` code; inactive status not disclosed |
| EC-AUTH-004 | Submitting the login form with empty `username` or `password` fields | Pydantic validation error returned as `422`; login page re-renders with Arabic field-level error messages |
| EC-AUTH-005 | Accessing a protected route with an expired JWT | `401 UNAUTHORIZED`; UI routes redirect to `/ui/login` |
| EC-AUTH-006 | Accessing a protected route with a tampered JWT signature | `401 UNAUTHORIZED`; log the event at `WARNING` level with the raw token (truncated to 32 chars) |
| EC-AUTH-007 | Accessing a protected route with a JWT for a user that was deactivated after token issuance | `get_current_user` re-fetches user from DB on every request; returns `401` because `is_active = FALSE` |
| EC-AUTH-008 | Logout called with no active session (no cookie) | `200` response; no error (idempotent logout) |
| EC-AUTH-009 | Operator attempts to access an admin-only endpoint | `403 FORBIDDEN` with code `INSUFFICIENT_PERMISSIONS` |
| EC-AUTH-010 | Admin accesses an operator endpoint | `200 OK`; admins have supervisory access to operator features (`require_operator` permits both `OPERATOR` and `ADMIN`) |
| EC-AUTH-011 | JWT cookie present but user record deleted from DB | `401 UNAUTHORIZED`; treat as if user does not exist |
| EC-AUTH-012 | `SECRET_KEY` rotated in production (all existing JWTs invalidated) | All users see `401` on next request and are redirected to login; no crash |

---

### 4.2 User Management Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-USER-001 | Creating an operator with `gate_number = 0` or `gate_number = 6` | `422 Unprocessable Entity`; field error: gate must be between 1 and 5 |
| EC-USER-002 | Creating an operator without providing `gate_number` | `422`; gate_number is required for operators |
| EC-USER-003 | Creating an admin with `gate_number = 3` | `422`; admins must have null gate_number |
| EC-USER-004 | Creating a user with a duplicate `username` | `409 Conflict` with code `USERNAME_ALREADY_EXISTS` |
| EC-USER-005 | Admin attempting to deactivate their own account | `403` with code `CANNOT_DEACTIVATE_SELF` |
| EC-USER-006 | Deactivating an already-inactive user | `409 Conflict` with code `USER_ALREADY_INACTIVE` |
| EC-USER-007 | `full_name` contains Arabic characters (e.g., `"أحمد محمد"`) | Stored and returned as-is; UTF-8 encoding preserved end-to-end |
| EC-USER-008 | `username` submitted with leading or trailing whitespace | Stripped and normalized before validation and storage |
| EC-USER-009 | `username` containing Arabic characters | `422`; usernames must be ASCII alphanumeric + underscore only (for reliable keyboard input on workstation PCs) |
| EC-USER-010 | Password shorter than 8 characters | `422` with field error indicating minimum password length |
| EC-USER-011 | Password reset for a user who is currently logged in (has active JWT) | Password updated; existing JWT remains valid until expiry (no session invalidation in Phase 1 — documented limitation) |
| EC-USER-012 | Fetching a user by `id` that does not exist | `404` with code `USER_NOT_FOUND` |

---

### 4.3 Database & Migration Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-DB-001 | Running `alembic upgrade head` when tables already exist | Alembic detects current revision and no-ops cleanly; does not error or duplicate tables |
| EC-DB-002 | Running `seed.py` on a database with no tables | Script exits with a clear error message instructing the deployer to run migrations first |
| EC-DB-003 | Running `seed.py` when all seed records already exist | Script skips all inserts and prints a "nothing to seed" summary |
| EC-DB-004 | `DATABASE_URL` points to an unreachable host | App startup prints a connection error and still serves `/ui/login` with a `503` database-unavailable message |
| EC-DB-005 | SQLite database file is read-only (permissions error) | App fails to start with a clear `PermissionError` message identifying the file path |
| EC-DB-006 | `PRAGMA foreign_keys = ON` not set (SQLite) | Integration tests verify FK violations are rejected; a test deliberately inserts an orphaned FK to confirm enforcement |
| EC-DB-007 | Concurrent login requests from the same operator on two terminals | Both succeed; two valid JWTs are issued. No single-session enforcement in Phase 1 (documented limitation) |
| EC-DB-008 | `updated_at` auto-update on User with no actual field change (spurious update) | `updated_at` changes; this is acceptable. True field-level dirty checking is not required in Phase 1 |

---

### 4.4 Configuration Edge Cases

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-CFG-001 | `SECRET_KEY` is exactly 31 characters | App refuses to start with `ValueError: SECRET_KEY must be at least 32 characters` |
| EC-CFG-002 | `JWT_EXPIRE_HOURS` set to `0` or a negative number | App refuses to start with a validation error |
| EC-CFG-003 | `JWT_EXPIRE_HOURS` set to a non-integer string | `pydantic-settings` raises a `ValidationError` at startup |
| EC-CFG-004 | `ENVIRONMENT` set to an unrecognized value (e.g., `"prod"`) | App refuses to start; `ENVIRONMENT` must be one of `development`, `staging`, `production` |
| EC-CFG-005 | `.env` file missing entirely | App reads from real environment variables; if required vars are absent, startup fails with a list of missing keys |
| EC-CFG-006 | `DEBUG=True` and `ENVIRONMENT=production` set simultaneously | `ValueError` on startup; message: `"DEBUG must not be True in production"` |

---

### 4.5 Arabic & Localization Edge Cases

> Note: Full Arabic plate normalization is implemented in Phase 2 (`PlateService`).
> The following edge cases apply to Phase 1's handling of Arabic text in user records.

| ID | Scenario | Expected Behaviour |
|---|---|---|
| EC-L10N-001 | `full_name` containing mixed Arabic and Latin characters (e.g., `"Ahmed أحمد"`) | Accepted and stored as-is; rendered correctly in RTL context with `dir="auto"` on the element |
| EC-L10N-002 | `full_name` containing HTML special characters (e.g., `<script>`) | Jinja2 auto-escaping prevents XSS; stored raw, displayed escaped |
| EC-L10N-003 | `full_name` containing only whitespace | `422`; whitespace-only names are rejected after stripping |
| EC-L10N-004 | `full_name` exceeding 120 characters | `422` with field length error |
| EC-L10N-005 | Login page rendered on a device with system language set to English | Page still renders in Arabic RTL; language is hardcoded to `ar`, not inferred from browser `Accept-Language` header |
| EC-L10N-006 | Timestamps displayed on the login error message | All displayed timestamps are in `Africa/Cairo` timezone (UTC+2), formatted as `DD/MM/YYYY HH:mm` using Arabic-Indic numerals |
| EC-L10N-007 | Arabic text in `full_name` containing diacritics (tashkeel, e.g., `"أَحْمَد"`) | Stored and returned with diacritics preserved; no normalization applied to user names |
| EC-L10N-008 | Bidirectional text overflow on compact viewports (360px) | Base template enforces `overflow-wrap: break-word` and `max-width: 100%` on all text containers; no overflow |
| EC-L10N-009 | `translations/ar.json` key referenced in a template is missing | Jinja2 custom `t()` filter returns the key name wrapped in `[[ ]]` markers in development; raises a startup error in production (all keys validated at boot) |

---

## 5. Defined Error Codes (Phase 1)

All error responses follow the envelope: `{"detail": "<human-readable Arabic or English message>", "code": "<MACHINE_CODE>"}`.

| Code | HTTP Status | Trigger |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | Wrong username, wrong password, or inactive user at login |
| `UNAUTHORIZED` | 401 | Missing, expired, or invalid JWT on a protected route |
| `INSUFFICIENT_PERMISSIONS` | 403 | Valid JWT but wrong role for the requested resource |
| `USER_NOT_FOUND` | 404 | No user with the given `id` |
| `USERNAME_ALREADY_EXISTS` | 409 | Duplicate username on user creation |
| `USER_ALREADY_INACTIVE` | 409 | Deactivating an already-inactive user |
| `CANNOT_DEACTIVATE_SELF` | 403 | Admin attempting to deactivate their own account |
| `VALIDATION_ERROR` | 422 | Pydantic schema violation (FastAPI default, extended with `code` field) |
| `DATABASE_UNAVAILABLE` | 503 | Database connection failed on request |
| `INTERNAL_ERROR` | 500 | Unhandled exception (detail sanitized in non-development environments) |

---

## 6. Out of Scope for Phase 1

The following items are explicitly deferred and must not be implemented during Phase 1, even if they seem straightforward:

- Parking session creation, exit, or price calculation.
- Shift start, shift close, or shift reconciliation.
- Pricing rule activation or modification via the API.
- Operator dashboard content beyond the login redirect.
- Admin dashboard UI.
- Receipt generation or print functionality.
- Arabic plate normalization (`PlateService`).
- Token refresh or multi-session management.
- Rate limiting or brute-force lockout (deferred to Phase 4).
- Any reporting endpoint.

---

*This specification is complete when all Acceptance Criteria, Functional Requirements, Non-Functional Requirements, and Edge Cases listed above have corresponding passing tests.*
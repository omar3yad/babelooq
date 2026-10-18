import os
import sys
import asyncio
from alembic import command
from config import get_settings
from alembic.config import Config
from sqlalchemy import text, select
from models.user import User, UserRole
from datetime import datetime, timezone
from models.pricing_rule import PricingRule
from services.auth_service import AuthService
from database import engine, AsyncSessionLocal

def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

async def verify_tables_exist():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM users LIMIT 1"))
            await conn.execute(text("SELECT 1 FROM pricing_rules LIMIT 1"))
            await conn.execute(text("SELECT 1 FROM shifts LIMIT 1"))
            await conn.execute(text("SELECT 1 FROM parking_sessions LIMIT 1"))
            await conn.execute(text("SELECT 1 FROM audit_logs LIMIT 1"))
    except Exception as e:
        print(f"Error: Database tables verification failed: {e}", file=sys.stderr)
        sys.exit(1)

async def seed_admin_user(db, settings, auth_service) -> dict:
    username = settings.SEED_ADMIN_USERNAME or os.environ.get("SEED_ADMIN_USERNAME", "Mohamed_abdou")
    password = settings.SEED_ADMIN_PASSWORD or os.environ.get("SEED_ADMIN_PASSWORD", "198245")
    full_name = settings.SEED_ADMIN_FULL_NAME or os.environ.get("SEED_ADMIN_FULL_NAME", "محمد عبده")

    result = await db.execute(select(User).where(User.username == username))
    existing = result.scalars().first()
    if existing:
        return {"created": False, "reason": "already exists", "user": existing}

    hashed = auth_service.hash_password(password)
    admin = User(
        full_name=full_name,
        username=username,
        hashed_password=hashed,
        role=UserRole.ADMIN,
        gate_number=None,
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    return {"created": True, "reason": "-", "user": admin}

async def seed_operator_user(db, settings, auth_service, gate: int) -> dict:
    if gate == 1:
        default_username = "op_entry"
        default_name = "عامل الدخول"
    elif gate == 2:
        default_username = "op_exit"
        default_name = "عامل الخروج"
    else:
        default_username = f"op{gate}"
        default_name = f"مشغل بوابة {gate}"

    username = os.environ.get(f"SEED_OP_{gate}_USERNAME", default_username)
    password = os.environ.get(f"SEED_OP_{gate}_PASSWORD", f"op{gate}password")
    full_name = os.environ.get(f"SEED_OP_{gate}_FULL_NAME", default_name)

    result = await db.execute(select(User).where(User.username == username))
    existing = result.scalars().first()
    if existing:
        return {"created": False, "reason": "already exists", "user": existing}

    hashed = auth_service.hash_password(password)
    op_user = User(
        full_name=full_name,
        username=username,
        hashed_password=hashed,
        role=UserRole.OPERATOR,
        gate_number=gate,
        is_active=True,
    )
    db.add(op_user)
    await db.flush()
    return {"created": True, "reason": "-", "user": op_user}

async def seed_default_pricing_rule(db, admin_user_id: int) -> dict:
    label = "السعر الافتراضي"
    result = await db.execute(select(PricingRule).where(PricingRule.label == label))
    existing = result.scalars().first()
    if existing:
        return {"created": False, "reason": "already exists"}

    rule = PricingRule(
        label=label,
        rate_per_hour=1000,  # 10 EGP
        first_hour_charge=2000,  # 20 EGP for the first hour
        subsequent_hour_charge=1000,  # 10 EGP for subsequent hours
        minimum_charge=0,
        grace_period_mins=5,
        is_active=True,
        effective_from=datetime.now(timezone.utc).replace(tzinfo=None),
        effective_until=None,
        created_by=admin_user_id,
    )
    db.add(rule)
    await db.flush()
    return {"created": True, "reason": "-"}

async def main():
    print("Running database migrations programmatically...")
    await asyncio.to_thread(run_migrations)
    await verify_tables_exist()
    print("Database tables verified successfully.")

    settings = get_settings()
    auth_service = AuthService(settings)

    async with AsyncSessionLocal() as db:
        try:
            summary = []

            # 1. Seed Admin
            admin_res = await seed_admin_user(db, settings, auth_service)
            admin_user = admin_res["user"]
            summary.append(("Admin User", "Created" if admin_res["created"] else "Skipped", admin_res["reason"]))

            # 2. Seed Operators (Gates 1-5)
            for gate in range(1, 6):
                op_res = await seed_operator_user(db, settings, auth_service, gate)
                summary.append((f"Operator Gate {gate}", "Created" if op_res["created"] else "Skipped", op_res["reason"]))

            # 3. Seed Pricing Rule
            rule_res = await seed_default_pricing_rule(db, admin_user.id)
            summary.append(("Default Pricing Rule", "Created" if rule_res["created"] else "Skipped", rule_res["reason"]))

            # Commit once
            await db.commit()
            print("Seeding transaction committed successfully.")

            # Print formatted summary table
            print("\nEntity               | Status   | Reason")
            print("---------------------|----------|-------------------")
            for entity, status, reason in summary:
                print(f"{entity:<20} | {status:<8} | {reason}")
            print()

        except Exception as e:
            await db.rollback()
            print(f"Error during seeding transaction, rolled back: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

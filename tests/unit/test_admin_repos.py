import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User, UserRole
from models.shift import Shift
from models.parking_card import ParkingCard, CardStatus
from models.parking_session import ParkingSession, SessionStatus
from models.pricing_rule import PricingRule
from repositories.report_repo import ReportRepository
from repositories.admin_shift_repo import AdminShiftRepository
from schemas.admin_reports import ReportFilters, ShiftFilters


@pytest.mark.asyncio
async def test_report_and_shift_repos(db_session: AsyncSession) -> None:
    # 1. Seed user
    admin = User(
        full_name="المدير",
        username="admin_user",
        hashed_password="pw",
        role=UserRole.ADMIN,
    )
    operator = User(
        full_name="عامل 1",
        username="op_user",
        hashed_password="pw",
        role=UserRole.OPERATOR,
        gate_number=1,
    )
    db_session.add_all([admin, operator])
    await db_session.flush()

    # 2. Seed cards
    c1 = ParkingCard(card_code="CARD01", status=CardStatus.AVAILABLE)
    c2 = ParkingCard(card_code="CARD02", status=CardStatus.DAMAGED)
    db_session.add_all([c1, c2])
    await db_session.flush()

    # 3. Seed shifts
    now = datetime.utcnow()
    shift1 = Shift(
        operator_id=operator.id,
        gate_number=1,
        started_at=now - timedelta(hours=2),
        ended_at=None,
        opening_cash_egp=1000,
    )
    shift2 = Shift(
        operator_id=operator.id,
        gate_number=1,
        started_at=now - timedelta(hours=14),
        ended_at=now - timedelta(hours=6),
        opening_cash_egp=500,
        closing_cash_egp=2000,
    )
    db_session.add_all([shift1, shift2])
    await db_session.flush()

    # 4. Seed pricing rule
    pr = PricingRule(
        label="Standard",
        rate_per_hour=1000,
        minimum_charge=1000,
        grace_period_mins=15,
        created_by=admin.id,
        effective_from=now - timedelta(days=1),
    )
    db_session.add(pr)
    await db_session.flush()

    # 5. Seed sessions
    s1 = ParkingSession(
        card_id=c1.id,
        card_code=c1.card_code,
        status=SessionStatus.ACTIVE,
        gate_number=1,
        shift_id=shift1.id,
        operator_id=operator.id,
        entry_time=now - timedelta(hours=1),
    )
    s2 = ParkingSession(
        card_id=c2.id,
        card_code=c2.card_code,
        status=SessionStatus.COMPLETED,
        gate_number=1,
        shift_id=shift2.id,
        exit_shift_id=shift2.id,
        operator_id=operator.id,
        exit_operator_id=operator.id,
        entry_time=now - timedelta(hours=10),
        exit_time=now - timedelta(hours=8),
        amount_charged=3000,
        duration_minutes=120,
    )
    db_session.add_all([s1, s2])
    await db_session.commit()

    # Test ReportRepository
    report_repo = ReportRepository(db_session)

    # Active sessions
    assert await report_repo.count_active_sessions() == 1

    # Total card capacity (excludes DAMAGED)
    assert await report_repo.count_total_card_capacity() == 1

    # Open shifts
    assert await report_repo.count_open_shifts() == 1

    # Long stay sessions (s1 is only 1 hr old, threshold 24h ago -> 0)
    assert await report_repo.count_long_stay_sessions(now - timedelta(hours=24)) == 0

    # Overdue shifts (shift1 started 2 hr ago, threshold 12h ago -> 0)
    assert await report_repo.count_overdue_shifts(now - timedelta(hours=12)) == 0

    # Revenue today
    rev = await report_repo.sum_revenue_today(
        now - timedelta(days=1), now + timedelta(days=1)
    )
    assert rev == 3000

    # Gate panel
    panel = await report_repo.get_gate_panel()
    assert len(panel) == 1
    assert panel[0]["gate_number"] == 1
    assert panel[0]["operator_name"] == "عامل 1"
    assert panel[0]["active_sessions"] == 1

    # Revenue summary
    summary = await report_repo.get_revenue_summary(
        start_utc=now - timedelta(days=1),
        end_utc=now + timedelta(days=1),
        gate_number=1,
        operator_id=operator.id,
    )
    assert summary["total_sessions"] == 1
    assert summary["total_revenue"] == 3000
    assert summary["total_duration"] == 120

    # Revenue by gate
    gate_rev = await report_repo.get_revenue_by_gate(None, None, None)
    assert len(gate_rev) == 1
    assert gate_rev[0]["total_piastres"] == 3000

    # Revenue by operator
    op_rev = await report_repo.get_revenue_by_operator(None, None, None)
    assert len(op_rev) == 1
    assert op_rev[0]["operator_name"] == "عامل 1"

    # Daily revenue raw
    daily = await report_repo.get_daily_revenue_raw(
        now - timedelta(days=2), now + timedelta(days=2), None, None
    )
    assert len(daily) >= 1

    # Sessions filtered
    filtered, total = await report_repo.get_sessions_filtered(
        ReportFilters(), page=1, size=10
    )
    assert total == 2
    assert len(filtered) == 2

    # Sessions export
    export_sessions = []
    async for sess in report_repo.get_sessions_for_export(
        ReportFilters(), chunk_size=1
    ):
        export_sessions.append(sess)
    assert len(export_sessions) == 2

    # Test AdminShiftRepository
    shift_repo = AdminShiftRepository(db_session)

    # Filtered shifts
    shifts, s_count = await shift_repo.get_shifts_filtered(
        ShiftFilters(status="open"), page=1, size=10
    )
    assert s_count == 1
    assert shifts[0].id == shift1.id

    # Shift session totals
    totals = await shift_repo.get_shift_session_totals([shift1.id, shift2.id])
    assert totals[shift1.id] == 0
    assert totals[shift2.id] == 3000

    # Shift session counts
    counts = await shift_repo.get_shift_session_counts(shift2.id)
    assert counts["COMPLETED"] == 1
    assert counts["ACTIVE"] == 0

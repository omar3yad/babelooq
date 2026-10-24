from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from typing import Any
import asyncio

from sqlalchemy import select, func, text, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.parking_session import ParkingSession, SessionStatus
from models.parking_card import ParkingCard, CardStatus
from models.shift import Shift
from schemas.admin_reports import ReportFilters
from utils.time import cairo_date_to_utc_start, cairo_date_to_utc_end


class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def count_active_sessions(self) -> int:
        """Counts parking sessions where status = 'ACTIVE'."""
        result = await self.db.execute(
            select(func.count(ParkingSession.id)).where(
                ParkingSession.status == SessionStatus.ACTIVE
            )
        )
        return result.scalar_one_or_none() or 0

    async def count_total_card_capacity(self) -> int:
        """Counts cards where status != 'DAMAGED'."""
        result = await self.db.execute(
            select(func.count(ParkingCard.id)).where(
                ParkingCard.status != CardStatus.DAMAGED
            )
        )
        return result.scalar_one_or_none() or 0

    async def sum_revenue_today(self, start_utc: datetime, end_utc: datetime) -> int:
        """Sums amount_charged for sessions COMPLETED or LOST_CARD exited within
        [start_utc, end_utc).
        """
        result = await self.db.execute(
            select(func.coalesce(func.sum(ParkingSession.amount_charged), 0)).where(
                ParkingSession.status.in_(
                    [SessionStatus.COMPLETED, SessionStatus.LOST_CARD]
                ),
                ParkingSession.exit_time >= start_utc,
                ParkingSession.exit_time < end_utc,
            )
        )
        return int(result.scalar_one_or_none() or 0)

    async def count_open_shifts(self) -> int:
        """Counts shifts where ended_at IS NULL."""
        result = await self.db.execute(
            select(func.count(Shift.id)).where(Shift.ended_at.is_(None))
        )
        return result.scalar_one_or_none() or 0

    async def get_gate_panel(self) -> list[dict[str, Any]]:
        """Returns per-gate occupancy and open shift info."""
        bind = self.db.get_bind()
        dialect_name = bind.dialect.name if bind else "postgresql"
        if dialect_name == "sqlite":
            active_expr = "SUM(CASE WHEN ps.status = 'ACTIVE' THEN 1 ELSE 0 END)"
        else:
            active_expr = "COUNT(ps.id) FILTER (WHERE ps.status = 'ACTIVE')"

        query = text(f"""
            SELECT
                s.gate_number,
                u.full_name AS operator_name,
                u.id AS operator_id,
                s.started_at AS shift_start,
                COALESCE({active_expr}, 0) AS active_sessions
            FROM shifts s
            JOIN users u ON s.operator_id = u.id
            LEFT JOIN parking_sessions ps ON ps.shift_id = s.id
            WHERE s.ended_at IS NULL
            GROUP BY s.gate_number, u.full_name, u.id, s.started_at
            ORDER BY s.gate_number
        """)
        rows = (await self.db.execute(query)).mappings().all()
        return [
            {
                "gate_number": int(r["gate_number"]),
                "operator_name": r["operator_name"],
                "operator_id": (
                    int(r["operator_id"]) if r["operator_id"] is not None else None
                ),
                "shift_start": r["shift_start"],
                "active_sessions": int(r["active_sessions"] or 0),
            }
            for r in rows
        ]

    async def count_long_stay_sessions(self, threshold_utc: datetime) -> int:
        """Counts active sessions whose entry_time is earlier than threshold_utc."""
        result = await self.db.execute(
            select(func.count(ParkingSession.id)).where(
                ParkingSession.status == SessionStatus.ACTIVE,
                ParkingSession.entry_time < threshold_utc,
            )
        )
        return result.scalar_one_or_none() or 0

    async def count_overdue_shifts(self, threshold_utc: datetime) -> int:
        """Counts open shifts started earlier than threshold_utc."""
        result = await self.db.execute(
            select(func.count(Shift.id)).where(
                Shift.ended_at.is_(None),
                Shift.started_at < threshold_utc,
            )
        )
        return result.scalar_one_or_none() or 0

    async def get_revenue_summary(
        self,
        start_utc: datetime | None,
        end_utc: datetime | None,
        gate_number: int | None,
        operator_id: int | None,
    ) -> dict[str, int]:
        """Returns total_sessions, total_revenue, total_duration for
        completed/lost sessions.
        """
        clauses = ["status IN ('COMPLETED', 'LOST_CARD')"]
        params: dict[str, Any] = {}

        if start_utc is not None:
            clauses.append("exit_time >= :start_utc")
            params["start_utc"] = start_utc
        if end_utc is not None:
            clauses.append("exit_time < :end_utc")
            params["end_utc"] = end_utc
        if gate_number is not None:
            clauses.append("gate_number = :gate_number")
            params["gate_number"] = gate_number
        if operator_id is not None:
            clauses.append("COALESCE(exit_operator_id, operator_id) = :operator_id")
            params["operator_id"] = operator_id

        where_sql = " AND ".join(clauses)
        sql = text(f"""
            SELECT
                COUNT(*) AS total_sessions,
                COALESCE(SUM(amount_charged), 0) AS total_revenue,
                COALESCE(SUM(duration_minutes), 0) AS total_duration
            FROM parking_sessions
            WHERE {where_sql}
        """)
        res = (await self.db.execute(sql, params)).mappings().one()
        return {
            "total_sessions": int(res["total_sessions"] or 0),
            "total_revenue": int(res["total_revenue"] or 0),
            "total_duration": int(res["total_duration"] or 0),
        }

    async def get_revenue_by_gate(
        self,
        start_utc: datetime | None,
        end_utc: datetime | None,
        operator_id: int | None,
    ) -> list[dict[str, int]]:
        """Returns session count and revenue grouped by gate."""
        clauses = ["status IN ('COMPLETED', 'LOST_CARD')"]
        params: dict[str, Any] = {}

        if start_utc is not None:
            clauses.append("exit_time >= :start_utc")
            params["start_utc"] = start_utc
        if end_utc is not None:
            clauses.append("exit_time < :end_utc")
            params["end_utc"] = end_utc
        if operator_id is not None:
            clauses.append("COALESCE(exit_operator_id, operator_id) = :operator_id")
            params["operator_id"] = operator_id

        where_sql = " AND ".join(clauses)
        sql = text(f"""
            SELECT
                gate_number,
                COUNT(*) AS session_count,
                COALESCE(SUM(amount_charged), 0) AS total_piastres
            FROM parking_sessions
            WHERE {where_sql}
            GROUP BY gate_number
            ORDER BY gate_number
        """)
        rows = (await self.db.execute(sql, params)).mappings().all()
        return [
            {
                "gate_number": int(r["gate_number"]),
                "session_count": int(r["session_count"]),
                "total_piastres": int(r["total_piastres"]),
            }
            for r in rows
        ]

    async def get_revenue_by_service_type(
        self,
        start_utc: datetime | None,
        end_utc: datetime | None,
        operator_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Returns revenue and counts broken down by service type:
        1. Regular Tickets (Hourly / Casual)
        2. Subscriptions (Monthly Plans)
        3. Lost Cards / Penalties
        """
        # 1. Regular Tickets
        ticket_clauses = [
            "status = 'COMPLETED'",
            "is_lost_card = FALSE",
            "(is_subscribed = FALSE OR is_subscribed IS NULL)",
        ]
        ticket_params: dict[str, Any] = {}
        if start_utc is not None:
            ticket_clauses.append("exit_time >= :start_utc")
            ticket_params["start_utc"] = start_utc
        if end_utc is not None:
            ticket_clauses.append("exit_time < :end_utc")
            ticket_params["end_utc"] = end_utc
        if operator_id is not None:
            ticket_clauses.append("COALESCE(exit_operator_id, operator_id) = :operator_id")
            ticket_params["operator_id"] = operator_id

        ticket_sql = text(
            f"SELECT COUNT(*) AS cnt, COALESCE(SUM(amount_charged), 0) AS total "
            f"FROM parking_sessions WHERE {' AND '.join(ticket_clauses)}"
        )
        ticket_row = (await self.db.execute(ticket_sql, ticket_params)).mappings().one()

        # 2. Lost Cards
        lost_clauses = [
            "(is_lost_card = TRUE OR status = 'LOST_CARD' OR (lost_card_penalty_applied IS NOT NULL AND lost_card_penalty_applied > 0))"
        ]
        lost_params: dict[str, Any] = {}
        if start_utc is not None:
            lost_clauses.append("exit_time >= :start_utc")
            lost_params["start_utc"] = start_utc
        if end_utc is not None:
            lost_clauses.append("exit_time < :end_utc")
            lost_params["end_utc"] = end_utc
        if operator_id is not None:
            lost_clauses.append("COALESCE(exit_operator_id, operator_id) = :operator_id")
            lost_params["operator_id"] = operator_id

        lost_sql = text(
            f"SELECT COUNT(*) AS cnt, COALESCE(SUM(amount_charged), 0) AS total "
            f"FROM parking_sessions WHERE {' AND '.join(lost_clauses)}"
        )
        lost_row = (await self.db.execute(lost_sql, lost_params)).mappings().one()

        # 3. Monthly Subscriptions
        sub_clauses = ["status = 'ACTIVE'"]
        sub_params: dict[str, Any] = {}
        if start_utc is not None:
            sub_clauses.append("paid_at >= :start_utc")
            sub_params["start_utc"] = start_utc
        if end_utc is not None:
            sub_clauses.append("paid_at < :end_utc")
            sub_params["end_utc"] = end_utc
        if operator_id is not None:
            sub_clauses.append("collected_by = :operator_id")
            sub_params["operator_id"] = operator_id

        sub_sql = text(
            f"SELECT COUNT(*) AS cnt, COALESCE(SUM(amount_paid_piastres), 0) AS total "
            f"FROM subscriptions WHERE {' AND '.join(sub_clauses)}"
        )
        sub_row = (await self.db.execute(sub_sql, sub_params)).mappings().one()

        t_cnt = int(ticket_row["cnt"] or 0)
        t_total = int(ticket_row["total"] or 0)

        s_cnt = int(sub_row["cnt"] or 0)
        s_total = int(sub_row["total"] or 0)

        l_cnt = int(lost_row["cnt"] or 0)
        l_total = int(lost_row["total"] or 0)

        grand_total = t_total + s_total + l_total

        def pct(val: int) -> float:
            return round((val / grand_total * 100), 1) if grand_total > 0 else 0.0

        return [
            {
                "service_type": "tickets",
                "label": "تذاكر عادية (انتظار بالساعة)",
                "session_count": t_cnt,
                "total_piastres": t_total,
                "percentage": pct(t_total),
            },
            {
                "service_type": "subscriptions",
                "label": "اشتراكات شهرية (باقات وتجديد)",
                "session_count": s_cnt,
                "total_piastres": s_total,
                "percentage": pct(s_total),
            },
            {
                "service_type": "lost_cards",
                "label": "غرامات وكروت مفقودة",
                "session_count": l_cnt,
                "total_piastres": l_total,
                "percentage": pct(l_total),
            },
        ]

    async def get_revenue_by_operator(
        self,
        start_utc: datetime | None,
        end_utc: datetime | None,
        gate_number: int | None,
    ) -> list[dict[str, Any]]:
        """Returns session count and revenue grouped by operator."""
        clauses = ["ps.status IN ('COMPLETED', 'LOST_CARD')"]
        params: dict[str, Any] = {}

        if start_utc is not None:
            clauses.append("ps.exit_time >= :start_utc")
            params["start_utc"] = start_utc
        if end_utc is not None:
            clauses.append("ps.exit_time < :end_utc")
            params["end_utc"] = end_utc
        if gate_number is not None:
            clauses.append("ps.gate_number = :gate_number")
            params["gate_number"] = gate_number

        where_sql = " AND ".join(clauses)
        sql = text(f"""
            SELECT
                COALESCE(ps.exit_operator_id, ps.operator_id) AS operator_id,
                u.full_name AS operator_name,
                COUNT(*) AS session_count,
                COALESCE(SUM(ps.amount_charged), 0) AS total_piastres
            FROM parking_sessions ps
            JOIN users u ON COALESCE(ps.exit_operator_id, ps.operator_id) = u.id
            WHERE {where_sql}
            GROUP BY COALESCE(ps.exit_operator_id, ps.operator_id), u.full_name
            ORDER BY total_piastres DESC
        """)
        rows = (await self.db.execute(sql, params)).mappings().all()
        return [
            {
                "operator_id": int(r["operator_id"]),
                "operator_name": str(r["operator_name"]),
                "session_count": int(r["session_count"]),
                "total_piastres": int(r["total_piastres"]),
            }
            for r in rows
        ]

    async def get_daily_revenue_raw(
        self,
        start_utc: datetime,
        end_utc: datetime,
        gate_number: int | None,
        operator_id: int | None,
    ) -> list[dict[str, Any]]:
        """Groups revenue by Cairo calendar date."""
        bind = self.db.get_bind()
        dialect_name = bind.dialect.name if bind else "postgresql"

        if dialect_name == "sqlite":
            date_expr = "DATE(exit_time, '+2 hours')"
        else:
            date_expr = "DATE((exit_time + INTERVAL '2 hours'))"

        clauses = [
            "status IN ('COMPLETED', 'LOST_CARD')",
            "exit_time >= :start_utc",
            "exit_time < :end_utc",
        ]
        params: dict[str, Any] = {
            "start_utc": start_utc,
            "end_utc": end_utc,
        }
        if gate_number is not None:
            clauses.append("gate_number = :gate_number")
            params["gate_number"] = gate_number
        if operator_id is not None:
            clauses.append("COALESCE(exit_operator_id, operator_id) = :operator_id")
            params["operator_id"] = operator_id

        where_sql = " AND ".join(clauses)
        sql = text(f"""
            SELECT
                {date_expr} AS cairo_date,
                COUNT(*) AS session_count,
                COALESCE(SUM(amount_charged), 0) AS total_piastres
            FROM parking_sessions
            WHERE {where_sql}
            GROUP BY cairo_date
            ORDER BY cairo_date
        """)
        rows = (await self.db.execute(sql, params)).mappings().all()
        return [
            {
                "cairo_date": str(r["cairo_date"]),
                "session_count": int(r["session_count"]),
                "total_piastres": int(r["total_piastres"]),
            }
            for r in rows
        ]

    def _build_session_filter_conditions(self, filters: ReportFilters) -> list[Any]:
        conditions = []
        if filters.start_date:
            conditions.append(
                ParkingSession.exit_time >= cairo_date_to_utc_start(filters.start_date)
            )
        if filters.end_date:
            conditions.append(
                ParkingSession.exit_time < cairo_date_to_utc_end(filters.end_date)
            )
        if filters.gate_number is not None:
            conditions.append(ParkingSession.gate_number == filters.gate_number)
        if filters.operator_id is not None:
            conditions.append(
                or_(
                    ParkingSession.operator_id == filters.operator_id,
                    ParkingSession.exit_operator_id == filters.operator_id,
                )
            )
        if filters.status is not None:
            conditions.append(ParkingSession.status == filters.status)
        if filters.card_code:
            escaped_code = self._escape_like(filters.card_code)
            conditions.append(ParkingSession.card_code.like(f"%{escaped_code}%"))
        if filters.plate_number:
            from services.plate_service import PlateService

            norm_plate = PlateService().search_normalized(filters.plate_number)
            escaped_plate = self._escape_like(norm_plate)
            conditions.append(ParkingSession.plate_number.like(f"%{escaped_plate}%"))
        if filters.long_stay:
            threshold = datetime.utcnow() - timedelta(hours=24)
            conditions.append(ParkingSession.status == SessionStatus.ACTIVE)
            conditions.append(ParkingSession.entry_time < threshold)
        return conditions

    async def get_sessions_filtered(
        self,
        filters: ReportFilters,
        page: int,
        size: int,
    ) -> tuple[list[ParkingSession], int]:
        """Returns paginated sessions and total count matching filters."""
        conditions = self._build_session_filter_conditions(filters)

        count_q = select(func.count(ParkingSession.id))
        if conditions:
            count_q = count_q.where(and_(*conditions))
        total_count = (await self.db.execute(count_q)).scalar_one_or_none() or 0

        data_q = select(ParkingSession)
        if conditions:
            data_q = data_q.where(and_(*conditions))
        data_q = (
            data_q.order_by(ParkingSession.entry_time.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        sessions = list((await self.db.execute(data_q)).scalars().all())
        return sessions, total_count

    async def get_sessions_for_export(
        self,
        filters: ReportFilters,
        chunk_size: int = 500,
    ) -> AsyncIterator[ParkingSession]:
        """Yields sessions matching filters in chunks without loading all
        into memory.
        """
        conditions = self._build_session_filter_conditions(filters)
        offset = 0
        while True:
            data_q = select(ParkingSession)
            if conditions:
                data_q = data_q.where(and_(*conditions))
            data_q = (
                data_q.order_by(ParkingSession.entry_time.desc())
                .offset(offset)
                .limit(chunk_size)
            )
            chunk = list((await self.db.execute(data_q)).scalars().all())
            if not chunk:
                break
            for s in chunk:
                yield s
            offset += chunk_size
            await asyncio.sleep(0)

    @staticmethod
    def _escape_like(value: str) -> str:
        """Escapes % and _ characters for SQL LIKE queries."""
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


__all__ = ["ReportRepository"]

from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_operator, require_admin, require_any_role
from models.user import User
from models.pricing_rule import PricingRule
from models.parking_session import ParkingSession, SessionStatus
from repositories.session_repo import ParkingSessionRepository
from schemas.common import PaginatedResponse
from schemas.parking_session import (
    SessionOpenRequest,
    SessionResponse,
    SessionLostCardRequest,
    PriceBreakdownResponse,
)
from schemas.receipt import ReceiptData
from services.session_service import SessionService
from services.card_service import CardService
from services.pricing_service import PricingService
from services.shift_service import ShiftService
from services.audit_service import AuditService
from services.plate_service import PlateService
from services.pricing_helpers import format_duration, format_egp
from services.exceptions import (
    InvalidBarcodeFormatError,
    CardNotFoundError,
    CardAlreadyActiveError,
    CardNotAvailableError,
    NoActiveShiftError,
    SessionNotFoundError,
    SessionNotActiveError,
    NoPricingRuleError,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

def get_session_repo(db: AsyncSession = Depends(get_db)) -> ParkingSessionRepository:
    return ParkingSessionRepository(db)

def get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    card_service = CardService(db)
    session_repo = ParkingSessionRepository(db)
    pricing_service = PricingService(db)
    audit_service = AuditService(db)
    shift_service = ShiftService(db, audit_service)
    plate_service = PlateService()
    return SessionService(
        db=db,
        card_service=card_service,
        session_repo=session_repo,
        pricing_service=pricing_service,
        shift_service=shift_service,
        audit_service=audit_service,
        plate_service=plate_service,
    )

@router.post("/", status_code=201)
async def open_session(
    data: SessionOpenRequest,
    current_user: User = Depends(require_operator),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session = await session_service.open_session(
            card_code=data.card_code,
            operator_id=current_user.id,
            plate_number=data.plate_number,
        )
    except InvalidBarcodeFormatError as e:
        raise HTTPException(status_code=422, detail=e.message, headers={"X-Error-Code": "INVALID_BARCODE_FORMAT"})
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message, headers={"X-Error-Code": "CARD_NOT_FOUND"})
    except CardAlreadyActiveError as e:
        raise HTTPException(status_code=409, detail=e.message, headers={"X-Error-Code": "CARD_ALREADY_ACTIVE"})
    except CardNotAvailableError as e:
        raise HTTPException(status_code=409, detail=e.message, headers={"X-Error-Code": "CARD_NOT_AVAILABLE"})
    except NoActiveShiftError as e:
        raise HTTPException(status_code=403, detail=e.message, headers={"X-Error-Code": "NO_ACTIVE_SHIFT"})

    return {"data": SessionResponse.model_validate(session).model_dump(mode="json")}

@router.get("/active", response_model=PaginatedResponse[SessionResponse])
async def get_active_sessions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(ParkingSession).where(ParkingSession.status == SessionStatus.ACTIVE)
    count_query = select(func.count()).select_from(ParkingSession).where(ParkingSession.status == SessionStatus.ACTIVE)

    # Count total active
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Get paginated active sessions
    offset_val = (page - 1) * size
    query = query.order_by(ParkingSession.entry_time.desc()).offset(offset_val).limit(size)
    result = await db.execute(query)
    sessions = list(result.scalars().all())

    responses = [SessionResponse.model_validate(s) for s in sessions]
    return PaginatedResponse[SessionResponse](
        data=responses,
        total=total,
        page=page,
        size=size,
    )

@router.get("/{session_id}")
async def get_session(
    session_id: int,
    current_user: User = Depends(require_any_role),
    session_repo: ParkingSessionRepository = Depends(get_session_repo),
):
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
            headers={"X-Error-Code": "SESSION_NOT_FOUND"},
        )
    return {"data": SessionResponse.model_validate(session).model_dump(mode="json")}

@router.patch("/{session_id}/exit")
async def close_session(
    session_id: int,
    current_user: User = Depends(require_operator),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session, calc = await session_service.close_session(session_id, current_user.id)
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message, headers={"X-Error-Code": "SESSION_NOT_FOUND"})
    except SessionNotActiveError as e:
        raise HTTPException(status_code=409, detail=e.message, headers={"X-Error-Code": "SESSION_NOT_ACTIVE"})
    except NoActiveShiftError as e:
        raise HTTPException(status_code=403, detail=e.message, headers={"X-Error-Code": "NO_ACTIVE_SHIFT"})
    except NoPricingRuleError as e:
        raise HTTPException(status_code=503, detail=e.message, headers={"X-Error-Code": "NO_ACTIVE_PRICING_RULE"})

    return {
        "data": SessionResponse.model_validate(session).model_dump(mode="json"),
        "price_breakdown": PriceBreakdownResponse.model_validate(calc).model_dump(mode="json"),
    }

@router.patch("/{session_id}/lost-card")
async def resolve_lost_card(
    session_id: int,
    data: SessionLostCardRequest,
    current_user: User = Depends(require_operator),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        session, calc = await session_service.resolve_lost_card(
            session_id=session_id,
            operator_id=current_user.id,
            notes=data.notes,
        )
    except SessionNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message, headers={"X-Error-Code": "SESSION_NOT_FOUND"})
    except SessionNotActiveError as e:
        raise HTTPException(status_code=409, detail=e.message, headers={"X-Error-Code": "SESSION_NOT_ACTIVE"})
    except NoActiveShiftError as e:
        raise HTTPException(status_code=403, detail=e.message, headers={"X-Error-Code": "NO_ACTIVE_SHIFT"})
    except NoPricingRuleError as e:
        raise HTTPException(status_code=503, detail=e.message, headers={"X-Error-Code": "NO_ACTIVE_PRICING_RULE"})

    return {
        "data": SessionResponse.model_validate(session).model_dump(mode="json"),
        "price_breakdown": PriceBreakdownResponse.model_validate(calc).model_dump(mode="json"),
    }

@router.get("/{session_id}/receipt")
async def get_session_receipt(
    session_id: int,
    current_user: User = Depends(require_any_role),
    db: AsyncSession = Depends(get_db),
    session_repo: ParkingSessionRepository = Depends(get_session_repo),
    session_service: SessionService = Depends(get_session_service),
):
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
            headers={"X-Error-Code": "SESSION_NOT_FOUND"},
        )

    # Fetch Operator Username
    operator_name = "Unknown"
    if session.exit_operator_id is not None:
        operator_res = await db.execute(
            select(User.username).where(User.id == session.exit_operator_id).limit(1)
        )
        operator_name = operator_res.scalar() or "Unknown"

    # Fetch Pricing Rule details
    rule_label = "Standard"
    rate_per_hour = 0
    grace_period_mins = 0
    lost_card_penalty = 0
    if session.pricing_rule_id is not None:
        rule_res = await db.execute(
            select(PricingRule).where(PricingRule.id == session.pricing_rule_id).limit(1)
        )
        rule = rule_res.scalars().first()
        if rule:
            rule_label = rule.label
            rate_per_hour = rule.rate_per_hour
            grace_period_mins = rule.grace_period_mins
            lost_card_penalty = rule.lost_card_penalty

    # Record receipt print timestamp
    await session_service.mark_receipt_printed(session_id)

    # Calculate receipt base/penalty details
    if session.is_lost_card:
        penalty_amount = lost_card_penalty
        base_amount = (session.amount_charged or 0) - lost_card_penalty
        is_grace_period = False
    else:
        penalty_amount = 0
        base_amount = session.amount_charged or 0
        is_grace_period = (session.duration_minutes or 0) <= grace_period_mins

    # Construct receipt data model
    receipt = ReceiptData(
        session_id=session.id,
        card_code=session.card_code,
        plate_number=session.plate_number,
        gate_number=session.gate_number,
        operator_name=operator_name,
        entry_time=session.entry_time,
        exit_time=session.exit_time or datetime.utcnow(),
        duration_minutes=session.duration_minutes or 0,
        duration_display=format_duration(session.duration_minutes or 0),
        pricing_rule_label=rule_label,
        rate_per_hour=rate_per_hour,
        grace_period_mins=grace_period_mins,
        base_amount=base_amount,
        penalty_amount=penalty_amount,
        total_amount=session.amount_charged or 0,
        total_display=format_egp(session.amount_charged or 0),
        payment_method="نقدي",
        is_lost_card=session.is_lost_card,
        is_grace_period=is_grace_period,
        company_name="garage4u",
        garage_name="جراج باب اللوق",
    )

    return {"data": receipt.model_dump(mode="json")}

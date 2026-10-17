from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Request, UploadFile, File, Form, Response, Body, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_admin
from models.user import User
from models.parking_card import CardStatus
from models.subscription import SubscriptionStatus
from repositories.subscription_plan_repo import SubscriptionPlanRepository
from repositories.subscriber_repo import SubscriberRepository
from repositories.subscription_repo import SubscriptionRepository
from repositories.card_repo import ParkingCardRepository
from repositories.session_repo import ParkingSessionRepository
from services.plate_service import PlateService
from services.audit_service import AuditService
from services.subscriber_service import SubscriberService
from services.subscription_service import SubscriptionService
from services.card_service import CardService
from services.excel_import_service import ExcelImportService

router = APIRouter(prefix="/ui/admin", tags=["ui-subscriptions"])


@router.get("/plans")
async def admin_plans_page(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    plan_repo = SubscriptionPlanRepository(db)
    plans = await plan_repo.get_all(active_only=False)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/plans.html",
        {
            "request": request,
            "user": current_user,
            "plans": plans,
        },
    )


@router.get("/subscribers")
async def admin_subscribers_page(
    request: Request,
    search: str | None = None,
    status: str | None = None,
    plan_id: int | None = None,
    expiring_days: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    subscriber_repo = SubscriberRepository(db)
    sub_repo = SubscriptionRepository(db)
    plan_repo = SubscriptionPlanRepository(db)
    audit_svc = AuditService(db)
    subscriber_service = SubscriberService(db, subscriber_repo, PlateService(), audit_svc)

    subscribers, total = await subscriber_service.get_filtered(
        search=search,
        status_filter=status,
        plan_id=plan_id,
        expiring_days=expiring_days,
        subscription_repo=sub_repo,
        page=page,
        size=size,
    )
    all_plans = await plan_repo.get_all(active_only=False)
    plans_map = {p.id: p for p in all_plans}
    active_plans = [p for p in all_plans if p.is_active]

    # Populate plan_label on active_subscription for template
    for sub in subscribers:
        if getattr(sub, "active_subscription", None) and sub.active_subscription.plan_id in plans_map:
            sub.active_subscription.plan_label = plans_map[sub.active_subscription.plan_id].label

    total_pages = (total + size - 1) // size if total > 0 else 1

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/subscribers.html",
        {
            "request": request,
            "user": current_user,
            "subscribers": subscribers,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "plans": active_plans,
            "search": search or "",
            "status": status or "",
            "plan_id": plan_id,
            "expiring_days": expiring_days,
        },
    )


@router.get("/subscribers/new")
async def admin_subscriber_new_page(
    request: Request,
    current_user: User = Depends(require_admin),
):
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/subscriber_new.html",
        {
            "request": request,
            "user": current_user,
        },
    )


# ---------------------------------------------------------------------------
# Excel Corporate / Bulk Subscribers Import (Must be before {subscriber_id})
# ---------------------------------------------------------------------------


@router.get("/subscribers/import")
@router.get("/subscribers-import")
async def admin_subscribers_import_page(
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    plan_repo = SubscriptionPlanRepository(db)
    active_plans = await plan_repo.get_all(active_only=True)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/subscribers_import.html",
        {
            "request": request,
            "user": current_user,
            "plans": active_plans,
        },
    )


@router.get("/subscribers/template-excel")
async def download_subscribers_template(
    current_user: User = Depends(require_admin),
):
    content = ExcelImportService.generate_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="subscribers_template.xlsx"'},
    )


@router.post("/subscribers/import-preview")
async def preview_subscribers_import(
    file: UploadFile = File(...),
    default_company: str = Form(""),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        content = await file.read()
        parsed = ExcelImportService.parse_file(content, file.filename or "upload.xlsx")
        preview_data = await ExcelImportService.preview(parsed, default_company.strip(), db)
        return JSONResponse(
            {
                "success": True,
                "data": preview_data,
                "parsed_rows": parsed,
            }
        )
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=400,
        )


@router.post("/subscribers/import-confirm")
async def confirm_subscribers_import(
    payload: Dict[str, Any] = Body(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = payload.get("rows", [])
        if not rows:
            return JSONResponse({"success": False, "error": "لا توجد بيانات للاستيراد"}, status_code=400)

        default_company = (payload.get("default_company") or "").strip()
        plan_id = payload.get("plan_id")
        if plan_id:
            plan_id = int(plan_id)
        update_existing = bool(payload.get("update_existing", True))

        result = await ExcelImportService.execute_import(
            parsed_rows=rows,
            default_company=default_company,
            plan_id=plan_id,
            update_existing=update_existing,
            current_user_id=current_user.id,
            db=db,
        )
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/subscribers/{subscriber_id}")
async def admin_subscriber_detail_page(
    subscriber_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    subscriber_repo = SubscriberRepository(db)
    sub_repo = SubscriptionRepository(db)
    plan_repo = SubscriptionPlanRepository(db)
    card_repo = ParkingCardRepository(db)
    session_repo = ParkingSessionRepository(db)

    subscriber = await subscriber_repo.get_by_id(subscriber_id)
    if not subscriber:
        return RedirectResponse("/ui/admin/subscribers", status_code=303)

    active_sub = await sub_repo.get_active_for_subscriber(subscriber_id)
    history = await sub_repo.get_all_by_subscriber(subscriber_id)

    # Attach plan details and card details to active subscription
    active_plan = None
    active_card = None
    if active_sub:
        active_plan = await plan_repo.get_by_id(active_sub.plan_id)
        if active_sub.card_id:
            active_card = await card_repo.get_by_id(active_sub.card_id)

    # Fetch recent sessions (last 10) for this subscriber
    sub_ids = [s.id for s in history]
    sessions, _ = await session_repo.get_by_subscription_ids(sub_ids, page=1, size=10)

    # Also map plans and cards for historical subscriptions
    all_plans = await plan_repo.get_all(active_only=False)
    plans_map = {p.id: p for p in all_plans}

    history_with_plans = []
    for s in history:
        history_with_plans.append({
            "subscription": s,
            "plan": plans_map.get(s.plan_id),
        })

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/subscriber_detail.html",
        {
            "request": request,
            "user": current_user,
            "subscriber": subscriber,
            "active_subscription": active_sub,
            "active_plan": active_plan,
            "active_card": active_card,
            "history": history_with_plans,
            "sessions": sessions,
        },
    )


@router.get("/subscribers/{subscriber_id}/subscribe")
async def admin_subscriber_subscribe_page(
    subscriber_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    subscriber_repo = SubscriberRepository(db)
    plan_repo = SubscriptionPlanRepository(db)
    card_repo = ParkingCardRepository(db)

    subscriber = await subscriber_repo.get_by_id(subscriber_id)
    if not subscriber:
        return RedirectResponse("/ui/admin/subscribers", status_code=303)

    active_plans = await plan_repo.get_all(active_only=True)
    cards, _ = await card_repo.get_all(status=CardStatus.AVAILABLE, page=1, size=200)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/subscriber_subscribe.html",
        {
            "request": request,
            "user": current_user,
            "subscriber": subscriber,
            "plans": active_plans,
            "cards": cards,
        },
    )


@router.get("/subscribers/{subscriber_id}/renew")
async def admin_subscriber_renew_page(
    subscriber_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    subscriber_repo = SubscriberRepository(db)
    sub_repo = SubscriptionRepository(db)
    plan_repo = SubscriptionPlanRepository(db)

    subscriber = await subscriber_repo.get_by_id(subscriber_id)
    if not subscriber:
        return RedirectResponse("/ui/admin/subscribers", status_code=303)

    active_sub = await sub_repo.get_active_for_subscriber(subscriber_id)
    if not active_sub:
        return RedirectResponse(f"/ui/admin/subscribers/{subscriber_id}/subscribe", status_code=303)

    plan = await plan_repo.get_by_id(active_sub.plan_id)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/subscriber_renew.html",
        {
            "request": request,
            "user": current_user,
            "subscriber": subscriber,
            "subscription": active_sub,
            "plan": plan,
        },
    )


@router.get("/subscriptions")
async def admin_subscriptions_page(
    request: Request,
    status: SubscriptionStatus | None = None,
    plan_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    sub_repo = SubscriptionRepository(db)
    plan_repo = SubscriptionPlanRepository(db)
    subscriber_repo = SubscriberRepository(db)

    subscriptions, total = await sub_repo.get_filtered(
        status=status,
        plan_id=plan_id,
        page=page,
        size=size,
    )

    all_plans = await plan_repo.get_all(active_only=False)
    active_plans = [p for p in all_plans if p.is_active]
    plans_map = {p.id: p for p in all_plans}

    # Fetch subscribers in batch
    subscriber_ids = list({s.subscriber_id for s in subscriptions})
    subscribers_map = {}
    for sid in subscriber_ids:
        sub = await subscriber_repo.get_by_id(sid)
        if sub:
            subscribers_map[sid] = sub

    enriched_items = []
    for s in subscriptions:
        sub_obj = subscribers_map.get(s.subscriber_id)
        plan_obj = plans_map.get(s.plan_id)
        enriched_items.append({
            "subscription": s,
            "subscriber": sub_obj,
            "plan": plan_obj,
        })

    total_pages = (total + size - 1) // size if total > 0 else 1

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/subscriptions.html",
        {
            "request": request,
            "user": current_user,
            "subscriptions": enriched_items,
            "total": total,
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "plans": active_plans,
            "status": status.value if status else "",
            "plan_id": plan_id,
        },
    )


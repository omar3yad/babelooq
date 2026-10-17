import pytest
import io
import openpyxl
from services.excel_import_service import ExcelImportService
from models.user import User, UserRole
from models.subscription_plan import SubscriptionPlan
from models.parking_card import ParkingCard, CardStatus
from models.subscriber import Subscriber
from models.subscription import Subscription


@pytest.mark.asyncio
async def test_generate_template():
    content = ExcelImportService.generate_template()
    assert isinstance(content, bytes)
    assert len(content) > 0

    # Read with openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content))
    ws = wb.active
    assert ws.title == "المشتركين"
    assert ws.cell(row=1, column=1).value == "رقم الكارت (إجباري)"


@pytest.mark.asyncio
async def test_parse_template():
    content = ExcelImportService.generate_template()
    rows = ExcelImportService.parse_file(content, "subscribers_template.xlsx")
    assert len(rows) == 4
    assert rows[0]["card_code"] == "3101"
    assert rows[0]["full_name"] == "أحمد محمد محمود"
    assert rows[0]["company_name"] == "بنك مصر"
    assert rows[0]["plate_number"] == "ق ر س 1 2 3"


@pytest.mark.asyncio
async def test_parse_csv():
    csv_text = "رقم الكارت,الاسم,الشركة,رقم اللوحة,الهاتف\n5001,علي حسن,البنك الأهلي,س ص ع 999,0109999999\n5002,منى سعيد,البنك الأهلي,,0108888888"
    rows = ExcelImportService.parse_file(csv_text.encode("utf-8-sig"), "data.csv")
    assert len(rows) == 2
    assert rows[0]["card_code"] == "5001"
    assert rows[0]["company_name"] == "البنك الأهلي"
    assert rows[1]["card_code"] == "5002"
    assert rows[1]["plate_number"] == ""


@pytest.mark.asyncio
async def test_preview_and_execute_import(db_session):
    # Setup test admin
    admin = User(
        username="testadmin_excel",
        hashed_password="hash",
        role=UserRole.ADMIN,
        full_name="Admin Test",
        is_active=True,
    )
    db_session.add(admin)

    # Setup Plan
    plan = SubscriptionPlan(
        label="باقة شهرية تجريبية",
        duration_days=30,
        price_piastres=50000,
        is_active=True,
        created_by=1,
    )
    db_session.add(plan)
    await db_session.flush()

    # Create one existing card
    card_existing = ParkingCard(
        card_code="7001",
        status=CardStatus.AVAILABLE,
        created_by=admin.id,
    )
    db_session.add(card_existing)
    await db_session.flush()

    parsed_rows = [
        {"row_num": 1, "card_code": "7001", "full_name": "سامي يوسف", "company_name": "بنك القاهرة", "plate_number": "أ ب ج 777", "phone_number": "0100000001", "notes": ""},
        {"row_num": 2, "card_code": "7002", "full_name": "ريم أحمد", "company_name": "بنك القاهرة", "plate_number": "", "phone_number": "0100000002", "notes": ""},
    ]

    # Test preview
    preview_res = await ExcelImportService.preview(parsed_rows, "بنك القاهرة", db_session)
    assert preview_res["total_rows"] == 2
    assert preview_res["new_cards_count"] == 1
    assert preview_res["existing_cards_count"] == 1

    # Test execute
    exec_res = await ExcelImportService.execute_import(
        parsed_rows=parsed_rows,
        default_company="بنك القاهرة",
        plan_id=plan.id,
        update_existing=True,
        current_user_id=admin.id,
        db=db_session,
    )

    assert exec_res["success"] is True
    assert exec_res["created_cards"] == 1  # 7002 created
    assert exec_res["created_subscribers"] == 2
    assert exec_res["created_subscriptions"] == 2

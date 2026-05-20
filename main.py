from fastapi import FastAPI, Request, Query, Depends, HTTPException, Form, UploadFile, File, Header
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Literal
from dotenv import load_dotenv
from whatsapp_service import send_whatsapp_message
from ai_service import ask_ai, close_ollama_client, warm_up_ollama
import os
import secrets
import traceback
import uuid
import shutil
from pathlib import Path
from database import (
    init_db,
    insert_booking,
    get_admin_dashboard_data,
    get_all_bookings,
    get_business_stats,
    get_customer_history,
    get_customer_vehicles,
    get_table_summary,
    get_vehicle_catalog,
    get_active_memberships,
    insert_customer_membership,
    update_booking_status,
    update_booking_vehicle,
    update_booking_payment,
    get_booking_status,
    get_booking_payment_info,
    delete_booking,
    insert_customer,
    update_customer,
    delete_customer,
    insert_vehicle,
    update_vehicle,
    delete_vehicle,
    insert_service,
    update_service,
    delete_service,
    insert_payment,
    update_payment,
    delete_payment,
    insert_membership,
    update_membership,
    delete_membership,
)

load_dotenv()

app = FastAPI(title="Xtreem Car Care")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

init_db()

_http_basic = HTTPBasic()


@app.on_event("startup")
async def startup_ai():
    try:
        await warm_up_ollama()
    except Exception:
        print("Ollama warmup skipped:")
        traceback.print_exc()


@app.on_event("shutdown")
async def shutdown_ai():
    await close_ollama_client()


def require_admin(credentials: HTTPBasicCredentials = Depends(_http_basic)):
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    ok = (
        secrets.compare_digest(credentials.username.encode(), admin_user.encode())
        and secrets.compare_digest(credentials.password.encode(), admin_pass.encode())
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="Xtreem Admin"'},
        )


def verify_admin_password(password: str | None):
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    if not password or not secrets.compare_digest(password, admin_pass):
        raise HTTPException(status_code=401, detail="Invalid admin password")


def customer_public_url(request: Request, token: str) -> str:
    public_base_url = (os.getenv("PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if public_base_url:
        return f"{public_base_url}/customer/{token}"
    return str(request.url_for("customer_history", token=token))


class StatusUpdate(BaseModel):
    status: Literal["pending", "confirmed", "completed", "cancelled"]


class BookingRequest(BaseModel):
    name: str
    phone: str
    vehicle_type: str
    vehicle_brand: str = ""
    vehicle_model: str
    vehicle_plate: str = ""
    service: str
    preferred_date: str
    preferred_time: str
    pickup_address: str = ""
    payment_method: str = ""


class AdminCustomerRequest(BaseModel):
    name: str
    phone: str
    whatsapp_opt_in: bool = True
    notes: str = ""


class AdminVehicleRequest(BaseModel):
    customer_id: int
    vehicle_type: str
    vehicle_brand: str = ""
    vehicle_model: str
    vehicle_plate: str = ""
    color: str = ""


class AdminServiceRequest(BaseModel):
    name: str
    category: str = "Custom"
    base_price: int = 0
    duration: str = ""
    active: bool = True


class AdminMembershipRequest(BaseModel):
    name: str
    monthly_price: int
    description: str = ""
    active: bool = True


class AdminPaymentRequest(BaseModel):
    booking_id: int | None = None
    customer_id: int | None = None
    amount: int = 0
    method: str = ""
    payment_status: Literal["unpaid", "paid", "partial", "refunded"] = "unpaid"
    reference: str = ""
    paid_at: str | None = None


class MembershipSignupRequest(BaseModel):
    name: str
    phone: str
    membership_id: int


@app.get("/")
async def home(request: Request):
    memberships = get_active_memberships()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"memberships": memberships},
    )


@app.post("/api/booking")
async def create_booking(booking: BookingRequest):
    data = booking.model_dump()
    data["vehicle_plate"] = "".join(ch for ch in data["vehicle_plate"].upper() if ch.isalnum())
    insert_booking(data)
    return JSONResponse({
        "success": True,
        "message": "Thank you! Your booking has been received. We will confirm your slot shortly."
    })


@app.post("/api/membership")
async def subscribe_membership(
    name: str = Form(...),
    phone: str = Form(...),
    membership_id: int = Form(...),
    payment_method: str = Form("UPI"),
    notes: str = Form(""),
    screenshot: UploadFile | None = File(None),
):
    if not screenshot:
        raise HTTPException(status_code=400, detail="Payment screenshot is required")

    upload_dir = Path("static") / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(screenshot.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{extension}"
    destination = upload_dir / filename

    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(screenshot.file, buffer)
    finally:
        screenshot.file.close()

    payment_proof = f"/static/uploads/{filename}"
    insert_customer_membership(
        name,
        phone,
        membership_id,
        payment_proof=payment_proof,
    )
    return JSONResponse({
        "success": True,
        "message": "Your membership subscription has been received. We will contact you soon."
    })


@app.get("/api/bookings")
async def list_bookings():
    return get_all_bookings()


@app.post("/admin/customers")
async def create_admin_customer(customer: AdminCustomerRequest, _=Depends(require_admin)):
    insert_customer(
        customer.name,
        customer.phone,
        1 if customer.whatsapp_opt_in else 0,
        customer.notes,
    )
    return {"success": True}


@app.patch("/admin/customers/{customer_id}")
async def update_admin_customer(customer_id: int, customer: AdminCustomerRequest, _=Depends(require_admin)):
    update_customer(
        customer_id,
        customer.name,
        customer.phone,
        1 if customer.whatsapp_opt_in else 0,
        customer.notes,
    )
    return {"success": True}


@app.delete("/admin/customers/{customer_id}")
async def remove_admin_customer(customer_id: int, _=Depends(require_admin)):
    delete_customer(customer_id)
    return {"success": True}


@app.post("/admin/vehicles")
async def create_admin_vehicle(vehicle: AdminVehicleRequest, _=Depends(require_admin)):
    insert_vehicle(
        vehicle.customer_id,
        vehicle.vehicle_type,
        vehicle.vehicle_brand,
        vehicle.vehicle_model,
        vehicle.vehicle_plate,
        vehicle.color,
    )
    return {"success": True}


@app.patch("/admin/vehicles/{vehicle_id}")
async def update_admin_vehicle(vehicle_id: int, vehicle: AdminVehicleRequest, _=Depends(require_admin)):
    update_vehicle(
        vehicle_id,
        vehicle.vehicle_type,
        vehicle.vehicle_brand,
        vehicle.vehicle_model,
        vehicle.vehicle_plate,
        vehicle.color,
    )
    return {"success": True}


@app.delete("/admin/vehicles/{vehicle_id}")
async def remove_admin_vehicle(vehicle_id: int, _=Depends(require_admin)):
    delete_vehicle(vehicle_id)
    return {"success": True}


@app.post("/admin/services")
async def create_admin_service(service: AdminServiceRequest, _=Depends(require_admin)):
    insert_service(
        service.name,
        service.category,
        service.base_price,
        service.duration,
        1 if service.active else 0,
    )
    return {"success": True}


@app.patch("/admin/services/{service_id}")
async def update_admin_service(service_id: int, service: AdminServiceRequest, _=Depends(require_admin)):
    update_service(
        service_id,
        service.name,
        service.category,
        service.base_price,
        service.duration,
        1 if service.active else 0,
    )
    return {"success": True}


@app.delete("/admin/services/{service_id}")
async def remove_admin_service(service_id: int, _=Depends(require_admin)):
    delete_service(service_id)
    return {"success": True}


@app.post("/admin/payments")
async def create_admin_payment(payment: AdminPaymentRequest, _=Depends(require_admin)):
    payment_id = insert_payment(
        payment.booking_id,
        payment.customer_id,
        payment.amount,
        payment.method,
        payment.payment_status,
        payment.reference,
        payment.paid_at,
    )
    if not payment_id:
        raise HTTPException(status_code=400, detail="Invalid booking or customer for payment")
    return {"success": True, "id": payment_id}


@app.patch("/admin/payments/{payment_id}")
async def update_admin_payment(payment_id: int, payment: AdminPaymentRequest, _=Depends(require_admin)):
    success = update_payment(
        payment_id,
        payment.booking_id,
        payment.customer_id,
        payment.amount,
        payment.method,
        payment.payment_status,
        payment.reference,
        payment.paid_at,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Invalid payment, booking, or customer")
    return {"success": True}


@app.patch("/admin/bookings/{booking_id}/payment")
async def update_admin_booking_payment(
    booking_id: int,
    payment: AdminPaymentRequest,
    admin_password: str | None = Header(None, alias="X-Admin-Password"),
    _=Depends(require_admin),
):
    current_payment = get_booking_payment_info(booking_id)
    if current_payment is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_payment["payment_status"] != "unpaid" and (
        payment.payment_status != current_payment["payment_status"]
        or payment.method != current_payment["method"]
        or payment.amount != current_payment["amount"]
        or payment.reference != (current_payment["reference"] or "")
        or payment.paid_at != current_payment["paid_at"]
    ):
        verify_admin_password(admin_password)

    success = update_booking_payment(
        booking_id,
        payment.amount,
        payment.method,
        payment.payment_status,
        payment.reference,
        payment.paid_at,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Invalid booking")
    return {"success": True}


@app.delete("/admin/payments/{payment_id}")
async def remove_admin_payment(payment_id: int, _=Depends(require_admin)):
    if not delete_payment(payment_id):
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"success": True}


@app.post("/admin/memberships")
async def create_admin_membership(membership: AdminMembershipRequest, _=Depends(require_admin)):
    insert_membership(
        membership.name,
        membership.monthly_price,
        membership.description,
        1 if membership.active else 0,
    )
    return {"success": True}


@app.patch("/admin/memberships/{membership_id}")
async def update_admin_membership(membership_id: int, membership: AdminMembershipRequest, _=Depends(require_admin)):
    update_membership(
        membership_id,
        membership.name,
        membership.monthly_price,
        membership.description,
        1 if membership.active else 0,
    )
    return {"success": True}


@app.delete("/admin/memberships/{membership_id}")
async def remove_admin_membership(membership_id: int, _=Depends(require_admin)):
    delete_membership(membership_id)
    return {"success": True}


@app.get("/api/vehicle-catalog")
async def vehicle_catalog():
    return get_vehicle_catalog()


class AIRequest(BaseModel):
    question: str


@app.post("/api/ai-chat")
async def ai_chat(request: AIRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        answer = await ask_ai(question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI assistant error: {exc}")
    return {"success": True, "answer": answer}


@app.get("/api/customer-vehicles")
async def customer_vehicles(
    customer_id: int | None = Query(None, ge=1),
    phone: str | None = Query(None),
):
    return get_customer_vehicles(customer_id=customer_id, phone=phone)


@app.patch("/admin/bookings/{booking_id}/vehicle")
async def change_booking_vehicle(booking_id: int, body: dict, _=Depends(require_admin)):
    vehicle_id = body.get('vehicle_id')
    if not isinstance(vehicle_id, int):
        raise HTTPException(status_code=400, detail='vehicle_id is required')
    success = update_booking_vehicle(booking_id, vehicle_id)
    if not success:
        raise HTTPException(status_code=400, detail='Invalid booking or vehicle')
    return {"success": True}


@app.get("/customer/{token}")
async def customer_history(request: Request, token: str):
    history = get_customer_history(token)
    if not history:
        raise HTTPException(status_code=404, detail="Customer history not found")
    return templates.TemplateResponse(
        request=request,
        name="customer.html",
        context={"history": history},
    )


@app.get("/admin")
async def admin_panel(request: Request, _=Depends(require_admin)):
    bookings = get_all_bookings()
    stats = get_business_stats()
    dashboard = get_admin_dashboard_data()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"bookings": bookings, "stats": stats, "dashboard": dashboard},
    )


@app.get("/admin/schema")
async def admin_schema(_=Depends(require_admin)):
    return get_table_summary()


@app.patch("/admin/bookings/{booking_id}/status")
async def set_booking_status(
    booking_id: int,
    body: StatusUpdate,
    admin_password: str | None = Header(None, alias="X-Admin-Password"),
    _=Depends(require_admin),
):
    current_status = get_booking_status(booking_id)
    if current_status is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    if current_status != "pending" and current_status != body.status:
        verify_admin_password(admin_password)

    update_booking_status(booking_id, body.status)
    return {"success": True}


@app.delete("/admin/bookings/{booking_id}")
async def remove_booking(booking_id: int, _=Depends(require_admin)):
    delete_booking(booking_id)
    return {"success": True}


@app.get("/admin/customer-qr/{token}.svg")
async def customer_qr(request: Request, token: str, _=Depends(require_admin)):
    url = customer_public_url(request, token)
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Install qrcode[pil] to generate customer QR codes.",
        ) from exc

    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=10, border=2)
    return Response(content=img.to_string().decode("utf-8"), media_type="image/svg+xml")


@app.get("/admin/customer-qr/{token}")
async def customer_qr_preview(request: Request, token: str, _=Depends(require_admin)):
    history = get_customer_history(token)
    if not history:
        raise HTTPException(status_code=404, detail="Customer history not found")
    scan_url = customer_public_url(request, token)
    is_local_url = "127.0.0.1" in scan_url or "localhost" in scan_url
    return templates.TemplateResponse(
        request=request,
        name="qr_preview.html",
        context={
            "history": history,
            "token": token,
            "scan_url": scan_url,
            "is_local_url": is_local_url,
        },
    )


@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == os.getenv("VERIFY_TOKEN"):
        return int(hub_challenge)
    return {"error": "Verification failed"}


@app.post("/webhook")
async def receive_message(request: Request):
    try:
        data = await request.json()
        print("Incoming webhook:", data)

        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return {"status": "ignored"}

        message = value["messages"][0]

        if message.get("type") != "text":
            return {"status": "ignored"}

        sender = message.get("from")

        if not sender:
            return {"status": "sample payload"}

        user_message = message["text"]["body"]
        print("Sender:", sender)
        print("User Message:", user_message)

        send_whatsapp_message(sender, "Hello! Your WhatsApp chatbot is working successfully.")
        print("Reply sent successfully.")
        return {"status": "success"}

    except Exception:
        print("ERROR OCCURRED:")
        traceback.print_exc()
        return {"status": "error"}

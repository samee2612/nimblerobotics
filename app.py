"""Fulfillment Exception Copilot — a local demo application with synthetic data."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

ROOT = Path(__file__).parent
MAX_AUTO_APPROVAL_COST = 25.00


class Order(BaseModel):
    id: str
    customer: str
    destination: str
    sku: str
    product: str
    quantity: int
    value: float
    promised_delivery: str
    risk: str
    risk_reason: str


class InventoryPosition(BaseModel):
    warehouse: str
    city: str
    on_hand: int
    reserved: int
    available_to_promise: int
    transit_days: int


class CarrierOption(BaseModel):
    service: str
    delivery_days: int
    incremental_cost: float
    cutoff_status: str
    eligible: bool


class RecoveryPlan(BaseModel):
    action: Literal["reroute_inventory", "expedite_from_origin"]
    source_warehouse: str
    carrier_service: str
    incremental_cost: float = Field(ge=0)
    customer_impact: str
    rationale: str
    confidence: Literal["high", "medium", "low"]


class RecoveryOption(BaseModel):
    title: str
    detail: str
    incremental_cost: float
    status: Literal["recommended", "viable", "rejected"]


class ValidationResult(BaseModel):
    valid: bool
    checks: list[dict]
    rejection_reason: str | None = None


class PlanResponse(BaseModel):
    plan: RecoveryPlan
    source: Literal["gemini", "local fallback"]
    validation: ValidationResult
    tools_used: list[str]
    recovery_options: list[RecoveryOption]
    decision_context: str
    ai_status: str


class ApprovalRequest(BaseModel):
    order_id: str = ORDER.id if 'ORDER' in globals() else "NB-48291"
    plan: RecoveryPlan
    approved_by: str = "Operations Coordinator"


class AuditEntry(BaseModel):
    id: str
    order_id: str
    approved_by: str
    approved_at: str
    decision: str
    incremental_cost: float


ORDER = Order(
    id="NB-48291",
    customer="Avery Chen",
    destination="San Francisco, CA",
    sku="HX-42-GRAPHITE",
    product="Nimbus Home Hub",
    quantity=1,
    value=389.00,
    promised_delivery="Tomorrow by 8 PM",
    risk="High risk",
    risk_reason="Origin sortation delay means the current carrier handoff will miss its 4:30 PM cutoff.",
)

ORDERS = [
    ORDER,
    Order(id="NB-48307", customer="Jordan Lee", destination="Austin, TX", sku="CAM-11-WHITE", product="Nimble Vision Cam", quantity=1, value=149.00, promised_delivery="Friday by 8 PM", risk="Medium risk", risk_reason="A replenishment delay may miss the regional sort window."),
    Order(id="NB-48322", customer="Maya Patel", destination="Chicago, IL", sku="RB-08-BLACK", product="Rover Dock", quantity=1, value=229.00, promised_delivery="Tomorrow by noon", risk="High risk", risk_reason="Carrier capacity is constrained and the current label is not scanned."),
]


def get_order(order_id: str) -> Order:
    return next((item for item in ORDERS if item.id == order_id), ORDER)

INVENTORY = [
    InventoryPosition(
        warehouse="Reno, NV", city="Reno", on_hand=4, reserved=4,
        available_to_promise=0, transit_days=1,
    ),
    InventoryPosition(
        warehouse="Ontario, CA", city="Ontario", on_hand=7, reserved=2,
        available_to_promise=5, transit_days=1,
    ),
    InventoryPosition(
        warehouse="Phoenix, AZ", city="Phoenix", on_hand=11, reserved=1,
        available_to_promise=10, transit_days=2,
    ),
]

CARRIERS = [
    CarrierOption(
        service="UPS Next Day Air", delivery_days=1, incremental_cost=18.50,
        cutoff_status="Eligible · cutoff in 1h 18m", eligible=True,
    ),
    CarrierOption(
        service="FedEx Priority Overnight", delivery_days=1, incremental_cost=24.00,
        cutoff_status="Eligible · cutoff in 46m", eligible=True,
    ),
    CarrierOption(
        service="Ground", delivery_days=2, incremental_cost=0.00,
        cutoff_status="Misses promise date", eligible=False,
    ),
]

FALLBACK_PLAN = RecoveryPlan(
    action="reroute_inventory",
    source_warehouse="Ontario, CA",
    carrier_service="UPS Next Day Air",
    incremental_cost=18.50,
    customer_impact="Arrives tomorrow by 8 PM; no customer outreach required.",
    rationale=(
        "Ontario has 5 units available-to-promise, is one day from the destination, "
        "and can still meet the UPS Next Day Air cutoff. It is the lowest-cost valid option."
    ),
    confidence="high",
)

RECOVERY_OPTIONS = [
    RecoveryOption(
        title="Ontario, CA → UPS Next Day Air",
        detail="Meets promise date at the lowest valid incremental cost.",
        incremental_cost=18.50,
        status="recommended",
    ),
    RecoveryOption(
        title="Ontario, CA → FedEx Priority Overnight",
        detail="Also meets the promise date, but costs $5.50 more.",
        incremental_cost=24.00,
        status="viable",
    ),
    RecoveryOption(
        title="Keep current shipment → Ground",
        detail="No extra cost, but it misses the customer's promised delivery date.",
        incremental_cost=0.00,
        status="rejected",
    ),
]


class Scenario(BaseModel):
    inventory: list[InventoryPosition]
    carriers: list[CarrierOption]
    fallback_plan: RecoveryPlan
    recovery_options: list[RecoveryOption]


SCENARIOS = {
    ORDER.id: Scenario(
        inventory=INVENTORY, carriers=CARRIERS, fallback_plan=FALLBACK_PLAN,
        recovery_options=RECOVERY_OPTIONS,
    ),
    "NB-48307": Scenario(
        inventory=[
            InventoryPosition(warehouse="Reno, NV", city="Reno", on_hand=3, reserved=3, available_to_promise=0, transit_days=2),
            InventoryPosition(warehouse="Phoenix, AZ", city="Phoenix", on_hand=12, reserved=1, available_to_promise=11, transit_days=2),
            InventoryPosition(warehouse="Ontario, CA", city="Ontario", on_hand=2, reserved=2, available_to_promise=0, transit_days=3),
        ],
        carriers=[
            CarrierOption(service="Ground", delivery_days=2, incremental_cost=0.00, cutoff_status="Eligible · arrives Friday", eligible=True),
            CarrierOption(service="UPS 2nd Day Air", delivery_days=2, incremental_cost=10.00, cutoff_status="Eligible · unnecessary for promise", eligible=True),
        ],
        fallback_plan=RecoveryPlan(action="reroute_inventory", source_warehouse="Phoenix, AZ", carrier_service="Ground", incremental_cost=0.00, customer_impact="Arrives Friday by 8 PM; no customer outreach required.", rationale="Phoenix has 11 available units and standard Ground service still meets Friday's promise at no incremental cost.", confidence="high"),
        recovery_options=[
            RecoveryOption(title="Phoenix, AZ → Ground", detail="Meets Friday promise with 11 units available and no extra cost.", incremental_cost=0.00, status="recommended"),
            RecoveryOption(title="Phoenix, AZ → UPS 2nd Day Air", detail="Also works, but adds $10 with no service benefit.", incremental_cost=10.00, status="viable"),
            RecoveryOption(title="Reno, NV → Ground", detail="Looks close, but every unit is already reserved.", incremental_cost=0.00, status="rejected"),
        ],
    ),
    "NB-48322": Scenario(
        inventory=[
            InventoryPosition(warehouse="Reno, NV", city="Reno", on_hand=6, reserved=6, available_to_promise=0, transit_days=2),
            InventoryPosition(warehouse="Ontario, CA", city="Ontario", on_hand=3, reserved=2, available_to_promise=1, transit_days=1),
            InventoryPosition(warehouse="Phoenix, AZ", city="Phoenix", on_hand=8, reserved=2, available_to_promise=6, transit_days=2),
        ],
        carriers=[
            CarrierOption(service="UPS Next Day Air", delivery_days=1, incremental_cost=18.50, cutoff_status="Cutoff missed", eligible=False),
            CarrierOption(service="FedEx Priority Overnight", delivery_days=1, incremental_cost=24.00, cutoff_status="Eligible · cutoff in 46m", eligible=True),
            CarrierOption(service="Ground", delivery_days=2, incremental_cost=0.00, cutoff_status="Misses noon promise", eligible=False),
        ],
        fallback_plan=RecoveryPlan(action="reroute_inventory", source_warehouse="Ontario, CA", carrier_service="FedEx Priority Overnight", incremental_cost=24.00, customer_impact="Arrives tomorrow by noon; promise preserved.", rationale="Only Ontario has available inventory close enough, and FedEx Priority Overnight is the sole carrier still inside its cutoff.", confidence="high"),
        recovery_options=[
            RecoveryOption(title="Ontario, CA → FedEx Priority Overnight", detail="Only eligible carrier that preserves the noon promise.", incremental_cost=24.00, status="recommended"),
            RecoveryOption(title="Ontario, CA → UPS Next Day Air", detail="Cheaper, but the carrier cutoff has already passed.", incremental_cost=18.50, status="rejected"),
            RecoveryOption(title="Phoenix, AZ → Ground", detail="No extra cost, but transit time misses the noon promise.", incremental_cost=0.00, status="rejected"),
        ],
    ),
}


def get_scenario(order_id: str) -> Scenario:
    return SCENARIOS.get(order_id, SCENARIOS[ORDER.id])


def validate_plan_for(plan: RecoveryPlan, order: Order, scenario: Scenario) -> ValidationResult:
    warehouse = next((item for item in scenario.inventory if item.warehouse == plan.source_warehouse), None)
    carrier = next((item for item in scenario.carriers if item.service == plan.carrier_service), None)
    checks = [
        {"name": "Available-to-promise inventory", "passed": bool(warehouse and warehouse.available_to_promise >= order.quantity), "detail": f"{warehouse.available_to_promise} available unit(s) at {warehouse.warehouse}" if warehouse else "Unknown warehouse"},
        {"name": "Delivery promise and carrier cutoff", "passed": bool(carrier and carrier.eligible), "detail": carrier.cutoff_status if carrier else "Unknown carrier service"},
        {"name": "Auto-approval cost limit", "passed": plan.incremental_cost <= MAX_AUTO_APPROVAL_COST, "detail": f"${plan.incremental_cost:.2f} of ${MAX_AUTO_APPROVAL_COST:.2f} allowed"},
    ]
    failed = next((check for check in checks if not check["passed"]), None)
    return ValidationResult(valid=failed is None, checks=checks, rejection_reason=f"Rejected: {failed['name']} — {failed['detail']}" if failed else None)


def gemini_plan_for(order: Order, scenario: Scenario) -> RecoveryPlan:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    from google import genai
    from google.genai import types
    eligible_inventory = [item.model_dump() for item in scenario.inventory if item.available_to_promise >= order.quantity]
    eligible_carriers = [item.model_dump() for item in scenario.carriers if item.eligible]
    prompt = f"""You are a fulfillment operations copilot. Choose one recovery plan for this order.
Order: {order.model_dump()}
Inventory tool result: {eligible_inventory}
Carrier tool result: {eligible_carriers}
Choose only facts from these results. Prefer the lowest cost option that preserves the promise. Return JSON only."""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"), contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=RecoveryPlan, temperature=0.2),
    )
    return RecoveryPlan.model_validate_json(response.text)


def inventory_tool() -> list[InventoryPosition]:
    """Operational data tool: availability excludes already-reserved stock."""
    return INVENTORY


def carrier_tool() -> list[CarrierOption]:
    """Operational data tool: only services that meet delivery promise are eligible."""
    return CARRIERS


def validate_plan(plan: RecoveryPlan) -> ValidationResult:
    warehouse = next((item for item in INVENTORY if item.warehouse == plan.source_warehouse), None)
    carrier = next((item for item in CARRIERS if item.service == plan.carrier_service), None)
    checks = [
        {
            "name": "Available-to-promise inventory",
            "passed": bool(warehouse and warehouse.available_to_promise >= ORDER.quantity),
            "detail": (
                f"{warehouse.available_to_promise} available unit(s) at {warehouse.warehouse}"
                if warehouse else "Unknown warehouse"
            ),
        },
        {
            "name": "Delivery promise and carrier cutoff",
            "passed": bool(carrier and carrier.eligible),
            "detail": carrier.cutoff_status if carrier else "Unknown carrier service",
        },
        {
            "name": "Auto-approval cost limit",
            "passed": plan.incremental_cost <= MAX_AUTO_APPROVAL_COST,
            "detail": f"${plan.incremental_cost:.2f} of ${MAX_AUTO_APPROVAL_COST:.2f} allowed",
        },
    ]
    failed = next((check for check in checks if not check["passed"]), None)
    return ValidationResult(
        valid=failed is None,
        checks=checks,
        rejection_reason=(f"Rejected: {failed['name']} — {failed['detail']}" if failed else None),
    )


def gemini_plan() -> RecoveryPlan:
    """Ask Gemini for a typed recommendation using pre-queried operational facts."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    eligible_inventory = [item.model_dump() for item in inventory_tool() if item.available_to_promise >= ORDER.quantity]
    eligible_carriers = [item.model_dump() for item in carrier_tool() if item.eligible]
    prompt = f"""You are a fulfillment operations copilot. Recommend one recovery plan for this delayed order.
Order: {ORDER.model_dump()}
Eligible inventory tool result: {eligible_inventory}
Eligible carrier tool result: {eligible_carriers}

Rules: use only an eligible warehouse and carrier shown above. Prefer the lowest incremental cost that still preserves the promised delivery date. Do not invent facts. Return the requested JSON only."""
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RecoveryPlan,
            temperature=0.2,
        ),
    )
    return RecoveryPlan.model_validate_json(response.text)


app = FastAPI(title="Fulfillment Exception Copilot")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def homepage():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/exception")
def get_exception(order_id: str = "NB-48291"):
    scenario = get_scenario(order_id)
    return {"order": get_order(order_id), "orders": ORDERS, "inventory": scenario.inventory, "carriers": scenario.carriers, "auto_approval_limit": MAX_AUTO_APPROVAL_COST}


@app.post("/api/plan", response_model=PlanResponse)
def generate_plan(order_id: str = "NB-48291"):
    order = get_order(order_id)
    scenario = get_scenario(order_id)
    source: Literal["gemini", "local fallback"] = "local fallback"
    ai_status = "Gemini is not configured; local decision rules selected the recommendation."
    try:
        plan = gemini_plan_for(order, scenario)
        source = "gemini"
        ai_status = f"Gemini ({os.getenv('GEMINI_MODEL')}) generated this structured recommendation."
    except Exception as error:
        plan = scenario.fallback_plan
        if os.getenv("GEMINI_API_KEY"):
            ai_status = f"Gemini was unavailable ({type(error).__name__}); local decision rules selected the recommendation."

    validation = validate_plan_for(plan, order, scenario)
    if not validation.valid:
        plan = scenario.fallback_plan
        validation = validate_plan_for(plan, order, scenario)
        source = "local fallback"

    return PlanResponse(
        plan=plan,
        source=source,
        validation=validation,
        tools_used=["inventory availability lookup", "carrier cutoff lookup", "cost policy validation"],
        recovery_options=scenario.recovery_options,
        decision_context=f"{order.id}: {len(scenario.inventory)} warehouse positions and {len(scenario.carriers)} carrier options were evaluated.",
        ai_status=ai_status,
    )


@app.post("/api/approve", response_model=AuditEntry)
def approve_plan(request: ApprovalRequest):
    validation = validate_plan_for(request.plan, get_order(request.order_id), get_scenario(request.order_id))
    if not validation.valid:
        raise HTTPException(status_code=400, detail=validation.rejection_reason)
    return AuditEntry(
        id=f"AUD-{uuid4().hex[:8].upper()}",
        order_id=request.order_id,
        approved_by=request.approved_by,
        approved_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        decision=f"{request.plan.source_warehouse} via {request.plan.carrier_service}",
        incremental_cost=request.plan.incremental_cost,
    )

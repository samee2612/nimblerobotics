from fastapi.testclient import TestClient

from app import FALLBACK_PLAN, REJECTED_CANDIDATE, app, validate_plan

client = TestClient(app)


def test_reserved_inventory_candidate_is_rejected():
    result = validate_plan(REJECTED_CANDIDATE)
    assert result.valid is False
    assert "Available-to-promise" in result.rejection_reason


def test_fallback_plan_passes_every_policy_check():
    result = validate_plan(FALLBACK_PLAN)
    assert result.valid is True
    assert all(check["passed"] for check in result.checks)


def test_exception_endpoint_exposes_synthetic_operational_data():
    response = client.get("/api/exception")
    assert response.status_code == 200
    assert response.json()["order"]["id"] == "NB-48291"
    assert len(response.json()["orders"]) == 3


def test_queue_can_select_a_different_order():
    response = client.get("/api/exception", params={"order_id": "NB-48307"})
    assert response.status_code == 200
    assert response.json()["order"]["customer"] == "Jordan Lee"


def test_each_order_has_its_own_recovery_decision(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    first = client.post("/api/plan", params={"order_id": "NB-48291"}).json()
    second = client.post("/api/plan", params={"order_id": "NB-48307"}).json()
    third = client.post("/api/plan", params={"order_id": "NB-48322"}).json()
    assert first["plan"]["carrier_service"] == "UPS Next Day Air"
    assert second["plan"]["carrier_service"] == "Ground"
    assert third["plan"]["carrier_service"] == "FedEx Priority Overnight"


def test_plan_endpoint_remains_reliable_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post("/api/plan")
    assert response.status_code == 200
    assert response.json()["validation"]["valid"] is True
    assert len(response.json()["recovery_options"]) == 3


def test_approval_creates_audit_record():
    response = client.post("/api/approve", json={"plan": FALLBACK_PLAN.model_dump()})
    assert response.status_code == 200
    assert response.json()["id"].startswith("AUD-")

"""API integration tests: auth, RBAC, cameras, zones, events, reports, WS."""
import time

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin(client):
    r = client.post("/api/auth/login",
                    json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_login_bad_password(client):
    r = client.post("/api/auth/login",
                    json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_missing_token(client):
    assert client.get("/api/cameras").status_code == 401


def test_cameras_list(client, admin):
    r = client.get("/api/cameras", headers=admin)
    assert r.status_code == 200
    assert len(r.json()) == 4


def test_rbac_viewer_forbidden(client):
    r = client.post("/api/auth/login",
                    json={"username": "viewer", "password": "viewer123"})
    tok = r.json()["token"]
    r = client.get("/api/admin/users", headers={"Authorization": "Bearer " + tok})
    assert r.status_code == 403


def test_add_and_delete_camera(client, admin):
    r = client.post("/api/cameras", headers=admin, json={
        "bop_id": 1, "name": "CAM-TEST", "source_type": "synthetic",
        "source_config": {"type": "synthetic", "scene": "checkpoint"}})
    assert r.status_code == 201
    new = [c for c in r.json() if c["name"] == "CAM-TEST"][0]
    time.sleep(3)  # worker connects
    st = client.get("/api/system/status", headers=admin).json()
    assert any(c["id"] == new["id"] and c["status"] == "online"
               for c in st["cameras"])
    assert client.delete(f"/api/cameras/{new['id']}", headers=admin).status_code == 200


def test_zone_crud(client, admin):
    r = client.post("/api/cameras/1/zones", headers=admin, json={
        "name": "test-zone", "kind": "perimeter",
        "points": [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]})
    assert r.status_code == 201
    zid = r.json()["id"]
    zs = client.get("/api/zones?camera_id=1", headers=admin).json()
    assert any(z["id"] == zid for z in zs)
    assert client.delete(f"/api/zones/{zid}", headers=admin).status_code == 200


def test_events_and_reports(client, admin):
    time.sleep(14)  # synthetic scenes produce their first breach by ~11 s
    evs = client.get("/api/events?limit=50", headers=admin).json()
    assert isinstance(evs, list) and len(evs) >= 1
    rep = client.get("/api/reports/summary?days=1", headers=admin).json()
    assert rep["totals"]["total"] >= 1
    assert "by_type" in rep and "by_day" in rep and "by_camera" in rep


def test_system_status(client, admin):
    r = client.get("/api/system/status", headers=admin)
    assert r.status_code == 200
    assert len(r.json()["cameras"]) == 4


def test_websocket_authed(client, admin):
    tok = admin["Authorization"].split()[-1]
    with client.websocket_connect(f"/ws/realtime?token={tok}") as ws:
        msg = ws.receive_text()
        assert msg.startswith("{")


def test_audit_trail(client, admin):
    # admin sees the seeded audit entry; viewer is forbidden
    r = client.get("/api/admin/audit?limit=10", headers=admin)
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list) and len(rows) >= 1
    assert {"id", "action", "detail", "at", "user"} <= set(rows[0].keys())
    assert rows[0]["action"]  # e.g. "seed" / "user.add" / "event.ack"
    v = client.post("/api/auth/login",
                    json={"username": "viewer", "password": "viewer123"})
    vt = v.json()["token"]
    assert client.get("/api/admin/audit",
                      headers={"Authorization": "Bearer " + vt}).status_code == 403

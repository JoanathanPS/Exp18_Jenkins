"""
Unit tests run by Jenkins in the 'Test' stage, *inside* the freshly built
Docker image (see Jenkinsfile) — this is what proves the pipeline isn't
just building blindly, it's actually validating the app before deploy.
"""

from app import app


def client():
    app.testing = True
    return app.test_client()


def test_index_returns_200():
    resp = client().get("/")
    assert resp.status_code == 200
    assert "message" in resp.get_json()


def test_health_check():
    resp = client().get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_add_endpoint():
    resp = client().get("/add/3/4")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["sum"] == 7


def test_add_endpoint_negative_case():
    resp = client().get("/add/0/0")
    assert resp.get_json()["sum"] == 0

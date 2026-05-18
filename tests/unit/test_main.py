import pytest

from app.main import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["message"] == "hello world"


def test_version_shape(client):
    response = client.get("/version")
    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload.keys()) == {"version", "environment", "commit"}


def test_items_crud_roundtrip(client):
    assert client.get("/items").get_json() == []

    created = client.post("/items", json={"name": "widget", "price": 9.99})
    assert created.status_code == 201
    body = created.get_json()
    assert body["name"] == "widget"
    assert body["price"] == 9.99
    item_id = body["id"]

    fetched = client.get(f"/items/{item_id}")
    assert fetched.status_code == 200
    assert fetched.get_json() == body

    deleted = client.delete(f"/items/{item_id}")
    assert deleted.status_code == 204
    assert client.get(f"/items/{item_id}").status_code == 404


def test_create_item_validation(client):
    response = client.post("/items", json={"name": "", "price": 1.0})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_missing_item_returns_404(client):
    assert client.get("/items/9999").status_code == 404
    assert client.delete("/items/9999").status_code == 404

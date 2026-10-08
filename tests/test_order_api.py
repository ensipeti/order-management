import pytest
from fastapi.testclient import TestClient

from order_management.order_api import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_add_price_and_remove(client: TestClient) -> None:
    first = {"order_id": 1, "symbol": "JPM", "side": "Buy", "amount": 20, "price": 20}
    second = first | {"order_id": 4, "amount": 10, "price": 21}
    assert client.post("/orders", json=first).status_code == 201
    assert client.post("/orders", json=second).status_code == 201
    assert client.get("/orders/1").json() == first
    for _ in range(2):
        response = client.post("/prices", json={"symbol": "JPM", "side": "Buy", "amount": 22})
        assert response.status_code == 200
        assert response.json()["total_price"] == 442
    deleted = client.delete("/orders/1")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get("/orders/1").status_code == 404
    assert (
        client.post("/prices", json={"symbol": "JPM", "side": "Buy", "amount": 11}).status_code
        == 409
    )


def test_errors_and_generated_docs(client: TestClient) -> None:
    order = {"order_id": 1, "symbol": "JPM", "side": "Buy", "amount": 20, "price": 20}
    client.post("/orders", json=order)
    assert client.post("/orders", json=order).status_code == 409
    assert client.delete("/orders/999").status_code == 404
    assert client.post("/orders", json=order | {"side": "Invalid"}).status_code == 422
    assert client.post("/orders", json=order | {"amount": "20"}).status_code == 422
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert set(client.get("/openapi.json").json()["paths"]) == {
        "/orders",
        "/orders/{order_id}",
        "/prices",
    }


def test_instances_have_separate_state(client: TestClient) -> None:
    client.post(
        "/orders", json={"order_id": 1, "symbol": "JPM", "side": "Buy", "amount": 20, "price": 20}
    )
    assert TestClient(create_app()).get("/orders/1").status_code == 404

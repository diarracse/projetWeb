"""Tests fonctionnels des routes de l'API."""
import json


# ── GET / ──────────────────────────────────────────────────────────────────────

def test_get_products_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_get_products_returns_json_with_products_key(client):
    resp = client.get("/")
    data = resp.get_json()
    assert "products" in data
    assert isinstance(data["products"], list)


def test_get_products_contains_seeded_products(client):
    resp = client.get("/")
    ids = [p["id"] for p in resp.get_json()["products"]]
    assert 1 in ids
    assert 4 in ids


# ── POST /order ────────────────────────────────────────────────────────────────

def test_post_order_missing_product_returns_422(client):
    resp = client.post("/order", json={})
    assert resp.status_code == 422
    assert resp.get_json()["errors"]["product"]["code"] == "missing-fields"


def test_post_order_missing_id_returns_422(client):
    resp = client.post("/order", json={"product": {"quantity": 1}})
    assert resp.status_code == 422


def test_post_order_missing_quantity_returns_422(client):
    resp = client.post("/order", json={"product": {"id": 1}})
    assert resp.status_code == 422


def test_post_order_quantity_zero_returns_422(client):
    resp = client.post("/order", json={"product": {"id": 1, "quantity": 0}})
    assert resp.status_code == 422


def test_post_order_out_of_stock_returns_422(client):
    resp = client.post("/order", json={"product": {"id": 4, "quantity": 1}})
    assert resp.status_code == 422
    assert resp.get_json()["errors"]["product"]["code"] == "out-of-inventory"


def test_post_order_success_returns_302(client):
    resp = client.post(
        "/order",
        json={"product": {"id": 1, "quantity": 1}},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/order/" in resp.headers["Location"]


def test_post_order_unknown_product_returns_422(client):
    resp = client.post("/order", json={"product": {"id": 9999, "quantity": 1}})
    assert resp.status_code == 422


# ── GET /order/<id> ────────────────────────────────────────────────────────────

def _create_order(client):
    resp = client.post(
        "/order",
        json={"product": {"id": 1, "quantity": 2}},
        follow_redirects=False,
    )
    location = resp.headers["Location"]
    order_id = int(location.split("/")[-1])
    return order_id


def test_get_order_not_found_returns_404(client):
    resp = client.get("/order/99999")
    assert resp.status_code == 404


def test_get_order_returns_correct_structure(client):
    oid = _create_order(client)
    resp = client.get(f"/order/{oid}")
    assert resp.status_code == 200
    order = resp.get_json()["order"]
    for key in ("id", "product", "total_price", "shipping_price", "paid",
                "email", "shipping_information", "credit_card", "transaction"):
        assert key in order


def test_get_order_total_price_is_price_times_quantity(client):
    oid = _create_order(client)
    order = client.get(f"/order/{oid}").get_json()["order"]
    assert order["total_price"] == 2810 * 2


def test_get_order_shipping_price_for_800g(client):
    oid = _create_order(client)
    order = client.get(f"/order/{oid}").get_json()["order"]
    assert order["shipping_price"] == 1000


def test_get_order_paid_is_false_initially(client):
    oid = _create_order(client)
    order = client.get(f"/order/{oid}").get_json()["order"]
    assert order["paid"] is False


def test_get_order_credit_card_empty_when_unpaid(client):
    oid = _create_order(client)
    order = client.get(f"/order/{oid}").get_json()["order"]
    assert order["credit_card"] == {}
    assert order["transaction"] == {}


# ── PUT /order/<id> – shipping ─────────────────────────────────────────────────

SHIPPING = {
    "country": "Canada",
    "address": "201, rue Président-Kennedy",
    "postal_code": "G7X 3Y7",
    "city": "Chicoutimi",
    "province": "QC",
}


def test_put_order_shipping_returns_200(client):
    oid = _create_order(client)
    resp = client.put(
        f"/order/{oid}",
        json={"order": {"email": "test@test.com", "shipping_information": SHIPPING}},
    )
    assert resp.status_code == 200


def test_put_order_shipping_updates_email(client):
    oid = _create_order(client)
    client.put(
        f"/order/{oid}",
        json={"order": {"email": "hello@test.com", "shipping_information": SHIPPING}},
    )
    order = client.get(f"/order/{oid}").get_json()["order"]
    assert order["email"] == "hello@test.com"


def test_put_order_shipping_calculates_total_price_tax_qc(client):
    oid = _create_order(client)
    client.put(
        f"/order/{oid}",
        json={"order": {"email": "t@t.com", "shipping_information": SHIPPING}},
    )
    order = client.get(f"/order/{oid}").get_json()["order"]
    expected = round(2810 * 2 * 1.15, 2)
    assert order["total_price_tax"] == expected


def test_put_order_shipping_missing_email_returns_422(client):
    oid = _create_order(client)
    resp = client.put(
        f"/order/{oid}",
        json={"order": {"shipping_information": SHIPPING}},
    )
    assert resp.status_code == 422


def test_put_order_shipping_missing_field_returns_422(client):
    oid = _create_order(client)
    incomplete = {k: v for k, v in SHIPPING.items() if k != "postal_code"}
    resp = client.put(
        f"/order/{oid}",
        json={"order": {"email": "t@t.com", "shipping_information": incomplete}},
    )
    assert resp.status_code == 422


def test_put_order_not_found_returns_404(client):
    resp = client.put(
        "/order/99999",
        json={"order": {"email": "t@t.com", "shipping_information": SHIPPING}},
    )
    assert resp.status_code == 404


# ── PUT /order/<id> – credit_card (missing client info) ───────────────────────

def test_put_order_credit_card_without_shipping_returns_422(client):
    oid = _create_order(client)
    resp = client.put(
        f"/order/{oid}",
        json={
            "credit_card": {
                "name": "John Doe",
                "number": "4242 4242 4242 4242",
                "expiration_year": 2030,
                "cvv": "123",
                "expiration_month": 9,
            }
        },
    )
    assert resp.status_code == 422
    code = resp.get_json()["errors"]["order"]["code"]
    assert code == "missing-fields"


def test_put_order_credit_and_order_together_returns_422(client):
    oid = _create_order(client)
    resp = client.put(
        f"/order/{oid}",
        json={
            "credit_card": {"name": "J", "number": "4242 4242 4242 4242",
                             "expiration_year": 2030, "cvv": "123",
                             "expiration_month": 9},
            "order": {"email": "t@t.com", "shipping_information": SHIPPING},
        },
    )
    assert resp.status_code == 422

from inf349.database import db
from inf349.models import Product, Order

def seed_product(in_stock=True, price=1000, weight=400):
    db.connect(reuse_if_open=True)
    Product.create(
        id=10,
        name="P",
        description="D",
        price=price,     # cents
        weight=weight,   # grams
        image="x.jpg",
        in_stock=in_stock,
    )
    db.close()

def test_post_order_success_returns_302_location(client):
    seed_product(in_stock=True)

    resp = client.post("/order", json={"product": {"id": 10, "quantity": 2}})
    assert resp.status_code == 302
    assert "Location" in resp.headers
    assert resp.headers["Location"].startswith("/order/")

def test_post_order_missing_fields(client):
    resp = client.post("/order", json={})
    assert resp.status_code == 422
    data = resp.get_json()
    assert data["errors"]["product"]["code"] == "missing-fields"

def test_post_order_out_of_inventory(client):
    seed_product(in_stock=False)

    resp = client.post("/order", json={"product": {"id": 10, "quantity": 1}})
    assert resp.status_code == 422
    data = resp.get_json()
    assert data["errors"]["product"]["code"] == "out-of-inventory"

def test_put_shipping_missing_fields(client):
    seed_product(in_stock=True)
    # créer commande
    resp = client.post("/order", json={"product": {"id": 10, "quantity": 1}})
    order_url = resp.headers["Location"]

    # manque shipping_information
    resp2 = client.put(order_url, json={"order": {"email": "a@b.com"}})
    assert resp2.status_code == 422
    data = resp2.get_json()
    assert data["errors"]["order"]["code"] == "missing-fields"

def test_put_shipping_then_get_order_contains_shipping(client):
    seed_product(in_stock=True)
    resp = client.post("/order", json={"product": {"id": 10, "quantity": 1}})
    order_url = resp.headers["Location"]

    payload = {
        "order": {
            "email": "test@test.com",
            "shipping_information": {
                "country": "Canada",
                "address": "1 rue test",
                "postal_code": "G7X 3Y7",
                "city": "Chicoutimi",
                "province": "QC",
            }
        }
    }
    resp2 = client.put(order_url, json=payload)
    assert resp2.status_code == 200

    resp3 = client.get(order_url)
    assert resp3.status_code == 200
    order = resp3.get_json()["order"]
    # Selon votre implémentation GET, ça doit être rempli après update
    assert "shipping_information" in order
"""Tests d'intégration – paiement avec le service distant (réseau requis)."""
import pytest

SHIPPING = {
    "country": "Canada",
    "address": "201, rue Président-Kennedy",
    "postal_code": "G7X 3Y7",
    "city": "Chicoutimi",
    "province": "QC",
}


def _create_and_fill_order(client):
    resp = client.post(
        "/order",
        json={"product": {"id": 1, "quantity": 1}},
        follow_redirects=False,
    )
    oid = int(resp.headers["Location"].split("/")[-1])
    client.put(
        f"/order/{oid}",
        json={"order": {"email": "test@test.com", "shipping_information": SHIPPING}},
    )
    return oid


@pytest.mark.integration
def test_payment_valid_card(client):
    oid = _create_and_fill_order(client)
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
    assert resp.status_code == 200
    order = resp.get_json()["order"]
    assert order["paid"] is True
    assert order["transaction"]["success"] is True
    assert str(order["credit_card"]["first_digits"]) == "4242"
    assert str(order["credit_card"]["last_digits"]) == "4242"


@pytest.mark.integration
def test_payment_declined_card(client):
    oid = _create_and_fill_order(client)
    resp = client.put(
        f"/order/{oid}",
        json={
            "credit_card": {
                "name": "John Doe",
                "number": "4000 0000 0000 0002",
                "expiration_year": 2030,
                "cvv": "123",
                "expiration_month": 9,
            }
        },
    )
    assert resp.status_code == 422
    assert resp.get_json()["errors"]["credit_card"]["code"] == "card-declined"


@pytest.mark.integration
def test_payment_already_paid_returns_422(client):
    oid = _create_and_fill_order(client)
    cc_payload = {
        "credit_card": {
            "name": "John Doe",
            "number": "4242 4242 4242 4242",
            "expiration_year": 2030,
            "cvv": "123",
            "expiration_month": 9,
        }
    }
    client.put(f"/order/{oid}", json=cc_payload)
    resp = client.put(f"/order/{oid}", json=cc_payload)
    assert resp.status_code == 422
    assert resp.get_json()["errors"]["order"]["code"] == "already-paid"


@pytest.mark.integration
def test_get_paid_order_contains_transaction(client):
    oid = _create_and_fill_order(client)
    client.put(
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
    order = client.get(f"/order/{oid}").get_json()["order"]
    assert order["paid"] is True
    assert "id" in order["transaction"]
    assert order["transaction"]["success"] is True

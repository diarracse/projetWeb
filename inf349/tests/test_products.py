from inf349.database import db
from inf349.models import Product

def test_get_products_returns_list(client):
    db.connect(reuse_if_open=True)
    Product.create(
        id=1,
        name="Test product",
        description="desc",
        price=1234,   # cents
        weight=400,
        image="0.jpg",
        in_stock=True,
    )
    db.close()

    resp = client.get("/")
    assert resp.status_code == 200

    data = resp.get_json()
    assert "products" in data
    assert isinstance(data["products"], list)
    assert len(data["products"]) == 1
    assert data["products"][0]["id"] == 1
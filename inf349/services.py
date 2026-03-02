import json
import urllib.request
from .database import db
from .models import Product

PRODUCTS_URL = "http://dimensweb.uqac.ca/~jgnault/shops/products/"

def _price_to_cents(value):
    # Si API renvoie float (28.1), convertit en cents (2810)
    if isinstance(value, float):
        return int(round(value * 100))
    if isinstance(value, str) and "." in value:
        return int(round(float(value) * 100))
    return int(value)

def fetch_products_once():
    with urllib.request.urlopen(PRODUCTS_URL) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    products = data.get("products", [])

    db.connect(reuse_if_open=True)
    for p in products:
        Product.insert(
            id=p["id"],
            name=p["name"],
            description=p.get("description"),
            price=_price_to_cents(p["price"]),
            weight=int(p["weight"]),
            image=p.get("image"),
            in_stock=bool(p.get("in_stock", True)),
        ).on_conflict(
            conflict_target=[Product.id],
            preserve=[
                Product.name, Product.description, Product.price,
                Product.weight, Product.image, Product.in_stock
            ]
        ).execute()
    db.close()
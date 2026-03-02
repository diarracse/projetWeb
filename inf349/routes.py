from flask import Blueprint, jsonify, request, make_response
from .models import Product, Order

api = Blueprint("api", __name__)

# --- GET / : liste produits ---
@api.get("/")
def get_products():
    products = []
    for p in Product.select():
        products.append({
            "id": p.id,
            "name": p.name,
            "in_stock": p.in_stock,
            "description": p.description,
            "price": p.price,      # cents
            "weight": p.weight,
            "image": p.image,
        })
    return jsonify({"products": products})


# --- helpers ---
def shipping_price_cents(weight_grams: int) -> int:
    # <= 500g : 5$ ; 500g à < 2kg : 10$ ; >= 2kg : 25$
    if weight_grams <= 500:
        return 500
    if weight_grams < 2000:
        return 1000
    return 2500


# --- POST /order : créer commande ---
@api.post("/order")
def create_order():
    # Force lecture JSON si Content-Type est application/json
    data = request.get_json(force=False, silent=True)

    # Debug utile si problème de requête (tu peux enlever après)
    # print("CONTENT-TYPE:", request.headers.get("Content-Type"))
    # print("RAW DATA:", request.get_data(as_text=True))
    # print("PARSED JSON:", data)

    if not isinstance(data, dict) or "product" not in data:
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "La création d'une commande nécessite un produit"
                }
            }
        }), 422

    product_data = data.get("product")
    if not isinstance(product_data, dict):
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires"
                }
            }
        }), 422

    if "id" not in product_data or "quantity" not in product_data:
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires"
                }
            }
        }), 422

    try:
        pid = int(product_data["id"])
        qty = int(product_data["quantity"])
    except Exception:
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires"
                }
            }
        }), 422

    if qty < 1:
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires"
                }
            }
        }), 422

    product = Product.get_or_none(Product.id == pid)
    if not product:
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "La création d'une commande nécessite un produit"
                }
            }
        }), 422

    if not product.in_stock:
        return jsonify({
            "errors": {
                "product": {
                    "code": "out-of-inventory",
                    "name": "Le produit demandé n'est pas en inventaire"
                }
            }
        }), 422

    total_price = product.price * qty
    shipping_price = shipping_price_cents(product.weight * qty)

    order = Order.create(
        product_id=pid,
        quantity=qty,
        total_price=total_price,
        shipping_price=shipping_price,
        paid=False
    )

    response = make_response("", 302)
    response.headers["Location"] = f"/order/{order.id}"
    return response

# --- GET /order ---

@api.get("/order/<int:order_id>")
def get_order(order_id):
    order = Order.get_or_none(Order.id == order_id)

    if not order:
        return jsonify({
            "errors": {
                "order": {
                    "code": "not-found",
                    "name": "La commande n'existe pas"
                }
            }
        }), 404

    return jsonify({
        "order": {
            "id": order.id,
            "product": {
                "id": order.product_id,
                "quantity": order.quantity
            },
            "total_price": order.total_price,
            "total_price_tax": order.total_price_tax,
            "email": order.email,
            "shipping_information": {},
            "credit_card": {},
            "paid": order.paid,
            "transaction": {},
            "shipping_price": order.shipping_price
        }
    })

# --- PUT / order ---

TAX_RATES = {
    "QC": 0.15,
    "ON": 0.13,
    "AB": 0.05,
    "BC": 0.12,
    "NS": 0.14,
}

@api.put("/order/<int:order_id>")
def update_order(order_id):
    order = Order.get_or_none(Order.id == order_id)
    if not order:
        return jsonify({
            "errors": {
                "order": {"code": "not-found", "name": "La commande n'existe pas"}
            }
        }), 404

    data = request.get_json(silent=True) or {}
    order_data = data.get("order")

    if not isinstance(order_data, dict):
        return jsonify({
            "errors": {
                "order": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires"
                }
            }
        }), 422

    # IMPORTANT: cet appel sert seulement à email + shipping (pas paiement)
    if "credit_card" in data or "credit_card" in order_data:
        return jsonify({
            "errors": {
                "order": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires"
                }
            }
        }), 422

    email = order_data.get("email")
    shipping = order_data.get("shipping_information")

    required_ship = ["country", "address", "postal_code", "city", "province"]
    if not email or not isinstance(shipping, dict) or any(not shipping.get(k) for k in required_ship):
        return jsonify({
            "errors": {
                "order": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires"
                }
            }
        }), 422

    province = shipping["province"]
    if province not in TAX_RATES:
        return jsonify({
            "errors": {
                "order": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires"
                }
            }
        }), 422

    # total_price_tax = total_price * (1 + taxe)
    rate = TAX_RATES[province]
    order.total_price_tax = float(order.total_price) * (1.0 + rate)

    order.email = email
    order.ship_country = shipping["country"]
    order.ship_address = shipping["address"]
    order.ship_postal_code = shipping["postal_code"]
    order.ship_city = shipping["city"]
    order.ship_province = province

    order.save()

    return jsonify({
        "order": {
            "id": order.id,
            "product": {"id": order.product_id, "quantity": order.quantity},
            "total_price": order.total_price,
            "total_price_tax": order.total_price_tax,
            "email": order.email,
            "shipping_information": {
                "country": order.ship_country,
                "address": order.ship_address,
                "postal_code": order.ship_postal_code,
                "city": order.ship_city,
                "province": order.ship_province,
            },
            "credit_card": {},
            "paid": order.paid,
            "transaction": {},
            "shipping_price": order.shipping_price
        }
    })
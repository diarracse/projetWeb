import json
import urllib.request
import urllib.error

from flask import Blueprint, jsonify, request, make_response
from .models import Product, Order

api = Blueprint("api", __name__)

# --- GET / : liste produits ---
#HTTPS car le serveur refuse les requêtes non sécurisées pour le paiement
PAY_URL = "https://dimensweb.uqac.ca/~jgnault/shops/pay/"

TAX_RATES = {
    "QC": 0.15,
    "ON": 0.13,
    "AB": 0.05,
    "BC": 0.12,
    "NS": 0.14,
}


def shipping_price_cents(weight_grams):
    if weight_grams <= 500:
        return 500
    if weight_grams < 2000:
        return 1000
    return 2500


def _order_dict(order):
    if order.paid:
        credit_card = {
            "name": order.cc_name,
            "first_digits": order.cc_first_digits,
            "last_digits": order.cc_last_digits,
            "expiration_year": order.cc_exp_year,
            "expiration_month": order.cc_exp_month,
        }
        transaction = {
            "id": order.tx_id,
            "success": order.tx_success,
            "amount_charged": order.tx_amount_charged,
        }
    else:
        credit_card = {}
        transaction = {}

    shipping = (
        {
            "country": order.ship_country,
            "address": order.ship_address,
            "postal_code": order.ship_postal_code,
            "city": order.ship_city,
            "province": order.ship_province,
        }
        if order.ship_country
        else {}
    )

    return {
        "id": order.id,
        "product": {"id": order.product_id, "quantity": order.quantity},
        "total_price": order.total_price,
        "total_price_tax": order.total_price_tax,
        "email": order.email,
        "shipping_information": shipping,
        "credit_card": credit_card,
        "paid": order.paid,
        "transaction": transaction,
        "shipping_price": order.shipping_price,
    }


# GET /
@api.get("/")
def get_products():
    products = []
    for p in Product.select():
        products.append({
            "id": p.id,
            "name": p.name,
            "in_stock": p.in_stock,
            "description": p.description,
            "price": p.price,
            "weight": p.weight,
            "image": p.image,
        })
    return jsonify({"products": products})


# POST /order
@api.post("/order")
def create_order():
    data = request.get_json(force=False, silent=True)

    if not isinstance(data, dict) or "product" not in data:
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "La création d'une commande nécessite un produit",
                }
            }
        }), 422

    product_data = data.get("product")
    if not isinstance(product_data, dict):
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "La création d'une commande nécessite un produit",
                }
            }
        }), 422

    if "id" not in product_data or "quantity" not in product_data:
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "La création d'une commande nécessite un produit",
                }
            }
        }), 422

    try:
        pid = int(product_data["id"])
        qty = int(product_data["quantity"])
    except (ValueError, TypeError):
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "La création d'une commande nécessite un produit",
                }
            }
        }), 422

    if qty < 1:
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "La création d'une commande nécessite un produit",
                }
            }
        }), 422

    product = Product.get_or_none(Product.id == pid)
    if not product:
        return jsonify({
            "errors": {
                "product": {
                    "code": "missing-fields",
                    "name": "La création d'une commande nécessite un produit",
                }
            }
        }), 422

    if not product.in_stock:
        return jsonify({
            "errors": {
                "product": {
                    "code": "out-of-inventory",
                    "name": "Le produit demandé n'est pas en inventaire",
                }
            }
        }), 422

    total_price = product.price * qty
    s_price = shipping_price_cents(product.weight * qty)

    order = Order.create(
        product_id=pid,
        quantity=qty,
        total_price=total_price,
        shipping_price=s_price,
        paid=False,
    )

    response = make_response("", 302)
    response.headers["Location"] = f"/order/{order.id}"
    return response


# GET /order/<id>
@api.get("/order/<int:order_id>")
def get_order(order_id):
    order = Order.get_or_none(Order.id == order_id)
    if not order:
        return jsonify({
            "errors": {
                "order": {"code": "not-found", "name": "La commande n'existe pas"}
            }
        }), 404

    return jsonify({"order": _order_dict(order)})


# PUT /order/<id>
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

    # --- Cas 1 : paiement par carte de crédit ---
    if "credit_card" in data:
        if "order" in data:
            return jsonify({
                "errors": {
                    "order": {
                        "code": "missing-fields",
                        "name": "Il manque un ou plusieurs champs qui sont obligatoires",
                    }
                }
            }), 422

        if order.paid:
            return jsonify({
                "errors": {
                    "order": {
                        "code": "already-paid",
                        "name": "La commande a déjà été payée.",
                    }
                }
            }), 422

        required_shipping = [
            order.ship_country,
            order.ship_address,
            order.ship_postal_code,
            order.ship_city,
            order.ship_province,
        ]
        if (not order.email) or any(v is None or v == "" for v in required_shipping):
            return jsonify({
                "errors": {
                    "order": {
                        "code": "missing-fields",
                        "name": "Les informations du client sont nécessaire avant d'appliquer une carte de crédit",
                    }
                }
            }), 422

        cc = data["credit_card"]

        amount = order.total_price + order.shipping_price

        payload = json.dumps({
            "credit_card": cc,
            "amount_charged": amount,
        }).encode("utf-8")

        req = urllib.request.Request(
            PAY_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                pay_data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {}
            errors = body.get("errors", body)
            return jsonify({"errors": errors}), 422
        except urllib.error.URLError:
            return jsonify({"errors": {"order": {"code": "network-error", "name": "Impossible de contacter le service de paiement"}}}), 422

        cc_info = pay_data["credit_card"]
        tx_info = pay_data["transaction"]

        order.paid = True
        order.cc_name = cc_info.get("name")
        order.cc_first_digits = cc_info.get("first_digits")
        order.cc_last_digits = cc_info.get("last_digits")
        order.cc_exp_year = cc_info.get("expiration_year")
        order.cc_exp_month = cc_info.get("expiration_month")
        order.tx_id = tx_info.get("id")
        success_val = tx_info.get("success")
        order.tx_success = success_val is True or success_val == "true"
        order.tx_amount_charged = tx_info.get("amount_charged")
        order.save()

        return jsonify({"order": _order_dict(order)})

    # --- Cas 2 : mise à jour email + shipping ---
    order_data = data.get("order")
    if not isinstance(order_data, dict):
        return jsonify({
            "errors": {
                "order": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires",
                }
            }
        }), 422

    email = order_data.get("email")
    shipping = order_data.get("shipping_information")
    required_ship = ["country", "address", "postal_code", "city", "province"]

    if (
        not email
        or not isinstance(shipping, dict)
        or any(not shipping.get(k) for k in required_ship)
    ):
        return jsonify({
            "errors": {
                "order": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires",
                }
            }
        }), 422

    province = shipping["province"]
    if province not in TAX_RATES:
        return jsonify({
            "errors": {
                "order": {
                    "code": "missing-fields",
                    "name": "Il manque un ou plusieurs champs qui sont obligatoires",
                }
            }
        }), 422

    rate = TAX_RATES[province]

    order.total_price_tax = int(round(order.total_price * (1 + rate)))

    order.email = email
    order.ship_country = shipping["country"]
    order.ship_address = shipping["address"]
    order.ship_postal_code = shipping["postal_code"]
    order.ship_city = shipping["city"]
    order.ship_province = province
    order.save()

    return jsonify({"order": _order_dict(order)})
from peewee import (
    Model, IntegerField, CharField, BooleanField, TextField, FloatField
)
from .database import db

class BaseModel(Model):
    class Meta:
        database = db

class Product(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    description = TextField(null=True)
    price = IntegerField()          # en cents (int)
    weight = IntegerField()         # grammes
    image = CharField(null=True)
    in_stock = BooleanField(default=True)

class Order(BaseModel):
    # Remise 1: une commande = un seul produit
    product_id = IntegerField()
    quantity = IntegerField()

    # Client
    email = CharField(null=True)
    ship_country = CharField(null=True)
    ship_address = CharField(null=True)
    ship_postal_code = CharField(null=True)
    ship_city = CharField(null=True)
    ship_province = CharField(null=True)

    # Prix
    total_price = IntegerField()       # cents, sans shipping
    shipping_price = IntegerField()    # cents
    total_price_tax = FloatField(null=True)

    # Paiement
    paid = BooleanField(default=False)

    cc_name = CharField(null=True)
    cc_first_digits = CharField(null=True)
    cc_last_digits = CharField(null=True)
    cc_exp_year = IntegerField(null=True)
    cc_exp_month = IntegerField(null=True)

    tx_id = CharField(null=True)
    tx_success = BooleanField(null=True)
    tx_amount_charged = IntegerField(null=True)
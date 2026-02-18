from peewee import SqliteDatabase

db = SqliteDatabase("instance/database.db")

def init_db():
    from .models import Product, Order
    db.connect()
    db.create_tables([Product, Order])
    db.close()

import os
from peewee import SqliteDatabase

db = SqliteDatabase(None)

def init_db(app):
    # DB dans instance/app.db
    os.makedirs(app.instance_path, exist_ok=True)
    db_path = os.path.join(app.instance_path, "app.db")
    db.init(db_path)
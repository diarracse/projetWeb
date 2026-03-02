import click
from flask import Flask

from .database import init_db, db
from .models import Product, Order
from .routes import api
from .services import fetch_products_once


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Initialiser DB (chemin sqlite)
    init_db(app)

    # Enregistrer le blueprint
    app.register_blueprint(api)

    # Connexion DB auto par requête
    @app.before_request
    def _db_connect():
        if db.is_closed():
            db.connect(reuse_if_open=True)

    @app.teardown_request
    def _db_close(exc):
        if not db.is_closed():
            db.close()

    # Commande obligatoire
    @app.cli.command("init-db")
    def init_db_command():
        # Créer tables
        db.connect(reuse_if_open=True)
        db.create_tables([Product, Order])
        db.close()

        # Charger les produits (une fois) juste après init
        fetch_products_once()

        click.echo("Database initialized and products loaded.")

    return app
from flask import Flask
from .database import init_db
from .routes import api

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("inf349.config")

    app.register_blueprint(api)

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database initialized")

    return app

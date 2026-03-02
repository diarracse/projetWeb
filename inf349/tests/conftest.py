import os
import pytest

from inf349 import create_app
from inf349.database import db
from inf349.models import Product, Order

@pytest.fixture
def app(tmp_path):
    """
    Crée une app Flask de test + DB SQLite temporaire.
    On évite d'utiliser init-db (qui fetch les produits sur internet).
    """
    app = create_app()
    app.config.update(TESTING=True)

    # DB temporaire
    test_db_path = tmp_path / "test.db"
    db.init(str(test_db_path))

    # Créer tables vides
    db.connect(reuse_if_open=True)
    db.drop_tables([Order, Product], safe=True)
    db.create_tables([Product, Order])
    db.close()

    return app

@pytest.fixture
def client(app):
    return app.test_client()
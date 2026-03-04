import pytest
from peewee import SqliteDatabase
from inf349 import create_app
from inf349.database import db
from inf349.models import Product, Order

TEST_DB = SqliteDatabase(":memory:")


@pytest.fixture
def app():
    application = create_app()
    application.config["TESTING"] = True

    TEST_DB.bind([Product, Order], bind_refs=False, bind_backrefs=False)
    TEST_DB.connect()
    TEST_DB.create_tables([Product, Order])

    Product.create(
        id=1,
        name="Brown eggs",
        description="Raw organic brown eggs in a basket",
        price=2810,
        weight=400,
        image="0.jpg",
        in_stock=True,
    )
    Product.create(
        id=4,
        name="Green smoothie",
        description="A green smoothie",
        price=1768,
        weight=399,
        image="3.jpg",
        in_stock=False,
    )

    yield application

    TEST_DB.drop_tables([Product, Order])
    TEST_DB.close()
    TEST_DB.bind([Product, Order], bind_refs=False, bind_backrefs=False)
    db.bind([Product, Order], bind_refs=False, bind_backrefs=False)


@pytest.fixture
def client(app):
    return app.test_client()

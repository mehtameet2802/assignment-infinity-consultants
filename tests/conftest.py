import os

# Must be set before app modules create the engine.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session, sessionmaker

from app import create_app
from app.database import Base, engine


@pytest.fixture
def db_session() -> Session:
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def app(db_session: Session) -> Flask:
    application = create_app()
    application.config["DB_SESSION"] = db_session
    return application


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()

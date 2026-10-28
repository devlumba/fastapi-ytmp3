import pytest
from fastapi.testclient import TestClient
from ytmp3 import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def celery_eager():
    from ytmp3 import celery_app
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False



import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy_utils import create_database, drop_database
from yarl import URL

from analyzer.db.core import SYNCHRONOUS_DATABASE_URL
from analyzer.utils.database import make_alembic_config


@pytest.fixture()
def sqlite():
    """
    Создает временную БД для запуска теста
    """

    tmp_name = ".".join([uuid.uuid4().hex, "pytest"])
    tmp_url = str(URL(SYNCHRONOUS_DATABASE_URL).with_path(tmp_name)).replace("/", "///")
    create_database(tmp_url)

    try:
        yield tmp_url
    finally:
        drop_database(tmp_url)


@pytest.fixture()
def alembic_config(sqlite):
    """
    Создает объект с конфигурацией для alembic, настроенный на временную БД.
    """

    cmd_options = SimpleNamespace(config="alembic.ini", name="alembic", sqlite_url=sqlite, raiseerr=False, x=None)
    return make_alembic_config(cmd_options)

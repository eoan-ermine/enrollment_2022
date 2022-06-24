import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy_utils import create_database, drop_database
from yarl import URL

from analyzer.db.core import SYNC_DATABASE_URL
from analyzer.utils.database import make_alembic_config


@pytest.fixture()
def postgres():
    """
    Создает временную БД для запуска теста
    """

    tmp_name = uuid.uuid4().hex
    print("postgres():", SYNC_DATABASE_URL)
    tmp_url = str(URL(SYNC_DATABASE_URL).with_path(tmp_name))
    create_database(tmp_url)

    try:
        yield tmp_url
    finally:
        drop_database(tmp_url)


@pytest.fixture()
def alembic_config(postgres):
    """
    Создает объект с конфигурацией для alembic, настроенный на временную БД.
    """

    cmd_options = SimpleNamespace(config="alembic.ini", name="alembic", pg_url=postgres, raiseerr=False, x=None)
    return make_alembic_config(cmd_options)

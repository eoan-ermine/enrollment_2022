from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Union

from alembic.config import Config
from sqlalchemy import insert
from sqlalchemy.orm import Session

from analyzer.db.core import SessionLocal

PROJECT_PATH = Path(__file__).parent.parent.resolve()


def make_alembic_config(cmd_opts: Union[SimpleNamespace], base_path: str = PROJECT_PATH) -> Config:

    """
    Создает объект конфигурации alembic на основе аргументов командной строки,
    подменяет относительные пути на абсолютные.
    """
    # Подменяем путь до файла alembic.ini на абсолютный
    if not os.path.isabs(cmd_opts.config):
        cmd_opts.config = os.path.join(base_path, cmd_opts.config)

    config = Config(file_=cmd_opts.config, ini_section=cmd_opts.name, cmd_opts=cmd_opts)

    # Подменяем путь до папки с alembic на абсолютный
    alembic_location = config.get_main_option("script_location")
    if not os.path.isabs(alembic_location):
        config.set_main_option("script_location", os.path.join(base_path, alembic_location))
    if cmd_opts.pg_url:
        config.set_main_option("sqlalchemy.url", cmd_opts.pg_url)

    return config


async def get_session() -> Session:
    async with SessionLocal() as session:
        yield session


class BatchInserter:
    def __init__(self):
        self.values = dict()

    def add(self, model, values):
        if model not in self.values:
            self.values[model] = []
        self.values[model].append(values)

    async def execute(self, session: Session):
        for model, values in self.values.items():
            await session.execute(insert(model).values(values))

"""
Alembic environment script.
Reads DATABASE_URL from environment / .env file.
Supports both sync (for migrations) and async engines.
"""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Load .env so DATABASE_URL is available when running `alembic upgrade head`
load_dotenv(Path(__file__).parent.parent / ".env")

# Alembic Config object
config = context.config

# Inject DATABASE_URL from environment into alembic.ini's sqlalchemy.url
database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/db/ai_signals.db")
# Alembic needs a sync driver for --autogenerate; swap async driver prefix
sync_url = (
    database_url
    .replace("sqlite+aiosqlite", "sqlite")
    .replace("postgresql+asyncpg", "postgresql+psycopg2")
)
config.set_main_option("sqlalchemy.url", sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so autogenerate sees them
from app.core.database import Base  # noqa: E402
import app.models  # noqa: E402, F401  — side-effect import registers all models

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

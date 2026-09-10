from sqlalchemy import Connection, create_engine, pool

from alembic import context
from app import models  # noqa: F401 - registers models in Base.metadata
from app.core.config import get_settings
from app.db.base import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(get_settings().database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def migrate_connection(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Tests can supply an isolated PostgreSQL schema through this connection.
    connection = context.config.attributes.get("connection")
    if isinstance(connection, Connection):
        migrate_connection(connection)
        return
    engine = create_engine(str(get_settings().database_url), poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            migrate_connection(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

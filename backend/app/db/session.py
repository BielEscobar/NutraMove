from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        str(get_settings().database_url),
        hide_parameters=True,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


def get_db() -> Iterator[Session]:
    # Closing the session also rolls back any uncommitted transaction.
    with Session(get_engine()) as session:
        yield session

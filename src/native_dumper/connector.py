from typing import NamedTuple

from .defines import (
    DEFAULT_DATABASE,
    DEFAULT_USER,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
)


class CHConnector(NamedTuple):
    """Connector for Clickhouse."""

    host: str
    dbname: str = DEFAULT_DATABASE
    user: str = DEFAULT_USER
    password: str = DEFAULT_PASSWORD
    port: int = DEFAULT_PORT

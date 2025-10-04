from typing import Iterable
from uuid import uuid4

from light_compressor import (
    CompressionMethod,
    define_reader,
)
from nativelib import (
    Column,
    NativeReader,
)

from .connector import CHConnector
from .errors import ClickhouseServerError
from .logger import Logger
from .pyo3http import (
    HttpResponse,
    HttpSession,
)
from ..version import __version__


class HTTPCursor:
    """Class for send queryes to Clickhouse server
    and read/write Native format."""

    def __init__(
        self,
        connector: CHConnector,
        compression_method: CompressionMethod,
        logger: Logger,
        timeout: int,
    ) -> None:
        """Class initialization."""

        self.connector = connector
        self.compression_method = compression_method
        self.logger = logger
        self.timeout = timeout
        self.mode = {
            443: "https",
        }.get(int(self.connector.port), "http")
        self.session = HttpSession()
        self.headers = {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "User-Agent": f"{self.__class__.__name__}/{__version__}",
            "Accept-Encoding": self.compression_method.method,
            "Content-Encoding": self.compression_method.method,
            "X-ClickHouse-User": self.connector.user,
            "X-ClickHouse-Key": self.connector.password,
            "X-ClickHouse-Compression": self.compression_method.method,
            "X-ClickHouse-Format": "Native",
            "X-Content-Type-Options": "nosniff",
        }
        self.url = (
            f"{self.mode}://{self.connector.host}:{self.connector.port}/"
            "?enable_http_compression=1"
        )
        self.params = {
            "database": connector.dbname,
            "query": "",
            "session_id": str(uuid4()),
        }
        self.check_length = {
            CompressionMethod.NONE: 1024,
        }

    def send_hello(self) -> str:
        """Get server version."""

        reader = self.get_stream("SELECT version()")
        return tuple(reader.to_rows())[0][0]

    def get_response(
        self,
        query: str,
        data: Iterable[bytes] | None = None,
    ) -> HttpResponse:
        """Get response from clickhouse server."""

        self.params["query"] = query

        return self.session.post(
            url=self.url,
            data=data,
            params=self.params,
            headers=self.headers,
            timeout=self.timeout,
        )

    def get_stream(
        self,
        query: str,
    ) -> NativeReader:
        """Get answer from server as unpacked stream file."""

        stream = self.get_response(query)
        status = stream.get_status()
        bufferobj = define_reader(stream, self.compression_method)

        try:
            check_error = bufferobj.read(
                self.check_length.get(self.compression_method, 4)
            )[:4]
        except EOFError:
            error = "Server sent empty data."
            self.logger.error(f"ClickhouseServerError: {error}")
            raise ClickhouseServerError(error)

        bufferobj.seek(0)

        if check_error == b"Code" or status != 200:
            error = bufferobj.read().decode("utf-8", errors="replace")
            self.logger.error(f"ClickhouseServerError: {error}")
            raise ClickhouseServerError(error)

        return NativeReader(bufferobj)

    def upload_data(
        self,
        table: str,
        data: Iterable[bytes],
    ) -> None:
        """Download data into table."""

        response = self.get_response(
            query=f"INSERT INTO {table} FORMAT Native",
            data=data,
        )
        status = response.get_status()

        if status != 200:
            bufferobj = define_reader(response, self.compression_method)
            error = bufferobj.read().decode("utf-8", errors="replace")
            self.logger.error(f"ClickhouseServerError: {error}")
            raise ClickhouseServerError(error)

    def metadata(
        self,
        table: str,
    ) -> list[Column]:
        """Get table metadata."""

        reader = self.get_stream(f"DESCRIBE TABLE {table}")
        return [
            Column(*describe[:2])
            for describe in reader.to_rows()
        ]

    def execute(
        self,
        query: str,
    ) -> None:
        """Simple exetute method without return."""

        response = self.get_response(query)
        status = response.get_status()

        if status != 200:
            bufferobj = define_reader(response, self.compression_method)
            error = bufferobj.read().decode("utf-8", errors="replace")
            self.logger.error(f"ClickhouseServerError: {error}")
            raise ClickhouseServerError(error)

    def last_query(self) -> str:
        """Show last query."""

        return self.params["query"]

    def refresh(self) -> None:
        """Refresh Session ID."""

        self.params["session_id"] = str(uuid4())

    def close(self) -> None:
        """Close HTTPCursor session."""

        self.session.close()

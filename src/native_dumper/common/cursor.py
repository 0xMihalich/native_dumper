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

from ..version import __version__
from .connector import CHConnector
from .defines import CHUNK_SIZE
from .errors import ClickhouseServerError
from .logger import Logger
from .pyo3http import (
    HttpResponse,
    HttpSession,
)


def string_error(data: bytes) -> str:
    """Bytes to string decoder."""

    return data.decode("utf-8", errors="replace").strip()


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
        self.session = HttpSession(timeout=self.timeout)
        self.is_connected = False
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
        self.mode = {
            443: "https",
        }.get(int(self.connector.port), "http")
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
        self.server_version = None

    def send_hello(self) -> str:
        """Get server version."""

        reader = self.get_stream("SELECT version()")
        server_version = tuple(reader.to_rows())[0][0]
        self.is_connected = True
        self.server_version = server_version
        return self.server_version

    def get_response(
        self,
        query: str,
        data: Iterable[bytes] | None = None,
    ) -> HttpResponse:
        """Get response from clickhouse server."""

        self.params["query"] = query

        response = self.session.post(
            url=self.url,
            params=self.params,
            headers=self.headers,
            timeout=self.timeout,
            data=data,
        )
        status = response.get_status()

        if status != 200:

            if not self.is_connected:
                error = string_error(response.read())
                response.close()
            else:
                bufferobj = define_reader(response, self.compression_method)
                error = string_error(bufferobj.read(CHUNK_SIZE))
                bufferobj.close()

            self.logger.error(f"ClickhouseServerError: {error}")
            raise ClickhouseServerError(error)

        return response

    def get_stream(
        self,
        query: str,
    ) -> NativeReader:
        """Get answer from server as unpacked stream file."""

        stream = self.get_response(query)

        try:
            bufferobj = define_reader(stream, self.compression_method)
            check_error = bufferobj.read(
                self.check_length.get(self.compression_method, 4)
            )[:4]
            bufferobj.seek(0)
        except EOFError:
            error = (
                "Code: 92. DB::Exception: (EMPTY_DATA_PASSED) "
                f"(version {self.server_version} (official build))"
            )
            self.logger.error(f"ClickhouseServerError: {error}")
            raise ClickhouseServerError(error)

        if check_error == b"Code":
            error = string_error(bufferobj.read(CHUNK_SIZE))
            bufferobj.close()
            self.logger.error(f"ClickhouseServerError: {error}")
            raise ClickhouseServerError(error)

        return NativeReader(bufferobj)

    def upload_data(
        self,
        table: str,
        data: Iterable[bytes],
    ) -> None:
        """Download data into table."""

        self.get_response(
            query=f"INSERT INTO {table} FORMAT Native",
            data=data,
        )

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

        self.get_response(query)

    def last_query(self) -> str:
        """Show last query."""

        return self.params["query"]

    def refresh(self) -> None:
        """Refresh Session ID."""

        self.params["session_id"] = str(uuid4())

    def close(self) -> None:
        """Close HTTPCursor session."""

        self.session.close()
        self.is_connected = False

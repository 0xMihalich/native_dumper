from typing import BinaryIO
from uuid import uuid4

from lz4.frame import LZ4FrameFile
from requests import (
    Session,
    Response,
)

from .connector import CHConnector
from .enums import CompressionMethod
from .logger import Logger
from .stream import StreamReader
from .version import __version__


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
        self.timeout = timeout
        self.logger = logger
        self.session = Session()
        self.session.headers = {
            "User-Agent": f"{self.__class__.__name__}/{__version__}",
            "Accept-Encoding": self.compression_method.method,
            "Content-Encoding": self.compression_method.method,
            "Accept": "*/*",
            "Connection": "keep-alive",
            "X-ClickHouse-User": self.connector.user,
            "X-ClickHouse-Key": self.connector.password,
            "X-ClickHouse-Compression": self.compression_method.method,
            "X-Content-Type-Options": "nosniff",
        }
        self.url = f"http://{self.connector.host}:{self.connector.port}/"
        self.params = {
            "database": connector.dbname,
            "query": "",
            "session_id": str(uuid4()),
        }
        self.native_header = {
            "X-ClickHouse-Format": "Native",
        }

    def send_hello(self) -> str:
        """Get server version."""

        return self.get_string("select version()")

    def get_response(
        self,
        query: str,
        is_native: bool = False,
        data: BinaryIO | None = None,
    ) -> Response:
        """Get response from clickhouse server."""

        if is_native:
            headers = self.native_header
            url = (
                f"{self.url}?enable_http_compression=1"
            )
            query = f"{query} FORMAT Native"
        else:
            headers = None
            url = self.url

        self.params["query"] = query

        resp: Response = self.session.post(
            url=url,
            data=data,
            params=self.params,
            headers=headers,
            timeout=self.timeout,
            stream=True,
        )
        resp.raise_for_status()
        return resp

    def get_string(
        self,
        query: str,
    ) -> str:
        """Get answer from server as string."""

        return self.get_response(query).text.strip()

    def get_stream(
        self,
        query: str,
    ) -> StreamReader:
        """Get answer from server as unpacked stream file."""

        stream = StreamReader(self.get_response(query, True).raw)

        if self.compression_method == CompressionMethod.LZ4:
            return LZ4FrameFile(stream)

        return stream

    def upload_data(
        self,
        table: str,
        data: BinaryIO,
    ) -> None:
        """Download data into table."""

        self.get_response(
            query=f"INSERT INTO {table}",
            is_native=True,
            data=data,
        )

    def execute(
        self,
        query: str,
    ) -> None:
        """Simple exetute method without return."""

        self.get_response(query)

    def last_query(self) -> str:
        """Show last query."""

        return self.params["query"]

    def close(self) -> None:
        """Close HTTPCursor session."""

        self.session.close()

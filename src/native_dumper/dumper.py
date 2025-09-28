from io import (
    BufferedReader,
    BufferedWriter,
)
from types import MethodType
from typing import (
    Any,
    BinaryIO,
    Iterable,
)

from nativelib import (
    Column,
    NativeReader,
    NativeWriter,
)
from pandas import DataFrame as PdFrame
from polars import DataFrame as PlFrame
from sqlparse import format as sql_format

from .connector import CHConnector
from .cursor import HTTPCursor
from .defines import DBMS_DEFAULT_TIMEOUT_SEC
from .enums import CompressionMethod
from .errors import (
    NativeDumperError,
    NativeDumperReadError,
    NativeDumperValueError,
    NativeDumperWriteError,
)
from .logger import (
    DumperLogger,
    Logger,
)
from .multiquery import chunk_query


class NativeDumper:
    """Class for read and write Native format."""

    def __init__(
        self,
        connector: CHConnector,
        compression_method: CompressionMethod = CompressionMethod.ZSTD,
        logger: Logger = DumperLogger(),
        timeout: int = DBMS_DEFAULT_TIMEOUT_SEC,
    ) -> None:
        """Class initialization."""

        try:
            self.connector = connector
            self.compression_method = compression_method
            self.logger = logger
            self.cursor = HTTPCursor(
                connector=self.connector,
                compression_method=self.compression_method,
                logger=self.logger,
                timeout=timeout,
            )
            self.version = self.cursor.send_hello()
        except Exception as error:
            logger.error(error)
            raise NativeDumperError(error)

        self.logger.info(
            f"NativeDumper initialized for host {self.connector.host}"
            f"[version {self.version}]"
        )

    @staticmethod
    def multiquery(dump_method: MethodType):
        """Multiquery decorator."""

        def wrapper(*args, **kwargs):

            first_part: list[str]
            second_part: list[str]

            self: NativeDumper = args[0]
            cursor: HTTPCursor = kwargs.get("cursor_src") or self.cursor
            query: str = kwargs.get("query_src") or kwargs.get("query")
            part: int = 0
            first_part, second_part = chunk_query(self.query_formatter(query))
            total_prts = len(sum((first_part, second_part), [])) or 1

            if first_part:
                self.logger.info("Multiquery detected.")

                for query in first_part:
                    self.logger.info(f"Execute query {part}/{total_prts}")
                    cursor.execute(query)
                    part += 1

            if second_part:
                for key in ("query", "query_src"):
                    if key in kwargs:
                        kwargs[key] = second_part.pop(0)
                        break

            self.logger.info(
                f"Execute query {part or 1}/{total_prts}[copy method]"
            )
            output = dump_method(*args, **kwargs)

            if second_part:
                for query in second_part:
                    part += 1
                    self.logger.info(f"Execute query {part}/{total_prts}")
                    cursor.execute(query)

            return output

        return wrapper

    def query_formatter(self, query: str) -> str | None:
        """Reformat query."""

        if not query:
            return
        return sql_format(sql=query, strip_comments=True).strip().strip(";")

    @multiquery
    def to_reader(
        self,
        query: str | None = None,
        table_name: str | None = None,
    ) -> NativeReader:
        """Get stream from Clickhouse as NativeReader object."""

        if not query and not table_name:
            error_message = "Query or table name not defined."
            self.logger.error(error_message)
            raise NativeDumperValueError(error_message)

        if not query:
            query = f"SELECT * FROM {table_name}"

        self.logger.info(
            f"Get NativeReader object from {self.connector.host}."
        )
        stream = self.cursor.get_stream(query)
        return NativeReader(stream)

    @multiquery
    def read_dump(
        self,
        fileobj: BufferedWriter,
        query: str | None = None,
        table_name: str | None = None,
    ) -> None:
        """Read Native dump from Clickhouse."""

        if not query and not table_name:
            error_message = "Query or table name not defined."
            self.logger.error(error_message)
            raise NativeDumperValueError(error_message)

        if not query:
            query = f"SELECT * FROM {table_name}"

        self.logger.info(f"Start read from {self.connector.host}.")

        try:
            self.logger.info(
                "Reading native dump with compression "
                f"{self.compression_method.name}."
            )
            stream = self.cursor.get_response(query, True).raw
            fileobj.write(stream.read())
        except Exception as error:
            self.logger.error(error)
            raise NativeDumperReadError(error)

        self.logger.info(f"Read from {self.connector.host} done.")

    def write_dump(
        self,
        fileobj: BufferedReader | BinaryIO,
        table_name: str,
    ) -> None:
        """Write Native dump into Clickhouse."""

        if not table_name:
            error_message = "Table name not defined."
            self.logger.error(error_message)
            raise NativeDumperValueError(error_message)

        self.logger.info(
            f"Start write into {self.connector.host}.{table_name}."
        )

        try:
            self.cursor.upload_data(
                table=table_name,
                data=fileobj.read(),
            )
        except Exception as error:
            self.logger.error(error)
            raise NativeDumperWriteError(error)

        self.logger.info(
            f"Write into {self.connector.host}.{table_name} done."
        )

    @multiquery
    def write_between(
        self,
        table_dest: str,
        table_src: str | None = None,
        query_src: str | None = None,
        cursor_src: HTTPCursor | None = None,
    ) -> None:
        """Write between Clickhouse servers."""

        if not query_src and not table_src:
            error_message = "Source query or table name not defined."
            self.logger.error(error_message)
            raise NativeDumperValueError(error_message)

        if not table_dest:
            error_message = "Destination table name not defined."
            self.logger.error(error_message)
            raise NativeDumperValueError(error_message)

        if not query_src:
            query_src = f"SELECT * FROM {table_src}"

        cursor = cursor_src or HTTPCursor(
            connector=self.connector,
            compression_method=self.compression_method,
            logger=self.logger,
            timeout=self.cursor.timeout,
        )

        if cursor.compression_method != self.compression_method:
            error_message = "Compression method must be same."
            self.logger.error(error_message)
            raise NativeDumperValueError(error_message)

        try:
            self.logger.info(
                f"Copy from {cursor.connector.host} into "
                f"{self.connector.host}.{table_dest} started."
            )
            with self.cursor.get_response(query_src, True).raw as stream:
                cursor.upload_data(table_dest, stream.read())
            self.logger.info(
                f"Copy from {cursor.connector.host} into "
                f"{self.connector.host}.{table_dest} done."
            )
        except Exception as error:
            self.logger.error(error)
            raise NativeDumperWriteError(error)

    def from_rows(
        self,
        dtype_data: Iterable[Any],
        table_name: str,
    ) -> None:
        """Write from python list into Clickhouse table."""

        if not table_name:
            error_message = "Table name not defined."
            self.logger.error(error_message)
            raise NativeDumperValueError(error_message)

        column_list = [
            Column(*column.split("\t")[:2]) for column in
            self.cursor.metadata(table_name).split("\n")
        ]
        writer = NativeWriter(column_list)

        self.logger.info(
            f"Start write into {self.connector.host}.{table_name}."
        )

        try:
            self.cursor.upload_data(
                table=table_name,
                data=writer.from_rows(dtype_data),
            )
        except Exception as error:
            self.logger.error(error)
            raise NativeDumperWriteError(error)

        self.logger.info(
            f"Write into {self.connector.host}.{table_name} done."
        )

    def from_pandas(
        self,
        data_frame: PdFrame,
        table_name: str,
    ) -> None:
        """Write from pandas.DataFrame into Clickhouse table."""

        self.from_rows(
            dtype_data=iter(data_frame.values),
            table_name=table_name,
        )

    def from_polars(
        self,
        data_frame: PlFrame,
        table_name: str,
    ) -> None:
        """Write from polars.DataFrame into Clickhouse table."""

        self.from_rows(
            dtype_data=data_frame.iter_rows(),
            table_name=table_name,
        )

    def close(self) -> None:
        """Close cursor session."""

        self.cursor.close()

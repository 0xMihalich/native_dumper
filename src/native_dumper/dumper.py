from collections import OrderedDict
from io import (
    BufferedReader,
    BufferedWriter,
)
from logging import Logger
from types import MethodType
from typing import (
    Any,
    BinaryIO,
    Iterable,
    Union,
)

from light_compressor import (
    CompressionMethod,
    auto_detector,
    define_reader,
    define_writer,
)
from nativelib import (
    NativeReader,
    NativeWriter,
)
from pandas import DataFrame as PdFrame
from polars import DataFrame as PlFrame
from sqlparse import format as sql_format

from .common import (
    CHUNK_SIZE,
    DBMS_DEFAULT_TIMEOUT_SEC,
    CHConnector,
    ClickhouseServerError,
    DBMetadata,
    DumperLogger,
    HTTPCursor,
    NativeDumperError,
    NativeDumperReadError,
    NativeDumperValueError,
    NativeDumperWriteError,
    chunk_query,
    file_writer,
    make_columns,
    transfer_diagram,
)


class NativeDumper:
    """Class for read and write Native format."""

    def __init__(
        self,
        connector: CHConnector,
        compression_method: CompressionMethod = CompressionMethod.ZSTD,
        logger: Logger | None = None,
        timeout: int = DBMS_DEFAULT_TIMEOUT_SEC,
    ) -> None:
        """Class initialization."""

        if not logger:
            logger = DumperLogger()

        try:
            self.connector = connector

            if int(self.connector.port) == 9000:
                raise ValueError(
                    "NativeDumper don't support port 9000, please, use 8123."
                )

            self.compression_method = compression_method
            self.logger = logger
            self.cursor = HTTPCursor(
                connector=self.connector,
                compression_method=self.compression_method,
                logger=self.logger,
                timeout=timeout,
            )
            self.version = self.cursor.send_hello()
            self._dbmeta: DBMetadata | None = None
        except ClickhouseServerError as error:
            raise error
        except Exception as error:
            logger.error(f"NativeDumperError: {error}")
            raise NativeDumperError(error)

        self.dbname = "clickhouse"
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
            cursor: HTTPCursor = (kwargs.get("dumper_src") or self).cursor
            query: str = kwargs.get("query_src") or kwargs.get("query")
            part: int = 1
            first_part, second_part = chunk_query(self.query_formatter(query))
            total_parts = len(sum((first_part, second_part), [])) + int(
                bool(kwargs.get("table_name") or kwargs.get("table_src"))
            )

            if len(first_part) > 1:
                for query in first_part:
                    self.logger.info(f"Execute query {part}/{total_parts}")
                    cursor.execute(query)
                    part += 1

            if second_part:
                for key in ("query", "query_src"):
                    if key in kwargs:
                        kwargs[key] = second_part.pop(0)
                        break

            self.logger.info(
                f"Execute stream {part}/{total_parts} [native mode]"
            )
            output = dump_method(*args, **kwargs)

            if second_part:
                for query in second_part:
                    part += 1
                    self.logger.info(f"Execute query {part}/{total_parts}")
                    cursor.execute(query)

            if output:
                self.refresh()

            return output

        return wrapper

    def query_formatter(self, query: str) -> str | None:
        """Reformat query."""

        if not query:
            return
        return sql_format(sql=query, strip_comments=True).strip().strip(";")

    @multiquery
    def __read_dump(
        self,
        fileobj: BufferedWriter,
        query: str | None,
        table_name: str | None,
    ) -> bool:
        """Internal method read_dump for generate kwargs to decorator."""

        if not query and not table_name:
            error_message = "Query or table name not defined."
            self.logger.error(f"NativeDumperValueError: {error_message}")
            raise NativeDumperValueError(error_message)

        if not query:
            query = f"SELECT * FROM {table_name}"

        self.logger.info(f"Start read from {self.connector.host}.")

        try:
            self.logger.info(
                "Reading native dump with compression "
                f"{self.compression_method.name}."
            )
            columns = make_columns(self.cursor.metadata(f"({query})"))
            source = DBMetadata(
                name=self.dbname,
                version=self.version,
                columns=columns,
            )
            destination = DBMetadata(
                name="file",
                version=fileobj.name,
                columns=columns,
            )
            self.logger.info(transfer_diagram(source, destination))
            stream = self.cursor.get_response(query)
            size = 0

            while chunk := stream.read(CHUNK_SIZE):
                size += fileobj.write(chunk)

            stream.close()
            fileobj.close()
            self.logger.info(f"Successfully read {size} bytes.")

            if not size:
                self.logger.warning("Empty data read!")

            self.logger.info(f"Read from {self.connector.host} done.")
            return True
        except ClickhouseServerError as error:
            raise error
        except Exception as error:
            self.logger.error(f"NativeDumperReadError: {error}")
            raise NativeDumperReadError(error)

    @multiquery
    def __write_between(
        self,
        table_dest: str,
        table_src: str | None,
        query_src: str | None,
        dumper_src: Union["NativeDumper", object],
    ) -> bool:
        """Internal method write_between for generate kwargs to decorator."""

        if not query_src and not table_src:
            error_message = "Source query or table name not defined."
            self.logger.error(f"NativeDumperValueError: {error_message}")
            raise NativeDumperValueError(error_message)

        if not table_dest:
            error_message = "Destination table name not defined."
            self.logger.error(f"NativeDumperValueError: {error_message}")
            raise NativeDumperValueError(error_message)

        if not dumper_src:
            cursor = HTTPCursor(
                connector=self.connector,
                compression_method=self.compression_method,
                logger=self.logger,
                timeout=self.cursor.timeout,
            )
            src_dbname = self.dbname
            src_version = self.version
            self.logger.info(
                f"Set new connection for host {self.connector.host}."
            )
        elif dumper_src.__class__ is NativeDumper:
            cursor = dumper_src.cursor
            src_dbname = dumper_src.dbname
            src_version = dumper_src.version
        else:
            reader = dumper_src.to_reader(
                query=query_src,
                table_name=table_src,
            )
            dtype_data = reader.to_rows()
            self.from_rows(
                dtype_data=dtype_data,
                table_name=table_dest,
                source=dumper_src._dbmeta,
            )
            size = reader.tell()
            self.logger.info(f"Successfully sending {size} bytes.")

            if not size:
                self.logger.warning("Empty data send!")

            return reader.close()

        if not query_src:
            query_src = f"SELECT * FROM {table_src}"

        source = DBMetadata(
            name=src_dbname,
            version=src_version,
            columns=make_columns(cursor.metadata(f"({query_src})")),
        )
        destination = DBMetadata(
            name=self.dbname,
            version=self.version,
            columns=make_columns(self.cursor.metadata(table_dest)),
        )
        self.logger.info(transfer_diagram(source, destination))
        stream = cursor.get_response(query_src)
        self.write_dump(stream, table_dest, cursor.compression_method)

    @multiquery
    def __to_reader(
        self,
        query: str | None,
        table_name: str | None,
    ) -> NativeReader:
        """Internal method to_reader for generate kwargs to decorator."""

        if not query and not table_name:
            error_message = "Query or table name not defined."
            self.logger.error(f"NativeDumperValueError: {error_message}")
            raise NativeDumperValueError(error_message)

        if not query:
            query = f"SELECT * FROM {table_name}"

        self.logger.info(
            f"Get NativeReader object from {self.connector.host}."
        )
        self._dbmeta = DBMetadata(
            name=self.dbname,
            version=self.version,
            columns=make_columns(self.cursor.metadata(f"({query})")),
        )
        return self.cursor.get_stream(query)

    def read_dump(
        self,
        fileobj: BufferedWriter,
        query: str | None = None,
        table_name: str | None = None,
    ) -> bool:
        """Read Native dump from Clickhouse."""

        return self.__read_dump(
            fileobj=fileobj,
            query=query,
            table_name=table_name,
        )

    def write_dump(
        self,
        fileobj: BufferedReader | BinaryIO,
        table_name: str,
        compression_method: CompressionMethod | None = None,
    ) -> None:
        """Write Native dump into Clickhouse."""

        if not table_name:
            error_message = "Table name not defined."
            self.logger.error(f"NativeDumperValueError: {error_message}")
            raise NativeDumperValueError(error_message)

        self.logger.info(
            f"Start write into {self.connector.host}.{table_name}."
        )

        try:
            if not compression_method:
                compression_method = auto_detector(fileobj)

            if compression_method != self.compression_method:
                reader = define_reader(fileobj, compression_method)
                data = define_writer(
                    file_writer(reader),
                    self.compression_method,
                )
            else:
                reader = fileobj
                data = file_writer(reader)

            self.cursor.upload_data(
                table=table_name,
                data=data,
            )
            size = reader.tell()
            self.logger.info(f"Successfully sending {size} bytes.")

            if not size:
                self.logger.warning("Empty data send!")

            reader.close()
        except ClickhouseServerError as error:
            raise error
        except Exception as error:
            self.logger.error(f"NativeDumperWriteError: {error}")
            raise NativeDumperWriteError(error)

        self.logger.info(
            f"Write into {self.connector.host}.{table_name} done."
        )
        self.refresh()

    def write_between(
        self,
        table_dest: str,
        table_src: str | None = None,
        query_src: str | None = None,
        dumper_src: Union["NativeDumper", object] = None,
    ) -> bool:
        """Write between Clickhouse servers."""

        return self.__write_between(
            table_dest=table_dest,
            table_src=table_src,
            query_src=query_src,
            dumper_src=dumper_src,
        )

    def to_reader(
        self,
        query: str | None = None,
        table_name: str | None = None,
    ) -> NativeReader:
        """Get stream from Clickhouse as NativeReader object."""

        return self.__to_reader(
            query=query,
            table_name=table_name,
        )

    def from_rows(
        self,
        dtype_data: Iterable[Any],
        table_name: str,
        source: DBMetadata | None = None,
    ) -> None:
        """Write from python list into Clickhouse table."""

        if not table_name:
            error_message = "Table name not defined."
            self.logger.error(f"NativeDumperValueError: {error_message}")
            raise NativeDumperValueError(error_message)

        if not source:
            source = DBMetadata(
                name="python",
                version="iterable object",
                columns={"Unknown": "Unknown"},
            )

        column_list = self.cursor.metadata(table_name)
        writer = NativeWriter(column_list)
        data = define_writer(
            writer.from_rows(dtype_data),
            self.compression_method,
        )

        destination = DBMetadata(
            name=self.dbname,
            version=self.version,
            columns=make_columns(column_list),
        )

        self.logger.info(transfer_diagram(source, destination))
        self.logger.info(
            f"Start write into {self.connector.host}.{table_name}."
        )

        try:
            self.cursor.upload_data(
                table=table_name,
                data=data,
            )
        except ClickhouseServerError as error:
            raise error
        except Exception as error:
            self.logger.error(f"NativeDumperWriteError: {error}")
            raise NativeDumperWriteError(error)

        self.logger.info(
            f"Write into {self.connector.host}.{table_name} done."
        )
        self.refresh()

    def from_pandas(
        self,
        data_frame: PdFrame,
        table_name: str,
    ) -> None:
        """Write from pandas.DataFrame into Clickhouse table."""

        self.from_rows(
            dtype_data=iter(data_frame.values),
            table_name=table_name,
            source=DBMetadata(
                name="pandas",
                version="DataFrame",
                columns=OrderedDict(zip(
                    data_frame.columns,
                    [str(dtype) for dtype in data_frame.dtypes],
                )),
            )
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
            source=DBMetadata(
                name="polars",
                version="DataFrame",
                columns=OrderedDict(zip(
                    data_frame.columns,
                    [str(dtype) for dtype in data_frame.dtypes],
                )),
            )
        )

    def refresh(self) -> None:
        """Refresh session."""

        self.cursor.refresh()
        self.logger.info(f"Connection to host {self.connector.host} updated.")

    def close(self) -> None:
        """Close session."""

        self.cursor.close()
        self.logger.info(f"Connection to host {self.connector.host} closed.")

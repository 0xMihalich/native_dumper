from typing_extensions import Buffer
from urllib3.response import HTTPResponse


class StreamReader:
    """Class for read unpacked stream from http requests."""

    def __init__(
        self,
        stream: HTTPResponse,
    ) -> None:
        """Class initialization."""

        self.stream = stream
        self.stream.decode_content = True
        self.pos = 0

    def __hash__(self) -> int:
        """StreamReader hash exploit."""

        return self.stream.__hash__()

    def __enter__(self) -> "StreamReader":
        """StreamReader __enter__ exploit."""

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        exc_tb: object,
    ) -> bool:
        """StreamReader __exit__ exploit."""

        return self.stream.__exit__(
            exc_type,
            exc_value,
            exc_tb,
        )

    @property
    def mode(self) -> str:
        return "rb"

    @property
    def closed(self) -> bool:
        return self.stream.closed

    def read(self, size: int | None = None) -> bytes:
        buffer = self.stream.read(amt=size, decode_content=True)
        self.pos += len(buffer)
        return buffer

    def readline(self, size: int = -1) -> bytes:
        return self.stream.readline(size)

    def readlines(self, hint: int = -1) -> list[bytes]:
        return self.stream.readlines(hint)

    def seek(self, target: int, whence: int = 0) -> int:
        if whence != 0:
            raise ValueError("whence don't have SEEK_SET value.")
        if self.tell() > target:
            raise ValueError("cannot seek stream backwards.")
        if self.tell() == target:
            return target
        pos = target - self.tell()
        self.read(pos)
        return self.pos

    def tell(self) -> int:
        return self.pos

    def close(self) -> None:
        self.stream.close()

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return True

    def readinto(self, b: Buffer) -> int:
        return self.stream.readinto(b)

    def isatty(self) -> bool:
        return self.stream.isatty()

    def fileno(self) -> int:
        return self.stream.fileno()

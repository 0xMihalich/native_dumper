from collections.abc import Generator
from io import BufferedReader


def file_writer(fileobj: BufferedReader) -> Generator[bytes, None, None]:
    """Chunk fileobj to bytes generator."""

    while chunk := fileobj.read(262_144):
        yield chunk

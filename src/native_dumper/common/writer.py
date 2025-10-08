from collections.abc import Generator
from io import BufferedReader

from .defines import CHUNK_SIZE


def file_writer(fileobj: BufferedReader) -> Generator[bytes, None, None]:
    """Chunk fileobj to bytes generator."""

    while chunk := fileobj.read(CHUNK_SIZE):
        yield chunk

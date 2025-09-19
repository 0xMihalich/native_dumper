from enum import Enum


class CompressionMethod(Enum):
    """List of compression codecs."""

    NONE = 0x02
    LZ4 = 0x82
    ZSTD = 0x90

    @property
    def method(self) -> str:
        """return selected method."""

        return self.name.lower()

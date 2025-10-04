class ClickhouseServerError(ValueError):
    """Clickhouse errors."""


class NativeDumperError(Exception):
    """NativeDumper base error."""


class NativeDumperReadError(NativeDumperError):
    """NativeDumper read error."""


class NativeDumperWriteError(NativeDumperError):
    """NativeDumper write error."""


class NativeDumperValueError(ValueError):
    """NativeDumper value error."""

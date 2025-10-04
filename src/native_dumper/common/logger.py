from datetime import datetime
from logging import (
    DEBUG,
    FileHandler,
    Formatter,
    Logger,
    StreamHandler,
)
from os import makedirs
from os.path import dirname
from sys import stdout

from ..version import __version__


def root_dir() -> str:
    """Get project directory."""

    try:
        import __main__

        return dirname(__main__.__file__)
    except AttributeError:
        return ""


class DumperLogger(Logger):
    """NativeDumper logger."""

    def __init__(
            self,
            level: int = DEBUG,
            use_console: bool = True,
    ) -> None:
        """Class initialize."""

        super().__init__("NativeDumper")

        self.fmt = (
            f"%(asctime)s | %(levelname)-8s | ver {__version__} "
            "| %(funcName)s-%(filename)s-%(lineno)04d <%(message)s>"
        )
        self.setLevel(level)
        self.log_path = f"{root_dir()}/native_logs"
        makedirs(self.log_path, exist_ok=True)

        formatter = Formatter(
            fmt=self.fmt,
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = FileHandler(
            "{}/{:%Y-%m-%d}_{}.log".format(
                self.log_path,
                datetime.now(),
                self.name,
            ),
            encoding="utf-8",
        )
        file_handler.setLevel(DEBUG)
        file_handler.setFormatter(formatter)
        self.addHandler(file_handler)

        if use_console:
            console_handler = StreamHandler(stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            self.addHandler(console_handler)

        self.propagate = False

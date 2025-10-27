from collections import OrderedDict

from nativelib import Column


def make_columns(
    column_list: list[Column],
) -> OrderedDict[str, str]:
    """Make DBMetadata.columns dictionary."""

    columns = OrderedDict()

    for column in column_list:
        col_type = column.dtype.name
        info = column.info

        if col_type == "FixedString":
            col_type = f"{col_type}({info.length})"
        elif col_type == "Decimal":
            col_type = f"{col_type}({info.precision}, {info.scale})"
        elif col_type == "DateTime64":
            col_type = f"{col_type}({info.precision}, {info.tzinfo})"
        elif col_type in ("Enum8", "Enum16"):
            col_type = f"{col_type}({info.enumcase})"
        elif col_type == "Time64":
            col_type = f"{col_type}({info.precision})"

        columns[column.column] = col_type

    return columns

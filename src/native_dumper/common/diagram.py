from collections import OrderedDict
from typing import NamedTuple


class DBMetadata(NamedTuple):
    """Database object."""

    name: str
    version: str
    columns: OrderedDict


def truncate_text(text: str, max_length: int) -> str:
    """Truncate text and add ellipsis if too long."""

    if len(text) > max_length:
        return text[: max_length - 1] + "…"
    return text


def format_table(
    metadata: DBMetadata,
    direction: str,
    table_width: int = 51,
) -> list[str]:
    """Format single table as list of lines."""

    lines = []

    title = f"{direction} [{metadata.name} {metadata.version}]"
    lines.append(f"┌{''.ljust(table_width, '─')}┐")
    lines.append(
        f"│ {truncate_text(title, table_width - 1).ljust(table_width - 1)}│"
    )
    lines.append(f"╞{'═' * 25}╤{'═' * 25}╡")
    lines.append(f"│ {'Column Name'.ljust(23)} │ {'Data Type'.ljust(23)} │")
    lines.append(f"╞{'═' * 25}╪{'═' * 25}╡")

    for i, (col_name, col_type) in enumerate(metadata.columns.items()):
        truncated_name = truncate_text(col_name, 23)
        truncated_type = truncate_text(str(col_type), 23)
        lines.append(
            f"│ {truncated_name.ljust(23)} │ {truncated_type.ljust(23)} │"
        )
        if i < len(metadata.columns) - 1:
            lines.append(f"├{'─' * 25}┼{'─' * 25}┤")

    lines.append(f"└{'─' * 25}┴{'─' * 25}┘")
    return lines


def transfer_diagram(source: DBMetadata, destination: DBMetadata) -> str:
    """Make transfer diagram with two tables and arrow."""

    src_lines = format_table(source, "Source")
    dest_lines = format_table(destination, "Destination")
    max_lines = max(len(src_lines), len(dest_lines), 9)

    src_lines.extend([" " * 53] * (max_lines - len(src_lines)))
    dest_lines.extend([" " * 53] * (max_lines - len(dest_lines)))

    middle_line = max_lines // 2
    arrow_config = [
        (middle_line - 3, " │╲   "),
        (middle_line - 2, " │ ╲  "),
        (middle_line - 1, "┌┘  ╲ "),
        (middle_line, "│    ╲"),
        (middle_line + 1, "│    ╱"),
        (middle_line + 2, "└┐  ╱ "),
        (middle_line + 3, " │ ╱  "),
        (middle_line + 4, " │╱   "),
    ]
    arrow_map = {line: arrow for line, arrow in arrow_config}

    return "Transfer data diagram:\n" + "\n".join(
        f"{src_lines[row]} {arrow_map.get(row, '      ')} {dest_lines[row]}"
        for row in range(max_lines)
    )

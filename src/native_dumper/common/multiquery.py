from re import split

def chunk_query(query: str | None) -> tuple[list[str]]:
    """Chunk multiquery to queryes."""

    if not query:
        return [], []

    pattern = r";(?=(?:[^']*'[^']*')*[^']*$)"
    parts = [
        part.strip(";").strip()
        for part in split(pattern, query)
        if part.strip(";").strip()
    ]

    if not parts:
        return [], []

    first_part: list[str] = []
    second_part: list[str] = []

    for i, part in enumerate(parts):
        first_part.append(part)

        if (i + 1 < len(parts) and parts[i + 1].lower().startswith(
                ('with ', 'select ')
            )
        ):
            second_part = parts[i + 1:]
            break
    else:
        second_part = []

    return first_part, second_part

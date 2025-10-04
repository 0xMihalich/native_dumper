def chunk_query(query: str | None) -> tuple[list[str]]:
    """Chunk multiquery to queryes."""

    if not query:
        return [], []

    first_part: list[str] = [
        part.strip()
        for part in query.split(";")
    ]
    second_part: list[str] = []

    for _ in first_part:
        second_part.append(first_part.pop())
        if any(
            word == second_part[-1][:len(word)].lower()
            for word in ("with", "select")
        ):
            second_part = list(reversed(second_part))
            break

    return first_part, second_part

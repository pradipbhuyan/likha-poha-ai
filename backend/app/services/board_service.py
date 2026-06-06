SUPPORTED_SCHOOL_BOARDS = [
    "CBSE",
    "ICSE",
    "State Board",
]

SOF_MODE = "SOF"


def normalize_board(value: str | None) -> str:
    """Normalize missing or free-text board labels while keeping CBSE default."""
    text = str(value or "").strip()

    if not text:
        return "CBSE"

    canonical = {
        "cbse": "CBSE",
        "icse": "ICSE",
        "state": "State Board",
        "state board": "State Board",
        "sof": SOF_MODE,
    }

    return canonical.get(text.lower(), text)


def is_school_board(board: str | None) -> bool:
    """Return whether a board value should use school-board access controls."""
    return normalize_board(board) in SUPPORTED_SCHOOL_BOARDS


def resolve_request_board(mode: str | None, board: str | None = None) -> str:
    """Resolve the board dimension without disturbing existing CBSE requests."""
    normalized_mode = normalize_board(mode)

    if is_school_board(normalized_mode):
        return normalized_mode

    return normalize_board(board)

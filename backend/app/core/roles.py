from enum import Enum


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


ADMIN_ONLY_PATHS: set[tuple[str, str]] = {
    ("POST", "/documents/upload"),
}

ADMIN_ONLY_PREFIXES: list[tuple[str, str]] = [
    ("GET", "/documents"),
    ("DELETE", "/documents/"),
    ("POST", "/documents/"),
]

from enum import Enum


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


ADMIN_ONLY_PATHS: set[tuple[str, str]] = {
    ("POST", "/import-docx"),
    ("POST", "/proverbs"),
    ("DELETE", "/proverbs"),
}

ADMIN_ONLY_PREFIXES: list[tuple[str, str]] = [
    ("PUT", "/proverbs/"),
    ("DELETE", "/proverbs/"),
]

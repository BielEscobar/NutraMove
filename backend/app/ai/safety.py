"""Reject plainly out-of-scope medical content before persisting suggestions."""

from collections.abc import Mapping

PROHIBITED = (
    "medicamento",
    "remédio",
    "hormônio",
    "esteroide",
    "anabolizante",
    "testosterona",
    "insulina",
    "antibiótico",
    "cura garantida",
)


def validate_scope(value: object) -> None:
    if isinstance(value, str):
        if any(term in value.casefold() for term in PROHIBITED):
            raise ValueError("out_of_scope")
    elif isinstance(value, Mapping):
        for item in value.values():
            validate_scope(item)
    elif isinstance(value, list):
        for item in value:
            validate_scope(item)

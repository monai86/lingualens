"""Opaque correlation identifiers for the assessment v2 boundary."""

from __future__ import annotations

import re
from uuid import uuid4


_OPAQUE_CORRELATION_ID = re.compile(r"^[0-9a-f]{32}$")


def sanitize_correlation_id(value: object) -> str:
    """Accept only generated-style IDs so request headers cannot carry identifiers."""

    if isinstance(value, str) and _OPAQUE_CORRELATION_ID.fullmatch(value):
        return value
    return uuid4().hex

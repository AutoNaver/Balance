from __future__ import annotations

from datetime import date


def year_fraction(start: date, end: date) -> float:
    """ACT/365 year fraction."""
    return (end - start).days / 365.0

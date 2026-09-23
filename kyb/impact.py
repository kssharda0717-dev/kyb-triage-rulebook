"""What a rulebook change would do, before anyone signs it off: re-run the
same applications under both versions and list every outcome that moves."""
from __future__ import annotations

from .engine import assess


def impact(cases: list[dict], old: dict, new: dict, as_of) -> list[dict]:
    moved = []
    for c in cases:
        a, b = assess(c, old, as_of), assess(c, new, as_of)
        if a["outcome"] != b["outcome"]:
            moved.append({"case_id": c["case_id"], "legal_name": c["entity"]["legal_name"],
                          "from": a["outcome"], "to": b["outcome"], "because": b["reasons"]})
    return moved

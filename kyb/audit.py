"""Append-only, hash-chained audit log (POL-7.4).

Each entry stores the hash of the previous entry. Editing, deleting or
reordering any line breaks the chain from that point on, and `verify`
names the first line that no longer checks out.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .rulebook import canonical

GENESIS = "0" * 64


def _entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "entry_hash"}
    return hashlib.sha256(canonical(body).encode()).hexdigest()


def read(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append(path: Path, event: str, case_id: str, at: str, payload: dict) -> dict:
    path = Path(path)
    entries = read(path)
    prev = entries[-1]["entry_hash"] if entries else GENESIS
    entry = {"seq": len(entries) + 1, "at": at, "event": event, "case_id": case_id,
             "payload": payload, "prev_hash": prev}
    entry["entry_hash"] = _entry_hash(entry)
    with path.open("a", encoding="utf-8") as f:
        f.write(canonical(entry) + "\n")
    return entry


def verify(path: Path) -> tuple[bool, str]:
    prev = GENESIS
    entries = read(path)
    for i, e in enumerate(entries, start=1):
        if e.get("seq") != i:
            return False, f"line {i}: sequence number is {e.get('seq')}, expected {i}"
        if e.get("prev_hash") != prev:
            return False, f"line {i}: does not chain to the line before it"
        if _entry_hash(e) != e.get("entry_hash"):
            return False, f"line {i}: contents changed after it was written"
        prev = e["entry_hash"]
    return True, f"{len(entries)} entries, chain intact"


def decision_payload(d: dict) -> dict:
    return {k: d[k] for k in ("outcome", "deciding_rules", "rulebook_version", "rulebook_hash",
                              "case_hash", "engine_version", "as_of")} | {"risk_score": d["risk"]["score"],
                                                                          "risk_band": d["risk"]["band"]}

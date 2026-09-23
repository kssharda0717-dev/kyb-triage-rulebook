"""Overrides of automated outcomes (POL-7.3). Refused unless every condition
in the rulebook is met."""
from __future__ import annotations


class OverrideError(ValueError):
    pass


def check_override(decision: dict, rb: dict, to: str, reason: str, note: str, by: str, role: str) -> dict:
    cfg = rb["overrides"]
    problems = []
    if to not in rb["outcomes"]:
        problems.append(f"unknown outcome {to}")
    if to == decision["outcome"]:
        problems.append(f"case is already {to}")
    if reason not in cfg["reasons"]:
        problems.append(f"reason code {reason} is not in the rulebook ({', '.join(cfg['reasons'])})")
    if len((note or "").strip()) < cfg["min_note_chars"]:
        problems.append(f"note must be at least {cfg['min_note_chars']} characters")
    if not (by or "").strip():
        problems.append("overrider name is required")
    if decision["outcome"] in cfg["mlro_only"] and role != "MLRO":
        problems.append(f"only the MLRO may override {decision['outcome']}")
    if problems:
        raise OverrideError(f"Override on {decision['case_id']} refused: " + "; ".join(problems))
    return {"from": decision["outcome"], "to": to, "reason_code": reason,
            "reason": cfg["reasons"][reason], "note": note.strip(), "by": by.strip(), "role": role,
            "rulebook_version": rb["meta"]["version"]}

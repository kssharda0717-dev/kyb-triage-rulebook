"""Load and validate the rulebook. A rulebook that fails validation is refused,
never partially applied."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "rulebook" / "rulebook.yaml"
RATINGS = ("low", "medium", "high", "prohibited")
CLAUSE = re.compile(r"\[(POL-\d+\.\d+)\]")


class RulebookError(ValueError):
    """The rulebook is inconsistent and must not be used."""


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256(obj) -> str:
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def policy_clauses(path: Path) -> set[str]:
    return set(CLAUSE.findall(path.read_text(encoding="utf-8")))


def load(path: Path | str = DEFAULT_PATH) -> dict:
    path = Path(path)
    rb = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate(rb, policy_path=ROOT / rb["meta"]["policy"])
    rb["_hash"] = sha256({k: v for k, v in rb.items() if not k.startswith("_")})
    rb["_path"] = str(path)
    return rb


def validate(rb: dict, policy_path: Path) -> None:
    from .engine import CHECKS  # checks are code; the rulebook decides which run

    problems: list[str] = []
    clauses = policy_clauses(policy_path)
    effects = rb["effects"]
    outcomes = rb["outcomes"]

    if rb["meta"].get("status") != "approved":
        problems.append("rulebook status is not 'approved'")
    for name, eff in effects.items():
        if eff["outcome"] not in outcomes:
            problems.append(f"effect {name} points at unknown outcome {eff['outcome']}")
    seen = set()
    for rule in rb["rules"]:
        rid = rule["id"]
        if rid in seen:
            problems.append(f"duplicate rule id {rid}")
        seen.add(rid)
        if rule["check"] not in CHECKS:
            problems.append(f"{rid}: no check named {rule['check']}")
        if rule["policy"] not in clauses:
            problems.append(f"{rid}: cites {rule['policy']}, which is not in the policy")
        if rule["effect"] != "by_band" and rule["effect"] not in effects:
            problems.append(f"{rid}: unknown effect {rule['effect']}")
    for code, j in rb["jurisdictions"].items():
        if j["rating"] not in RATINGS:
            problems.append(f"jurisdiction {code}: bad rating {j['rating']}")
    for sector, rating in rb["sectors"].items():
        if rating not in RATINGS:
            problems.append(f"sector {sector}: bad rating {rating}")
    scoring = rb["risk_scoring"]
    for band in scoring["auto_approve_bands"]:
        if band not in scoring["bands"]:
            problems.append(f"auto_approve_bands names unknown band {band}")
    for band, eff in scoring["band_effects"].items():
        if eff not in effects:
            problems.append(f"band {band}: unknown effect {eff}")
    for band in scoring["bands"]:
        if band not in scoring["auto_approve_bands"] and band not in scoring["band_effects"]:
            problems.append(f"band {band} is neither auto-approved nor routed")
    for outcome in rb["overrides"]["mlro_only"]:
        if outcome not in outcomes:
            problems.append(f"overrides.mlro_only names unknown outcome {outcome}")
    if problems:
        raise RulebookError("Rulebook refused:\n  - " + "\n  - ".join(problems))

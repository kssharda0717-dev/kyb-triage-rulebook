"""Resolve screening potential matches against identifiers the firm holds.

Each hit ends in exactly one state:
  FALSE_POSITIVE  cleared by rule (identifiers disprove it)
  CONFIRMED       confirmed by rule (strong name match, identifiers agree)
  POTENTIAL       neither; an analyst decides
"""
from __future__ import annotations

FALSE_POSITIVE, CONFIRMED, POTENTIAL = "FALSE_POSITIVE", "CONFIRMED", "POTENTIAL"


def subjects(case: dict) -> dict[str, dict]:
    """Every screened party, keyed by name, with the identifiers we hold."""
    out = {}
    ent = case["entity"]
    out[ent["legal_name"]] = {"dob": None, "country": ent["incorporation_jurisdiction"],
                              "subject_type": "entity", "role": "entity"}
    for o in case.get("owners", []):
        out.setdefault(o["name"], {"dob": o.get("dob"), "country": o.get("nationality"),
                                   "subject_type": o.get("type", "individual"), "role": "owner"})
    for d in case.get("directors", []):
        out.setdefault(d["name"], {"dob": d.get("dob"), "country": d.get("nationality"),
                                   "subject_type": "individual", "role": "director"})
    return out


def resolve(hit: dict, held: dict | None, cfg: dict) -> dict:
    record = hit.get("list_record", {})
    matches, mismatches, unknown = [], [], []
    for ident in cfg["identifiers"]:
        ours = (held or {}).get(ident)
        theirs = record.get(ident)
        if ours is None or theirs is None:
            unknown.append(ident)
        elif str(ours).strip().lower() == str(theirs).strip().lower():
            matches.append(ident)
        else:
            mismatches.append(ident)

    score = float(hit["match_score"])
    our_type, their_type = (held or {}).get("subject_type"), record.get("subject_type")
    type_clash = bool(our_type and their_type and our_type != their_type)
    fp, low, conf = cfg["clear_false_positive"], cfg["clear_low_score"], cfg["confirm"]
    if held is None:
        state, reason = POTENTIAL, "screened name is not a party on the application"
    elif type_clash and cfg.get("clear_on_type_mismatch"):
        state, reason = FALSE_POSITIVE, f"list record is a {their_type}; screened party is a {our_type}"
    elif len(mismatches) >= fp["min_mismatches"] and len(matches) <= fp["max_matches"]:
        state, reason = FALSE_POSITIVE, f"identifiers disagree: {', '.join(mismatches)}"
    elif score < low["below_score"] and len(matches) <= low["max_matches"]:
        state, reason = FALSE_POSITIVE, f"match score {score:.2f} below {low['below_score']:.2f} and no identifier agrees"
    elif (score >= conf["at_or_above_score"] and len(matches) >= conf["min_matches"]
          and len(mismatches) <= conf["max_mismatches"]):
        state, reason = CONFIRMED, f"match score {score:.2f} and identifiers agree: {', '.join(matches)}"
    else:
        state, reason = POTENTIAL, (f"match score {score:.2f}; agree: {', '.join(matches) or 'none'}; "
                                    f"disagree: {', '.join(mismatches) or 'none'}; "
                                    f"not held: {', '.join(unknown) or 'none'}")
    if type_clash and state != FALSE_POSITIVE:
        mismatches.append("subject_type")
    return {**hit, "state": state, "reason": reason, "matches": matches,
            "mismatches": mismatches, "unknown": unknown,
            "role": (held or {}).get("role", "unknown")}


def resolve_all(case: dict, cfg: dict) -> list[dict]:
    held = subjects(case)
    return [resolve(h, held.get(h["subject"]), cfg) for h in case.get("screening", [])]

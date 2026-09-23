"""Apply the rulebook to one KYB application.

Deterministic by design: no model, no network, no clock. The assessment date
(`as_of`) is an input, so any past decision can be replayed exactly under the
rulebook version it was made with (POL-1.2).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from . import __version__
from .rulebook import sha256
from .screening import CONFIRMED, POTENTIAL, resolve_all

REQUIRED_FIELDS = ("legal_name", "entity_type", "incorporation_jurisdiction",
                   "operating_jurisdictions", "incorporated_on", "sector",
                   "expected_monthly_volume_usd")


class CaseError(ValueError):
    """The application is malformed. It is refused, not guessed at."""


def parse_when(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_day(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def check_case(case: dict) -> None:
    problems = []
    if not case.get("case_id"):
        problems.append("case_id missing")
    ent = case.get("entity") or {}
    problems += [f"entity.{f} missing" for f in REQUIRED_FIELDS if ent.get(f) in (None, "", [])]
    for i, o in enumerate(case.get("owners", [])):
        if not isinstance(o.get("ownership_pct"), (int, float)):
            problems.append(f"owners[{i}].ownership_pct is not a number")
    for i, h in enumerate(case.get("screening", [])):
        if not isinstance(h.get("match_score"), (int, float)) or not 0 <= h["match_score"] <= 1:
            problems.append(f"screening[{i}].match_score must be between 0 and 1")
    if problems:
        raise CaseError(f"{case.get('case_id', '?')}: " + "; ".join(problems))


# ── context helpers ──────────────────────────────────────────────────────────
def _jurisdictions(ctx) -> list[str]:
    ent = ctx["case"]["entity"]
    codes = [ent["incorporation_jurisdiction"], *ent["operating_jurisdictions"]]
    return list(dict.fromkeys(codes))


def _rating(ctx, code):
    j = ctx["rb"]["jurisdictions"].get(code)
    return j["rating"] if j else None


def _hits(ctx, lst, state):
    return [h for h in ctx["hits"] if h["list"] == lst and h["state"] == state]


def _fmt_hit(h):
    return f"{h['list']} hit on {h['subject']} ({h['role']}) vs '{h['matched_name']}': {h['reason']}"


# ── checks: each returns (fired, detail, open_items) ─────────────────────────
def required_documents(ctx):
    etype = ctx["case"]["entity"]["entity_type"]
    required = ctx["rb"]["documents"]["required"].get(etype)
    if required is None:
        return True, f"no document list for entity type '{etype}'", [f"Confirm the legal form of the entity (given as '{etype}')"]
    held = {d["type"] for d in ctx["case"].get("documents", [])}
    missing = [d for d in required if d not in held]
    if missing:
        return True, "missing: " + ", ".join(missing), [f"Provide {d.replace('_', ' ')}" for d in missing]
    return False, f"all {len(required)} required documents held", []


def document_age(ctx):
    limits = ctx["rb"]["documents"]["max_age_days"]
    today = ctx["as_of"].date()
    stale, items = [], []
    for d in ctx["case"].get("documents", []):
        if d["type"] not in limits:
            continue
        issued = parse_day(d["issued_on"])
        age = (today - issued).days
        if age < 0:
            stale.append(f"{d['type']} dated after the assessment date")
            items.append(f"Re-send {d['type'].replace('_', ' ')}: the date on it ({issued}) is in the future")
        elif age > limits[d["type"]]:
            stale.append(f"{d['type']} is {age} days old (limit {limits[d['type']]})")
            items.append(f"Provide a {d['type'].replace('_', ' ')} dated within the last {limits[d['type']]} days")
    return (True, "; ".join(stale), items) if stale else (False, "all dated documents within limits", [])


def jurisdiction_prohibited(ctx):
    bad = [c for c in _jurisdictions(ctx) if _rating(ctx, c) == "prohibited"]
    return (True, "prohibited: " + ", ".join(bad), []) if bad else (False, "none prohibited", [])


def jurisdiction_high(ctx):
    high = [c for c in _jurisdictions(ctx) if _rating(ctx, c) == "high"]
    return (True, "high-risk: " + ", ".join(high), []) if high else (False, "none high-risk", [])


def jurisdiction_unknown(ctx):
    unk = [c for c in _jurisdictions(ctx) if _rating(ctx, c) is None]
    return (True, "not rated in the risk assessment: " + ", ".join(unk), []) if unk else (False, "all rated", [])


def sector_prohibited(ctx):
    s = ctx["case"]["entity"]["sector"]
    return (True, f"sector '{s}' is prohibited", []) if ctx["rb"]["sectors"].get(s) == "prohibited" else (False, f"sector '{s}' permitted", [])


def sector_unknown(ctx):
    s = ctx["case"]["entity"]["sector"]
    return (True, f"sector '{s}' not rated", []) if s not in ctx["rb"]["sectors"] else (False, f"sector '{s}' rated", [])


def volume_escalation(ctx):
    vol = ctx["case"]["entity"]["expected_monthly_volume_usd"]
    cap = ctx["rb"]["volume_escalation_usd"]
    if vol > cap:
        return True, f"expected USD {vol:,.0f}/month exceeds USD {cap:,.0f}", []
    return False, f"expected USD {vol:,.0f}/month", []


def ubo_verified(ctx):
    t = ctx["rb"]["ownership"]["ubo_threshold_pct"]
    ubos = [o for o in ctx["case"].get("owners", []) if o["ownership_pct"] >= t]
    if not ubos:
        return True, f"no owner at or above {t}% declared", [f"Declare every individual owning {t}% or more, or confirm none does"]
    unverified = [o for o in ubos if not o.get("id_verified")]
    if unverified:
        return (True, "unverified UBO: " + ", ".join(f"{o['name']} ({o['ownership_pct']}%)" for o in unverified),
                [f"Provide verified identity documents for {o['name']} ({o['ownership_pct']}%)" for o in unverified])
    return False, f"{len(ubos)} UBO(s) identified and verified", []


def ownership_reconciles(ctx):
    total = round(sum(o["ownership_pct"] for o in ctx["case"].get("owners", [])), 2)
    tol = ctx["rb"]["ownership"]["reconcile_tolerance_pct"]
    if abs(total - 100) > tol:
        gap = round(100 - total, 2)
        return True, f"declared ownership totals {total}%", [f"Declared ownership totals {total}%; account for the remaining {gap}%"]
    return False, f"declared ownership totals {total}%", []


def ownership_depth(ctx):
    layers = ctx["case"].get("structure", {}).get("ownership_layers", 1)
    limit = ctx["rb"]["ownership"]["max_layers"]
    return (True, f"{layers} layers (limit {limit})", []) if layers > limit else (False, f"{layers} layer(s)", [])


def bearer_or_nominee(ctx):
    s = ctx["case"].get("structure", {})
    found = [k.replace("_", " ") for k in ("bearer_shares", "nominee_shareholders") if s.get(k)]
    return (True, "declared: " + ", ".join(found), []) if found else (False, "none declared", [])


def sanctions_confirmed(ctx):
    h = _hits(ctx, "sanctions", CONFIRMED)
    return (True, "; ".join(map(_fmt_hit, h)), []) if h else (False, "no confirmed sanctions match", [])


def pep_confirmed(ctx):
    h = _hits(ctx, "pep", CONFIRMED)
    return (True, "; ".join(map(_fmt_hit, h)), []) if h else (False, "no confirmed PEP", [])


def _adverse(ctx, high: bool):
    sev = set(ctx["rb"]["screening"]["adverse_media_escalate_severity"])
    h = [x for x in _hits(ctx, "adverse_media", CONFIRMED) if (x.get("severity") in sev) == high]
    return (True, "; ".join(map(_fmt_hit, h)), []) if h else (False, "none", [])


def adverse_media_high(ctx):
    return _adverse(ctx, True)


def adverse_media_other(ctx):
    return _adverse(ctx, False)


def screening_unresolved(ctx):
    h = [x for x in ctx["hits"] if x["state"] == POTENTIAL]
    if h:
        return True, "; ".join(map(_fmt_hit, h)), [f"Resolve {x['list']} potential match on {x['subject']} vs '{x['matched_name']}'" for x in h]
    return False, "all hits resolved by rule", []


def risk_band(ctx):
    band = ctx["risk"]["band"]
    if band in ctx["rb"]["risk_scoring"]["auto_approve_bands"]:
        return False, f"score {ctx['risk']['score']} is {band} risk: eligible for auto-approval", []
    return True, f"score {ctx['risk']['score']} is {band} risk: not eligible for auto-approval", []


CHECKS = {f.__name__: f for f in (
    required_documents, document_age, jurisdiction_prohibited, jurisdiction_high,
    jurisdiction_unknown, sector_prohibited, sector_unknown, volume_escalation,
    ubo_verified, ownership_reconciles, ownership_depth, bearer_or_nominee,
    sanctions_confirmed, pep_confirmed, adverse_media_high, adverse_media_other,
    screening_unresolved, risk_band)}


# ── scoring ──────────────────────────────────────────────────────────────────
def score(ctx) -> dict:
    cfg = ctx["rb"]["risk_scoring"]
    pts = cfg["points"]
    ent = ctx["case"]["entity"]
    lines = []

    order = ["low", "medium", "high"]
    rated = [(c, _rating(ctx, c)) for c in _jurisdictions(ctx) if _rating(ctx, c) in order]
    if rated:
        code, r = max(rated, key=lambda x: order.index(x[1]))
        lines.append({"factor": "Jurisdiction (highest rated)", "value": f"{code} ({r})", "points": pts["jurisdiction"][r], "policy": "POL-3.4"})
    s = ctx["rb"]["sectors"].get(ent["sector"])
    if s in order:
        lines.append({"factor": "Sector", "value": f"{ent['sector']} ({s})", "points": pts["sector"][s], "policy": "POL-4.2"})
    inc = parse_day(ent["incorporated_on"])
    today = ctx["as_of"].date()
    months = (today.year - inc.year) * 12 + (today.month - inc.month) - (today.day < inc.day)
    yc = pts["young_company"]
    lines.append({"factor": "Company age", "value": f"{months} months",
                  "points": yc["points"] if months < yc["under_months"] else 0, "policy": "POL-4.4"})
    vol = ent["expected_monthly_volume_usd"]
    vpts = max([t["points"] for t in pts["volume"] if vol > t["above_usd"]], default=0)
    lines.append({"factor": "Expected monthly volume", "value": f"USD {vol:,.0f}", "points": vpts, "policy": "POL-4.3"})
    layers = ctx["case"].get("structure", {}).get("ownership_layers", 1)
    if layers > ctx["rb"]["ownership"]["max_layers"]:
        lines.append({"factor": "Ownership depth", "value": f"{layers} layers", "points": pts["deep_ownership"], "policy": "POL-5.3"})
    if _hits(ctx, "pep", CONFIRMED):
        lines.append({"factor": "Confirmed PEP", "value": "yes", "points": pts["confirmed_pep"], "policy": "POL-6.4"})

    total = sum(l["points"] for l in lines)
    band = next(b for b, r in cfg["bands"].items() if total >= r["min"] and (r["max"] is None or total <= r["max"]))
    return {"score": total, "band": band, "breakdown": lines}


# ── assessment ───────────────────────────────────────────────────────────────
def assess(case: dict, rb: dict, as_of) -> dict:
    check_case(case)
    as_of = parse_when(as_of)
    ctx = {"case": case, "rb": rb, "as_of": as_of,
           "hits": resolve_all(case, rb["screening"])}
    ctx["risk"] = score(ctx)

    results, open_items = [], []
    for rule in rb["rules"]:
        fired, detail, items = CHECKS[rule["check"]](ctx)
        effect = rule["effect"]
        if effect == "by_band":
            effect = rb["risk_scoring"]["band_effects"].get(ctx["risk"]["band"]) if fired else None
        results.append({"id": rule["id"], "name": rule["name"], "policy": rule["policy"],
                        "effect": effect if fired else None, "fired": fired, "detail": detail})
        if fired:
            open_items += items

    fired = [r for r in results if r["fired"]]
    if fired:
        top = min(rb["effects"][r["effect"]]["rank"] for r in fired)
        deciding = [r for r in fired if rb["effects"][r["effect"]]["rank"] == top]
        outcome = rb["effects"][deciding[0]["effect"]]["outcome"]
    else:
        deciding, outcome = [], "AUTO_APPROVE"

    meta = rb["outcomes"][outcome]
    incomplete = any(r["effect"] == "incomplete" for r in fired)
    unresolved = any(h["state"] == POTENTIAL for h in ctx["hits"])
    return {
        "case_id": case["case_id"],
        "legal_name": case["entity"]["legal_name"],
        "submitted_at": case.get("submitted_at"),
        "as_of": as_of.isoformat(),
        "rulebook_version": rb["meta"]["version"],
        "rulebook_hash": rb["_hash"],
        "case_hash": sha256(case),
        "engine_version": __version__,
        "outcome": outcome,
        "outcome_label": meta["label"],
        "owner": meta["owner"],
        "sla_hours": meta["sla_hours"],
        "due_by": (as_of + timedelta(hours=meta["sla_hours"])).isoformat(),
        "deciding_rules": [r["id"] for r in deciding],
        "reasons": [f"{r['id']} {r['name']}: {r['detail']}" for r in deciding]
                   or ["No rule fired; low risk and eligible for auto-approval (POL-7.1)"],
        "risk": ctx["risk"],
        "rules": results,
        "open_items": open_items,
        "hits": ctx["hits"],
        "decision_ready": not incomplete and not unresolved,
        "sent_before_complete": outcome == "MLRO_ESCALATION" and incomplete,
    }

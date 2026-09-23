"""The three KPIs the role is measured on, computed from decisions."""
from __future__ import annotations

from collections import Counter

from .screening import CONFIRMED, FALSE_POSITIVE, POTENTIAL


def _pct(a, b):
    return f"{(100 * a / b):.0f}%" if b else "n/a"


def compute(decisions: list[dict], rb: dict) -> dict:
    lowmed = [d for d in decisions if d["risk"]["band"] in ("low", "medium") and d["outcome"] != "REJECT"]
    hits = [h for d in decisions for h in d["hits"]]
    states = Counter(h["state"] for h in hits)
    mlro = [d for d in decisions if d["outcome"] == "MLRO_ESCALATION"]
    return {
        "cases": len(decisions),
        "outcomes": dict(Counter(d["outcome"] for d in decisions)),
        "lowmed_cases": len(lowmed),
        "lowmed_auto": sum(d["outcome"] == "AUTO_APPROVE" for d in lowmed),
        "lowmed_review": sum(d["outcome"] == "ANALYST_REVIEW" for d in lowmed),
        "lowmed_waiting": sum(d["outcome"] == "INCOMPLETE" for d in lowmed),
        "lowmed_escalated": sum(d["outcome"] == "MLRO_ESCALATION" for d in lowmed),
        "alerts": len(hits),
        "alerts_cleared": states[FALSE_POSITIVE],
        "alerts_confirmed": states[CONFIRMED],
        "alerts_manual": states[POTENTIAL],
        "mlro_cases": len(mlro),
        "mlro_ready": sum(d["decision_ready"] for d in mlro),
        "review_sla_hours": rb["outcomes"]["ANALYST_REVIEW"]["sla_hours"],
        "auto_bands": rb["risk_scoring"]["auto_approve_bands"],
    }


def report(k: dict, rb: dict) -> str:
    by_rule = k["alerts_cleared"] + k["alerts_confirmed"]
    order = ["AUTO_APPROVE", "ANALYST_REVIEW", "INCOMPLETE", "MLRO_ESCALATION", "REJECT"]
    rows = "\n".join(f"| {o} | {k['outcomes'].get(o, 0)} |" for o in order)
    return f"""# KPI report

Rulebook v{rb['meta']['version']} · {k['cases']} applications

| Outcome | Cases |
|---|---|
{rows}

## 1. KYB submission to trading-ready under 24 hours (low and medium risk)

{k['lowmed_cases']} applications scored low or medium risk.

- **{k['lowmed_auto']}** approved automatically at submission, with no one touching them.
- **{k['lowmed_review']}** routed to analyst review with an {k['review_sla_hours']}-hour SLA, inside the 24-hour target if the SLA is met.
- **{k['lowmed_waiting']}** waiting on client information; outreach drafted, clock depends on the client.
- **{k['lowmed_escalated']}** escalated to the MLRO by a specific trigger despite a low or medium score.

Auto-approval is currently limited to bands: {', '.join(k['auto_bands'])}. Extending it to medium risk is a
one-line rulebook change, and needs MLRO sign-off (POL-7.1).

## 2. Alerts cleared by rule rather than by hand

{k['alerts']} screening alerts. **{by_rule} ({_pct(by_rule, k['alerts'])}) resolved by rule**:
{k['alerts_cleared']} cleared as false positives, {k['alerts_confirmed']} confirmed.
{k["alerts_manual"]} left for an analyst; the pack shows which identifiers were missing or disagreed.

## 3. MLRO can decide without asking for more information

{k['mlro_cases']} cases escalated. **{k['mlro_ready']} of {k['mlro_cases']} ({_pct(k['mlro_ready'], k['mlro_cases'])})
decision-ready**: documents complete and every screening hit resolved or explained.
"""

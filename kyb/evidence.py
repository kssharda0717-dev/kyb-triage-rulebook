"""Evidence pack per case, written so the MLRO can decide from the page
without asking for more (POL-7.2)."""
from __future__ import annotations

from datetime import timedelta

from .engine import parse_when


def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(out)


def outreach(decision: dict, case: dict, rb: dict) -> str:
    days = rb["client_response_days"]
    reply_by = (parse_when(decision["as_of"]) + timedelta(days=days)).date()
    items = "\n".join(f"{i}. {x}" for i, x in enumerate(decision["open_items"], 1))
    contact = case.get("contact", {}).get("name", "team")
    return (f"Subject: {decision['legal_name']}: information needed to complete onboarding\n\n"
            f"Hi {contact},\n\n"
            f"Thanks for your application. We can't finish our checks until we have the following:\n\n"
            f"{items}\n\n"
            f"Please send these by {reply_by}. Once they're in, we'll complete the review within our "
            f"published service level. If anything here is unclear, reply to this email and we'll help.\n\n"
            f"Compliance Onboarding")


def pack(decision: dict, case: dict, rb: dict, override: dict | None = None) -> str:
    d, ent = decision, case["entity"]
    L = [f"# Evidence pack: {d['case_id']} {d['legal_name']}", ""]
    L += [_table(["Field", "Value"], [
        ["Outcome", f"**{d['outcome']}**: {d['outcome_label']}"],
        ["Next action owner", d["owner"]],
        ["Next action due", f"{d['due_by']} (SLA {d['sla_hours']}h)"],
        ["Risk", f"{d['risk']['score']} ({d['risk']['band']})"],
        ["Decision-ready for MLRO", "yes" if d["decision_ready"] else "no, see open items"],
        ["Submitted", d["submitted_at"] or "not recorded"],
        ["Assessed as of", d["as_of"]],
        ["Rulebook", f"v{d['rulebook_version']}, sha256 {d['rulebook_hash'][:16]}…"],
        ["Application hash", f"sha256 {d['case_hash'][:16]}…"],
    ]), ""]
    if d["sent_before_complete"]:
        L += ["> Sent to the MLRO before the file is complete, as POL-6.3 requires for a confirmed sanctions match.", ""]
    if "R-SCR-01" in d["deciding_rules"]:
        L += ["> **Do not contact the client about this match** (POL-6.3, no tipping off). "
              "Open items below are for the MLRO, not for client outreach.", ""]

    L += ["## Why", ""] + [f"- {r}" for r in d["reasons"]] + [""]

    L += ["## Open items", ""]
    L += ([f"- [ ] {x}" for x in d["open_items"]] if d["open_items"] else ["None."]) + [""]

    L += ["## Risk score", "", _table(["Factor", "Value", "Points", "Policy"],
          [[l["factor"], l["value"], l["points"], l["policy"]] for l in d["risk"]["breakdown"]]
          + [["**Total**", f"**{d['risk']['band']}**", f"**{d['risk']['score']}**", ""]]), ""]

    L += ["## Every rule checked", "", _table(["Rule", "Check", "Result", "Effect", "Policy", "Detail"],
          [[r["id"], r["name"], "FIRED" if r["fired"] else "pass", r["effect"] or "", r["policy"], r["detail"]]
           for r in d["rules"]]), ""]

    L += ["## Screening", ""]
    if d["hits"]:
        L += [_table(["List", "Subject", "Role", "Matched name", "Score", "Result", "How it was resolved"],
              [[h["list"], h["subject"], h["role"], h["matched_name"], f"{h['match_score']:.2f}", h["state"], h["reason"]]
               for h in d["hits"]]), ""]
    else:
        L += ["No potential matches returned.", ""]

    L += ["## Entity", "", _table(["Field", "Value"], [
        ["Legal name", ent["legal_name"]], ["Registration number", ent.get("registration_number", "")],
        ["Entity type", ent["entity_type"]], ["Incorporated", f"{ent['incorporated_on']} in {ent['incorporation_jurisdiction']}"],
        ["Operates in", ", ".join(ent["operating_jurisdictions"])], ["Sector", ent["sector"]],
        ["Expected monthly volume", f"USD {ent['expected_monthly_volume_usd']:,.0f}"],
    ]), ""]
    s = case.get("structure", {})
    L += ["## Ownership", "", _table(["Owner", "Type", "Ownership", "ID verified", "Nationality"],
          [[o["name"], o.get("type", "individual"), f"{o['ownership_pct']}%", "yes" if o.get("id_verified") else "no",
            o.get("nationality", "")] for o in case.get("owners", [])]),
          "", f"Ownership layers: {s.get('ownership_layers', 1)}. Bearer shares: {'yes' if s.get('bearer_shares') else 'no'}. "
              f"Nominee shareholders: {'yes' if s.get('nominee_shareholders') else 'no'}.", ""]
    L += ["## Documents held", "", _table(["Document", "Dated"],
          [[x["type"], x["issued_on"]] for x in case.get("documents", [])]), ""]

    if d["outcome"] == "INCOMPLETE":
        L += ["## Client outreach draft", "", "```", outreach(d, case, rb), "```", ""]

    if override:
        L += ["## Override", "", _table(["Field", "Value"], [
            ["From → to", f"{override['from']} → {override['to']}"],
            ["Reason", f"{override['reason_code']}: {override['reason']}"],
            ["Note", override["note"]], ["By", f"{override['by']} ({override['role']})"]]), ""]

    if d["outcome"] in ("MLRO_ESCALATION", "REJECT"):
        L += ["## MLRO sign-off", "", "Decision: ☐ Approve  ☐ Approve with conditions  ☐ Reject", "",
              "Conditions / rationale: ______________________________", "",
              "Name: ______________________  Date: ____________", ""]
    return "\n".join(L)

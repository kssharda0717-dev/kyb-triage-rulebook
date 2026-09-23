"""Render rulebook.yaml as the human-readable RULEBOOK.md. The document an
analyst reads and the rules the engine runs come from the same file."""
from __future__ import annotations


def render(rb: dict) -> str:
    m = rb["meta"]
    L = [f"# {m['name']}", "",
         "> Generated from `rulebook/rulebook.yaml` by `python -m kyb render`. Do not edit by hand.", "",
         "| | |", "|---|---|",
         f"| Version | {m['version']} ({m['status']}) |",
         f"| Effective from | {m['effective_from']} |",
         f"| Approved by | {m['approved_by']}, {m['approved_on']} |",
         f"| Next review by | {m['next_review_by']} |",
         f"| Implements | `{m['policy']}` |", "",
         "## Rules", "",
         "Every rule runs on every application. When several fire, the effect with the lowest rank decides the outcome.", "",
         "| ID | Rule | Effect if fired | Policy |", "|---|---|---|---|"]
    L += [f"| {r['id']} | {r['name']} | {r['effect']} | {r['policy']} |" for r in rb["rules"]]
    L += ["", "## Effects and outcomes", "", "| Rank | Effect | Outcome | Owner | SLA |", "|---|---|---|---|---|"]
    for name, e in sorted(rb["effects"].items(), key=lambda x: x[1]["rank"]):
        o = rb["outcomes"][e["outcome"]]
        L.append(f"| {e['rank']} | {name} | {e['outcome']} | {o['owner']} | {o['sla_hours']}h |")
    a = rb["outcomes"]["AUTO_APPROVE"]
    L += [f"| – | none fired | AUTO_APPROVE | {a['owner']} | {a['sla_hours']}h |", "",
          f"Client response window for missing information: {rb['client_response_days']} days.", ""]
    rs = rb["risk_scoring"]
    L += ["## Risk scoring", "", "| Band | Score |", "|---|---|"]
    L += [f"| {b} | {r['min']}–{r['max'] if r['max'] is not None else '∞'} |" for b, r in rs["bands"].items()]
    L += ["", f"Auto-approval bands: **{', '.join(rs['auto_approve_bands'])}**. "
          + "Other bands: " + ", ".join(f"{b} → {e}" for b, e in rs["band_effects"].items()) + ".", "",
          "| Factor | Points |", "|---|---|"]
    p = rs["points"]
    L += [f"| Jurisdiction ({k}) | {v} |" for k, v in p["jurisdiction"].items()]
    L += [f"| Sector ({k}) | {v} |" for k, v in p["sector"].items()]
    L += [f"| Company younger than {p['young_company']['under_months']} months | {p['young_company']['points']} |"]
    L += [f"| Volume above USD {t['above_usd']:,}/month | {t['points']} |" for t in p["volume"]]
    L += [f"| Ownership deeper than {rb['ownership']['max_layers']} layers | {p['deep_ownership']} |",
          f"| Confirmed PEP | {p['confirmed_pep']} |", "",
          f"Volume above USD {rb['volume_escalation_usd']:,}/month escalates to the MLRO.", ""]
    d = rb["documents"]
    L += ["## Documents", ""] + [f"- **{t}**: {', '.join(docs)}" for t, docs in d["required"].items()]
    L += ["", "| Document | Maximum age |", "|---|---|"] + [f"| {k} | {v} days |" for k, v in d["max_age_days"].items()]
    o = rb["ownership"]
    L += ["", "## Ownership", "", f"- UBO threshold: {o['ubo_threshold_pct']}%",
          f"- Declared ownership must total 100% ± {o['reconcile_tolerance_pct']}%",
          f"- Maximum ownership layers before review: {o['max_layers']}", ""]
    s = rb["screening"]
    fp, low, c = s["clear_false_positive"], s["clear_low_score"], s["confirm"]
    def most(n, what):
        return f"no identifier {what}" if n == 0 else f"at most {n} {what}"
    L += ["## Screening: how a potential match is resolved", "",
          f"Identifiers compared: {', '.join(s['identifiers'])}. Checked in this order:", "",
          ("1. **False positive** if the list record is a different kind of party (person, company, vessel) from the one screened.\n"
           if s.get("clear_on_type_mismatch") else "") +
          f"1. **False positive** if at least {fp['min_mismatches']} identifiers disagree and {most(fp['max_matches'], 'agrees')}.",
          f"1. **False positive** if the match score is below {low['below_score']} and {most(low['max_matches'], 'agrees')}.",
          f"1. **Confirmed** if the score is at least {c['at_or_above_score']}, at least {c['min_matches']} identifier agrees and {most(c['max_mismatches'], 'disagrees')}.",
          "1. Otherwise **potential**: an analyst decides.", "",
          f"Adverse media escalates to the MLRO at severity: {', '.join(s['adverse_media_escalate_severity'])}.", ""]
    L += ["## Jurisdictions", "", "| Code | Name | Rating |", "|---|---|---|"]
    L += [f"| {k} | {v['name']} | {v['rating']} |" for k, v in rb["jurisdictions"].items()]
    L += ["", "## Sectors", "", "| Sector | Rating |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rb["sectors"].items()]
    ov = rb["overrides"]
    L += ["", "## Overrides", "", "| Code | Reason |", "|---|---|"] + [f"| {k} | {v} |" for k, v in ov["reasons"].items()]
    L += ["", f"Only the MLRO may override: {', '.join(ov['mlro_only'])}. A note of at least {ov['min_note_chars']} characters and the overrider's name are required.", "",
          "## Change log", "", "| Version | Date | Change |", "|---|---|---|"]
    L += [f"| {c['version']} | {c['date']} | {c['change']} |" for c in m["change_log"]]
    return "\n".join(L) + "\n"

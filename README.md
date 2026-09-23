# KYB Triage Rulebook

Business onboarding is slow when the criteria live in people's heads. Two
analysts read the same AML policy and reach different answers, every case
needs a person, and the MLRO sends files back for missing information.

This repo writes a sample AML policy down as rules a script can apply, then
runs a queue of KYB applications through them. Low-risk cases clear with no one
touching them. Everything else goes to the right person with the reason, the
open items and an evidence pack the MLRO can decide from first time.

```
policy/aml_policy.md ──► rulebook/rulebook.yaml ──► kyb engine ──► decision + evidence pack
 (clauses POL-x.y)        (every threshold,          (no model,      ├─ AUTO_APPROVE     trading-ready now
                           list and rule;             no network,    ├─ ANALYST_REVIEW   8h SLA
                           MLRO sign-off)             no clock)      ├─ INCOMPLETE       outreach drafted
                                                                     ├─ MLRO_ESCALATION  sign-off block
                                                                     └─ REJECT
                                                          │
                                                          └──► hash-chained audit log, KPI report
```

## Run it

```bash
pip install -r requirements.txt
python -m kyb triage --cases data/cases --as-of 2026-09-23T10:00:00Z --out output
python -m kyb verify --log output/audit.jsonl
python -m pytest
```

Or open [`demo.ipynb`](demo.ipynb), which walks through everything below with
its outputs saved. A finished run is committed in [`examples/`](examples/) so
you can read the packs without installing anything.

## The demo queue

13 synthetic applications, each built to exercise a different path.

| Case | Company | Outcome | Deciding rule |
|---|---|---|---|
| C001 | Brightline Software | AUTO_APPROVE | none fired |
| C002 | Harbour Freight Traders | ANALYST_REVIEW | medium risk score |
| C003 | Kestrel Design Studio | INCOMPLETE | missing proof of address, stale register |
| C004 | Orbit Digital Exchange | MLRO_ESCALATION | high-risk jurisdiction, high score |
| C005 | Meridian Holdings | REJECT | prohibited jurisdiction |
| C006 | Northgate Analytics | AUTO_APPROVE | two alerts cleared as false positives by rule |
| C007 | Coastal Metals Trading | MLRO_ESCALATION | confirmed sanctions match, sent before file complete |
| C008 | Aster Payments | MLRO_ESCALATION | confirmed PEP director |
| C009 | Lumen Retail | INCOMPLETE | unverified UBO, ownership totals 80% |
| C010 | Fairwind Ventures | MLRO_ESCALATION | nominee shareholders |
| C011 | Silverline Gaming | REJECT | prohibited sector |
| C012 | Pinecrest Components | ANALYST_REVIEW | screening hit the rule can't settle |
| C013 | Tidewater Labs | AUTO_APPROVE | sanctions hit on a vessel, cleared by rule |

The [KPI report](examples/kpi.md) scores the run against three measures:
submission to trading-ready for low and medium risk, alerts cleared by rule
(5 of 6 here), and MLRO cases decision-ready on arrival (3 of 4; the fourth is
the sanctions case, which POL-6.3 sends up immediately on purpose).

## Design choices

- **The rulebook is the only place a threshold lives.** Allowing medium-risk
  auto-approval is a one-line YAML change, not a code change. `RULEBOOK.md` is
  generated from the YAML and a test fails if the two drift apart, so the
  document an analyst reads is the rules the engine runs.
- **Every rule cites a policy clause.** A rule citing a clause that doesn't
  exist, a draft rulebook, or a risk band with no route are all refused at load.
- **No model in the decision path.** Decisions must be reproducible and
  explainable to an auditor. AI is useful around the edges (drafting outreach,
  extracting fields from documents); it doesn't decide.
- **Fails closed.** An unrated jurisdiction or sector goes to an analyst. A
  malformed application is refused with the field named, never guessed at.
- **Precedence is written down.** Reject beats everything. A confirmed sanctions
  match goes to the MLRO immediately. Otherwise missing information is collected
  before escalating, so the MLRO isn't sent a file they'll send back.
- **No tipping off.** A sanctions escalation never produces client outreach, and
  the pack says so at the top.
- **False-positive clearing is a rule, and it shows its working.** A hit is
  cleared when the list record is a different kind of party, when two
  identifiers disagree, or when the name match is weak and nothing agrees. The
  pack records which identifiers disproved it.
- **Replayable.** The assessment date is an input. Any past decision can be
  re-run exactly under the rulebook version it was made with.
- **Impact before sign-off.** `kyb.impact` re-runs the queue under a proposed
  rulebook and lists every case whose outcome would move.
- **Overrides need a reason code, a note and a name.** Only the MLRO can
  override a rejection or an escalation. Every override is logged.
- **Tamper-evident audit log.** Each entry carries the hash of the one before.
  Editing, deleting or reordering a line breaks the chain, and `verify` names
  the line.

## Repo layout

```
policy/        sample AML policy (clause IDs) and risk-assessment ratings
rulebook/      rulebook.yaml (source of truth) and generated RULEBOOK.md
kyb/           engine, screening resolution, evidence packs, audit log,
               overrides, KPIs, impact analysis, CLI
data/          synthetic applications and the script that generates them
examples/      a committed run: packs, decisions, KPI report, audit log
tests/         65 tests, including deliberate tamper and override attempts
demo.ipynb     executed walkthrough
```

## What this is not

- **Not a real policy.** The policy and ratings are illustrative, written for
  the demo, and not legal advice. Jurisdictions are fictional (`XA`–`XZ`).
- **Screening is simulated.** Alerts arrive as provider-style results in the
  case file; there is no live sanctions, PEP or adverse-media integration.
- **Onboarding only.** Transaction monitoring, periodic refresh and offboarding
  would use the same pattern (written thresholds, rule trace, evidence pack)
  but aren't built here.
- **No document extraction.** Document fields are supplied as structured data.
  An LLM extraction step with schema validation is the obvious next piece, and
  would sit in front of the engine, not inside it.

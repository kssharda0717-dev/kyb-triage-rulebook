# Sample KYB Onboarding Rulebook

> Generated from `rulebook/rulebook.yaml` by `python -m kyb render`. Do not edit by hand.

| | |
|---|---|
| Version | 1.0.0 (approved) |
| Effective from | 2026-09-01 |
| Approved by | Group MLRO (sample sign-off), 2026-08-28 |
| Next review by | 2027-02-28 |
| Implements | `policy/aml_policy.md` |

## Rules

Every rule runs on every application. When several fire, the effect with the lowest rank decides the outcome.

| ID | Rule | Effect if fired | Policy |
|---|---|---|---|
| R-DOC-01 | Required documents present | incomplete | POL-2.1 |
| R-DOC-02 | Documents recent enough to rely on | incomplete | POL-2.2 |
| R-JUR-01 | No prohibited jurisdiction | reject | POL-3.1 |
| R-JUR-02 | High-risk jurisdiction needs EDD | escalate | POL-3.2 |
| R-JUR-03 | Every jurisdiction is rated | review | POL-3.3 |
| R-SEC-01 | No prohibited sector | reject | POL-4.1 |
| R-SEC-02 | Sector is rated | review | POL-4.5 |
| R-VOL-01 | Expected volume under escalation threshold | escalate | POL-4.3 |
| R-UBO-01 | UBOs identified and verified | incomplete | POL-5.1 |
| R-UBO-02 | Ownership reconciles to 100% | incomplete | POL-5.2 |
| R-UBO-03 | Ownership chain within depth limit | review | POL-5.3 |
| R-UBO-04 | No bearer shares or nominees | escalate | POL-5.4 |
| R-SCR-01 | No confirmed sanctions match | escalate_immediate | POL-6.3 |
| R-SCR-02 | Confirmed PEP needs EDD | escalate | POL-6.4 |
| R-SCR-03 | High-severity adverse media | escalate | POL-6.5 |
| R-SCR-04 | Other confirmed adverse media | review | POL-6.5 |
| R-SCR-05 | No unresolved potential matches | review | POL-6.6 |
| R-RISK-01 | Risk band eligible for auto-approval | by_band | POL-7.1 |

## Effects and outcomes

| Rank | Effect | Outcome | Owner | SLA |
|---|---|---|---|---|
| 1 | reject | REJECT | Compliance analyst (notification) | 24h |
| 2 | escalate_immediate | MLRO_ESCALATION | Group MLRO | 24h |
| 3 | incomplete | INCOMPLETE | Compliance analyst (outreach) | 4h |
| 4 | escalate | MLRO_ESCALATION | Group MLRO | 24h |
| 5 | review | ANALYST_REVIEW | Compliance analyst | 8h |
| – | none fired | AUTO_APPROVE | System | 0h |

Client response window for missing information: 5 days.

## Risk scoring

| Band | Score |
|---|---|
| low | 0–24 |
| medium | 25–49 |
| high | 50–∞ |

Auto-approval bands: **low**. Other bands: medium → review, high → escalate.

| Factor | Points |
|---|---|
| Jurisdiction (low) | 0 |
| Jurisdiction (medium) | 15 |
| Jurisdiction (high) | 35 |
| Sector (low) | 0 |
| Sector (medium) | 15 |
| Sector (high) | 30 |
| Company younger than 12 months | 10 |
| Volume above USD 250,000/month | 10 |
| Volume above USD 1,000,000/month | 20 |
| Ownership deeper than 2 layers | 15 |
| Confirmed PEP | 30 |

Volume above USD 5,000,000/month escalates to the MLRO.

## Documents

- **company**: certificate_of_incorporation, register_of_directors, register_of_shareholders, proof_of_address, ubo_declaration
- **partnership**: partnership_agreement, register_of_partners, proof_of_address, ubo_declaration

| Document | Maximum age |
|---|---|
| proof_of_address | 90 days |
| register_of_directors | 365 days |
| register_of_shareholders | 365 days |
| register_of_partners | 365 days |
| ubo_declaration | 365 days |

## Ownership

- UBO threshold: 25%
- Declared ownership must total 100% ± 0.5%
- Maximum ownership layers before review: 2

## Screening: how a potential match is resolved

Identifiers compared: dob, country. Checked in this order:

1. **False positive** if the list record is a different kind of party (person, company, vessel) from the one screened.
1. **False positive** if at least 2 identifiers disagree and no identifier agrees.
1. **False positive** if the match score is below 0.75 and no identifier agrees.
1. **Confirmed** if the score is at least 0.95, at least 1 identifier agrees and no identifier disagrees.
1. Otherwise **potential**: an analyst decides.

Adverse media escalates to the MLRO at severity: high.

## Jurisdictions

| Code | Name | Rating |
|---|---|---|
| XA | Jurisdiction A | low |
| XB | Jurisdiction B | low |
| XC | Jurisdiction C | low |
| XM | Jurisdiction M | medium |
| XH | Jurisdiction H | high |
| XJ | Jurisdiction J | high |
| XP | Jurisdiction P | prohibited |

## Sectors

| Sector | Rating |
|---|---|
| software | low |
| professional_services | low |
| manufacturing | low |
| ecommerce | medium |
| import_export | medium |
| marketing | medium |
| crypto_exchange | high |
| money_services | high |
| precious_metals | high |
| unlicensed_gambling | prohibited |
| shell_company_services | prohibited |

## Overrides

| Code | Reason |
|---|---|
| OVR-01 | Information received after the automated decision |
| OVR-02 | Screening hit resolved with evidence the system does not hold |
| OVR-03 | Risk rating adjusted on a documented business rationale |
| OVR-04 | Rulebook error identified (rulebook change raised) |

Only the MLRO may override: REJECT, MLRO_ESCALATION. A note of at least 20 characters and the overrider's name are required.

## Change log

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-28 | First approved version. |

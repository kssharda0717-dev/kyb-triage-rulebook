# Sample AML & KYB Onboarding Policy (illustrative)

> **Sample document.** Written for this demo to show how a policy becomes rules.
> It is not legal advice and not a real firm's policy. Jurisdictions are
> fictional (ISO user-assigned codes `XA`–`XZ`), so no real country is rated.

Each clause carries an ID. Every rule in `rulebook/rulebook.yaml` cites the
clause it implements, and the test suite fails if a rule cites a clause that
does not exist here.

## 1. Scope

**[POL-1.1]** This policy applies to every business client (KYB) before it is
permitted to trade, and again at each periodic refresh.

**[POL-1.2]** A decision must be reproducible: the same application, assessed
under the same rulebook version on the same date, must receive the same outcome.

## 2. Documents

**[POL-2.1]** A client must supply the documents required for its entity type
before a decision is made. An application missing any of them is incomplete.

**[POL-2.2]** Documents that evidence current facts (address, registers of
directors and shareholders) must be recent enough to be relied on. Maximum ages
are set in the rulebook.

## 3. Jurisdiction risk

**[POL-3.1]** The firm does not onboard clients incorporated or operating in a
jurisdiction rated *prohibited* in the business-wide risk assessment.

**[POL-3.2]** Clients incorporated or operating in a *high-risk* jurisdiction
require enhanced due diligence and an MLRO decision.

**[POL-3.3]** A jurisdiction not rated in the risk assessment is treated as
unknown, and the case is reviewed by an analyst. The system fails closed.

**[POL-3.4]** The highest jurisdiction rating among the places a client is
incorporated or operates contributes to its overall risk score.

## 4. Business activity

**[POL-4.1]** The firm does not onboard clients whose primary activity is a
*prohibited* sector in the risk assessment.

**[POL-4.2]** Sector risk contributes to the client's overall risk score.

**[POL-4.3]** Expected transaction volume contributes to risk. Volume above the
escalation threshold requires an MLRO decision.

**[POL-4.4]** Recently incorporated companies carry additional risk.

**[POL-4.5]** A sector not rated in the risk assessment is treated as unknown,
and the case is reviewed by an analyst.

## 5. Ownership and control

**[POL-5.1]** Every ultimate beneficial owner (UBO) holding the ownership
threshold or more must be identified and have verified identity documents.

**[POL-5.2]** Declared ownership must reconcile to 100%. An unexplained gap is
treated as missing information, not as a rounding difference.

**[POL-5.3]** Ownership chains deeper than the rulebook limit are reviewed by
an analyst for a legitimate business rationale.

**[POL-5.4]** Bearer shares or nominee shareholders require an MLRO decision.

## 6. Screening

**[POL-6.1]** The entity, its UBOs and its directors are screened against
sanctions, PEP and adverse-media sources.

**[POL-6.2]** A potential match may be cleared as a false positive only by the
written clearing rule, and the identifiers that disproved it are recorded.

**[POL-6.3]** A confirmed sanctions match stops onboarding and goes to the MLRO
immediately, whatever else is outstanding. The client is not contacted about
the match (no tipping off).

**[POL-6.4]** A confirmed PEP match requires enhanced due diligence and an MLRO
decision.

**[POL-6.5]** Confirmed adverse media is escalated to the MLRO when rated high
severity, and reviewed by an analyst otherwise.

**[POL-6.6]** A potential match that the clearing rule can neither clear nor
confirm is reviewed by an analyst.

## 7. Decisions, escalation and overrides

**[POL-7.1]** Low-risk clients with no open triggers may be approved
automatically. The bands eligible for automatic approval are set in the
rulebook and signed off by the MLRO. Clients in a band not eligible for
automatic approval are reviewed by an analyst, and high-risk clients require
an MLRO decision.

**[POL-7.2]** Cases sent to the MLRO must be decision-ready: all documents in,
all screening hits resolved or explained. Missing information is collected
before escalation, except under POL-6.3.

**[POL-7.3]** An override of an automated outcome requires a reason code from
the rulebook, a written note and the overrider's name. Only the MLRO may
override a rejection or an MLRO escalation.

**[POL-7.4]** Every decision and override is recorded in a tamper-evident
audit log that names the rulebook version it was made under.

## 8. Governance

**[POL-8.1]** The rulebook is versioned, dated and signed off by the Group MLRO,
and reviewed at least every six months or when policy, risk appetite or
jurisdictions change.

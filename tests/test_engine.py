import copy
import json

import pytest

from conftest import AS_OF
from kyb.engine import CaseError, assess

EXPECTED = {
    "C001": ("AUTO_APPROVE", []),
    "C002": ("ANALYST_REVIEW", ["R-RISK-01"]),
    "C003": ("INCOMPLETE", ["R-DOC-01", "R-DOC-02"]),
    "C004": ("MLRO_ESCALATION", ["R-JUR-02", "R-RISK-01"]),
    "C005": ("REJECT", ["R-JUR-01"]),
    "C006": ("AUTO_APPROVE", []),
    "C007": ("MLRO_ESCALATION", ["R-SCR-01"]),
    "C008": ("MLRO_ESCALATION", ["R-SCR-02", "R-RISK-01"]),
    "C009": ("INCOMPLETE", ["R-UBO-01", "R-UBO-02"]),
    "C010": ("MLRO_ESCALATION", ["R-UBO-04"]),
    "C011": ("REJECT", ["R-SEC-01"]),
    "C012": ("ANALYST_REVIEW", ["R-SCR-05"]),
    "C013": ("AUTO_APPROVE", []),
}


@pytest.mark.parametrize("cid", sorted(EXPECTED))
def test_demo_case_outcomes(rb, cases, cid):
    d = assess(cases[cid], rb, AS_OF)
    assert (d["outcome"], d["deciding_rules"]) == EXPECTED[cid]


def test_same_input_same_answer(rb, cases):
    for c in cases.values():
        a, b = assess(c, rb, AS_OF), assess(copy.deepcopy(c), rb, AS_OF)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_key_order_does_not_change_the_case_hash(rb, clean):
    shuffled = json.loads(json.dumps(clean, sort_keys=True))
    assert assess(clean, rb, AS_OF)["case_hash"] == assess(shuffled, rb, AS_OF)["case_hash"]


def test_every_rule_runs_on_every_case(rb, cases):
    for c in cases.values():
        assert len(assess(c, rb, AS_OF)["rules"]) == len(rb["rules"])


def test_sanctions_outranks_missing_documents(rb, cases):
    d = assess(cases["C007"], rb, AS_OF)
    assert d["outcome"] == "MLRO_ESCALATION"
    assert d["sent_before_complete"] and not d["decision_ready"]


def test_missing_documents_outrank_ordinary_escalation(rb, cases):
    """Don't send the MLRO a file they will send back (POL-7.2)."""
    c = copy.deepcopy(cases["C004"])
    c["documents"] = [x for x in c["documents"] if x["type"] != "proof_of_address"]
    d = assess(c, rb, AS_OF)
    assert d["outcome"] == "INCOMPLETE"
    assert "Provide proof of address" in d["open_items"]


def test_unrated_jurisdiction_fails_closed(rb, clean):
    clean["entity"]["operating_jurisdictions"].append("XZ")
    d = assess(clean, rb, AS_OF)
    assert d["outcome"] == "ANALYST_REVIEW" and d["deciding_rules"] == ["R-JUR-03"]


def test_unrated_sector_fails_closed(rb, clean):
    clean["entity"]["sector"] = "space_tourism"
    assert assess(clean, rb, AS_OF)["deciding_rules"] == ["R-SEC-02"]


def test_prohibited_operating_jurisdiction_rejects_even_if_incorporated_elsewhere(rb, clean):
    clean["entity"]["operating_jurisdictions"].append("XP")
    assert assess(clean, rb, AS_OF)["outcome"] == "REJECT"


@pytest.mark.parametrize("field", ["sector", "entity_type", "expected_monthly_volume_usd"])
def test_malformed_application_is_refused_not_guessed(rb, clean, field):
    del clean["entity"][field]
    with pytest.raises(CaseError, match=field):
        assess(clean, rb, AS_OF)


def test_match_score_out_of_range_is_refused(rb, clean):
    clean["screening"] = [{"subject": "Maya Collins", "list": "pep", "matched_name": "M", "match_score": 87, "list_record": {}}]
    with pytest.raises(CaseError, match="match_score"):
        assess(clean, rb, AS_OF)


def test_future_dated_document_is_incomplete(rb, clean):
    clean["documents"][3]["issued_on"] = "2026-12-01"
    d = assess(clean, rb, AS_OF)
    assert d["outcome"] == "INCOMPLETE" and "R-DOC-02" in d["deciding_rules"]


@pytest.mark.parametrize("pct,fires", [(99.6, False), (100.4, False), (99.4, True), (100.6, True)])
def test_ownership_reconciliation_tolerance(rb, clean, pct, fires):
    clean["owners"][1]["ownership_pct"] = round(pct - 70, 2)
    r = next(x for x in assess(clean, rb, AS_OF)["rules"] if x["id"] == "R-UBO-02")
    assert r["fired"] is fires


def test_young_company_boundary(rb, clean):
    clean["entity"]["incorporated_on"] = "2025-09-23"  # exactly 12 months
    line = next(l for l in assess(clean, rb, AS_OF)["risk"]["breakdown"] if l["factor"] == "Company age")
    assert line["points"] == 0
    clean["entity"]["incorporated_on"] = "2025-09-24"  # one day short
    line = next(l for l in assess(clean, rb, AS_OF)["risk"]["breakdown"] if l["factor"] == "Company age")
    assert line["points"] == rb["risk_scoring"]["points"]["young_company"]["points"]


def test_replay_on_a_later_date_can_differ_and_says_why(rb, clean):
    """Document age depends on as_of, so the date is part of every decision."""
    later = "2026-12-01T10:00:00Z"
    assert assess(clean, rb, AS_OF)["outcome"] == "AUTO_APPROVE"
    d = assess(clean, rb, later)
    assert d["outcome"] == "INCOMPLETE" and d["as_of"].startswith("2026-12-01")

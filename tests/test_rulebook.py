import copy

import pytest
import yaml

from conftest import AS_OF, ROOT
from kyb import rulebook
from kyb.engine import assess
from kyb.render import render


def raw():
    return yaml.safe_load((ROOT / "rulebook" / "rulebook.yaml").read_text())


def test_loads_and_is_approved(rb):
    assert rb["meta"]["status"] == "approved"
    assert len(rb["_hash"]) == 64


def test_every_rule_cites_a_real_policy_clause(rb):
    clauses = rulebook.policy_clauses(ROOT / rb["meta"]["policy"])
    assert {r["policy"] for r in rb["rules"]} <= clauses


def test_rule_citing_a_missing_clause_is_refused():
    rb = raw()
    rb["rules"][0]["policy"] = "POL-99.9"
    with pytest.raises(rulebook.RulebookError, match="POL-99.9"):
        rulebook.validate(rb, ROOT / rb["meta"]["policy"])


def test_unapproved_rulebook_is_refused():
    rb = raw()
    rb["meta"]["status"] = "draft"
    with pytest.raises(rulebook.RulebookError, match="approved"):
        rulebook.validate(rb, ROOT / rb["meta"]["policy"])


def test_band_with_no_route_is_refused():
    rb = raw()
    del rb["risk_scoring"]["band_effects"]["medium"]
    with pytest.raises(rulebook.RulebookError, match="medium"):
        rulebook.validate(rb, ROOT / rb["meta"]["policy"])


def test_rendered_rulebook_matches_the_yaml(rb):
    """The document analysts read must be the rules the engine runs."""
    on_disk = (ROOT / "rulebook" / "RULEBOOK.md").read_text()
    assert on_disk == render(rb), "RULEBOOK.md is stale: run `python -m kyb render`"


def test_thresholds_live_in_the_rulebook_not_the_code(rb, cases):
    """Allowing medium-risk auto-approval is a rulebook edit, not a code change."""
    assert assess(cases["C002"], rb, AS_OF)["outcome"] == "ANALYST_REVIEW"
    rb2 = copy.deepcopy(rb)
    rb2["risk_scoring"]["auto_approve_bands"] = ["low", "medium"]
    assert assess(cases["C002"], rb2, AS_OF)["outcome"] == "AUTO_APPROVE"


def test_score_lines_cite_real_clauses(rb, cases):
    clauses = rulebook.policy_clauses(ROOT / rb["meta"]["policy"])
    for c in cases.values():
        for line in assess(c, rb, AS_OF)["risk"]["breakdown"]:
            assert line["policy"] in clauses


def test_impact_analysis_lists_exactly_the_cases_a_change_moves(rb, cases):
    from kyb.impact import impact
    new = copy.deepcopy(rb)
    new["risk_scoring"]["auto_approve_bands"] = ["low", "medium"]
    moved = impact(list(cases.values()), rb, new, AS_OF)
    assert [(m["case_id"], m["from"], m["to"]) for m in moved] == [("C002", "ANALYST_REVIEW", "AUTO_APPROVE")]

import json

import pytest

from conftest import AS_OF, ROOT
from kyb import audit, cli
from kyb.overrides import OverrideError


@pytest.fixture
def run(tmp_path):
    cli.triage(ROOT / "data" / "cases", AS_OF, tmp_path)
    return tmp_path


def lines(p):
    return (p / "audit.jsonl").read_text().splitlines()


def test_chain_verifies(run):
    ok, msg = audit.verify(run / "audit.jsonl")
    assert ok, msg


def test_edited_entry_is_detected(run):
    ls = lines(run)
    e = json.loads(ls[3]); e["payload"]["outcome"] = "AUTO_APPROVE"; ls[3] = json.dumps(e)
    (run / "audit.jsonl").write_text("\n".join(ls) + "\n")
    ok, msg = audit.verify(run / "audit.jsonl")
    assert not ok and "line 4" in msg


def test_deleted_entry_is_detected(run):
    ls = lines(run); del ls[5]
    (run / "audit.jsonl").write_text("\n".join(ls) + "\n")
    assert not audit.verify(run / "audit.jsonl")[0]


def test_reordered_entries_are_detected(run):
    ls = lines(run); ls[1], ls[2] = ls[2], ls[1]
    (run / "audit.jsonl").write_text("\n".join(ls) + "\n")
    assert not audit.verify(run / "audit.jsonl")[0]


def test_analyst_cannot_override_a_rejection(run):
    with pytest.raises(OverrideError, match="only the MLRO"):
        cli.override(run, "C005", "ANALYST_REVIEW", "OVR-03", "Client says it has relocated its operations.", "A. Analyst", "ANALYST",
                     cases_dir=ROOT / "data" / "cases")


@pytest.mark.parametrize("reason,note,by,match", [
    ("OVR-99", "A long enough justification note here.", "A. Analyst", "reason code"),
    ("OVR-03", "too short", "A. Analyst", "at least"),
    ("OVR-03", "A long enough justification note here.", "  ", "name"),
])
def test_override_needs_code_note_and_name(run, reason, note, by, match):
    with pytest.raises(OverrideError, match=match):
        cli.override(run, "C002", "AUTO_APPROVE", reason, note, by, "ANALYST", cases_dir=ROOT / "data" / "cases")


def test_valid_override_is_logged_and_chain_still_verifies(run):
    ov = cli.override(run, "C002", "AUTO_APPROVE", "OVR-03", "Ten-year trading history reviewed; sector rating overstates risk.",
                      "A. Analyst", "ANALYST", cases_dir=ROOT / "data" / "cases")
    assert ov["from"] == "ANALYST_REVIEW"
    assert json.loads(lines(run)[-1])["event"] == "OVERRIDE"
    assert audit.verify(run / "audit.jsonl")[0]
    assert "## Override" in (run / "packs" / "C002.md").read_text()


def test_mlro_can_override_an_escalation(run):
    ov = cli.override(run, "C010", "AUTO_APPROVE", "OVR-02", "Nominee arrangement documented and beneficial owner verified.",
                      "Group MLRO", "MLRO", cases_dir=ROOT / "data" / "cases")
    assert ov["role"] == "MLRO"

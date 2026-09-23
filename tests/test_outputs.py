import json

from conftest import AS_OF, ROOT
from kyb import cli, kpi


def test_triage_writes_every_artefact(tmp_path):
    ds = cli.triage(ROOT / "data" / "cases", AS_OF, tmp_path)
    assert len(ds) == 13
    for f in ("decisions.json", "decisions.csv", "kpi.md", "audit.jsonl"):
        assert (tmp_path / f).exists()
    assert len(list((tmp_path / "packs").glob("*.md"))) == 13


def test_rerun_gives_identical_decisions(tmp_path):
    a = cli.triage(ROOT / "data" / "cases", AS_OF, tmp_path / "a")
    b = cli.triage(ROOT / "data" / "cases", AS_OF, tmp_path / "b")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_kpis_on_demo_data(tmp_path, rb):
    k = kpi.compute(cli.triage(ROOT / "data" / "cases", AS_OF, tmp_path), rb)
    assert (k["alerts"], k["alerts_cleared"], k["alerts_confirmed"], k["alerts_manual"]) == (6, 3, 2, 1)
    assert (k["mlro_cases"], k["mlro_ready"]) == (4, 3)
    assert k["outcomes"]["AUTO_APPROVE"] == 3


def test_outreach_only_for_incomplete_and_never_for_sanctions(tmp_path):
    cli.triage(ROOT / "data" / "cases", AS_OF, tmp_path)
    assert "Client outreach draft" in (tmp_path / "packs" / "C003.md").read_text()
    c007 = (tmp_path / "packs" / "C007.md").read_text()
    assert "Client outreach draft" not in c007 and "Do not contact the client" in c007


def test_mlro_packs_carry_a_sign_off_block(tmp_path):
    cli.triage(ROOT / "data" / "cases", AS_OF, tmp_path)
    assert "MLRO sign-off" in (tmp_path / "packs" / "C004.md").read_text()
    assert "MLRO sign-off" not in (tmp_path / "packs" / "C001.md").read_text()

import pytest

from kyb.screening import CONFIRMED, FALSE_POSITIVE, POTENTIAL, resolve

HELD = {"dob": "1983-08-17", "country": "XA", "subject_type": "individual", "role": "director"}


def hit(score, **record):
    return {"subject": "X", "list": "sanctions", "matched_name": "X", "match_score": score, "list_record": record}


@pytest.mark.parametrize("h,state", [
    (hit(1.0, subject_type="vessel"), FALSE_POSITIVE),                                     # different kind of party
    (hit(1.0, dob="1961-02-02", country="XH", subject_type="individual"), FALSE_POSITIVE),  # two identifiers disagree
    (hit(0.70, country="XH"), FALSE_POSITIVE),                                             # weak name, nothing agrees
    (hit(0.97, dob="1983-08-17", country="XA"), CONFIRMED),                                # strong name, identifiers agree
    (hit(0.90, country="XA"), POTENTIAL),                                                  # agrees, but name too weak
    (hit(0.97, dob="1983-08-17", country="XH"), POTENTIAL),                                # one agrees, one disagrees
    (hit(0.70, country="XA"), POTENTIAL),                                                  # weak name but country agrees
])
def test_clearing_rule(rb, h, state):
    assert resolve(h, HELD, rb["screening"])["state"] == state


def test_screened_name_not_on_application_goes_to_an_analyst(rb):
    r = resolve(hit(1.0, dob="1961-02-02", country="XH"), None, rb["screening"])
    assert r["state"] == POTENTIAL and "not a party" in r["reason"]


def test_clearing_records_the_identifiers_that_disproved_it(rb):
    r = resolve(hit(1.0, dob="1961-02-02", country="XH"), HELD, rb["screening"])
    assert r["mismatches"] == ["dob", "country"] and "dob, country" in r["reason"]

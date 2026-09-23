"""Generates the synthetic applications in data/cases/. Every name, number and
jurisdiction is invented. Re-run to rebuild: python data/make_cases.py"""
import copy
import json
from pathlib import Path

OUT = Path(__file__).parent / "cases"


def base(cid, name, jur, sector, inc, vol, owners, directors, contact):
    return {
        "case_id": cid,
        "submitted_at": "2026-09-23T08:30:00Z",
        "contact": {"name": contact},
        "entity": {"legal_name": name, "registration_number": f"REG-{cid[1:]}-{inc[:4]}",
                   "entity_type": "company", "incorporation_jurisdiction": jur,
                   "operating_jurisdictions": [jur], "incorporated_on": inc, "sector": sector,
                   "expected_monthly_volume_usd": vol},
        "documents": [{"type": "certificate_of_incorporation", "issued_on": inc},
                      {"type": "register_of_directors", "issued_on": "2026-03-15"},
                      {"type": "register_of_shareholders", "issued_on": "2026-03-15"},
                      {"type": "proof_of_address", "issued_on": "2026-08-10"},
                      {"type": "ubo_declaration", "issued_on": "2026-09-01"}],
        "owners": owners, "directors": directors,
        "structure": {"ownership_layers": 1, "bearer_shares": False, "nominee_shareholders": False},
        "screening": [],
    }


def person(name, pct, dob, nat, verified=True):
    return {"name": name, "type": "individual", "ownership_pct": pct, "dob": dob, "nationality": nat, "id_verified": verified}


def director(name, dob, nat):
    return {"name": name, "dob": dob, "nationality": nat}


cases = []

c = base("C001", "Brightline Software Ltd", "XA", "software", "2019-03-01", 120000,
         [person("Maya Collins", 70, "1986-04-12", "XA"), person("Tom Reyes", 30, "1984-11-02", "XA")],
         [director("Maya Collins", "1986-04-12", "XA")], "Maya")
cases.append(c)

c = base("C002", "Harbour Freight Traders Ltd", "XM", "import_export", "2018-06-20", 400000,
         [person("Omar Haddad", 100, "1979-01-30", "XM")], [director("Omar Haddad", "1979-01-30", "XM")], "Omar")
cases.append(c)

c = base("C003", "Kestrel Design Studio Ltd", "XB", "professional_services", "2020-09-14", 60000,
         [person("Priya Nair", 60, "1990-07-21", "XB"), person("Lena Fischer", 40, "1988-02-09", "XB")],
         [director("Priya Nair", "1990-07-21", "XB")], "Priya")
c["documents"] = [d for d in c["documents"] if d["type"] != "proof_of_address"]
for d in c["documents"]:
    if d["type"] == "register_of_directors":
        d["issued_on"] = "2025-06-01"
cases.append(c)

c = base("C004", "Orbit Digital Exchange Ltd", "XH", "crypto_exchange", "2023-02-10", 3000000,
         [person("Marco Bellini", 100, "1982-05-05", "XH")], [director("Marco Bellini", "1982-05-05", "XH")], "Marco")
c["entity"]["operating_jurisdictions"] = ["XH", "XA"]
cases.append(c)

c = base("C005", "Meridian Holdings Ltd", "XP", "import_export", "2017-01-09", 200000,
         [person("Ivan Sokol", 100, "1975-03-19", "XP")], [director("Ivan Sokol", "1975-03-19", "XP")], "Ivan")
cases.append(c)

c = base("C006", "Northgate Analytics Ltd", "XA", "software", "2016-10-03", 180000,
         [person("Daniel Okafor", 100, "1983-08-17", "XA")], [director("Daniel Okafor", "1983-08-17", "XA")], "Daniel")
c["screening"] = [
    {"subject": "Daniel Okafor", "list": "sanctions", "matched_name": "Daniel Okafor", "match_score": 1.0,
     "list_record": {"dob": "1961-02-02", "country": "XH", "subject_type": "individual"}},
    {"subject": "Northgate Analytics Ltd", "list": "adverse_media", "matched_name": "Northgate Analytic Group",
     "match_score": 0.68, "severity": "low", "list_record": {"country": "XJ", "subject_type": "entity"}},
]
cases.append(c)

c = base("C007", "Coastal Metals Trading Ltd", "XC", "precious_metals", "2015-05-11", 900000,
         [person("Viktor Adamescu", 100, "1970-12-01", "XJ")], [director("Viktor Adamescu", "1970-12-01", "XJ")], "Viktor")
c["documents"] = [d for d in c["documents"] if d["type"] != "ubo_declaration"]
c["screening"] = [{"subject": "Viktor Adamescu", "list": "sanctions", "matched_name": "Viktor Adamescu",
                   "match_score": 0.97, "list_record": {"dob": "1970-12-01", "country": "XJ", "subject_type": "individual"}}]
cases.append(c)

c = base("C008", "Aster Payments Ltd", "XB", "money_services", "2020-01-15", 800000,
         [person("Samuel Ortiz", 100, "1981-09-09", "XB")],
         [director("Samuel Ortiz", "1981-09-09", "XB"), director("Helena Varga", "1968-04-04", "XB")], "Samuel")
c["screening"] = [{"subject": "Helena Varga", "list": "pep", "matched_name": "Helena Varga", "match_score": 0.96,
                   "list_record": {"dob": "1968-04-04", "country": "XB", "subject_type": "individual"}}]
cases.append(c)

c = base("C009", "Lumen Retail Co Ltd", "XA", "ecommerce", "2021-11-30", 90000,
         [person("Chloe Martin", 50, "1992-06-06", "XA"), person("Ravi Shah", 30, "1987-10-10", "XA", verified=False)],
         [director("Chloe Martin", "1992-06-06", "XA")], "Chloe")
cases.append(c)

c = base("C010", "Fairwind Ventures Ltd", "XB", "professional_services", "2019-07-07", 150000,
         [person("Grace Liu", 100, "1980-03-03", "XB")], [director("Anders Holm", "1977-08-08", "XB")], "Anders")
c["structure"] = {"ownership_layers": 3, "bearer_shares": False, "nominee_shareholders": True}
cases.append(c)

c = base("C011", "Silverline Gaming Ltd", "XA", "unlicensed_gambling", "2022-04-04", 500000,
         [person("Noah Kent", 100, "1991-01-01", "XA")], [director("Noah Kent", "1991-01-01", "XA")], "Noah")
cases.append(c)

c = base("C012", "Pinecrest Components Ltd", "XA", "manufacturing", "2012-02-20", 220000,
         [person("Arjun Mehta", 100, "1978-05-25", "XA")], [director("Arjun Mehta", "1978-05-25", "XA")], "Arjun")
c["screening"] = [{"subject": "Arjun Mehta", "list": "sanctions", "matched_name": "Arjun Mehra", "match_score": 0.90,
                   "list_record": {"country": "XA", "subject_type": "individual"}}]
cases.append(c)

c = base("C013", "Tidewater Labs Ltd", "XA", "software", "2026-04-02", 50000,
         [person("Ella Brooks", 100, "1995-12-12", "XA")], [director("Ella Brooks", "1995-12-12", "XA")], "Ella")
c["screening"] = [{"subject": "Ella Brooks", "list": "sanctions", "matched_name": "ELLA BROOKS (vessel)", "match_score": 1.0,
                   "list_record": {"country": "XP", "subject_type": "vessel"}}]
cases.append(c)

OUT.mkdir(exist_ok=True)
for c in cases:
    (OUT / f"{c['case_id']}.json").write_text(json.dumps(c, indent=2) + "\n")
print(f"wrote {len(cases)} cases")

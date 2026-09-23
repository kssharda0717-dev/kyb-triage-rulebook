"""Command line.

  python -m kyb triage   --cases data/cases --as-of 2026-09-23T10:00:00Z --out output
  python -m kyb override --out output --case C002 --to AUTO_APPROVE --reason OVR-03 --note "..." --by "A. Analyst"
  python -m kyb verify   --log output/audit.jsonl
  python -m kyb render
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import audit, evidence, kpi, rulebook
from .engine import CaseError, assess, parse_when
from .overrides import OverrideError, check_override
from .render import render


def load_cases(folder: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(folder).glob("*.json"))]


def triage(cases_dir, as_of, out, rb_path=rulebook.DEFAULT_PATH) -> list[dict]:
    rb = rulebook.load(rb_path)
    out = Path(out)
    (out / "packs").mkdir(parents=True, exist_ok=True)
    log = out / "audit.jsonl"
    at = parse_when(as_of).isoformat()
    decisions, refused = [], []
    for case in load_cases(cases_dir):
        try:
            d = assess(case, rb, as_of)
        except CaseError as e:
            refused.append(str(e))
            audit.append(log, "REFUSED", case.get("case_id", "?"), at, {"error": str(e)})
            continue
        decisions.append(d)
        (out / "packs" / f"{d['case_id']}.md").write_text(evidence.pack(d, case, rb), encoding="utf-8")
        audit.append(log, "DECISION", d["case_id"], at, audit.decision_payload(d))

    (out / "decisions.json").write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    with (out / "decisions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "legal_name", "outcome", "risk_score", "risk_band", "deciding_rules",
                    "owner", "due_by", "decision_ready", "open_items"])
        for d in decisions:
            w.writerow([d["case_id"], d["legal_name"], d["outcome"], d["risk"]["score"], d["risk"]["band"],
                        " ".join(d["deciding_rules"]), d["owner"], d["due_by"], d["decision_ready"], len(d["open_items"])])
    (out / "kpi.md").write_text(kpi.report(kpi.compute(decisions, rb), rb), encoding="utf-8")
    for r in refused:
        print("REFUSED", r, file=sys.stderr)
    return decisions


def override(out, case_id, to, reason, note, by, role, cases_dir="data/cases", rb_path=rulebook.DEFAULT_PATH) -> dict:
    rb = rulebook.load(rb_path)
    out = Path(out)
    decisions = {d["case_id"]: d for d in json.loads((out / "decisions.json").read_text(encoding="utf-8"))}
    if case_id not in decisions:
        raise OverrideError(f"no decision for {case_id} in {out}")
    d = decisions[case_id]
    ov = check_override(d, rb, to, reason, note, by, role)
    audit.append(out / "audit.jsonl", "OVERRIDE", case_id, datetime.now(timezone.utc).isoformat(), ov)
    case = next(c for c in load_cases(cases_dir) if c["case_id"] == case_id)
    (out / "packs" / f"{case_id}.md").write_text(evidence.pack(d, case, rb, override=ov), encoding="utf-8")
    return ov


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="kyb")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("triage")
    t.add_argument("--cases", default="data/cases")
    t.add_argument("--as-of", required=True, help="assessment date-time, e.g. 2026-09-23T10:00:00Z")
    t.add_argument("--out", default="output")
    o = sub.add_parser("override")
    for a in ("--out", "--case", "--to", "--reason", "--note", "--by"):
        o.add_argument(a, required=a != "--out", default="output" if a == "--out" else None)
    o.add_argument("--role", default="ANALYST", choices=["ANALYST", "MLRO"])
    v = sub.add_parser("verify")
    v.add_argument("--log", default="output/audit.jsonl")
    sub.add_parser("render")
    args = p.parse_args(argv)

    try:
        if args.cmd == "triage":
            ds = triage(args.cases, args.as_of, args.out)
            for d in ds:
                print(f"{d['case_id']}  {d['outcome']:<16} {d['risk']['band']:<7} {' '.join(d['deciding_rules'])}")
            print(f"\n{len(ds)} decisions → {args.out}/  (packs, decisions.csv, kpi.md, audit.jsonl)")
        elif args.cmd == "override":
            ov = override(args.out, args.case, args.to, args.reason, args.note, args.by, args.role)
            print(f"{args.case}: {ov['from']} → {ov['to']} ({ov['reason_code']}) logged")
        elif args.cmd == "verify":
            ok, msg = audit.verify(Path(args.log))
            print(("OK  " if ok else "FAIL  ") + msg)
            return 0 if ok else 1
        elif args.cmd == "render":
            rb = rulebook.load()
            path = rulebook.ROOT / "rulebook" / "RULEBOOK.md"
            path.write_text(render(rb), encoding="utf-8")
            print(f"wrote {path.relative_to(rulebook.ROOT)}")
    except (OverrideError, rulebook.RulebookError) as e:
        print(e, file=sys.stderr)
        return 2
    return 0

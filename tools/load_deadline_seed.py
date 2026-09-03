#!/usr/bin/env python
"""Load SAIRNlaw deadline seed/calendar JSON into the live engine.

Every jurisdiction so far was loaded by hand, one POST at a time, and the load
step is where two real defects have already surfaced that no code-only check
caught: the California rows were rejected by the endpoint validator after the
ENGINE had learned the per-method service amount and the validator had not, and
a holiday entry filed under the wrong year would have been stored happily and
then been unreachable. Both were found by a real load. This script exists so
that load is one repeatable command instead of a hand-assembled curl loop.

BOTH ENDPOINT WRITES ARE UPSERTS -- add_rule keys on rule_id, add_holidays on
"<jurisdiction>:<year>" -- so re-running is idempotent and safe. It is not a
migration and it does not delete anything; a rule removed from the seed file is
NOT removed from the store by running this.

CALENDARS GO FIRST, DELIBERATELY. A rule with no calendar refuses
NOT_PROVISIONED, which is the safe direction, but a half-loaded jurisdiction
that can compute some dates and not others is harder to reason about than one
that refuses everything. Loading calendars first means the window where a rule
exists without its calendar is as short as possible.

PUSH AND WAIT FOR THE DEPLOY BEFORE LOADING A JURISDICTION THAT NEEDS A NEW
COMPUTATION STANDARD. Standards live in api/_lib/deadline-engine.js and are
validated server-side, so loading North Carolina against a deployment that
predated nc_rcp_6a rejected all 13 rules with "computation must be one of..."
while both calendars loaded fine -- a half-loaded jurisdiction, and exactly the
window the paragraph above is about. It failed safe (the rules simply were not
stored) and re-running after the deploy fixed it, because these are upserts.

NEVER PROBE A DEPLOYMENT WITH A WRITE ENDPOINT. Checking whether a standard had
deployed by POSTing a dummy add_rule stored the dummy: a junk `zz` / `__probe__`
row is now in the live store and this endpoint implements no delete. Probe with
rules_status (read-only), or with a compute you expect to refuse.

Usage:
    set SAIRNLAW_LICENSE_KEY=...            (or export, or pass --key)
    python tools/load_deadline_seed.py westvirginia
    python tools/load_deadline_seed.py westvirginia --dry-run
    python tools/load_deadline_seed.py --file sql/sairnlaw_deadline_seed_texas.json

A name argument is resolved against sql/sairnlaw_deadline_{seed,calendars}_<name>.json
and it is an error if neither exists -- a typo must not look like a clean run.
"""

import argparse
import glob
import json
import os
import sys
import urllib.error
import urllib.request
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import sairn_http  # noqa: E402  -- browser-shaped fetch; see that module


DEFAULT_ENDPOINT = "https://sairn.vercel.app/api/legal-deadlines"
SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")


def post(endpoint, key, payload, timeout=30):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=body, method="POST",
        headers=sairn_http.with_browser_ua(
            {"Content-Type": "application/json", "Authorization": "Bearer " + key}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # A Vercel bot-mitigation challenge is NOT an answer from the app, and a
        # gate that parses it as one reports "could not tell" when the truth is
        # "was blocked". CLAUDE.md already says could-not-tell is not a pass;
        # this makes the two distinguishable instead of identical.
        sairn_http.raise_if_challenge(e)
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:400]}
    except urllib.error.URLError as e:
        return 0, {"error": {"message": "connection failed: %s" % e.reason}}


def load_files(names, explicit):
    """Returns (calendars, rules) as lists of payload objects, with provenance."""
    paths = list(explicit)
    for name in names:
        found = []
        for kind in ("calendars", "seed"):
            p = os.path.join(SQL_DIR, "sairnlaw_deadline_%s_%s.json" % (kind, name))
            if os.path.exists(p):
                found.append(p)
        if not found:
            # Fail loudly. A misspelled jurisdiction that silently loaded
            # nothing would report a clean run having done nothing at all.
            avail = sorted({
                os.path.basename(f).replace("sairnlaw_deadline_seed_", "").replace(".json", "")
                for f in glob.glob(os.path.join(SQL_DIR, "sairnlaw_deadline_seed_*.json"))})
            raise SystemExit(
                "No seed or calendar file for '%s'.\nAvailable: %s" % (name, ", ".join(avail)))
        paths.extend(found)

    calendars, rules = [], []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            doc = json.load(f)
        for c in doc.get("holiday_calendars", []):
            calendars.append((p, c))
        for r in doc.get("rules", []):
            rules.append((p, r))
    return calendars, rules


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", nargs="*", help="jurisdiction file suffix, e.g. westvirginia")
    ap.add_argument("--file", action="append", default=[], help="explicit JSON path (repeatable)")
    ap.add_argument("--key", default=os.environ.get("SAIRNLAW_LICENSE_KEY", ""),
                    help="SAIRNlaw license key (default: $SAIRNLAW_LICENSE_KEY)")
    ap.add_argument("--endpoint", default=os.environ.get("SAIRNLAW_DEADLINES_API", DEFAULT_ENDPOINT))
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and report what would be sent; makes no network call")
    args = ap.parse_args()

    if not args.name and not args.file:
        ap.error("give a jurisdiction name or --file")

    calendars, rules = load_files(args.name, args.file)
    print("Parsed %d calendar entries and %d rules from %d file(s)."
          % (len(calendars), len(rules),
             len({p for p, _ in calendars} | {p for p, _ in rules})))

    if args.dry_run:
        for _, c in calendars:
            print("  CAL  %s %s (%d dates)" % (c.get("jurisdiction"), c.get("year"), len(c.get("dates", []))))
        for _, r in rules:
            print("  RULE %s" % r.get("rule_id"))
        print("Dry run: nothing sent.")
        return 0

    if not args.key:
        raise SystemExit(
            "No license key. Set SAIRNLAW_LICENSE_KEY or pass --key.\n"
            "Rules and calendars are stored PER LICENSE, so the key decides which\n"
            "tenant this lands in -- it is not a formality and must not be guessed.")

    failures = []

    for src, cal in calendars:
        st, res = post(args.endpoint, args.key, {"action": "add_holidays", "calendar": cal})
        tag = "%s:%s" % (cal.get("jurisdiction"), cal.get("year"))
        if st == 200 and res.get("ok"):
            print("  ok   CAL  %-12s %d dates" % (tag, res.get("count", 0)))
        else:
            msg = (res.get("message") or (res.get("error") or {}).get("message") or json.dumps(res))[:300]
            print("  FAIL CAL  %-12s HTTP %s  %s" % (tag, st, msg))
            failures.append(("calendar", tag, src, st, msg))

    for src, rule in rules:
        st, res = post(args.endpoint, args.key, {"action": "add_rule", "rule": rule})
        rid = rule.get("rule_id")
        if st == 200 and res.get("ok"):
            print("  ok   RULE %s" % rid)
        else:
            msg = (res.get("message") or (res.get("error") or {}).get("message") or json.dumps(res))[:300]
            print("  FAIL RULE %s  HTTP %s  %s" % (rid, st, msg))
            failures.append(("rule", rid, src, st, msg))

    # Read back what is actually stored. A load that reports success per row and
    # is never re-read is a claim, not a verification.
    st, res = post(args.endpoint, args.key, {"action": "rules_status"})
    if st == 200:
        rows = res.get("jurisdictions") or res.get("coverage") or res
        print("\nrules_status (live):")
        print(json.dumps(rows, indent=1)[:4000])
    else:
        print("\nrules_status returned HTTP %s: %s" % (st, json.dumps(res)[:300]))

    if failures:
        print("\n%d FAILED:" % len(failures))
        for kind, ident, src, st, msg in failures:
            print("  %s %s (%s) HTTP %s: %s" % (kind, ident, os.path.basename(src), st, msg))
        return 1
    print("\nAll %d calendars and %d rules loaded." % (len(calendars), len(rules)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

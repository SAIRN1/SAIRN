#!/usr/bin/env python
"""Is what a SAIRNlaw licence ACTUALLY holds what the seed files say it should?

WHY THIS EXISTS. On 2026-08-27 two committed corrections -- e1aa3f8 (FRCP 6(d)
does not reach Rule 4) and a9daad1 (Florida exclusivity) -- changed seed FILES.
A seed-file change is inert until tools/load_deadline_seed.py runs, and nobody
ran it. LAW-PINNACLE-2026, the canonical customer licence, went on computing
federal answer deadlines THREE DAYS LATE for a day, and it was found by accident
while chasing an unrelated false positive.

NOTHING ON THE PLATFORM COULD HAVE FOUND IT ON PURPOSE:

  - The push protocol live-verifies deployed CODE. Rule DATA has no such step,
    and this defect lived entirely in data.
  - `rules_status` reports COUNTS per jurisdiction. A stale rule and a corrected
    rule count exactly the same, so the counts were right the whole time.
  - The `version` field is the half-built detector. Every row carries it, every
    SAIRNlaw seed row is version 1, and e1aa3f8 -- which removed a three-day
    extension and therefore CHANGED A LEGAL DEADLINE -- left version at 1. A
    stale row and a corrected row are byte-distinguishable and not
    version-distinguishable.

So this compares BYTES, via a content hash, and treats `version` as a declared
intent to be reported rather than a signal to be trusted. Where a row is stale
AND its version matches the seed's, that is called out separately: it is the
version discipline failing, and it is the reason a hash had to exist at all.

WHAT IT REPORTS, per licence:
  MISSING  in the seed files, absent from the licence   -> never loaded
  STALE    present on both, content differs             -> loaded, then the seed
                                                          was corrected and not
                                                          reloaded. THIS is the
                                                          2026-08-27 defect.
  EXTRA    on the licence, absent from the seed files   -> loaded from something
                                                          that is not in the
                                                          repo, or a probe row
                                                          (see the loader's own
                                                          warning about `zz` /
                                                          `__probe__`)

READ-ONLY. It calls `rules_fingerprint` and nothing else. It cannot write a
rule, and it deliberately does not offer to fix what it finds -- reloading a
customer licence is a decision with a person's name on it, not a side effect of
running a check.

WHAT IT STILL CANNOT DO, stated in the words of the DB-side gate this replaced:
tell you a reload RAN. It reports what a licence HOLDS versus what the seeds
SAY. That is the question that matters, but it is not the same question.

── CONSOLIDATED 2026-08-29, one gate not two ────────────────────────────────
Two load-state gates were built the same night by two sessions working in
parallel: this one, and a generated SQL gate (tools/sairnlaw_build_load_gate.py
+ sql/sairnlaw_load_gate_generated.sql, commit ca83d1f). Two checks answering
one question is how they drift apart and how people stop believing either, so
the SQL pair was removed and this is canonical. The reasoning, recorded because
the deleted one was good work and the tradeoff was not one-sided:

  WHY THIS ONE. It needs only a licence key, so it runs from any clone and can
  gate a pre-push step; the SQL gate needed Supabase editor access. It reads the
  seeds at run time, so it cannot go stale; the SQL gate had to be REGENERATED
  after every seed change, and a forgotten regeneration is silently the same
  failure class the gate exists to catch. It covers holiday CALENDARS as well
  as rules -- the SQL gate globbed seed_*.json only, and would have missed the
  five doubly-defined 2027 calendars found on 2026-08-29. It reports MISSING and
  EXTRA, not just STALE. And it checks the live API path, which is what the app
  actually serves from.

  WHAT THE OTHER ONE HAD THAT THIS DOES NOT. Postgres compares jsonb
  canonically, so it never had to make two languages agree on a digest. That
  risk here is real and was closed by proof rather than by care: the JS and
  Python implementations were run against all 401 seed entries and agreed on
  401/401.

  A DEFECT IN THE DELETED GATE, worth keeping so it is not reintroduced: its
  INERT_KEYS listed `computation` as unable to change a computed date. It
  selects the counting standard -- frcp_6a vs fl_rgpja_2514 vs ok_12_2006 --
  and changing it changes the date. A rule whose computation standard drifted
  would have passed that gate clean. This one compares the whole blob minus a
  single field, which is subtractive selection taken to its limit and is the
  one design idea from the deleted gate worth restating: never hand-pick the
  fields that matter, because that list goes stale silently.

Exit codes, so this can gate rather than merely inform:
  0  the licence matches the seed files
  1  drift found (missing, stale or extra)
  2  could not tell (endpoint unreachable, licence rejected, not provisioned)

Usage:
    set SAIRNLAW_LICENSE_KEY=LAW-PINNACLE-2026
    python tools/deadline_load_state_check.py
    python tools/deadline_load_state_check.py --key LAW-TEST-2026
    python tools/deadline_load_state_check.py --key LAW-TEST-2026 --expect-stale

--expect-stale is for licences that are KNOWN to be behind on purpose --
LAW-TEST-2026 is an internal verification tenant deliberately frozen when
LAW-PINNACLE-2026 became canonical on 2026-08-25. It reports the drift exactly
the same way and exits 0, so a known-stale tenant does not train anyone to
ignore a red result.
"""

import argparse
import glob
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_ENDPOINT = "https://sairn.vercel.app/api/legal-deadlines"
SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")


def stable_json(v):
    """Byte-identical to stableJson() in api/legal-deadlines.js.

    ensure_ascii=False matters: JSON.stringify leaves non-ASCII raw, and these
    seeds are full of em-dashes and typographic quotes. Escaping them here
    would make every rule containing one read as drifted.
    """
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(data):
    """Same digest as contentHash() server-side: sha256/16 with
    authority.verified_by removed. That field records HOW a licence was loaded
    (employee session vs bearer-key loader), not what the rule says."""
    d = dict(data)
    a = d.get("authority")
    if isinstance(a, dict):
        a = dict(a)
        a.pop("verified_by", None)
        d["authority"] = a
    return hashlib.sha256(stable_json(d).encode("utf-8")).hexdigest()[:16]


def seed_expectations():
    """What the repo says each licence should hold, with the SAME two server-side
    transforms add_rule applies -- version defaulting to 1, and the authority
    object rebuilt. Anything else here would be comparing the seed to itself.

    EVERY sairnlaw_deadline_*.json IS SCANNED FOR BOTH KEYS, not seed_* for
    rules and calendars_* for calendars. Five 2027 calendars really do live
    inside seed_* files (in, mi, oh, pa, us-federal), and a check that trusted
    the filename would have declared them MISSING on a licence that holds them
    correctly -- a false alarm, which is how a check gets ignored.

    Conflicts are RETURNED, not resolved. Where two files define the same
    entry_id with different content, the loader stores whichever it sent last,
    so there is no fact of the matter about what "correct" is until a person
    decides. Silently picking one would let this check report a confident
    verdict on an ambiguous question.

    A seed file carrying a top-level `_hold_reason` is DELIBERATELY not loaded
    (Connecticut, whose first-day convention is unsourced -- loading it would
    compute one day LATE). Its entries are held out of the comparison and
    listed separately. Without this the check would report the same MISSING row
    on every licence forever, and a check that is always red is a check nobody
    reads. The loader ignores the key, so intent is recorded without changing
    what a load actually does."""
    rules, cals, conflicts, held = {}, {}, [], []

    def put(bucket, entry, record):
        prev = bucket.get(entry)
        if prev is not None and prev["hash"] != record["hash"]:
            conflicts.append((entry, prev["source"], prev["hash"],
                              record["source"], record["hash"]))
        bucket[entry] = record

    for path in sorted(glob.glob(os.path.join(SQL_DIR, "sairnlaw_deadline_*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        src = os.path.basename(path)
        if doc.get("_hold_reason"):
            for r in doc.get("rules", []):
                held.append(("rule", r["rule_id"], src, doc["_hold_reason"]))
            for c in doc.get("holiday_calendars", []):
                held.append(("calendar", "%s:%s" % (c.get("jurisdiction"), c.get("year")),
                             src, doc["_hold_reason"]))
            continue
        for r in doc.get("rules", []):
            stored = dict(r)
            stored["version"] = r.get("version") or 1
            put(rules, r["rule_id"], {
                "hash": content_hash(stored),
                "version": stored["version"],
                "jurisdiction": r.get("jurisdiction"),
                "source": src,
            })
        for c in doc.get("holiday_calendars", []):
            put(cals, "%s:%s" % (c.get("jurisdiction"), c.get("year")), {
                "hash": content_hash(dict(c)),
                "version": None,
                "jurisdiction": c.get("jurisdiction"),
                "source": src,
            })
    return rules, cals, conflicts, held


def fetch(endpoint, key):
    body = json.dumps({"action": "rules_fingerprint"}).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:400]}
    except urllib.error.URLError as e:
        return 0, {"error": {"message": "connection failed: %s" % e.reason}}


def compare(label, expected, live_rows):
    live = {row["entry_id"]: row for row in live_rows}
    missing, stale, extra, version_silent = [], [], [], []

    for entry, exp in sorted(expected.items()):
        got = live.get(entry)
        if got is None:
            missing.append((entry, exp))
        elif got["hash"] != exp["hash"]:
            stale.append((entry, exp, got))
            # The point of the whole exercise: the row changed and the field
            # meant to record that it changed did not move.
            if exp["version"] is not None and got.get("version") == exp["version"]:
                version_silent.append(entry)

    for entry in sorted(live):
        if entry not in expected:
            extra.append((entry, live[entry]))

    print("\n== %s" % label)
    print("   seed expects %d  |  licence holds %d" % (len(expected), len(live)))
    print("   MISSING %-4d STALE %-4d EXTRA %-4d" % (len(missing), len(stale), len(extra)))

    if missing:
        by_jur = {}
        for entry, exp in missing:
            by_jur.setdefault(exp["jurisdiction"], []).append(entry)
        print("\n   MISSING -- in the seed files, never loaded to this licence:")
        for jur in sorted(by_jur):
            ids = by_jur[jur]
            print("     %-12s %d: %s" % (jur, len(ids), ", ".join(ids[:4]) + (" ..." if len(ids) > 4 else "")))

    if stale:
        print("\n   STALE -- loaded, then the seed changed and was not reloaded:")
        for entry, exp, got in stale:
            print("     %-58s seed %s != live %s  (%s)"
                  % (entry, exp["hash"], got["hash"], exp["source"]))

    if extra:
        print("\n   EXTRA -- on the licence, not in any seed file:")
        for entry, got in extra:
            print("     %-58s live %s" % (entry, got["hash"]))

    if version_silent:
        print("\n   !! VERSION DID NOT MOVE on %d stale row(s): %s"
              % (len(version_silent), ", ".join(version_silent[:6])
                 + (" ..." if len(version_silent) > 6 else "")))
        print("     The seed and the live row disagree about content while agreeing")
        print("     about `version`. Nothing that reads `version` could see this.")
        print("     Bump `version` on any seed edit that changes a computed date.")

    return len(missing), len(stale), len(extra)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", default=os.environ.get("SAIRNLAW_LICENSE_KEY", ""),
                    help="SAIRNlaw license key (default: $SAIRNLAW_LICENSE_KEY)")
    ap.add_argument("--endpoint", default=os.environ.get("SAIRNLAW_DEADLINES_API", DEFAULT_ENDPOINT))
    ap.add_argument("--expect-stale", action="store_true",
                    help="licence is knowingly behind (e.g. LAW-TEST-2026); report drift but exit 0")
    args = ap.parse_args()

    if not args.key:
        raise SystemExit(
            "No license key. Set SAIRNLAW_LICENSE_KEY or pass --key.\n"
            "Rules are stored PER LICENSE, so the key decides which tenant is\n"
            "being checked -- it is not a formality and must not be guessed.")

    exp_rules, exp_cals, conflicts, held = seed_expectations()
    print("Seed files: %d rules, %d calendars" % (len(exp_rules), len(exp_cals)))
    print("Licence   : %s" % args.key)

    if held:
        print("\nHELD -- in the repo, deliberately not loaded (_hold_reason):")
        for kind, entry, src, reason in held:
            print("   %-9s %-46s %s" % (kind, entry, src))
            print("             %s" % reason[:150])
        print("   Not counted as drift. If one of these turns up ON a licence,")
        print("   it shows below as EXTRA, which is the direction that matters.")

    if conflicts:
        print("\n!! THE SEED FILES DISAGREE WITH THEMSELVES -- %d entr(ies) are defined"
              % len(conflicts))
        print("  twice, with different content. The loader stores whichever it sent")
        print("  LAST, so what a licence holds depends on file order, not on intent:")
        for entry, f1, h1, f2, h2 in conflicts:
            print("     %-18s %s (%s)" % (entry, f1, h1))
            print("     %-18s %s (%s)" % ("", f2, h2))
        print("  WHICH ONE LANDS depends on the order the loader is given its files")
        print("  -- a jurisdiction name, or the order of --file arguments -- not on")
        print("  anything recorded in the repo. Below, the second is treated as")
        print("  expected purely so the comparison has a reference; that is NOT a")
        print("  judgement about which is correct. Resolve it in the seed files.")

    st, res = fetch(args.endpoint, args.key)
    if st != 200 or not res.get("ok"):
        msg = (res.get("message") or (res.get("error") or {}).get("message")
               or json.dumps(res))[:300]
        print("\nCOULD NOT TELL -- rules_fingerprint returned HTTP %s: %s" % (st, msg))
        print("This is NOT a pass. Nothing was compared.")
        return 2

    m1, s1, e1 = compare("law_deadline_rules", exp_rules, res.get("law_deadline_rules", []))
    m2, s2, e2 = compare("law_holidays", exp_cals, res.get("law_holidays", []))
    drift = m1 + s1 + e1 + m2 + s2 + e2

    print("\n" + "-" * 72)
    if not drift:
        print("MATCHES THE SEED FILES. Nothing to reload.")
        return 0

    if args.expect_stale:
        print("DRIFT: %d entr(ies) -- reported, and accepted because --expect-stale" % drift)
        print("was passed. Use this ONLY for a licence that is behind on purpose.")
        return 0

    print("DRIFT: %d entr(ies). THIS LICENCE NEEDS A RELOAD." % drift)
    print("  python tools/load_deadline_seed.py <jurisdiction>   (upsert, idempotent)")
    print("Then re-run this check, and verify the affected deadlines by a CHANGED")
    print("COMPUTE on identical inputs -- the loader's exit code is not evidence.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

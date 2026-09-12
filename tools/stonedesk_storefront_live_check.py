"""Did sql/stonedesk_public_surface_schema.sql actually get run?

WHY THIS EXISTS. docs/SAIRN-OPEN-WORK-INDEX.md's StoneDesk storefront row ends
with an instruction: "Confirm by re-probing the two endpoints after the run, not
by the editor reporting success." That instruction depends on somebody
remembering it, and on them reading the answer correctly -- which is the harder
half, see below. This is that instruction, mechanised.

It is READ-ONLY against the product in the sense that matters: every request is
a public GET-shaped POST with a slug that cannot exist and a token that cannot
match, so nothing is created and no real record is touched. The rate limiter
does increment its own counter row, which is the one write, and that row expires
with its window.

── THE PART THAT IS EASY TO GET WRONG, AND THE REASON THIS IS A TOOL ────────
Three unauthenticated probes CANNOT prove all five tables exist. Traced through
the handlers rather than assumed:

  sd_public_rate_limits  PROVEN by any answer that is not 503 UNAVAILABLE.
                         checkAndIncrementRateLimit() fails CLOSED on an
                         unreadable or unwritable counter, so getting past it
                         means the table was both read and written.
  sd_public_shop         PROVEN by catalog answering 404 NOT_FOUND.
                         resolveShopSlug() THROWS on a non-ok lookup and the
                         handler turns that into 502 -- so a 404 means the query
                         genuinely ran and genuinely matched nothing.
  sd_order_links         PROVEN by track/view answering 404 NOT_FOUND.
                         503 NOT_PROVISIONED is that handler's own name for a
                         PostgREST 404/400 on this table.

  sd_quote_requests      NOT REACHED. quote_request stops at the slug lookup,
  sd_customers           NOT REACHED. track/view stops at the link lookup.

So a clean run here is "three of five, live" -- NOT "the migration is done".
Reporting the three as if they were five is exactly the confident-wrong-answer
shape this platform keeps finding, so the tool prints the gap on every run,
including a passing one, and names what closes it: re-capture the snapshot and
re-run tools/schema_snapshot_freshness.py, which sees all five.

A CHALLENGE IS NOT A PASS. tools/sairn_http.py raises Challenged rather than
letting Vercel's bot mitigation look like an answer; this exits 2 and says
UNVERIFIED, because a check that stopped checking without saying so is worse
than no check (see that module's header, and the post-push watcher that
swallowed a 403).

Usage:
    python tools/stonedesk_storefront_live_check.py
    python tools/stonedesk_storefront_live_check.py --base https://sairn.vercel.app

Exit codes: 0 = the three reachable tables are live; 1 = not provisioned;
2 = could not tell (challenged or unreachable) -- which is not a pass.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sairn_http as H  # noqa: E402

BASE = "https://sairn.vercel.app"

# A slug that cannot belong to a real shop, and a token of the right shape that
# cannot match a real link. Both are deliberately well-formed: a malformed one
# would be rejected by input validation before reaching the database, which
# would make the probe answer without touching the table it is asking about.
DEAD_SLUG = "sairn-storefront-liveness-probe-no-such-shop"
DEAD_TOKEN = "0" * 64


def probe(base, path, payload):
    return H.fetch_json(base + path, payload=payload)


def code_of(body):
    try:
        return str(body.get("error", {}).get("code", ""))
    except AttributeError:
        return ""


def main(argv):
    base = BASE
    if "--base" in argv:
        base = argv[argv.index("--base") + 1].rstrip("/")

    try:
        cat = probe(base, "/api/stonedesk-public",
                    {"action": "catalog", "slug": DEAD_SLUG})
        trk = probe(base, "/api/stonedesk-track",
                    {"action": "view", "token": DEAD_TOKEN})
    except H.Challenged as e:
        print("UNVERIFIED -- Vercel returned a bot challenge, so nothing was")
        print("measured. This is NOT a pass. Detail: %s" % e)
        return 2
    except Exception as e:  # noqa: BLE001 -- an unreachable host is also not a pass
        print("UNVERIFIED -- could not reach %s. This is NOT a pass." % base)
        print("  %r" % (e,))
        return 2

    print("StoneDesk public storefront -- live provisioning check against %s" % base)
    print("  POST /api/stonedesk-public {catalog}  -> HTTP %s %s"
          % (cat.status, code_of(cat.body)))
    print("  POST /api/stonedesk-track  {view}     -> HTTP %s %s"
          % (trk.status, code_of(trk.body)))
    print("")

    limits_live = not (cat.status == 503 and code_of(cat.body) == "UNAVAILABLE")
    links_live = not (trk.status == 503 and code_of(trk.body) == "NOT_PROVISIONED")

    # THREE STATES, NOT TWO, AND THE THIRD IS THE WHOLE POINT. The limiter runs
    # BEFORE the slug lookup and fails closed, so when it is down the catalog
    # probe never asks about sd_public_shop at all. Printing that as ABSENT
    # would be a not-asked reported as a measured absence -- the same shape as a
    # failed read rendered as an empty list, which is the defect this endpoint
    # was fixed for on 2026-09-04. sd_order_links has no such dependency: the
    # track probe reaches it directly, so its answer is always measured.
    if not limits_live:
        shop = ("NOT ASKED", "the limiter refused first, so the slug lookup never ran")
    elif cat.status == 404 and code_of(cat.body) == "NOT_FOUND":
        shop = ("LIVE", "404 NOT_FOUND means the slug lookup ran; a dead table throws and 502s")
    else:
        shop = ("ABSENT", "the lookup was reached and did not answer 404 -- HTTP %s %s"
                % (cat.status, code_of(cat.body)))

    verdict = [
        ("sd_public_rate_limits", "LIVE" if limits_live else "ABSENT",
         "the limiter fails closed, so getting past it means read AND write worked"),
        ("sd_public_shop", shop[0], shop[1]),
        ("sd_order_links", "LIVE" if links_live else "ABSENT",
         "503 NOT_PROVISIONED is this handler's own name for a 404/400 on the table"),
    ]
    for name, state, why in verdict:
        print("  %-24s %-9s %s" % (name, state, why))

    print("")
    print("  NOT REACHED BY ANY UNAUTHENTICATED PROBE, and therefore NOT CHECKED:")
    print("    sd_quote_requests   -- quote_request stops at the slug lookup")
    print("    sd_customers        -- track/view stops at the link lookup")
    print("  To settle all five: re-run sql/schema_snapshot_query.sql in the")
    print("  Supabase editor, SAVE the JSON as db/schema_snapshot.json, commit it,")
    print("  then run  python tools/schema_snapshot_freshness.py")

    # NOT ASKED counts as not-confirmed, deliberately. Only a measured LIVE
    # passes -- an unmeasured table must never be able to produce a zero exit.
    if all(state == "LIVE" for _, state, _ in verdict):
        print("")
        print("THREE OF FIVE CONFIRMED LIVE. That is not the whole migration.")
        return 0
    print("")
    print("NOT PROVISIONED -- run sql/stonedesk_public_surface_schema.sql in the")
    print("Supabase SQL editor. It is additive and idempotent.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

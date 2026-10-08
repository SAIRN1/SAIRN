# cody — handoff, 2026-10-07c (batch 25 / b2)

**Claim:** `cody / Tooling`, batch 25, taken at HEAD `b3ce8f23`.
**Written per item and committed per item**, as item 2 of batch 24 set the habit.
Every premise below was re-derived **at pickup** from `sairn_claim.py` (the
registry) and from `origin/main` — never from a claim-file read alone.

`sairn-guardian-v2` was **not loaded**: no item in this batch edits an app file.

---

## item 1 — BLOCKED. The holder is **cc**. 6 eligible, 0 discharged.

```
command : python tools/sairn_claim.py check Tooling "tier a review discharge docs/tier-a-reviews.json most overdue"
commit  : b3ce8f23        date: 2026-10-08
result  : EXIT 1 -- BLOCKED
```

```
session  : cc
claimed  : 2026-10-07T23:20:05Z  (0.7h ago)
declares : docs/tier-a-reviews.json  -- IN ITS FILES SEGMENT, not merely in prose
its own item 1 : "Tier A: my own most-overdue eligible first, freshness-checked
                  before each verdict" -- the identical discharge
```

**hank's claim was also checked, as the item asks.** `platform`, last activity
**8.0h ago** — past the 4h expiry, so **not live**; its Tier A text says its own
18 eligible were listed and not discharged. So hank is **not** the blocker; cc is.

**My 6 eligible, re-derived at `aa2f014d` on 2026-10-08** (22 open in the ledger;
authored by another session **and** `reviewer_owner == cody`):

| age | author | opened | resources |
|---|---|---|---|
| 57.1h | fourth | 2026-10-05T15:02:28Z | `quotes` |
| 50.7h | fourth | 2026-10-05T21:25:19Z | `alf_activities, alf_billing, alf_claim_routes, …` |
| 41.9h | hank | 2026-10-06T06:14:34Z | `alf_clients, alf_family_contacts, alf_mar` |
| 41.9h | cc | 2026-10-06T06:18:11Z | `quotes, sb_ap` |
| 40.7h | hank | 2026-10-06T07:29:58Z | `sdn_projects` |
| 40.2h | hank | 2026-10-06T07:56:17Z | `sen_settings` |

A further **9** are open, owned elsewhere and past the 48h takeover line. None
taken, for the same reason.

**No freshness check was run against any of the six**, because a freshness check
is the first step of a discharge and the discharge is blocked. Running the checks
and then not writing a verdict would produce six measurements with nothing to
attach them to.

**NEXT STEP:** when cc releases, `sairn_claim.py check` first, then declare the
ledger and discharge **fourth `2026-10-05T15:02:28Z` `quotes`** — freshness check
before the verdict — and work down the table.

## item 2 — SKIPPED, and this says so. cc's `superseded_by` support has NOT landed.

```
command : git show origin/main:tools/defect_register.py | grep -n "superseded_by\|superseded"
commit  : b3ce8f23        date: 2026-10-08
result  : ZERO hits
command : git ls-tree -r --name-only origin/main | grep -i superseded
result  : no such path -- cc's probe does not exist on origin/main either
working tree : grep -c superseded_by tools/defect_register.py -> 0
```

cc's live claim confirms why: its **item 3** is building that support now —
*"defect_register.py Option A: superseded_by honoured only when the named survivor
EXISTS and is an ANCESTOR of origin/main; `--reseat` never re-seats or reports
success on a superseded record; fixtures for live-survivor-passes,
survivor-missing, survivor-not-an-ancestor and self-reference"*. It is in
progress, not landed.

**So the four records are NOT touched** —
`88d7543b2698 -> f2ee7be0d6da`, `8ae20da10239 -> 6a2690bec035`,
`e90d8775c7b2 -> d051c89faa16`, `f13f4f4982d3 -> 7ed27c5e78fa` — and **no
`34 -> 31` / `194 -> 193` / `25 -> 22` figure is reported**, because writing a
`superseded_by` key no reader honours would produce exactly the silent-no-op this
platform keeps paying for: the field present, the counts unchanged, and a
standing document claiming otherwise.

`tools/defect_register.py` is **declared in FILES by cc** in any case, so the
support is not mine to add.

**NEXT STEP:** when cc's support is on `origin/main`, apply the four
`superseded_by` values through the tool and report the three count deltas
measured, not predicted. The division of labour cc's own report sets — cc builds
the support, cody applies the field — is unchanged.

## item 3 — ROUTED, not applied. The premise is wrong in two ways and the tool cannot reach the record.

**(a) THE RECORD IS NOT IN THE DEFECT REGISTER.** Searching both ledgers for
`2026-10-06T22:18:54Z`:

```
docs/defect-density-register.json : 0 records
docs/tier-a-reviews.json          : 1 record
    author_session  'cody'
    opened_at       '2026-10-06T22:18:54Z'
    opened_at_sha   '4aa33b4565ddceeaac1081997f1d379d05b9de47'
    status          'reviewed'
    reviewer_owner  'cc'
    resources       ['quotes']
    files           ['tools/ledger_append.py']
```

It is a **Tier A review record**, and `opened_at_sha` is that ledger's field.

**(b) `4aa33b4565dd` DOES RESOLVE.** The item says it does not:

```
git cat-file -t 4aa33b4565dd                        -> rc 0   OBJECT PRESENT
git merge-base --is-ancestor 4aa33b4565dd origin/main -> rc 1
git merge-base --is-ancestor 4aa33b4565dd HEAD        -> rc 1
git branch -a --contains 4aa33b4565dd                -> 0 branches
```

The accurate statement is **resolves but is ORPHANED** — unreachable from any
ref, gc-eligible. That distinction is not pedantic: the gate's own output
separates *"the recorded sha is not in this clone's object store"* from a
reachability failure, and only the second applies here. Its subject is identical
to the survivor's, so it is the pre-rebase twin.

**(c) cc's RECOVERY IS CORRECT, and I verified it myself as instructed:**

```
git log --diff-filter=A --format='%H %ad %s' --date=short -- tools/ledger_append.py
  -> 27de70bee07a208ab6aa1c7e424ca65643d30719  2026-10-06
     feat(tools)+fix(bounds): five tools land with their inventory entries ...
git cat-file -t 27de70bee07a                           -> rc 0
git merge-base --is-ancestor 27de70bee07a origin/main   -> rc 0  ON-REF
```

**(d) AND THE TOOL CANNOT RE-SEAT IT — this is the real finding.** The item says
"re-seat through the tool only". The only reseat path is
`tier_a_review_gate.py --reseat-shas`, and its first line of work is:

```python
rows = [r for r in (data.get('records') or []) if r.get('status') == 'open']
```

My record's status is **`reviewed`**. Its dry run confirms the consequence —
**0 mentions** of `2026-10-06T22:18:54Z` in the whole report, while it names 22
open records, 10 already reachable, 1 reseatable, 3 weak and 8 refused with
reasons. So **a reviewed record whose sha is orphaned is permanently unfixable by
the tool**, and nothing says so.

**(e) AND THE FILE IS CC'S.** `docs/tier-a-reviews.json` is declared in cc's
FILES segment under the live 0.7h claim. Even with a working tool path this write
is not mine.

**ROUTED TO CC** with everything above: the record identity, the measured
orphan-not-missing distinction, the independently verified survivor
`27de70bee07a`, and the `status == 'open'` filter that excludes it.
**NEXT STEP, two parts:** cc re-seats the record, and the reseat path grows a
mode that can reach `reviewed` records — or refuses out loud that it cannot,
rather than omitting them silently.

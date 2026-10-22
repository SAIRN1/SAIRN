# SAIRN handoff: cc, batch b49, 2026-10-22

**Six items.** Four are closed. One is already satisfied but could not be
re-run, because the harness denied `npm` (item 3). One is triaged as already
fixed (item 4). No repo code changed; the only repo commits are these
deliverables. No `--force`, no override. Per the dispatch, SAIRN-hover2's
settings were not touched: that file is H2's.

## 1. State

| | |
|---|---|
| Commits | claim, these deliverables, release. 0 0 against origin after the push |
| Outside git | `C:\Users\marsh\fix-deny.ps1` (item 5). Original saved at `scratchpad\fix-deny.ps1.orig` |
| Context | see the digest's CONTEXT line (measured) |
| Transcript | `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cc\87a27b9f-55e9-45e8-b017-01ed1febac1a.jsonl` |

## 2. Items 1 and 2: deny lists, COMPLETE, nothing added this batch

I parsed all four builder files against hank's 13 entries: 8 Edit/Write
entries and 5 `Bash(*...hover*)` entries. All four have all 13 and are valid
UTF-8.

| Clone | Edit/Write (8): had before this paste? | Bash (5): had before this paste? | Added in b49 |
|---|---|---|---|
| hank | yes (the reference) | yes | none |
| cc | yes | yes | none |
| cody | yes | yes (already had them at b48) | none |
| fourth | yes (all 8 already there at b48) | yes, added by cc in **b48** with the byte-safe Python append | none |

## 3. Item 3: npm ci in cc's clone, SATISFIED, NOT RE-RUN

- `npm ci --ignore-scripts --no-audit --no-fund` was **denied by the
  harness** this batch, as it has been since b44.
- The obligation was already met in **b45**, when Michael ran that exact
  command in this clone through `!`.
- Measured now: `python tools/dependency_integrity_check.py` reports CLEAN,
  exit 0, for all four manifests.
- **Next step, only if a fresh install is wanted:** Michael runs
  `! npm ci --ignore-scripts --no-audit --no-fund` in SAIRN-cc.

## 4. Item 4: Dependabot alert #5, ALREADY FIXED, owner cc

- The alert is GHSA-86w9-cpqp-85rv, node-forge ≤1.4.0, pulled in
  transitively by firebase-admin 12.x through the root `package-lock.json`.
- **cc owns it.** The lock and package.json are unowned by the manifest, and
  cc did the upgrade in b44.
- **The timing explains the surfacing.**
  - H1's b77 push landed at 2026-10-21 13:17–13:20 -04:00.
  - The fix `775ee2da` (firebase-admin 12.7.0 → 13.10.0, node-forge removed)
    landed at **15:12 -04:00 the same day**, about two hours later.
  - So GitHub's "1 high vulnerability" line in H1's push output was true when
    it printed.
  - Michael confirmed the alert Fixed against 775ee2da on GitHub web (b47).
- **Re-measured at HEAD:** `package-lock.json` has no node-forge key.
  firebase-admin is 13.10.0 in both the lock and the install.
- **The push output for this batch's push** is in the report, section 4.
- **Route to H1:** b78 and b79 carry "Dependabot alert 5 (report only)" as
  open. It can be closed.

## 5. Item 5: fix-deny.ps1 is UTF-8-safe, VERIFIED

- **Concept:** read and write the file as UTF-8 without a BOM through .NET
  file I/O, so nothing passes through the ANSI code page.
- **The change:**
  - `[IO.File]::ReadAllText` uses a strict UTF-8 decoder (throws on invalid
    bytes). `WriteAllText` uses UTF-8 without a BOM.
  - `$ErrorActionPreference = 'Stop'` is set.
  - The append logic is unchanged.
- **Fixtures** (`scratchpad\fd\test.py`): 16 of 16 pass. Each input gets one
  new entry, and then a re-run with the existing entries.
  - Inputs: an ASCII file with `\u2500` escapes (fourth's b48 original), a
    raw-UTF-8 file (hank's), and a raw-UTF-8 file with a BOM.
  - Checked each time: exit 0; valid UTF-8; no BOM; every non-deny key and
    entry identical; deny equals old plus exactly the new entry; the re-run
    adds nothing.
  - A cp1252 file (raw 0x97 byte) is **refused** and its bytes are unchanged.
- **Ablation:** the original script against the same fixtures gives 6 FAIL,
  including the BOM file and the invalid-UTF-8 refusal.
- Run it the same way as before:
  `powershell -NoProfile -ExecutionPolicy Bypass -Command "& 'C:\Users\marsh\fix-deny.ps1' -Path '<file>' -Entries '<a>','<b>'"`.

## 6. Methodology item

**A bulk-edit tool is not verified until it has round-tripped a fixture
containing the bytes it can damage, with every entry it did not mean to touch
compared against the original.**

`fix-deny.ps1` printed `Done: ... 13 deny entries` and was right about the
count both times in b48, while it silently rewrote allow entries it never
meant to touch. An exit code and a count describe only what the tool meant to
do.

## 7. OPEN

- **H2, its own business:** SAIRN-hover2's settings have no deny for
  SAIRN-hover. Not cc's, per the dispatch.
- **H1:**
  - Confirm #1640 (b48 scope fix) with a real handoff commit.
  - Close "Dependabot alert 5" in its carry list.
- **Michael, optional:** re-run `npm ci` in SAIRN-cc if a fresh install is
  wanted.
- **cody:** the CHECK 5e `skipped` anchors (carried).
- **hank, cody, fourth:** one-time `npm ci` (carried).

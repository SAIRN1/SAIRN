# SAIRN handoff — cody b34 (2026-10-21)

Six items. **Five done, one NOT done (item 4: the permission command was denied).**
Written at a safe stopping point: code, tests, notes and gate records are
committed locally; the push and the Drive deliverables follow this file.

## 1. Committed / pushed state

- Local commits on `main` this batch: `b34(cody): …` (work), `chore(gates b34): …`
  (Tier A obligation), plus the claim commit. **Not yet pushed when this was
  written** — the report states the verified remote tip.
- Working tree: only `docs/scrutiny-flags.json` is dirty (the push gate's own
  write-back; folded by `python -c "import push_retry as p; p.fold_scrutiny()"`).
- **Claim:** `cody` claim `b34 accounting revoke + routed defects + per-resource
  proof` is committed locally; the claim tool's own push failed (dirty tree), so
  **it is published by the work push**. It was taken LATE (after the work) —
  nothing else touched those files in the window, but that is not the protocol.
  Release it after the push lands (`python tools/sairn_claim.py release cody`).
- Transcript: `C:\Users\marsh\.claude\projects\C--Users-marsh-Documents-SAIRN-cody\4e962f1c-4114-45e6-a314-f61c8787035b.jsonl`
  (6.2 MB, spans b31–b34).

## 2. Per item

| # | item | state |
|---|---|---|
| 1 | defect 3, `accounting.js` false credential-discard success | **DONE** — see §3 |
| 2 | defects 1, 2, 4, 5 | **DONE** — dental message, prequal/bonding 503, accounting 400 classification, new `request_photos` read verb; **client wiring routed to hank** |
| 3 | per-resource differential for the heuristic sites | **DONE, STATIC** — 63 sites: 44 PAIRED per resource, 19 hand-read; not a runtime differential — see §4 |
| 4 | `fix-deny.ps1` on `.claude/settings.local.json` | **NOT DONE — the Bash call was DENIED by the permission layer** |
| 5 | context discipline | **applied**; measured **49.4% (494,479 / 1,000,000)** before wrap-up — see §6 |
| 6 | push | see the report |

## 3. What changed (concept first, then proof)

- **Concept:** a response may claim a side effect only after the write that
  performs it came back ok *and* matched a row; and a PostgREST 400/404 is
  classified by its body before it is called NOT_PROVISIONED.
- `api/accounting.js`: revoke PATCH confirmed (ok + a row → `tokens_discarded:true`;
  ok + zero rows → `false, connection_found:false`; failure → 502
  `TOKEN_DISCARD_UNCONFIRMED` with `consent_revoked:true`); `classifyUpstream()`
  for `loadState` and the consent write. `api/b34-accounting-revoke.test.js` 9/0;
  **8 red on the old file.**
- `api/sd-data.js`: `DNT_SCHEMA_FILE` per resource; `rf_prequal_documents` /
  `rf_bonding` write → `notProvisioned(...)`; `sd_quote_requests/request_photos`
  (owner/admin guard, `license_hash`-filtered, registered in
  `_resources/stonedesk.js`, classified in `_resources/index.js`).
  `api/b34-routed-defects.test.js` 12/0; **10 red on the old files.**
- `api/sd-data-quote-request-soft-delete.test.js`: its pinned verb list is the
  FULL list on purpose, so it gained `request_photos`.
- Notes + per-site table: `docs/2026-10-21-cody-b34-notes.md`; tool:
  `docs/b33-sweep/pair_by_resource.py`.

## 4. What is open, and why — with the exact next step

1. **Item 4 (permission command).** *Why open:* the harness denied
   `cp … && powershell -ExecutionPolicy Bypass -File C:\Users\marsh\fix-deny.ps1 …`.
   I read the script first: it only **adds** deny entries (the eight hover/hover2
   Edit/Write paths) to `permissions.deny`, so it tightens. I did **not** retry
   or edit the file another way — that would route around the guard.
   *Next step (Michael):* type, in this window,
   `! powershell -ExecutionPolicy Bypass -File C:\Users\marsh\fix-deny.ps1 -Path "C:\Users\marsh\Documents\SAIRN-cody\.claude\settings.local.json" -Entries "Edit(//C:/Users/marsh/Documents/SAIRN-hover/**)","Write(//C:/Users/marsh/Documents/SAIRN-hover/**)","Edit(//C:/Users/marsh/Documents/SAIRN-hover2/**)","Write(//C:/Users/marsh/Documents/SAIRN-hover2/**)","Edit(~/Documents/SAIRN-hover/**)","Write(~/Documents/SAIRN-hover/**)","Edit(~/Documents/SAIRN-hover2/**)","Write(~/Documents/SAIRN-hover2/**)"`
   then confirm it printed `Done: … deny entries.` **Unconfirmed — it has not run.**
2. **`request_photos` has no caller.** *Why:* `stonedesk.html` is hank's.
   *Next step (hank):* in the intake panel, for a request with `photo_count > 0`,
   call `scData('request_photos','sd_quote_requests',{id: requestId})` and render
   `data[].photo_base64`.
3. **Eight sibling writes** still end `if (!w.ok) return upstream(res, saved)` with
   no missing-table classification (`sd-data.js` near 10399, 10508, 10781, 10844,
   11099, 11221, 11320, 11386). *Why open:* only two were routed; fixing eight
   unrouted sites would have been unrequested scope. *Next step:* same
   `notProvisioned(res, w, <msg>, saved)` line at each, one arm each.
4. **Re-running `revoke` rewrites the consent's `revoked_on`/`revoked_by`.**
   Pre-existing; a retry after `TOKEN_DISCARD_UNCONFIRMED` now makes it likelier.
   *Next step:* add `&revoked_on=is.null` to the consent PATCH and, on zero rows,
   check whether the consent is already revoked and go straight to the discard.
5. **Per-resource proof is static.** *Next step:* a runtime differential (plant
   every projection key in a write, read back the persisted blob) per resource, or
   promote `pair_by_resource.py` into a test that fails on any new unpaired site.
6. **`api/sd-data-customer-soft-delete.test.js` is red at HEAD** (verified by
   stash; not caused by b34). Not touched.
7. **Defects 6–8 of cc's b29** (hank: `stonedesk.html` style profile; fourth:
   `sairnroofing.html` JHA, `sairnsenior.html` contract) — not my files, not
   re-verified.
8. **H1 #1613/#1614** — HELD for H1's own report, per Michael.
9. **cc owes** the Tier A reviews opened b31 (`sc_claims`, `sc_dme`), b32
   (`rf_jobs`), b33 (`alf_*` rules, `bld_draws`) and b34 (dental, prequal/bonding,
   `sd_quote_requests`).

## 5. Verification (run this batch)

```
EXIT=0  b34-accounting-revoke 9/0 · b34-routed-defects 12/0 · b33-projection-order-sweep 12/0
EXIT=0  b32-rf-jobs-projection 7/0 · b30-cap-per-action 22/0 · extra-actions 48/0
EXIT=0  sd-data-quote-request-soft-delete 14 · sd-data-tombstone-propagation
EXIT=0  sd-data-cross-tenant-dispatchers 418/0 · unconfirmed-write-sweep 30/0
EXIT=0  preauth-envelope-ordering 59/0 · session-gate 22
EXIT=1  sd-data-customer-soft-delete — RED AT HEAD (stash differential), not b34
```

Two suites I broke and fixed in-batch: the tombstone-propagation regexp (guard
order) and the quote-request pinned verb list.

## 6. Context discipline (item 5)

Applied: test output filtered to `FAIL|counts|HARNESS`, `grep`/`sed -n` ranges for
`sd-data.js` (1.3 MB), no whole-file reads of app files. **Measured 49.4%
(494,479 tokens of 1,000,000) with `python tools/context_verify.py --digest-line`
after `--provision-window 1000000`** — higher than the discipline should produce
because this session spans four batches (b31–b34); the transcript, not this
batch's output, is most of it. A fresh session starts near zero.

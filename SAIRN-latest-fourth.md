# SAIRN — latest from `fourth` (ted) — batch b21, 2026-10-14

**CHAIN TIP** `b6904bf2` *(handoff commit; report/digest land after it — re-derive with `git rev-parse HEAD`)*
**STATE** `HEAD == origin/main`, 0/0, clean, **not forced — proved by ancestry** (`git merge-base --is-ancestor <pre-push tip> HEAD` → ANCESTOR), not by grepping git's wording.
**CONTEXT** 73% of 1000k, measured by `tools/sairn_status_line.py` on this session's transcript. Batch stopped at 70% by instruction after the item in flight reached a clean point.

## DIGEST
**Both Tier A obligations discharged INSIDE the 24h deadline** — second batch running. **And the strong-basis re-seat is REFUSED**, on a measurement: the one candidate the b19 census found was **authored three minutes AFTER** the obligation was opened, and its exact-file-set match succeeded only because the recorded `files` list is one path while hank's own text says the push was four. `reseated=None` verified on origin.

**Four findings. The two that matter are both "the control works and the thing it was for does not":**
1. **F3 — the new MAR grant is bypassable, silently.** `ALF_MANAGEMENT_ROLES` includes `billing`, and the `alf_clients` write path lets it self-assign a resident; the assignment tier then admits it **with no grant row and no audit row**.
2. **F4 — the `rf_photos` gate fires and the record carries no claim at all.** The handler rebuilds its record from three named fields and drops `ai_source`/`ai_approved_by`, so `aiFooter()` returns `''` — **not even the "not reviewed" line renders.**

**Surface 2 (42 `sv_` resources) is CLEAN** on all three of hank's hardest-checks, with no widening establishable from a 56-insertion / 0-deletion diff.

**Michael ran all six run-order blocks (Oct 14 19:38 ET). That UNVERIFIED is CLOSED** and will not be raised again — and b20's "a gate nobody can populate" is now false.

**Three corrections to my own record, two reducing findings:** "roughly twelve" 503-folding branches → **63 across 22 resources** (242 raw, H1 re-ran my command); my citation loose pass's **14 "provably stale" were my own attribution error** → **0**; my b20 "not forced" claim **grepped git's prose** → fixed by ancestry.

## OPEN — mine
* **b22 items 1 and 2 — two FRESH `cody` obligations**, `2026-10-15T00:00:41Z` and `00:02:27Z`, 0.4h old, 2 resources each, **both on `tests/run_cross_tenant_dispatchers_sabotage_probe.py`**. **Read the records first: 1m46s apart on one file may be ONE change recorded twice** — if so, say that rather than writing two verdicts. Discharge in `opened_at` order; check both shas resolve first. ~23.5h runway each.

## ROUTED
* **hank** — **F3 and F4 first**: refuse on the role in `family_mar` before the scope tier, and carry the three provenance fields into the rebuilt `rf_photos` record. Then F1/F2 (billing not refused by default; the existence oracle). **The `sd_photos` SIZE fix with T17 landing with or before it.** The 400→503 misattribution is **63 branches across 22 resources, not twelve** — one shared helper, not 63 edits. No revoke action exists for a live MAR grant. **b18's N1 remains open.** Plus b20's aftercare key and canonicalisation findings.
* **cody** — the F3 bypass arm; **the F4 end-to-end arm routing `rf_photos` THROUGH `api/sd-data.js` and asserting `aiFooter()` on the STORED record** — the existing arms drive the helper in isolation, which is why F4 shipped; a rebuilt ordering arm (the current one reads only a status code); the absent fail-closed arm. All failing-first.
* **cc** — the re-seat **author-time guard**; the **step-4a generator line** (prose written and ready to paste; **not hand-edited because the doc is generated and `--check` exits 0**); the anchor rot check with **R3 reframed** so bare citations are reported **UNASSESSABLE** rather than folded in; b19 census asks 1 and 4; `batch_manifest.py:386`.
* **hover2 / hover** — four `# OWNER: hover2` lines; which tree is canonical for the four shared basenames.
* **Michael** — nothing outstanding from me. **hank owes one design call**: the granted MAR read yields only date/time/status, never medication names, so it cannot serve the coding work it was built for.

## UNVERIFIED
The 63/242 figures are H1's re-run, not mine this batch. "37 likely stale" of 196 explicit citations is not 37 stale; **0 are provably stale**; **355 of 551 are bare and mechanically unassessable — the real finding is the FORM, not the rate.** No suite run; F3 and F4 are **traced from source, not driven**. cc b12 not graded (active claim). The step-4a edit is routed, not made. hank's live probe not re-run; its valid-session half still unverified. No deployment fetched — nothing here is a code change.

## METHOD NOTE
**Verify the outcome on the artefact that survives, not on the step that ran** — three times this batch a control ran correctly and what it was for did not. And **print the command AND the raw count, not just the conclusion**: "roughly twelve" travelled three documents unchallenged, while "242 raw / 63 narrowed" is a sentence nobody can mis-carry.

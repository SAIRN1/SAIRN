# SAIRNvet — Session 56 Handoff (for Claude Code)
Generated: July 7, 2026 | Chat session verified baseline independently via GitHub git tree/blob API (not /contents cache)

## Verified Current State (do not trust without re-verifying — see Iron Laws)
- Commit: 002d481103a2c4b3c9938b78164f0ac05b59963b (short: 002d4811)
- sairnvet.html: 201,035 bytes — byte size confirmed via git blob fetch
- 54 panels, 54 svNav() targets, 0 missing, 0 orphans (nav confirmed working; 12 panels use bare ids like `dashboard`/`billing`, 42 use `panel-` prefix — cosmetic inconsistency only, svNav() does plain getElementById so both resolve fine, leave as-is)
- VET_DRUGS: 208 entries, VET_DIAGNOSES: 346 entries — both counts confirmed by parsing the live arrays
- Guardian: 0 failures (no direct api.anthropic.com calls, no alert(), no console.log, no duplicate ids, no duplicate function declarations, no Unicode box chars, all localStorage keys sv_-prefixed)

## Finding: Data Model Gap (this is the priority fix, not just volume)
Current VET_DRUGS schema is one dose line per drug with species as a comma-joined string, e.g.:
```json
{"name":"Amoxicillin","class":"Penicillin","species":"dog,cat,exotic","route":"PO/SC","dose":"10-20mg/kg BID","controlled":false,"flag":""}
```
This applies ONE dose across all listed species, which is clinically wrong — a bearded dragon's amoxicillin dose/interval is not a dog's. Real veterinary formularies (Plumb's, Carpenter's Exotic Animal Formulary) give a separate dose line per species per drug.

**Required schema migration** — VET_DRUGS becomes one row per drug-per-species:
```json
{"name":"Amoxicillin","class":"Penicillin","species":"dog","route":"PO/SC","dose":"10-20mg/kg BID","controlled":false,"flag":""}
{"name":"Amoxicillin","class":"Penicillin","species":"bearded dragon","route":"PO","dose":"[correct exotic dose]","controlled":false,"flag":"[if any]"}
```
Migrate all 208 existing entries by exploding multi-species rows into per-species rows with correct per-species doses (verify against Plumb's/Carpenter's-consistent values, don't just duplicate the old single dose across species).

## Diagnosis Library Rebalance
Current 346 entries are 60% dog(121)/cat(86). Everything else is thin: reptile 19, bird 23, exotic 9, amphibian 5, aquatic/fish 8, zoo/wildlife ~15 total split across primate/raptor/marine mammal/cervid/bat (1-2 each). Rebalance targets for this expansion pass — don't just add more dog/cat entries:
- Reptile: expand per major captive taxa (bearded dragon, ball python, leopard gecko, box turtle, red-eared slider, monitor, chameleon) — target 60-80+
- Avian (pet/exotic): expand per grouping (macaw, cockatoo/cockatiel, African grey, conure, canary/finch, raptor) — target 50+
- Exotic mammal: rabbit, ferret, guinea pig, chinchilla, hedgehog, sugar glider, rat/mouse — target 60+
- Zoo/wildlife: this is the thinnest and highest-value gap. Add real depth per Columbus Zoo research this session:
  - **Great ape cardiology**: primate cardiomyopathy/arrhythmia, insertable cardiac monitor (ICM) placement and post-implant monitoring protocol — modeled on the real Great Ape Heart Project (Columbus Zoo is a lead contributor; ICMs placed in orangutans, bonobos, gorillas; human cardiologists/anesthesiologists join the procedure)
  - **Sirenian/manatee**: cold-stress syndrome, boat-strike trauma, body-condition/weight-gain rehab-to-release criteria, transport protocol — modeled on the real Manatee Rescue & Rehabilitation Partnership (Columbus Zoo is a second-stage rehab facility)
  - **Large carnivore, pachyderm, cervid, raptor, marine mammal**: bring each to double-digit depth, not 1-2 tokens
  - Target 80-100+ for zoo/wildlife alone
- Overall diagnosis target for this pass: ~800-1,000 (not the full 2,000 in one session — that's multiple passes; this pass fixes the imbalance and gets real depth into every category)

## Architecture Decisions From This Session (implement, don't skip)
These came out of a "how do we prevent AI diagnostic mistakes" discussion and are the core safety layer for every AI feature in the app (AI Assistant, dosing calculator, diagnosis protocol generator, SOAP generator, zoo immobilization generator):

1. **Grounding, not free generation.** Every AI call must have the matching VET_DRUGS/VET_DIAGNOSES records injected into the prompt as the only source of truth. System prompt must instruct: if the species/drug/diagnosis combo isn't in the seeded data, say so explicitly — never guess a dose or diagnosis from parametric knowledge alone.

2. **Dose math and bounds-checking is deterministic JS, not AI.** Add a `doseMin`/`doseMax` numeric field (in addition to the existing display `dose` string) to every VET_DRUGS entry. The dosing calculator computes and bounds-checks entirely in JS against these fields — the AI may only narrate/explain, never compute or override the number. Out-of-range results get a hard visual flag, not a soft warning.

3. **Contraindication gate runs before the AI, not inside it.** The existing red-flag data (acetaminophen/cats, ivermectin/chelonians, permethrin/cats, amitraz/cats+rabbits, penicillin/rodents, monensin/horses, carfentanil-etorphine human-lethality, melarsomine exercise restriction, digoxin narrow margin, etc.) becomes a separate deterministic pre-check function that runs BEFORE any AI-generated protocol is displayed, and blocks/hard-warns independent of what the AI says. A red flag must never depend on the model remembering to mention it.

4. **Diagnosis generator returns a ranked differential, never a single answer.** Multiple possibilities with reasoning, not one confident diagnosis.

5. **AI output is a suggestion pane, not the record.** Nothing AI-generated writes to a patient chart or prints until a vet actively reviews and accepts/edits it. No auto-populated "official" diagnosis or treatment field.

6. **Show sourcing and gaps.** Every AI response should indicate which record(s) it drew from, and explicitly flag when a case falls outside seeded knowledge instead of smoothing over the gap.

7. **Audit trail.** Log every AI suggestion with the data version it was grounded in, timestamp, and whether the vet accepted/edited/rejected it. localStorage key `sv_audit_log` or similar, sv_-prefixed per existing convention.

8. **Two-pass disagreement escalation for highest-stakes calls.** Controlled substances and zoo immobilization drugs (carfentanil-class) route through a second independent AI pass; if the two passes disagree, force "flag for manual review" rather than auto-resolving.

Positioning matters here: this is clinical decision support, never autonomous diagnosis. The licensed veterinarian retains all decision authority at every step — this should be reflected in UI copy, not just backend logic (current AVMA guidance explicitly frames AI as augmenting, not replacing, clinical judgment — this isn't just a legal CYA, it's the correct design target).

## UI Standard
Bring all 54 panels to the StoneDesk world-class standard (SHA 243aabc6 is the reference — 5 KPIs per panel, CSV export, AI integration pattern, showToast consistency, world-class print). Color stays locked at SAIRNvet's existing #7C3AED — do not adopt StoneDesk's green, only its structural/polish patterns.

## Patent Note (informational, not a build task)
A prior-art search this session found the general pattern (LLM output + independent deterministic verification layer + human sign-off) is actively published in human clinical CDS research as of 2025-2026 (multiple named systems doing close variants of this), plus existing prior art for AI-driven veterinary diagnosis/recommendation engines generally. Broad claims on the pattern itself are unlikely to be novel. The narrower, more defensible angle is the specific cross-species dose-bounds/contraindication implementation spanning companion through zoo/exotic in one unified system, plus the two-pass escalation for controlled/immobilization drugs specifically. Not a Claude Code task — flagging for Michael's patent counsel before any filing decision.

## Iron Laws (unchanged)
- GitHub REST API only — blob→tree→commit→ref, never git push
- Always fetch current SHA immediately before any write
- No Unicode box chars in JS, no dark backgrounds, no alert() (showToast() only)
- localStorage keys prefixed sv_
- All Claude calls through proxy only (sairn.vercel.app/api/claude), never api.anthropic.com directly
- Guardian scan (28 checks) must pass zero failures before any push
- Verify via git tree/blob API, never trust /contents cache or a prior handoff at face value

## Next Session Start Protocol
1. New PAT: SAIRN-Session57 | Fine-grained | SAIRN1/SAIRN | Contents R/W
2. Fetch sairnvet.html via git tree, confirm actual byte size/panel/drug/diagnosis counts before believing this handoff
3. Execute schema migration + rebalanced expansion + architecture items 1-8 above
4. Guardian scan before every push
5. Deploy from Windows CMD once satisfied: `git fetch origin && git reset --hard origin/master` then `npx vercel --prod --force`

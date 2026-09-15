# Item 97 — is the Tier A artifact the one that flies, or a stand-in for it?

**2026-09-15 (CC).** A sanity pass over the platform's current Tier A
assignments, not a re-tiering. Nothing was re-tiered here; the two findings
below were put to Michael's judgement, the same way the 2026-09-10 decision to
tier by resource was.

> **DECIDED AND FIXED THE SAME DAY — finding 1 is CLOSED.** Michael's call:
> the seven were an inconsistency, not a designed exception, and SAIRNcode's
> grant now matches the precedent it departed from. `api/_resources/sairncode.js`
> grants `soft_delete` to the seven and `delete` to the other 21;
> `api/sd-data.js` implements the soft delete, excludes marked rows from every
> read of those seven, and refuses a destroying `delete` on them even from an
> admin. **`tools/tier_a_replaceability_check.py` now reports 0 hard-deletable
> Tier A resources platform-wide, down from 7.** The measurement sections below
> are kept AS WRITTEN, describing the state that was found — a finding rewritten
> into the past tense stops being checkable against the commit that fixed it.
> Finding 2 is narrowed but still open: 68 of 80 evidence cells, down from 75.
> The unswept under-assignment direction in §4 is untouched and is still the
> dangerous one.

---

## 1. The discriminator, and why it is not the one the register already uses

`docs/CRITICALITY-TIERS.md` assigns a tier from **"the worst consequence of that
resource being WRONG"**. That is one of the two questions aerospace asks of a
serial number, and it is the easier one.

The other is whether the article in front of you is the one that **flies** or a
stand-in built to behave like it — a boilerplate capsule, a mass simulator, a
pathfinder. Both look identical on a bench and both can be wrong. Only one of
them is **unrecoverable if it is lost**.

**The direction of the error is asymmetric, and that asymmetry is the whole
value of the question.** Applying flight rigour to a test article wastes
rigour. Applying test-article treatment to a flight article is the accident.

The register never asks it. That is not a criticism of the register — a rubric
that asks one question well is worth more than one that blurs two — but it
means a Tier A label today carries **no claim at all** about whether the record
can be reconstructed.

Measured with `tools/tier_a_replaceability_check.py`, report-only. **Run it
rather than quoting the figures below**; they are dated, and the same document
that records item 20 had four hand-typed figures go wrong in a day.

## 2. FINDING — seven Tier A artifacts can be destroyed, and they are all in one app

    Tier A resources                : 80
    can be HARD DELETED             :  7   ← all seven are SAIRNcode
    soft_delete only (row survives) :  8
    no delete verb reachable        : 65

`sc_ar`, `sc_claims`, `sc_compliance`, `sc_credential_scope`, `sc_denial`,
`sc_denial_events`, `sc_revenue`.

**The total is not the finding. The concentration is.** Every other Tier A
resource on this platform either hides the row or cannot be deleted at all, so
this is not a platform-wide posture that SAIRNcode shares — it is the one place
that departs from it.

**And the grant was never a per-resource decision.** `api/_resources/sairncode.js`
builds it with a `reduce()` over the whole list:

> *"'delete' is a real verb for every sc_* resource and only for them —
> SAIRNcode's client has had real remove buttons since 2026-08-18 … Derived
> from RESOURCES above, so a resource added to this file can never be silently
> ungated or over-gated."*

That reasoning is sound **for the set** and it is exactly why the seven inherit
a destroy verb without anybody deciding it for them. A compliance finding and a
DME catalogue row get identical destroy rights because they are in one list.

**The platform has made the opposite call deliberately, twice, and written down
why both times:**

- `api/_resources/sairnvet.js` on `sv_controlled`: *"having no delete verb is
  the CORRECT design for a controlled-substance register."*
- `api/_resources/sairndental.js`: *"`'soft_delete'`, not `'delete'`: the record
  is marked and hidden, the row [survives]."*

So the judgement exists on this platform and has been exercised. It has simply
never been applied to these seven.

### The consequence is currently unbounded, and that is a dated statement

`docs/2026-09-14-nightly-backup-design.md` records, one day before this pass,
that Supabase is on the **free tier — no automated database backups, one-day
log retention** — and that the nightly workflow **has never run**: *"Every
secret it needs is absent and the role has not been created."*

If that is still true, a hard delete of one of these seven is **unrecoverable
today**. **I could not verify it independently** — this environment has no `gh`
and no Supabase console, so I could not check the plan or whether a workflow run
has since occurred. Check that before acting on this section.

**What I did verify, live, tonight:** the verb works on the deployed function.
`tools/sc_tier_a_write_gate_live_probe.py` hard-deleted rows from `sc_claims`
and `sc_compliance` on the production demo tenant with one admin call, and a
read-back through the API returned **0 rows** in each. This is not a theoretical
grant.

**This is not automatically a defect.** A hard delete verb is a decision, and
the probe above relies on it to clean up after itself — it is the reason that
probe can leave the tenant as it found it while the SAIRNroofing one cannot. The
finding is that **nobody made the decision for these seven specifically.**

## 3. FINDING — the evidence column establishes consequence and almost never replaceability

**75 of 80 Tier A rows say nothing about recoverability.** Five mention a
backup, a soft delete, or append-only behaviour; the rest state money or
regulation and stop.

**This is a documentation-coverage figure and must not be read as 75 defects.**
The measurement reads *language*, not intent, so a row that establishes
replaceability in words the pattern does not match is a false hit. The register
asked for consequence-if-wrong and got it, on every row. Replaceability is a
question nobody was asked.

The cheap fix, if Michael wants one, is a sentence in the evidence cell for the
rows where it is load-bearing — not a new column and not a new document.

## 4. What this pass did NOT do, named rather than implied

- **No re-tiering.** Not this session's call.
- ~~**THE UNDER-ASSIGNMENT DIRECTION IS NOT SWEPT**~~ — **SWEPT 2026-09-15,
  later the same day, and §6 below is what it found.** The hole named here is
  closed by `--under`; what remains is a decision, not a measurement.
- **No infrastructure was checked.** See the caveat in §2 about the backup.
- **`sairncash` has no registered resources at all**, so it contributes nothing
  to any figure here and is not evidence of a clean result.

## 5. Why a tool rather than a table in this document

Because the table in the item 20 document was wrong within twenty-four hours,
and it was written by somebody who knew that rule. The two counts here move
whenever a tier changes or a verb grant changes — neither of which announces
itself — so the durable half is
`tools/tier_a_replaceability_check.py` plus its probe,
`tests/run_tier_a_replaceability_probe.py`.

**The probe's third section is the part worth reading.** It demotes
`sc_compliance` to B in the real register, requires the hard-delete count to
fall from 7 to 6, restores the file and verifies the restore **by sha256** —
because a checker that prints a number is worth nothing until something has
watched the number move. Its fourth section proves the tool's own design claim
instead of asserting it: SAIRNcode grants `delete` through a `reduce()` and
never as a literal, so an implementation that scraped the source would have
found zero and reported the platform clean.

It is **report-only and deliberately unwired**, recorded as a `NOT_PROMOTED`
entry: its input is the register and the registry, not the push, so a push-time
entry would print the same seven names on every push regardless of what the push
contained.


---

## 6. The under-assignment sweep — `--under`, added the same day

**Over-tiering costs rigour. UNDER-tiering is the accident**, and §4 recorded
that direction as this tool's known hole. It is swept now.

**THE REGISTER ALREADY SAYS THIS IS ITS WEAK POINT**, which is why the sweep is
a triage and not an accusation:

> *"The B tier is 299 rows and it is the honest weak point of this file. Each
> says the same thing — auth-gated, not money, not regulated — because that is
> what the rule says, not because 299 files were read. A resource misfiled as B
> is the failure mode that matters."*

**274 rows carry the words "Classified by the stated B rule rather than
individually read."** Re-reading 274 files is not the answer. Narrowing them to
the rows an irreplaceability test flags is: **304 Tier B/C rows → 38.**

### Three signals, and the third is the one the B rule structurally cannot see

| Signal | Why it means irreplaceable |
|---|---|
| `HARD-DELETE` | a destroying `delete` verb — the row can be removed, not hidden |
| `LOG-SHAPED` | audit / log / history / trail / events in the name. An append-only record's whole value is that it cannot be reconstructed |
| `ATTESTATION` | its writer stores a **signer, a signature, a sign-off or a content hash**. **The B rule asks whether a resource is money or regulated and never asks whether it is EVIDENCE** |

### THE FINDING: a client's executed e-signature is filed as operational data

`law_portalesign` — **SAIRNlaw, Tier B.** Its writer stores
`{matter_id, document_id, esign_name, esign_at}`: a client's typed signature on
a matter document, with a timestamp. Its evidence cell reads *"neither money nor
a regulated record. **Classified by the stated B rule rather than individually
read.**"*

**An executed signature on a legal document is not operational data.** It is the
artifact — and the rule that filed it never had a question that could see that.

**Others on the shortlist, same shape:** `sf_signatures` (SAIRNfreedom — signer,
typed signature and a **document hash**, and the app's own refusal message says
*"a signature that does not match the name it is filed under is not evidence of
anything"*, so the app already calls it evidence); `sc_auth_requests`
(prior-auth with a **server-stamped** `signedOffBy`/`signedOffAt` — **and a hard
delete verb**); `leg_documents`, `sdn_contracts`, `rf_proposals`, `alf_mar`.

**NOT RE-TIERED HERE.** Same rule as §2: the measurement is mine, the tier is
Michael's call.

### THE SIGNAL SHIPPED DEAD, AND A POSITIVE CONTROL IS WHAT CAUGHT IT

The `ATTESTATION` pattern reached the file with a **literal backspace — byte
0x08** — where a word boundary was intended. `ATTEST.search('signer:signer')`
was `False` and the signal reported **zero hits platform-wide**: a clean result
from a dead pattern, on the one signal that was the whole reason for the sweep.

**CLAUDE.md already names this exact defect** as one of the three that made the
cross-domain disciplines necessary — *"a regex that shipped with a literal
backspace and could never match."* It was found by asserting the signal **fires
on a known case**, not by reading the line, which looks correct at any font
size. The tool now **refuses to import** if the pattern cannot match its own
reference case, and the probe carries a positive and a negative control for
every signal.

**And it was blind to one level of indirection.** Once alive it still returned
nothing for `sf_signatures`, because sairnfreedom binds
`var K_SIGNATURES='sf_signatures'` and every writer uses the **constant** — the
signing function sits 150 lines from the only place the string appears. It
resolves aliases now. **Two separate ways to report a confident zero, in one
signal, in one afternoon.**

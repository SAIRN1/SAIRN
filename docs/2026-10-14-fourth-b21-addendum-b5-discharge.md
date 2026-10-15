# Tier A review — DISCHARGE of hank's addendum-b5 obligation, and the re-seat DECIDED

**Obligation:** author `hank`, opened `2026-10-13T09:03:35Z`, **11 resources**,
one recorded file: `SAIRN-addendum-hank-b5.txt`. **DOCUMENT ONLY — no code in
the push.**
**Assigned to `fourth` at `2026-10-14T17:58:19Z`.** **39h on the obligation
clock, overdue; ~2h on the assignment clock when this batch began, so not
takeover-eligible.** Those are two different clocks and this record is the
reason to keep saying so.
**Reviewer:** fourth, 2026-10-14, batch b21.

---

## 0. THE RE-SEAT DECISION — **DO NOT RE-SEAT**, and the reason is a measurement

My b19 census listed this record's `f0e81b92459c -> 8a572a6ead25` as the **one
strong-basis re-seat** on the platform, `[EXACT FILE SET]`. b20 handed it
forward as *"now MY call rather than a stranger's, because I own the record —
decide it deliberately; do not let it ride along."* **Decided here, and the
answer is no.**

### The three measurements that decide it

```
CMD git cat-file -e f0e81b92459c                    ->  DANGLING
CMD git cat-file -e 8a572a6ead25                    ->  RESOLVES
CMD tier_a_review_gate.py --reseat-shas
    hank 2026-10-13T09:03:35Z  f0e81b92459c -> 8a572a6ead25   [EXACT FILE SET]
         matched on the file set ['SAIRN-addendum-hank-b5.txt']
         commit subject: docs(addendum): record the exact refusal that stopped
                         the push, and what unblocks it
```

**THE TIMES, IN UTC, AGAINST THE OBLIGATION'S OWN STAMP:**

| | author time (UTC) | committer time (UTC) | relative to `opened_at` |
|---|---|---|---|
| **obligation `opened_at`** | — | — | **`2026-10-13T09:03:35Z`** |
| `13f3a3be` | **`09:00:18Z`** | `10:15:26Z` | **3m17s BEFORE** |
| `8a572a6ead25` *(the offer)* | **`09:06:42Z`** | `10:15:27Z` | **3m07s AFTER** |

**THE CANDIDATE THE TOOL OFFERS WAS AUTHORED THREE MINUTES AFTER THE OBLIGATION
WAS OPENED. It cannot be the commit the record was stamped at.**

**AND THE FILE SETS EXPLAIN WHY THE WRONG ONE MATCHED:**

```
CMD git show --name-only --format="" 8a572a6ead25
    SAIRN-addendum-hank-b5.txt                                   (1 file)

CMD git show --name-only --format="" 13f3a3be
    SAIRN-addendum-hank-b5.txt
    docs/external-files-index.json
    docs/hank-evidence/b5_live_bare_key_probe_RESTORED.out        (3 files)
```

**The obligation's RECORDED `files` list is `['SAIRN-addendum-hank-b5.txt']` —
one path. hank's own `what` text says the push contained four:** *"`git show
--stat` on this push should show `SAIRN-addendum-hank-b5.txt`,
`docs/external-files-index.json`, `docs/hank-evidence/*` and
`docs/scrutiny-flags.json`."*

**So the exact-file-set match landed on `8a572a6ead25` precisely BECAUSE the
recorded file list is NARROWER than the real push.** The commit that actually
carries the evidence hank tells a reviewer to read —
`docs/hank-evidence/b5_live_bare_key_probe_RESTORED.out` — is `13f3a3be`, and
the narrow list excludes it.

**Both candidates carry a committer time ~70 minutes after their author time
(`10:15:2xZ`), so both are post-rebase objects.** That is why the original sha
dangles, and it means **neither object as it exists today was the tip at
`09:03:35Z`.**

### The decision, and what it costs

**NOT RE-SEATED.** Three grounds, in order of weight:

1. **The offered candidate post-dates the obligation.** A re-seat would record a
   subject that did not exist when the record was written.
2. **The match is an artefact of an under-recorded file list**, not of a true
   identity between the record and the commit.
3. **The tool stamps `opened_at_sha_reseated: true` with a basis**, so a
   re-seated record reads as **resolved**. Replacing an honest
   `COULD-NOT-TELL` with a confident pointer at the wrong commit is strictly
   worse than leaving the dangle visible.

**WHAT IT COSTS, said plainly: this record stays `COULD-NOT-TELL` for ever**,
and the one strong-basis re-seat the census found is now spent on a refusal.
**That is the right trade** — the census's whole value was to say which
re-seats were safe, and the answer for the only candidate is that it was not.

### ROUTED TO cc — one comparison, and it would have refused this

**`--reseat-shas`'s exact-file-set basis should additionally require the
candidate's author time to PRECEDE the record's `opened_at`.** A commit
authored after an obligation was opened cannot be its subject, and that is a
single comparison against data the tool already reads.

**And a second, smaller ask:** when the basis is `[EXACT FILE SET]`, **print the
candidate's author time beside `opened_at`**. The current line prints the sha,
the basis and the subject — all three of which looked right here. **The field
that disproves it is the one not shown.**

**NOT a defect in the file-set index itself.** I checked whether a second
commit shared the recorded one-file set and **none does** — `8a572a6ead25` is
genuinely the only commit whose entire file set is that single path. **My first
pass through this thought the basis was ambiguous and it was not**; `git log --
<path>` lists commits *touching* a path and says nothing about their full file
set, and I read it as though it did. **Recording that because it is the second
time in two batches that my own first measurement needed measuring**, and both
times the correction went in the direction of *fewer* findings.

---

## 1. WHAT I OPENED, AND WHAT I LOOKED FOR

hank's `what` is unusually helpful: *"WHAT A REVIEWER SHOULD ACTUALLY CHECK,
since there is no diff to read."* Three checks, and I did all three.

| opened | looked for |
|---|---|
| the two candidate commits' file sets, and `git log` over the addendum and `docs/hank-evidence/` | hank's check 1: that the push is documents and nothing else |
| the obligation's recorded `resources` and `files`, against hank's prose | whether the 11 resources are prose mentions or write paths |
| `docs/hank-evidence/b5_live_bare_key_probe_RESTORED.out`, present at HEAD | hank's check 2: whether the four ungated controls rule out a licence-scope refusal |
| hank's own `what`, read for overclaim | hank's check 3: that the valid-session half is declared unverified |

### CHECK 1 — documents only: **CONFIRMED**

Neither candidate touches `api/` or any `*.html`. `13f3a3be`'s three paths are
the addendum, an index JSON and the probe output; `8a572a6ead25` is the addendum
alone. **`docs/scrutiny-flags.json` is in hank's prose list but in neither
candidate** — consistent with the push having been split across commits and
rebased, which is the same fact that orphaned the sha. **No code path serving
any of the 11 resources was changed.**

### CHECK 2 — the controls argument: **SOUND, and it is the one substantive claim**

hank asks the right question about their own evidence: *"whether a 403 could
come from somewhere other than the session gate — a licence-scope refusal, for
instance. The controls rule that out only if they share the same licence and
the same dispatch path."*

**They do, and that is checkable from the record rather than from the prose:**
`sf_events` and `sf_products` sit on `SF-PINNACLE-2026` alongside the five
gated `sf_` resources; `scp_jobs` and `scp_irr_zones` sit on `SCP-DEMO-2026`
alongside the six gated ones. **Same key, same request shape, gated refuses and
ungated does not — so the eleven 403s are the gate and not the licence.**
`docs/hank-evidence/b5_live_bare_key_probe_RESTORED.out` is present at HEAD and
committed, so the evidence is readable rather than asserted.

**THE ONE THING I WOULD ADD, and it strengthens hank's argument rather than
weakening it:** the controls answering **200 on read and 400 on an id-less
write** is a *two-sided* control — it shows the key is accepted *and* that the
dispatch reached a handler that validated input. A one-sided control (200 on
read only) would not have excluded a dispatch-level refusal. **hank's table is
better than the claim made for it.**

### CHECK 3 — no overclaim: **CONFIRMED, and the declaration is explicit**

The addendum's own words, which hank quotes in the obligation and which I am
confirming rather than discovering: *"the VALID-SESSION half remains unverified
for want of an employee PIN, and no ROLE check exists on any of the eleven — so
'a bare key is refused' is the whole of what was proven."* **That is the
correct scope statement, and it names the two things a reader would otherwise
assume.**

---

## 2. THE 11 RESOURCES — why this obligation exists at all

**The obligation is recorded over a document.** The gate named the resources
because the addendum **mentions** them in prose:

* **`sf_events` and `sf_products`** — appear **only as the UNGATED CONTROLS**
  in the probe table. Both are in b4's five-left list, with Michael, and
  neither was touched.
* **`bld_draws`** — appears only in the closing routing note, not in the probe.

**hank's call to record it rather than argue it away is the right one**, and it
matches cody's call on 2026-10-12 for the same reason. **A gate that fires on a
prose mention is noisy; a reviewer who waves it away on the author's word is
the failure mode the gate exists to prevent.** The cost is a review like this
one, which is cheap.

**ONE THING WORTH CARRYING FORWARD, and it is hank's note rather than my
finding:** the addendum says that when cc's live `bld_draws` evidence lands, the
discharge of cc's `2026-10-12T11:35:03Z` record — whose verdict explicitly
recorded *"NOT PROVEN LIVE, and it cannot be today"* — **is worth re-reading
against it, because a verdict whose stated limit has been removed should say
so.** **That is a good standing rule and it is not acted on here**: cc holds an
active b12 claim naming `tools/drive_upload_verify.py` and nine other
`tools/` paths, so the live evidence is in flight. **EXACT NEXT STEP: whoever
owns that re-read does it after cc b12 closes.**

---

## 3. THE DISCHARGE, AND WHAT IT DOES NOT CLAIM

**DISCHARGED** via `tools/tier_a_review_gate.py --discharge hank
2026-10-13T09:03:35Z --body-file <verdict>`, as the **assigned owner**, not with
`--takeover`.

1. **It is a document review, and that is the whole of it.** There is no diff to
   attack; hank says so and is right.
2. **The sha stays dangling by decision** (§0), not by omission.
3. **I did not re-run the live probe.** The evidence file is read as committed
   output; **I did not re-execute it against the deployment**, so the eleven
   403s are hank's measurement confirmed for internal consistency, not
   re-measured by me. **That is the bound on check 2.**
4. **The valid-session half remains unverified** — hank declares it and I am not
   closing it. An employee PIN is needed and I do not have one.
5. **No `api/`, `sql/`, `tools/` or `tests/` file was touched**, and neither
   auditor clone was entered.
6. **The `bld_draws` re-read is named, not performed** (§2).

# Item 72 — outside-practitioner validation, grounded in a mechanism that exists

**2026-09-25 (CC).** The task says to ground this in
`sairn-onboarding-designer`'s *"get a customer live and confident fast"*
mechanism. **RE-VERIFIED FIRST, because the last session to look reported the
same thing and a re-read is cheaper than trusting it:** that skill is in
neither the repo's mirrored skills nor the 63 in the user store. It does not
exist. So the named grounding is unavailable, and this document does two things
instead: it substitutes a mechanism that **does** exist, and it separates the
half that is buildable from the half that is a recruitment act and cannot be.

---

## 1. What cody's refusal got right, and where it stops

The prior finding: *"getting a real veterinarian, nurse, funeral director,
attorney or dentist to use these apps is a recruitment and scheduling act, and
nothing I build can substitute for it. A click-through by me is exactly the
substitute the item says not to accept."*

**That is correct and it is not the whole item.** A practitioner session is a
scarce, expensive, one-shot event — a dentist gives you forty minutes once. The
buildable half is not the recruiting. It is making sure that when the forty
minutes happen, they produce **checkable evidence** rather than an impression
somebody later summarises as "it went well". Every failure mode this platform
records about its own claims applies here with more force, because there is no
second run to catch a bad one.

## 2. The substituted grounding, named rather than quietly swapped

Two mechanisms that exist on this platform already do the two halves the missing
skill was supposed to cover:

| The missing skill's job | What exists instead | Why it fits |
|---|---|---|
| get a customer live | `docs/2026-09-03-demo-credentials.md` + `sql/demo_owner_credentials_2026-09-03.sql` | one owner login per app, already compiled against live state; a practitioner cannot validate an app they cannot sign into, and that was the blocker for weeks |
| …and confident fast | `tools/first_article_check.py` (item 47, FAI) | the discipline of *verify every stated requirement exhaustively, once, before the thing is trusted* — which is exactly what a first practitioner session is |

**The demo-credentials document is the load-bearing one and its own history is
the argument.** It records that Michael held credentials for no app, that live
click-through was "substituted for, worked around, or skipped for weeks", and
that on 2026-09-03 two production bugs were found **only** because one licence
happened to have a documented PIN — both with a full green suite behind them,
neither findable without signing in. A practitioner validation without working
credentials is not a validation; it is a demo.

## 3. The instrument: what a practitioner session must produce

Modelled on FAI rather than on a satisfaction survey, because the failure mode
is identical — a claim nobody checked. Per vertical, the session produces a
record with these fields, and **an empty field is a finding, not a blank**:

1. **VERTICAL AND CREDENTIAL** — which app, which licence, which role signed in.
   A session run as `owner` validates nothing about the roles a real practice
   uses; the platform's own role-gate incidents are all about non-owner roles.
2. **THE TASK THEY CAME TO DO, IN THEIR WORDS, BEFORE THEY SEE THE APP.**
   Recorded first so it cannot be retro-fitted to what the app happens to do.
3. **COMPLETED / BLOCKED / ABANDONED, per task** — three states, and *abandoned*
   is distinct from *blocked*: blocked is the app refusing, abandoned is the
   practitioner giving up while the app kept working. Collapsing them loses the
   only signal about confidence.
4. **EVERY REFUSAL THEY HIT, with the code and whether they understood it.**
   This platform has spent weeks on 401-vs-403 and on messages that name the
   wrong fix; a practitioner is the only reader who can say whether a refusal
   told them what to do.
5. **EVERY NUMBER THEY DID NOT BELIEVE.** The fabricated-KPI class is the one
   defect family a practitioner detects instantly and no checker can: they know
   what a plausible collection rate looks like in their own practice.
6. **WHAT THEY EXPECTED THE APP TO DO AND IT DOES NOT** — the absent-feature
   half, which no test can report because a test only knows what exists.
7. **THE FACILITATOR'S OWN CONFLICT, DECLARED.** If a SAIRN session sat beside
   them and answered questions, the session measured a *guided* run, which is a
   different claim from *a practitioner used it*. Both are useful; only one may
   be reported as the second.

## 4. Two rules that make it evidence rather than an anecdote

**A SESSION IS ABOUT THE BUILD IT RAN ON.** FAI's own rule, and it transfers
exactly: the record carries the app file's hash at session time. The day the
file changes, the session stops being a statement about the app, and nothing
announces that — which is discipline 8 applied to the most expensive evidence
this platform can gather.

**THE FACILITATOR MAY NOT ALSO BE THE REVIEWER.** The same separation the Tier A
gate already enforces on code. A session written up by the person who built the
feature shares the blind spot that produced it, and here the blind spot is
worse: they know which parts to steer toward.

## 5. What is NOT built, and the honest reason for each

* **The recruiting.** Unchanged from cody's refusal. No tool substitutes for it.
* **A tool to hold these records.** Deliberately not built: there are ZERO
  practitioner sessions today, and this platform has recorded five separate
  tools that shipped able to judge with nothing to judge (the FMEA loop at 0%,
  the claim-provenance chain at three self-authored records, items 62 and 68
  data-blocked, item 99 unenforceable). **A sixth would be the same mistake.**
  The recording side comes when the first session is scheduled, and its shape is
  above so it does not have to be invented under time pressure.
* **A verdict on whether the apps are ready.** Nobody outside this team has used
  them. That sentence is the current answer and no amount of tooling changes it.

## 6. The one thing to do before the first session

**Run `sql/demo_owner_credentials_2026-09-03.sql`.** It is Michael's to run, it
is already written, and until it runs there is no vertical a practitioner can
sign into — so item 72 is blocked on one paste, not on a build. That is the
entire critical path and it is worth saying plainly rather than leaving it
inside a table.

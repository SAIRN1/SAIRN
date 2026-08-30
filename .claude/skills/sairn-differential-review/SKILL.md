---
name: sairn-differential-review
description: Review a CHANGE, not a codebase — what this diff does that the file did not do before, and what else must agree with it for the change to actually work. Trigger before every commit and every push, on every PR, and any time a diff touches a validator, a schema, a grant, an auth gate, a shared file, or a seed. Distinct from sairn-code-scrubber (bug patterns inside a file) and sairn-adversarial-reviewer (hostile personas on a feature) — this one is about the DELTA and its blast radius. Every check below comes from a real SAIRN incident where the code was correct and the change still broke something.
---

# SAIRN Differential Review

Reviewing a diff is not reviewing a file. A diff can be individually correct on
every line and still be wrong, because the thing it needed to agree with was not
in the diff. Every item here is a real incident on this platform.

Run it on `git diff --cached` before commit, and on `git diff origin/main...HEAD`
before push.

---

## 1. Check the diff SHAPE before reading the diff

**Incident:** a commit intended to add one array entry to `api/sd-data.js`
landed **88 insertions**, 87 of them another session's uncommitted handler
branch, and was pushed before anyone noticed. `node --check` passed the whole
time — syntax was never the problem.

    git diff --cached --numstat

**If the line counts surprise you, stop.** Four sessions work in four clones on
this repo; `git add <shared file>` sweeps in whatever else is dirty. Confirm the
numbers match what you meant to change *before* reading a single line of
content.

## 2. Name what else must agree — the two-files-one-change class

**Ask explicitly: what else has to be true for this change to work?** Then check
that thing, rather than assuming it followed.

**Incident:** California's service extensions needed a new rule shape. The
engine (`api/_lib/deadline-engine.js`) was taught it. Its validator, in the
separate file `api/legal-deadlines.js`, was not — it still required `add`
unconditionally. **84 of 84 isolation tests passed the whole time**, because
they call the compute function directly and never touch the storage validator.
All seven California civil rows were unstorable. The real write found it
instantly: `400 INVALID_RULE`.

Known pairs on this platform, all of which have broken at least once:

| Change here | Must also agree |
|---|---|
| compute engine | the storage validator in the *other* file |
| client-side cap | the SQL `CHECK` constraint |
| seed file | the live licence (a seed edit is **inert** until a loader runs) |
| new table | its `GRANT`, and for the verbs the CODE calls |
| endpoint role gate | the test harness's headers |
| `process.env.X` read | the variable actually existing in Vercel |

## 3. A grant must cover the verbs the CODE calls, not the verbs the schema granted

**Incident:** `sairncash_waitlist` was created and reported provisioned. Every
public signup returned 502 for hours. The grant was `select, insert`; the
endpoint used `ON CONFLICT DO UPDATE`, which requires **UPDATE at plan time even
when no conflict ever occurs**. A privilege check asking only "is INSERT
present?" came back clean.

Read the endpoint first. `Prefer: resolution=merge-duplicates` means
`ON CONFLICT DO UPDATE` means UPDATE is required.

## 4. A comment that describes a CONDITION becomes a lie when the condition changes

**Incident:** `dnt_cred_rules`' write branch carried a comment saying there was
no role gate *"because SAIRNdental has no employee auth,"* and asking whoever
added auth to come back and re-gate it. Auth was added. Nobody came back. The
comment stopped being true without changing, so the gap went back to being
undiscovered — any signed-in employee could rewrite a state credentialing
requirement.

**In review: if the diff changes a condition, grep for comments that assert it.**
Nothing checks comments.

## 5. Blast radius is "who can reach this now that could not before"

For any diff touching auth, a gate, or a resource registration, state in one
sentence: **who could not do this yesterday and can today, or vice versa.** If
you cannot say it in one sentence, the change is not understood well enough to
push.

Widening is the direction people check. **Narrowing needs the same scrutiny** —
tightening a bound refuses payloads someone downstream may be relying on, and
that belongs in the commit message.

## 6. Tests that cannot reach the code they name

**Incident:** `api/_lib/dental-credentials-endpoint.test.js` ran **1 passed / 15
failed** and had for some time. Its harness sent no `x-sd-auth` header, so every
branch 401'd after auth was added. The single passing test —
*"evaluate writes NOTHING"* — passed **for the wrong reason**: a 401 issues no
writes either.

**In review:** if the diff changes an auth gate or a required header, the test
file is part of the blast radius. And a green test that would also be green if
the feature were deleted is not evidence.

## 7. Does the diff claim a behaviour it does not verify?

Grep the diff's own additions for `success`, `saved`, `complete`, `verified`,
`live`. Each one is a claim. For each, find the code that makes it true.

**Incident class this exists for:** a fire-and-forget write showing "Saved"
while the write failed. See `sairn-silent-failure-sweep`.

## 8. Seed and data changes are inert until something loads them

**Incident:** two committed SAIRNlaw corrections changed seed *files*. A seed
file change does nothing until `load_deadline_seed.py` runs, and nobody ran it.
`LAW-PINNACLE-2026` computed federal answer deadlines **three days late for a
day**, and it was found by accident.

**If the diff touches `sql/*_seed*.json`, the review is not done until the live
licence is confirmed to match** —
`python tools/sairn_load_state_check.py --app <app>`. The push gate hook
enforces this; do not rely on remembering.

## 9. Deleting? Verify supersession topic-by-topic, not summary-by-summary

**Incident:** `security-auditor` was assessed as superseded by `owasp-security`,
with a six-field reporting template as *"its one unique asset."* Checking
topic-by-topic before deleting found **three more topics it named that the
replacement did not** — XSS by name, CORS, JWT. The assessment was about 75%
right: confident enough to act on, incomplete enough to lose content.

**A supersession claim is a claim like any other.** Enumerate the topics in the
thing being removed and grep each one against the replacement.

## 10. Line endings are not content

This repo stores blobs as **LF** and checks them out as **CRLF**
(`core.autocrlf=true`, and `.gitattributes` is scoped to `docs/skill-backups/`
and `scripts/*.sh` only). A diff that touches every line of a 2 MB file is
unreviewable, and a real change can hide inside 34,000 lines of noise.

> **Corrected 2026-08-30.** This rule previously read *"mixed line endings,
> file-by-file — `api/sd-data.js` is CRLF, `sairncare.html` is LF."* Measured in
> this clone, **both files are CRLF in the working tree and LF in the stored
> blob** — the specific contrast does not hold here. The hazard is real but its
> mechanism is the autocrlf round trip, not per-file divergence: an editor that
> rewrites endings produces a whole-file diff that git then normalises away,
> hiding the real change in the noise until commit.

`sed -i` is unsafe here. Detect the file's existing ending and preserve it
explicitly. A size difference of exactly one byte per line is CRLF, not drift —
normalise before calling anything diverged.

## 11. Verify against a marker that exists ONLY in this change

**Incident:** a live-verification grep for a colour fix returned a hit and read
as confirmation. The hit was a *different, pre-existing* code path containing
the same substring; the change had not deployed. A false green is worse than no
check, because it stops you looking.

Grep for a new function name or a distinctive comment fragment — never a generic
pattern the file already contained.

## 12. Push is a command; present-on-the-remote is a fact

`git push` can exit 0 without the commit arriving — wrong remote, credential
manager serving another account, empty directory. After push, query the remote:
the expected SHA on `origin/main`, and for a content change, fetch the real file
and compare.

`pushed_at == created_at` on a GitHub repo means **nothing has ever been
pushed**. Cheapest tell there is, and not obvious.

---

## The one-paragraph version

A diff is a claim that the world still works. Check the shape before the
content; name what else must agree and go look at it; say who gained or lost
access in one sentence; and treat every "verified", "superseded" and "pushed"
in your own review as a claim needing evidence, not a conclusion.

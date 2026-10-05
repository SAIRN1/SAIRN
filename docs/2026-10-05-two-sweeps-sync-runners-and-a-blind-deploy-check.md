# Two sweeps: test suites that print green over a failed async arm, and a deploy check that never runs on the platform's own push path

**Written 2026-10-05 (Fourth). FINDINGS AND A PROPOSAL. No test suite and no
hook was edited.** Both sweeps came out of the same defect found in
`tests/sairnsenior_negative_hours_claim.js` earlier today, and both findings
are driven rather than inferred.

---

## PART 1 — the sync-runner sweep

### What was looked for

A test file that hands **async** arms to a **synchronous** runner
(`try { fn(); pass++ } catch`). The runner returns before the arm's assertions
run, counts it a pass, and the failure surfaces later as an unhandled
rejection — after the summary has already printed.

### Population and result

**661 JavaScript test files scanned**, of which **138 hand async arms to a
test/check helper**.

| | count |
|---|---|
| runner awaits (fine) | **121** |
| **sync runner, no await** | **2** |
| no await and no sync runner — could not tell | **15** |

The 15 are **not** a clean bill. They are files where neither an awaiting
runner nor the `try { fn() }` shape matched, so the screen could not decide.
They are named in §1.4 rather than folded into the 121.

### 1.1 CONFIRMED by planting, not by reading

`tests/sairnbuild_server_backup.js` — 8 async arms. An assertion planted
**after an `await`** inside one of them produced:

```
  ok   server records absent locally are appended
ALL 29 SERVER-BACKUP ASSERTIONS PASS
AssertionError [ERR_ASSERTION]: PLANTED FAILURE AFTER AN AWAIT
```

**The failing arm reported `ok`. The summary claimed all 29 passed. The truth
printed after both.** The process did exit 1, so CI is safe — but a human
reading that output sees green and stops. That is PR 1.5: the expensive part
of a false success is the success message printed after the error.

**The first plant tested the wrong thing and is worth recording.** Placed
*before* the first `await`, the assertion threw synchronously and crashed
loudly — which looks like the suite working. Only a failure *after* an await
reaches the blind spot. A sweep that planted at the top of each arm would have
reported both files clean.

`tests/dnt_vendor_write_confirmation.js` — 5 async arms, same runner shape
(`:45-47`), same exposure.

### 1.2 The fix, which is NOT applied here

The pattern already proven in `tests/sairnsenior_negative_hours_claim.js`:

1. **Queue arms and `await` them** in a `runQueue(queue, log)`.
2. **Count unhandled rejections** instead of exiting on the first, so the
   summary can see them.
3. **Wait one macrotask** (`setImmediate`) before printing anything, so a
   rejection left by a `setTimeout` arm lands first.
4. **Reconcile arms-queued against arms-tallied** — an arm that never ran
   contributes to neither and is invisible in "N passed, 0 failed".
5. **Print `RESULT WITHHELD`** rather than a tally the run cannot stand behind.

**Not applied because rewriting the runner of two suites I do not own is a
bigger change than this sweep was asked to make, and both suites are currently
GREEN** — the defect is latent, exposed only when an arm actually fails. It
should be done, by whoever owns those suites or with an explicit go-ahead, and
it is a mechanical change: the senior suite is the worked example.

### 1.3 What the sweep cannot see

* **A runner that awaits but whose SUMMARY still prints early.** That was the
  third defect in the senior suite and this screen does not look for it; the
  121 "fine" files were checked for an awaiting runner, not for a guarded
  summary.
* **`check()`/`it()` helpers with unusual names.** The regex covers
  `test|check|it|arm`.
* **Python suites.** Scope was JavaScript only.

### 1.4 The 15 undecided files, named

`api/dnt-bi.test.js` (49 async arms), `api/_lib/employee-lifecycle.test.js`
(36), `tests/sairndental_write_failure_voice.js` (15),
`api/sc-credentials.test.js` (14), `tests/sairnlaw_invoiced_sync.js` (13),
`api/greeting.test.js` (13), `tests/sairnlaw_billable_rate.js` (10),
`tests/sairndental_coverage_edit.js` (8),
`tests/sairndental_unlinked_referral_queue.js` (7),
`tests/sairndental_settings_patch.js` (6), `api/sairnvet-transcribe.test.js`
(6), `api/_resources/app-boundary.test.js` (6),
`tests/sairnbiz_timesheet_hours.js` (4), `tests/stonedesk_server_backup.js`
(1), `api/_lib/sairnlaw-define-tool.test.js` (1).

**Settling these needs the same plant-after-an-await treatment, one file at a
time.** Reading them is not enough — reading is what missed the senior suite.

---

## PART 2 — a generic text match that silently skips the deploy check

### The finding

`tools/deploy_verify_notify.py:57` decides whether a Bash command was a push:

```python
if "git push" not in cmd:
    sys.exit(0)
```

**`tools/push_retry.py` pushes at line 610 via `git('push', 'origin', 'main')`
— a subprocess.** The Bash command string the hook sees is
`python tools/push_retry.py --loop`, which contains no `git push`.

**So the post-push deploy check never runs for the platform's own documented
contended-push path, and says nothing when it skips.**

That path is not an edge case. `push_retry.py` exists because five clones push
to one branch; it is what a session is told to use exactly when the branch is
busy — which is when a deploy is most likely to be disturbed. I used it twice
today.

### The same four lines are wrong in the other direction too

`"git push" in cmd` also matches a command that merely **mentions** a push —
`echo "run git push later"`, or a commit message containing the phrase. That
produces a deploy verification of a push that never happened, whose result is
then reported as though it meant something.

And `tool_response.get("success") is False` treats a **missing** `success` key
as a successful push. Wrong direction, but minor.

### Why this is the same defect as the push-failure misdiagnosis

Both match a **generic token** that correlates with the event instead of
identifying it. `error: failed to push some refs` is present for every push
failure, so matching it classifies nothing; `git push` is present in some
pushes and absent from others, so matching it detects nothing reliably. In
both cases the failure is **silent** — no output, no third state.

### Proposed fix, in the shape `tools/push_failure_reason.py` uses

1. **Detect the push from what HAPPENED, not from the command text.** The hook
   already has git available: compare `origin/main` before and after, or read
   `tool_response`. A command that moved `origin/main` pushed, whatever it was
   spelled like.
2. **If it cannot tell, SAY SO.** Right now the only outcomes are "checked" and
   "silently nothing". A third state — *"this looked like it might have pushed
   and I could not confirm"* — is what the hook's own comment already demands
   of its 403 branch: *"a check that silently stops running is the failure this
   hook was rewritten to remove."* The same sentence applies to its own
   entry condition.
3. **Cheap interim, if (1) is too invasive:** widen the match to cover
   `push_retry.py` and `sairn_claim.py` (which also pushes), and add a comment
   saying the list is a stopgap for a detection that should not be textual.

**Not applied. `deploy_verify_notify.py` is unclaimed, but it is a live hook
that fires on every push, and changing how it decides to run is not something
to do unprompted in the same batch that found the problem.**

---

## What both parts have in common

A screen that looks for the thing it expects to see, finds it or does not, and
reports **nothing** when it cannot tell. The fix in both cases is the same
three words the push classifier already implements: **could not tell** is a
verdict, and it has to be printed.

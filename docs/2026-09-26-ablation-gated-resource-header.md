# Item 98 ablation — `tests/gated_resource_direct_fetch_header.js`

**2026-09-26 (Cody). Methodology item 98: remove ONE named layer on
already-clean code and measure what it alone catches.**

**VALIDATED VERDICT: the safeguard is NOT redundant. It catches its own defect
class, and NOTHING ELSE on the platform catches it — zero of 120 candidate
layers.**

**AND THE FIRST RUN SAID THE OPPOSITE, WHICH IS THE MORE USEFUL HALF OF THIS
DOCUMENT.** The first ablation reported that the safeguard missed its own defect
while nine other layers caught it. Every part of that was wrong, and it was
wrong in a way that read as a clean, quotable result. §3 is what it took to find
out.

---

## 1. The layer, and why it was the right target

`tests/gated_resource_direct_fetch_header.js` (cc, 2026-09-25) asserts that
every DIRECT `fetch` naming a resource in `SD_SESSION_GATED` carries the
`X-SD-Auth` header. It exists because SAIRNdesign's session gate was measured by
counting `sdnData(` call sites — sound, and blind by construction to a path that
does not use the transport. The invoice-create path is exactly that, and from
the moment the gate landed every invoice creation returned 403 while the user
was told *"Saved on this device only — server sync failed"*. A wrong reason for a
real data loss, on a money record.

**It sweeps two sites** across 17 app files: `sairndesign.html:3059`
(`sdn_invoices`) and `stonedesk.html:38795` (`slabs`).

---

## 2. Method

A detached worktree at `885b25a7`, never the live clone. Candidate "other
layers" were derived **mechanically, not chosen**: every file under `tests/` and
`api/*.test.js` that reads the mutated app file, or sweeps `*.html` — **120 for
`stonedesk.html`**. The safeguard itself was excluded from that set.

---

## 3. THE FIRST RUN WAS INVALID IN THREE SEPARATE WAYS

Recorded in full because a reader who only sees §4 would learn the wrong lesson.

### 3.1 M1 was never planted, and the harness said so

The mutation for the real defect (SAIRNdesign invoice-create losing its header)
refused to apply: the anchor was not unique. The harness recorded
`"planted": false` and counted it neither way. **That part worked** — the one
piece of the first run that behaved correctly.

### 3.2 M2 removed the WRONG LINE, and "token-free" was measured in the wrong window

M2 removed the last `X-SD-Auth` line within 1500 characters before the `slabs`
call. The safeguard reads its window as **the paren-matched call segment plus
the 900 characters before it** — a different span. Worse, the two lines are near
duplicates differing only in whitespace:

```
removed:                try{ var tok = sessionStorage.getItem('sd_session_token'); ...   <- SPACED
actually guarding:      try{ var tok=sessionStorage.getItem('sd_session_token');  ...   <- UNSPACED
```

So the site kept its real token and **the safeguard's `rc=0` was CORRECT — there
was no defect to catch.**

**AND MY OWN VALIDATION CHECK (b) CONFIRMED THE WRONG THING.** It reported the
window token-free, because it located the enclosing call with
`rfind('fetch', 0, j)` while the safeguard locates it by scanning `fetch\s*\(`
forward. Two different windows, one of which really was clean. **A validation
that re-implements the thing it validates can agree with itself and still be
wrong** — the same second-copy-of-a-signature shape that broke this session's
probe spy.

The fix was to stop re-deriving and instead **run the safeguard's own detector**
and print `hasToken` per site. It said `true`. That single line settled it.

### 3.3 The nine "detections" were nine PRE-EXISTING FAILURES

The check named for this was: re-run the nine against a whitespace-only edit, so
a layer that merely refuses a dirty tree shows up as cascade rather than
detection. The result went further than the hypothesis:

| condition | of the nine, how many red |
|---|---|
| stonedesk.html mutated | 9 |
| stonedesk.html whitespace-only edit | **9** |
| **clean tree, untouched** | **9** |

**All nine are red at baseline.** They are not cascade and they are not
detection — they are simply failing, and every one of them appears in the
independent 56-failure pinned-run list. **The first ablation's headline was an
artifact of counting pre-existing red as a catch.**

---

## 4. THE VALID MUTATION, AND THE REAL RESULT

Planted by removing **every** `X-SD-Auth` occurrence inside the safeguard's own
900-character window — verified token-free by the safeguard's own detector
(`hasToken=false`), not by a re-implementation.

| | |
|---|---|
| **the safeguard** | **CAUGHT IT.** `FAIL every direct fetch naming a gated resource carries the session token` → `stonedesk.html:38794 -> slabs`, exit **1** |
| restored tree | exit **0** |
| **the other 120 layers** | **zero detections.** The nine that go red do so on a clean tree too. |

**So the layer is pulling its own weight and is not redundant with anything.**

### 4.1 One measurement error of mine worth recording

On the first reading of the valid mutant I recorded `rc=0` while the suite had
plainly printed `FAIL`. The cause was mine: `${PIPESTATUS[0]}` read from outside
a `( cd … && node … | tail )` subshell, so it reported the subshell rather than
node. Measured cleanly: **valid mutant `rc=1`, restored `rc=0`.** A harness that
misreads an exit code is the defect this platform has already recorded for a
pipe swallowing a verdict.

---

## 5. What this ablation does NOT establish

- **M1 was never driven.** The defect the safeguard was actually built for — the
  SAIRNdesign invoice-create path — could not be planted with a unique anchor,
  so its coverage of that specific site is still untested by ablation. The suite
  has a named arm asserting that site is among those swept, and that arm passes;
  that is weaker than a planted defect.
- **Two sites is the whole coverage.** The safeguard's value is real and narrow:
  17 app files, two direct-fetch sites. Its worth is as a tripwire for the NEXT
  gate, not as coverage of a wide surface.
- **Nine failing suites are a separate finding** and are triaged in
  `docs/2026-09-26-pinned-run-triage.md`, not here.

---

## 6. THE METHODOLOGY LESSON, which outlasts the verdict

**An ablation is a measurement, and a measurement needs its own control.** The
first run produced a clean, plausible, fully-wrong answer — safeguard blind,
nine peers covering for it — and nothing in its output hinted at trouble. Three
independent errors had to align to produce it, and two were in the harness
rather than in the subject.

**What caught each one:**

| error | what caught it |
|---|---|
| wrong line removed | running the SUBJECT's own detector instead of re-deriving its window |
| validation agreed with itself | noticing the validator re-implemented the thing it validated |
| pre-existing red counted as detection | a baseline run on a clean tree |

**The baseline run is the cheapest and it was the decisive one.** An ablation
that does not measure the unmutated state first cannot tell a catch from a
suite that was already red — and on this platform, with 56 failing files, that
is the default condition rather than an edge case.

**Item 98's own instruction says ablation is measured per ARM, not per exit
code. This run shows the prior step: per arm, on a baseline you established
yourself, before you trust a single number the harness prints.**

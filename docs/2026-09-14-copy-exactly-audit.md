# Copy Exactly — is the re-qualification actually happening?

**2026-09-14 (Hank).** The question asked: does SAIRN's real Copy-Exactly
propagation do the re-qualification `docs/2026-09-13-cross-domain-disciplines.md`
§7 describes — scale, input range and criticality tier re-checked before a
pattern is propagated — or is §7 a documented discipline nobody applies?

**The answer is worse than "nobody applies it", and it is worse in a way that
makes §7's point better than §7 does.**

---

## 1. There is exactly one literal Copy-Exactly block, and it has rotted

Searched the whole tree. One match outside the skill backups:
`SAIRNVET-FINAL-SPEC.md`, *"SAIRN CLAUDE ENGINE — Copy Exactly"*, a fenced
JavaScript block of five functions.

Compared against what `sairnvet.html` actually runs:

| | count |
|---|---|
| byte-identical to the spec | **0** |
| same code, reflowed only | 1 (`escHtml`) |
| **differs in substance** | **4** |
| absent from the app | 0 |

**Every one of the four is the app having been fixed and the document not.**

| Function | The spec still says | The app does |
|---|---|---|
| `svStore` | `try{localStorage.setItem(…)}catch(e){}` | `return st('sv_'+k,v);` |
| `svLoad` | `try{…}catch(e){return d;}` | a real error path that logs |
| `showToast` | assumes the toast element exists | carries the 2026-09-05 *"no toast element is a real state, not an impossible one"* fix |
| `callClaude` | no severity argument | passes `'error'` |

**So the propagation source ships a storage wrapper that swallows its own
failure.** Anyone starting a new app from this spec today reintroduces a
silent-failure write — the defect class this platform has spent more time
removing than any other.

**A block labelled *Copy Exactly* that no longer matches its own app is not a
propagation aid. It is a propagation vector.** Nothing was watching it.

## 2. What §7 asks, and what is actually in place

§7 wants three questions answered before a proven pattern moves:

| | Asked anywhere today? |
|---|---|
| **SCALE** — same order of magnitude as where it was proven? | **No** |
| **INPUT RANGE** — can the target receive values the source could not? | **No** |
| **CRITICALITY TIER** — same tier? | Only in the sense that `docs/CRITICALITY-TIERS.md` exists and nothing consults it at propagation time |

And the prior question — *does the source still match its own target* — **was
not being asked either**, which is the one this audit answers.

**§7's own prediction was right and is worth quoting against itself:** *"a
propagation tool that verifies byte-identity and nothing else is faster at
making this exact mistake, on more resources, than a human doing it by hand."*
What was found is one notch earlier than that: there is no propagation tool at
all, the byte-identity was never checked either, and the source drifted.

## 3. Built: `tools/copy_exactly_check.py`

Four states, never collapsed — `identical` / `reflowed` / `differs` / `absent`.

**`reflowed` is a state of its own on purpose.** Three false alarms on this
platform came from calling a whitespace difference a change (CRLF, 2026-09-03),
and a checker that reports a re-wrapped line as drift is one people switch off.
The probe pins this in both directions: a re-wrapped body must read `reflowed`,
a substantive change must read `differs`, and arm 4b asserts the two fixtures
gave *different* answers, so arm 3 cannot be passing because everything reads as
reflowed.

**It fails closed four ways**, none of them a pass: missing spec, missing app,
**renamed heading** — the case a naive checker would report as a clean sweep
while looking at nothing — and a block containing no functions at all.

`tests/run_copy_exactly_probe.py`, 17 arms. Arm 1 runs it against the real
repository so the fixture arms are not the only thing holding it up.

## 4. What this does NOT do, stated because a green run is misleading

**It does not answer §7.** It checks that the bytes still agree, and **agreeing
bytes are precisely what §7 warns is not safety.** The re-qualification half —
a refusal to propagate without a recorded answer on scale, input range and tier
— is **unbuilt**, and §7 itself says why it cannot be automatic: *"scale and
input range need somebody who knows the target; only the tier is already written
down."*

**It watches one block.** The wider propagation on this platform is not a
document at all — it is thirteen apps that grew the same `st()` / `ld()` /
`escHtml` shapes by copy-paste, and no checker knows those are meant to be the
same. Measured while auditing: **20 of the root apps carry at least one bare
`catch(e){}`**, 159 in `stonedesk.html` alone. **That number is a pointer, not a
defect count** — a bare catch around a non-critical parse is fine, and
classifying them is a separate job. It is here only to show the copy-paste
surface is two orders of magnitude larger than the one block with a label on it.

**Function extraction is regex plus brace matching, not a JS parse.** A function
expression assigned to a var, or a body containing a brace inside a string or
regex literal, is a shape this cannot see — the same blind-spot class that let
`tesseract.js` sit unregistered in the SOUP register, and it is written into the
tool's own output rather than left here.

## 5. The open decision

**What should the canonical source be?** The block is left unchanged on purpose:
`svStore` now delegates to `st()`, a helper that is not part of the block, so the
current app version is **not self-contained either** and pasting it would not
work. Three real options — this document, `sairnvet.html`, or a genuine shared
module the apps import — and they differ in cost and in what they make possible.
**Left for Michael.** The spec now carries a warning not to copy the block as it
stands, which is true regardless of which way that goes.

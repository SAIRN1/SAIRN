# Item 43 stops being a convention — and its first finding is ours

**2026-09-26 (cc).** `docs/2026-09-13-cross-domain-disciplines.md` item 7 — the
Ariane 5 Flight 501 lesson — has said since 2026-09-13 that propagating a proven
pattern requires an explicit re-qualification against the **target's** scale,
input range and criticality tier, and not merely a diff proving the bytes match.

**Nothing enforced it.** `tools/copy_exactly_gate.py` does now, and the first
thing it caught was this session's own work.

---

## 1. What the gate does, and the line it will not cross

It reads the outgoing commits, finds blocks of code **added to one file that
already exist in another**, and refuses the push unless the commit message
carries the three answers:

```
copy-exactly: sairnvet.html <- sairnbuild.html
  scale: ...
  input-range: ...
  tier: ...
```

**It does not judge whether a propagation is safe, and says so in its own
header.** It cannot: safety *is* the answer to those questions and the answers
are judgements. It refuses a propagation with **no answer recorded** — which is
precisely the gap item 7 describes, because the Ariane copy was faithful and the
review that would have caught it was never asked for.

**It is not a duplicate of `tools/copy_exactly_check.py`.** That tool asks *is
the SOURCE still right?* — it compares the one literal Copy-Exactly spec block
against what `sairnvet.html` actually runs, and measured 0 of 5 functions
byte-identical on 2026-09-14. Its header explicitly declines section 7's real
question. This is that question. The two probes are one word apart
(`run_copy_exactly_probe.py` / `run_copy_exactly_gate_probe.py`), which is worth
knowing before editing either.

---

## 2. Calibrated before it was wired in

A gate nobody can satisfy gets overridden, and then it is decoration with a
process around it. So the thresholds were measured against real history first:

```
python tools/copy_exactly_gate.py --measure 120
→ 1 of 120 commits would be flagged (0.8%)
```

The criteria are stamped `CRITERIA_VERSION = 2026-09-26.1`: a block must carry
**≥ 8 significant lines** (comments, blanks, punctuation-only lines and module
preamble removed) and be **≥ 60% distinct** so a repeated data table is not read
as a propagated mechanism. The blind lock carries six fixtures **in both
directions**, including the three near-misses that matter: the same file gaining
a second copy (not this gate's subject), a short shared CORS preamble (below the
floor), and a long repetitive table (a literal, not a mechanism).

---

## 3. The one commit it flagged is ours, and the finding is real

```
b015ea78  2 propagation(s)
    sairncode.html <- sairnbuild.html (11 lines) function sfFence(label,text){
    sairnvet.html  <- sairnbuild.html (11 lines) function sfFence(label,text){
```

That is this session's prompt-fence work. Its commit message said the copies
were **"byte-identical copies, not variants"** — which is exactly the
diff-proves-the-code-matches reasoning item 7 exists to refuse. The
re-qualification was never done. Doing it now:

**SCALE — no change.** `sfFence()` is called once per prompt build on a single
form-field string of at most a few hundred characters. sairnbuild fences a job
note and a disruption description; sairnvet a case note; sairncode a procedure
description and two code fields. No loop, no accumulation, same order of
magnitude.

**INPUT RANGE — one new shape, and it is already covered.** sairncode's second
code field is *optional*, so the fence can be called with an empty string, which
sairnbuild's call sites could not produce. `fencedBlock()` returns `''` on empty
or whitespace-only input rather than emitting an empty fence, and
`tests/prompt_fence_mirror.js` drives exactly that (`empty string`,
`whitespace only`, `null`, `undefined`). No other new value class reaches it:
all inputs are short free text from a form field.

**CRITICALITY TIER — IT ROSE, AND THIS IS THE ANSWER THE BYTE-DIFF HID.** The
pattern was proven on SAIRNbuild's trade-coverage and disruption prompts. The
targets are different in kind:

| | source | targets |
|---|---|---|
| sairnbuild | job note → trade-coverage summary | — |
| sairnvet | — | case note → **clinical decision support** (differentials, urgency flags), persisted to `sv_peerconsults` |
| sairncode | — | description and CPT/HCPCS codes → **billing determinations** a coder acts on |

**What that means concretely, rather than as a label:** the fence is a
*labelling mitigation, not a filter* — its own header says the only thing proven
is mechanical, that the text cannot close the fence, and that whether the model
honours the instruction is a question only a model call answers. That residual
failure mode now sits on a clinical suggestion path and a billing path rather
than on a trade summary. The mitigation did not get weaker; **the consequence of
its residual failure got worse, and nothing in the propagation recorded that.**

**Action taken from this re-qualification:** none to the code — the fence is
still the right mitigation and there is no better one available without the
model-call red-teaming that
`docs/2026-09-13-ai-red-teaming-scoping.md` defers. What changes is that the
tier rise is now written down where the next person propagating this block will
see it, which is the entire point of the discipline.

---

## 4. What this does not claim

- **A recorded answer is not a correct answer.** The gate checks that three
  questions were answered in a real sentence; it cannot check the sentences.
  `tier:` must name something, because "same tier" with no names is what gets
  typed when nobody looked — that is as far as a regex can push.
- **Detection is not complete.** The floor is 8 significant lines, so a
  propagated 5-line guard passes unseen, and a block reworked beyond
  comment/whitespace changes will not match. Both are stated limits, not
  assumptions of completeness.
- **0.8% is a rate over 120 commits of this repo's recent history**, not a
  general false-positive rate. Re-run `--measure` before trusting it, and
  before changing any threshold.
- **It fails open on its own internal errors**, deliberately and to the same
  standard as `.githooks/pre-push`: a gate that crashes closed gets disabled and
  then protects nothing. A detected propagation with no record exits 1; a range
  it cannot read exits 2 — could-not-run, never folded into a pass.

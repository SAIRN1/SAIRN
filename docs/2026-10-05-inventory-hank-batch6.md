# Hank inventory — batch 6, 2026-10-05

---

## 0. Premise log (item 7 methodology)

| Item | Premise at HEAD |
|---|---|
| 1 row 82 | **HELD, and NOW APPLIED** — not delivered a fourth time |
| 2 ranking | **HELD** — and it was 34 citations platform-wide, not one row |
| 3 enforcing path | **HELD** — and the fix had a real regression risk that had to be driven |
| 4 self-comment match | **HELD** — 22 absence assertions; 2 mine, fixed; **my first fix did nothing** |
| 5 `sairncash_usage` | **HELD, inverted** — not a missing cap; a bar implying one that was promised not to exist |
| 6 repoint queue | **ALREADY COMPLETE** — zero old citations remain |

---

## 1. Landed, with shas

| What | Sha | Verified by |
|---|---|---|
| Row 82 retracted, row 845 closed — **applied** | `0eb453fc` | `md_table_check` 827/827, 0 malformed; pipe counts asserted |
| Push gate enforcing path collects **all** denials | `0eb453fc` | `run_push_gate_preflight_probe` **13/0**, incl. E3 known-bad |
| Drift ranking: direct reference outranks distance | `0eb453fc` | `run_citation_line_drift_probe` **22/0**; sd_comms proved both ways |
| `tools/pycomments.py` + two probes fixed | `0eb453fc` | 6-case selftest; injection-proved load-bearing |
| `sairncash` usage bar no longer implies a cap | `0eb453fc` | `checkblocks` 3 blocks 0 failed |

---

## 2. The claim-registry distinction that nearly cost row 82 a fifth round

`python tools/sairn_claim.py list` showed **no cc claim**, so the index looked
free. The claim *check* **REFUSED** it:

    REFUSAL RECORD: cc held 'cc' on docs/SAIRN-OPEN-WORK-INDEX.md
    (registry, not yet on origin)

**`list` reads the committed claim files; `check` reads the live registry
outside every clone.** A session that trusts `list` will edit a file somebody
holds. Re-checked later in the batch — CLEAR — and applied then. **This is
why the brief's "re-check the claim fresh before honoring" is not ceremony**,
and it is the one procedural thing from this batch worth carrying forward.

---

## 3. Item 2 — the measured payoff, and what it does not fix

    before  SOUND 220  DRIFTED 170  INCONCLUSIVE 54
    after   ANCHORED 162  SOUND 92  DRIFTED 136  INCONCLUSIVE 54

**34 citations were being reported DRIFTED while directly referencing their own
resource.** The mis-ranking was not a one-row curiosity.

**What it still does not do, and must not pretend to:** the tool now answers
"is this line about the resource", not "is this the right line for this cell's
argument". `sd_comms:10606` (`var d=load();`) anchors at one hop and that is
correct — it genuinely references `sd_comms` — even though the auditor judged
the *better* citation to be the `commsEnsureIds()` call. Choosing between two
lines that both reference the resource is prose, and the remaining **136
DRIFTED is still a candidate list, not a work list.**

---

## 4. Item 3 — the regression that collecting would have shipped

The gate ends `except Exception: sys.exit(0)` — **exit 0 means ALLOW**. Code
after a `deny()` was written knowing it would never execute.

    with the denial-outranks-fail-open line:     exit 1, both reasons printed
    without it (known-bad, reconstructed):       exit 0 -- ALLOWS the push

So collecting without touching that handler would have turned the **first**
continuation crash into a silent allow — strictly worse than reaching one
check. Arm E3 holds the line in place.

---

## 5. Gaps

| # | Gap | Severity |
|---|---|---|
| **1** | **`sairncash` sidebar hardcodes `Plan: Pro`** | **MODERATE**, new |
| **2** | **`register_feed_gate.py` crashes printing its own docstring** | **MODERATE**, new — 5th cp1252 |
| **3** | 20 of 22 absence assertions still unstripped (not mine) | **MODERATE** |
| **4** | 136 DRIFTED citations need per-cell prose reads | **MODERATE** |
| **5** | `TOOLING-INVENTORY.md` left stale by this commit, deliberately | **LOW**, declared |

### 1. `Plan: Pro`, hardcoded — MODERATE, new

`sairncash.html:312`:
`<div class="stat-row"><span class="stat-label">Plan</span><span class="stat-val">Pro</span></div>`

**It is a literal.** A trial user sees "Pro"; a user whose subscription lapsed
sees "Pro"; a user who forged `sairncash_sub` sees "Pro". Found while reading
the same panel as item 5. This is the fabricated-value class Guardian check 0b
exists for — a displayed figure with no function behind it — on the one panel
that tells a customer what they are paying for.

**Not fixed:** it needs the real state from `getSub()`/`getTrial()`, which is a
behaviour change on a paid surface and deserves its own claim and its own arms,
not a line squeezed into a batch about citation ranking.

### 2. `register_feed_gate.py` cannot print its own usage — MODERATE, new

`python tools/register_feed_gate.py` → `UnicodeEncodeError` at `print(__doc__)`.
**Fifth instance of the cp1252 class today** (push_retry, my derivation script,
my msg-filter, citation_line_drift_check, now this). The fix is the three-line
`reconfigure` guard. Not applied: the file is not in my claim and the class now
deserves one sweep rather than a sixth one-line commit.

### 3. The other 20 absence assertions — MODERATE

Measured: 22 arms assert a token is absent from a source file; I fixed the two
that are mine. The remaining 20 belong to other sessions and are **one
documenting comment away from failing on the documentation.**
`tools/pycomments.py` is there for them, and two probes already carry their own
hand-rolled stripper, so the pattern now has three implementations and one
shared module.

---

## 6. What I will not claim

* **No live verification applies.** Two tools, one new module, four probes, one
  app file, three documents; nothing deployed changed in a way I drove.
* **The `sairncash` bar is not verified in a browser.** The arithmetic and the
  syntax are checked; the rendered width is not.
* **The two-hop anchor resolution can be wrong across an IIFE boundary.**
  Nearest-preceding is what a reader does and it is right inside a module; the
  limit is named in the tool and the cap is two hops.
* **I did not read the 136 remaining drifted cells.**
* **`TOOLING-INVENTORY.md` is stale as of this commit** and I left it that way
  on instruction. It will read wrong until cc or a later session regenerates
  it — stated here so nobody reads the staleness as a surprise.
* **The enforcing-path change is driven by injection, not by a real 2-finding
  push.** I tried to construct one and could not get two real checks to fire
  together; the injection test is stronger on the property that matters (a
  crash after a denial) and weaker on end-to-end realism, and that trade is
  stated rather than hidden.

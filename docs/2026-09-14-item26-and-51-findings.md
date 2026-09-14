# Items 26 and 51 — both answered with numbers, and neither is buildable yet

**2026-09-14 (Hank).** Two items whose prerequisites were declared met. One is
half-built and half-starved; the other is not close. Both answers are
measurements, not impressions.

---

## Item 26 phase 1 — the FMEA branch works; the near-miss branch has no input

### The FMEA-prediction branch is built and running

Wired into `defect_register.py --add` on 2026-09-13. It fired for real on
record 61 — `MISSED: sairnbiz.html — 1 draft(s) predate it and none cites 1.11`
— which is the loop answering at the only moment its answer changes. 87 drafts
on disk, `NO DRAFT AT ALL` at 0.

### The near-miss branch's obvious input is empty, measured

The natural source is a metamorphic violation: a checker whose answer moves
under a transform that cannot change the truth is a checker that is *about* to
be wrong. Item 18 built that frame and its first real run measured

> **660 comparisons (6 checkers × 22 app files × 5 relations), 0 violated, 0
> could-not-run.**

Re-run today on a target: exit 0, no violations.

**So a near-miss register fed by metamorphic violations would be an empty
tool** — the fourth instance tonight of *the tool is ready, the input is not*
(items 2/24, 4, 66). Building it would put a mechanism in place and prove
nothing, and its emptiness would read as safety.

### The real near-miss source exists, produces events daily, and records nothing

**A push-gate denial is the purest near miss on this platform**: the change was
fully formed, travelling, and stopped at the last barrier before origin.

`deny()` in `tools/sairn_push_gate_hook.py` has **30 call sites and writes
nothing durable** — a reason to stderr, then exit. **Every near miss this
platform has ever had evaporated when the developer read it.** Three of mine
were denied tonight alone: a generated document left stale, a commit-and-push in
one step, a new tool with no `PURPOSES` entry.

That matters against item 63's numbers. Item 63 counted which checkpoint caught
each *confirmed defect* — 49% a person reading, 51% an automated checker, and
only **3 of 67 the blocking gate**. That is defects that got in and were later
found. **Gate denials are the ones that never got in, and they are invisible.**
The gate may be the most load-bearing barrier on the platform or the least, and
nothing in the repo can currently tell the difference.

**Not built, and this is the decision.** Recording them means editing `deny()`,
which sits on the critical path of every push by every session. The log would
have to fail *open* — if it cannot write, the denial must still happen —
which inverts this repo's standing fail-closed rule and is exactly the kind of
inversion that should be chosen deliberately rather than slipped in. **Michael's
call, not mine to make while editing the gate.**

---

## Item 51 — per-entity baselines: the data is not there, and here is the number

The question was whether tonight's volume changes the answer. It does not.

**Defects per app, all 68 records:**

| App | n |
|---|---|
| `PLATFORM` | **44** |
| `sairndental` | 6 |
| `sairnvet` | 5 |
| `stonedesk` | 3 |
| the remaining 7 apps | 1–2 each |

- **11 distinct apps. Exactly one has ≥10 records, and it is `PLATFORM`** — a
  catch-all bucket, not an entity. It holds **65% of everything**.
- **9 of 11 apps have 3 or fewer.** A baseline needs a distribution; you cannot
  compute one from n=1, and a threshold set from n=1 is that single value
  wearing a decision.

**Per tool is worse, not better:** 2 tools have ≥5 finds; **11 have exactly
one.**

**Verdict: not buildable.** The honest bar is somewhere around 20–30 records per
entity before a per-entity baseline means anything, and the largest real entity
has 6.

### And the measurement found a defect in its own input

`SAIRNBIZ` and `sairnbiz` were sitting in the register as **two separate apps** —
one entity split in half. Every per-app figure quietly reported both, and
nothing noticed.

**On a global figure that is cosmetic. On a per-entity baseline it halves the
very count the baseline is computed from**, which is the one place it would do
real damage — and it would have done it silently, at exactly the moment somebody
trusted the number.

Normalised, and `--check` now **refuses two spellings of one app**. Proven to
fire: flipping one record's case makes `--check` exit 1 and name both spellings,
and the file restores byte-identical.

---

## What these findings do NOT claim

- **Metamorphic's 0 violations is a property of six checkers over 22 files**,
  not of the platform. A seventh checker could violate tomorrow.
- **No claim that the push gate is or is not load-bearing.** The point is
  precisely that nothing can currently say.
- **The 20–30 record bar for a baseline is a judgement**, stated so it can be
  argued with; nothing here derives it.
- **Nothing was built for either item.** One field guard was added, to the
  register, because the measurement surfaced a live defect in it.

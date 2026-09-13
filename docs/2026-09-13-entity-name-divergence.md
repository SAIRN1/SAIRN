# The company's own name has three spellings, and two of them carry © and ™

> **RESOLVED 2026-09-13, later the same day.** Michael confirmed
> **`SAIRN Tech LLC`** as the registered entity — the same string the Sept 3
> correction and all four `docs/legal/` signature blocks already carry, and the
> one `tests/base_prompt_single_source.js:78` had been pinning as *"the real
> legal entity … not `SAIRN Technologies LLC`"* since before this measurement
> ran. **45 sites across 17 files were corrected.** The measurement below is
> left exactly as it was written, as the record of what was found; **what
> changed, what was deliberately not changed, and the two questions the sweep
> raised are in "The correction" at the foot of this file.**

**2026-09-13 (CC).** Surfaced by `literal_drift_check.py`, which gates on
**entity name** precisely because it is an invariant: one company has one legal
name. **Nothing was changed.** Which string is the registered entity is a fact
about the company, not about the code, and putting the wrong one in a copyright
line would be worse than leaving the inconsistency visible.

## Measured

| string | app HTML | `docs/legal/` (documents a customer signs) | `docs/*.md` planning |
|---|---|---|---|
| `SAIRN Tech LLC` | 27 | **13** | 0 |
| `SAIRN Technologies` | 34 | 0 | 1 |
| `SAIRN Technologies LLC` | 0 | 0 | 3 |

Comment-aware: of the app occurrences, **23 `SAIRN Tech LLC` and 11
`SAIRN Technologies` are NOT comments** — they reach output.

## Both spellings reach customers, and two of the sites are legal assertions

**`SAIRN Tech LLC` — 23 live sites, including:**

- `sairnscape.html:244` — a visible page footer: *"Powered by Claude AI ·
  SAIRN Tech LLC · **© 2026 SAIRN Tech LLC** · Patents Pending"*. **A copyright
  notice.**
- Ten **AI system prompts** across StoneDesk's suite descriptions and
  SAIRNscape's — *"Built by SAIRN Tech LLC"*. The model states this as
  provenance when a user asks who made the product.
- `stonedesk.html:35622` — the header of a **printed document**.
- `stonedesk.html:35590` — the default shop name when a licence sets none.

**`SAIRN Technologies` — 11 live sites, including:**

- `sairnvet.html:166` and `:207` — a visible byline, **"by SAIRN Technologies™"**.
  **A trademark assertion.**
- `sairnscape.html:134` — a visible nav badge.
- `sairncode.html:711` — the logo area.
- `stonedesk.html:19099` — the footer of a **printed Standard Operating
  Procedures** document, marked Confidential.
- `sairnbiz.html:1871,1879` — demo/seed vendor rows. Seed data, arguably a
  separate question from the branding sites above, and listed separately for
  that reason.

So **five customer-facing apps assert two different company names**, one under
`©` and one under `™`.

## The third variant, and why this is not simply "pick the one in the code"

`docs/legal/` is the strongest in-repo signal: **every signature block, in all
four templates** — the SAIRNdental and SAIRNroofing service agreements, the DPA
Amendment and the AUP Revision — reads `SAIRN Tech LLC`, 13 occurrences, with
no other variant present. Those are the documents a customer signs.

**But the planning documents use a third string.**
`docs/2026-08-30-sairntech-questions-for-counsel-and-cpa.md` is *titled*
**"SAIRN Technologies LLC"**, and
`docs/2026-08-30-sairntech-shell-and-inquiry-scoping.md` records the plugin
marketplace README as published under **SAIRN Technologies LLC**.

A document written to ask counsel questions, using a different entity name from
the one in the signature blocks, is exactly the shape of an **open question**
rather than a typo. That is why this is not resolved here.

## What is needed, and it is one fact

**Which string is the registered legal entity?** Everything else follows
mechanically once that is stated:

- the `©` line and the `™` byline must both use it;
- the AI system prompts state provenance and should match it;
- the marketplace README is published under a name and should match it;
- the signature blocks already agree with each other and may already be right.

## What was deliberately not done

- **No occurrence was changed.** 34 live sites across 8 files; a bulk rename
  would be the find-replace `CLAUDE.md` forbids, applied to a legal fact nobody
  has confirmed.
- **No variant was declared correct**, including the one with the most
  occurrences and the one in the signature blocks. Frequency is not authority.
- **`literal_drift_check.py` was not silenced or exempted.** Its gated finding
  is correct and should stay red until the name is decided — that is what a
  gated invariant is for.

---

# The correction

**2026-09-13 (CC), after Michael confirmed the fact.** The entity is
**`SAIRN Tech LLC`**. Everything below follows from that one string.

## How it was done — not a find-replace

`CLAUDE.md` forbids bulk find-replace, and 45 sites is exactly the size where
one is tempting. The sweep ran from a **line-pinned site list**: each entry
named a file, a line number and the exact substring expected on that line, and
the script **aborted the whole run with nothing written** if any single line
did not match. A stale line number therefore cannot silently edit its
neighbour. Twenty of the sites are byte-identical banner comments in
`stonedesk.html`, which is precisely why they had to be pinned by line rather
than matched by text.

## What changed — 45 sites, 17 files

| where | sites | files |
|---|---|---|
| app HTML | **34** | 6 |
| live JS comments (`api/_lib/exec-context.js`, `tests/exec_role_gate.js`) | 2 | 2 |
| published skill marketplace (2 × `LICENSE`, 2 × `.json`, `README.md`) | 5 | 5 |
| documents that leave the company | 4 | 4 |

Of the **34 app sites, 9 render** and 25 are comments. The nine:

- `stonedesk.html:19099` — the footer of the printed, Confidential SOP.
- `stonedesk.html:27908` — the **CEO advisor's opening line** in the Executive
  Suite. The model greeted the user with the wrong company name.
- `stonedesk.html:39229` — the footer of the printed Ask Stonehead answer.
- `sairnscape.html:134` — the nav badge, on the same page whose footer at
  `:244` already read `© 2026 SAIRN Tech LLC`. **One page, both spellings.**
- `sairnvet.html:166` and `:207` — the login byline and the sidebar logo.
- `sairncode.html:711` — the logo area.
- `sairnbiz.html:1871,1879` — the demo expense row and vendor row.

Two **MIT copyright notices** were also wrong and are not app strings at all:
`dist/skills-public/sairn-skills/LICENSE` and the `postgres-grant-sweep`
plugin's, both reading `Copyright (c) 2026 SAIRN Technologies LLC`. They were
not in the original measurement because that pass filtered by file extension
and `LICENSE` has none.

## What the gate could not have told you

`literal_drift_check.py` gates the entity name **per file**, and a per-file
invariant cannot see a cross-file divergence. **SAIRNvet, SAIRNcode and
SAIRNbiz were 100% wrong and all three reported `ok entity name — one value`
and exited 0.** Unanimity inside one file is what the check calls correct. It
fired only on the two files that were internally mixed, `stonedesk.html` and
`sairnscape.html`; the other three were found by a repo-wide grep and would
have survived any number of clean gate runs. Recorded in the tool itself.

## Two decisions taken here, both reversible, both worth saying out loud

1. **The ™ was dropped, not carried over.** **27** of the corrected sites read
   `SAIRN Technologies™`, five of them rendered. `SAIRN Tech LLC™` would assert a trademark on a
   corporate entity designator — a *new* legal claim, and confirming the
   registered name is not confirmation of that. The bare form also matches the
   house convention already live at `sairnscape.html:244`
   (`· SAIRN Tech LLC · © 2026 SAIRN Tech LLC ·`) and in the ten AI system
   prompts (`built by SAIRN Tech LLC`). **Dropping it removes an unverified
   assertion rather than adding one.** If SAIRN *is* an asserted mark, the
   place for the ™ is the product or brand — `SAIRNvet™` — not the LLC name.
2. **The demo vendor rows were swept with everything else.** The prior pass
   listed `sairnbiz.html:1871,1879` separately, and the argument for holding
   them back does not survive contact: the software vendor in that demo **is**
   this company under either spelling, so the name was equally real before.
   Separately and unchanged: that vendor row carries a **fabricated phone
   number** `(800) 724-7600` next to the entity name. That is a demo-data
   question, not an entity-name one, and was left alone rather than folded in.

## What was deliberately left

- **Historical records keep the old spelling**: the active-work logs, session
  handoffs, dated specs (`SAIRNVET-FINAL-SPEC.md`, the 2026-09-02 gap audit)
  and the measurement above. Rewriting a dated record to match today is how a
  log stops being evidence.
- **`tests/base_prompt_single_source.js:78` and
  `tests/run_literal_drift_control_probe.py:188`** name the wrong spelling **on
  purpose** — one is an assertion message, the other a synthetic fixture the
  detector is measured against. Changing either would break what it tests.
- **`.claude/skills/sairn-build-lifecycle/SKILL.md:3`** — one line of
  descriptive prose, in a file that is a **mirror of the user skill store**.
  Editing the repo copy alone creates mirror drift, which costs more than the
  line is worth. **Flagged, not fixed.**

## The one thing this repo cannot close

The skill marketplace is **published outside this repo**, at
`sairn-tech/sairn-skills` (`/plugin marketplace add sairn-tech/sairn-skills`).
The copy under `dist/` is corrected; **the published copy is not, and nothing
in this clone can reach it.** Until that repo is updated, the public
`marketplace.json` owner, both MIT copyright lines and the README byline still
read `SAIRN Technologies LLC`. **`dist/` has no generator** — it is
hand-maintained — so there is no build step that will carry this across.

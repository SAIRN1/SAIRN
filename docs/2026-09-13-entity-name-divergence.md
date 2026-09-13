# The company's own name has three spellings, and two of them carry © and ™

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

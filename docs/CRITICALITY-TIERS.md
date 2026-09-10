# Criticality tiers — every vertical on the platform

**Hand-written on purpose. `python tools/criticality_tier_check.py` checks it and never rewrites it** — the tier and the sentence explaining it are a judgement, and a tool that regenerated this file would delete exactly the part that matters. Same reasoning as `docs/SOUP-REGISTER.md` and `tools/sairn_app_map_check.py`.

**Why it exists.** Started 2026-09-10 as the third of the three standing disciplines for vertical work, alongside the SOUP register and the requirements-to-test traceability matrix. Nothing on this platform stated a criticality tier for a vertical before this file.

**What the tier is.** The **worst consequence of that vertical failing or being wrong**, not how likely it is and not how much code it has. The scheme is taken verbatim from `docs/SOUP-REGISTER.md` rather than invented, so the platform has one scheme and not two:

| Tier | Meaning |
|---|---|
| **A** | Catastrophic — money moves wrongly, a regulated record is corrupted, or authentication is bypassed |
| **B** | Serious — data loss or exposure without a regulatory dimension |
| **C** | Contained — a feature degrades, nothing else is reachable |

## How to read the Evidence column, because it is the whole point

A tier asserted with no evidence is a label. **Every tier below cites something already recorded in this repo** — a commit, an index row, a schema file, a real incident — so a reader checks the claim against that source rather than against this table.

Where no such evidence exists yet, the row says **UNTIERED** and names what would settle it. That is not an oversight to be tidied away: guessing a tier is worse than an open question, because a guess is indistinguishable from a decision once it is written down.

## The register

| Vertical | Tier | Worst consequence if it is wrong | Evidence |
|---|---|---|---|
| `sairnvet.html` | **A** | An invented controlled-substance balance in a DEA-relevant register, unremovable | Real incident: the lazy demo seed pushed invented Ketamine, Butorphanol and Fentanyl balances with named vets to the live server, and there is no delete path anywhere in the product (`a858cab7`) |
| `sairnlaw.html` | **A** | A court deadline computed wrong, and a filing missed | Real incident: the endpoint dropped `service_methods` and Florida ran five days late for five days on the shortest answer period in the engine (`api/_lib/deadline-endpoint-inputs.test.js` header) |
| `sairndental.html` | **A** | A patient billed against a wrong ledger, or a federally required estimate issued incomplete | 45 CFR 149.610(c)(1) is enforced server-side in `api/_lib/dental-gfe.js`; the money ledger has five validated resources in `api/_lib/dental-ledger.js`, each closing a measured arithmetic defect |
| `stonedesk.html` | **A** | A quote or invoice wrong, or a customer record lost with no server copy | Money throughout; 21 collections reached no server at all until `93d37aa5`, and the open-work row measured 26 of 37 local-only |
| `sairnbiz.html` | **A** | The shared employee roster three other apps read is wrong, or written by the wrong role | It is the only writer of the platform-shared `employees` table (`api/sd-data.js` employees write branch), and `stonedesk.html`, `sairnbuild.html` and `sairnsenior.html` all read it |
| `sairncare.html` | **A** | A regulated ALF compliance or payer rule wrong on a live licence | Per-licence reference tables with a load-state gate (`tools/sairn_load_state_check.py --app sairncare`), built after a seed correction shipped unloaded |
| `sairnsenior.html` | **A** | A visit note, medication administration or EVV entry silently not saved | Its `st()` had 32 call sites and **all 32** ignored the return before `83227f71` — the storage-wrapper row names this the highest-stakes of the four |
| `sairncode.html` | **A** | A compliance credential accepted that should not be, or provisioning granted to the wrong role | Its `PROVISIONING_ROLES` is `admin`, not `owner` — CLAUDE.md records a guard that hardcoded `owner` passing it clean forever while checking nothing |
| `sairnroofing.html` | **B** | A certification or contingency term wrong on an agreement | Per-licence reference tables under the same load-state gate; no regulated register and no direct money movement recorded |
| `sairnbuild.html` | **B** | Bid or training-assessment data lost | Employee auth and a server backup exist; nothing recorded ties it to money movement or a regulated record |
| `sairnmechanical.html` | **B** | A check-register entry lost or duplicated | Active work as of 2026-09-10 on the cheque-number key; the register is money-adjacent but the decision is open |
| `sairnfreedom.html` | **B** | Member or service-hour records lost from one device | 78 of 78 `st()` call sites ignored the return before `76d0e940`; ORC Chapter 2915 research exists but no regulated write path is recorded |
| `sairngrounds.html` | **B** | Job or crew records lost | Employee auth present; no regulated or money path recorded |
| `sairnscape.html` | **B** | Job records lost | Employee auth present; no regulated or money path recorded |
| `sairndesign.html` | **B** | Project records lost | Employee auth present; no regulated or money path recorded |
| `sairnlegacy.html` | **B** | Client records lost | Employee auth present; no regulated or money path recorded |
| `sairncash.html` | **UNTIERED** | Would be **A** the moment Stripe is live — money moves | `api/sairncash/checkout.js` returns `Stripe not configured` today, so nothing moves. **Settles when `STRIPE_SECRET_KEY` is set**, and the tier must be revisited in the same change |
| `sairndental-book.html` | **UNTIERED** | An unauthenticated booking surface writing into a Tier A app | Public-by-design, declared in `tools/public_endpoint_declarations.json`. **Settles by deciding whether a public writer inherits the tier of what it writes into** — that is a platform rule, not one app's call |
| `sairndental-complaint.html` | **UNTIERED** | As above, for patient complaints | Public-by-design writer into a Tier A app, same shape as `sairndental-book.html`. **Settles with that one, by the same platform rule**: whether a public writer inherits the tier of what it writes into |
| `stonedesk-intake.html` | **UNTIERED** | As above, for customer intake | Public-by-design writer into a Tier A app. **Settles with `sairndental-book.html`, by the same platform rule** about whether a public writer inherits the tier of what it writes into |
| `stonedesk-catalog.html` | **UNTIERED** | A public catalogue showing wrong prices | Read-only surface; **settles by confirming it cannot write anything** |
| `stonedesk-hr.html` | **UNTIERED** | HR records exposed or wrong | **Settles by establishing what it reads and whether it shares StoneDesk's session** |

## The gaps — read this section first

- **Six verticals are UNTIERED and each one names what would settle it.** Five of the six are the same unanswered platform question: *does an unauthenticated public surface inherit the tier of the app it writes into?* That is one decision, not five, and it is Michael's.
- **`sairncash.html` is the one with a date on it.** It is untiered because nothing moves today, and it becomes Tier A on the day a Stripe key is set. The tier must be revisited in that same change, not afterwards.
- **The B tier is doing a lot of work here.** Six verticals sit at B with the same evidence — employee auth present, nothing recorded tying them to money or a regulated record. That is honest about what is *recorded*, and it is weaker than a review: an absence of recorded evidence is not the same as a measured absence, and this file does not pretend otherwise.
- **`piac.html` is deliberately not in this register.** It is not a vertical — it is a 138 KB saved copy of an Indiana Department of Health 404 page, untracked at the repo root since 2026-08-28, and it already has its own open-work row. The checker declares the exclusion out loud rather than filtering it silently. **It is UNTRACKED, so a fresh checkout has 22 verticals and nothing to exclude** -- that is correct, not a difference to reconcile, and the probe provokes the file into existence rather than assuming it, after the first version of that arm measured the environment instead of the logic.

## What a tier is FOR

It is not a badge. It decides three things, and it should be cited when it does:

1. **How much verification a change needs before it ships.** A Tier A change is where independent review and a live check stop being optional.
2. **Whether a guard belongs in the blocking set.** `GUARD_TESTS` in `tools/sairn_push_gate_hook.py` is the blocking registry; a Tier A consequence with no guard is a finding.
3. **What an incident costs, before it happens.** The tier is written down so nobody has to estimate it during the incident, which is the worst moment to be forming that judgement for the first time.

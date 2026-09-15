# SAIRNlaw and Privacy scope — read from the app, not assumed

**Status: DECISION-READY. Measured 2026-09-15 against `sairnlaw.html`,
`api/_resources/sairnlaw.js` and `api/_lib/deadline-engine.js`.**

The question asked was whether SAIRNlaw's practice-area coverage — family law,
immigration, and similar genuinely PII-heavy work — puts it in or out of Privacy
scope for the SOC 2 readiness effort. The instruction was to read the real
coverage rather than assume it.

**The app answers a different question than the one asked, and that IS the
answer.**

---

## 1. What was measured

| Question | Method | Result |
|---|---|---|
| Does SAIRNlaw enumerate practice areas? | read the `practice_area` field and look for an option list | **No.** It is FREE TEXT. There is no `<option>` list, no `MATTER_TYPES` constant, no validation |
| What practice areas does it ship with? | read the seeded matters | exactly two, as sample data: `'Estate Planning'` and `'Commercial Litigation'` |
| Does it model family law? | `divorce`, `dissolution`, `child support`, `parenting`, `guardian ad litem` across the app and the deadline engine | **0 hits each** |
| Does it model immigration? | `immigration`, `asylum`, `USCIS`, `I-130`, `I-485`, `N-400` | **0 hits each** |
| `custody` — 7 hits, the one apparent signal | read every one | **all seven are "AI Chain of Custody"**, the AI-interaction audit feature. None is child custody |

**SAIRNLAW IS PRACTICE-AREA-AGNOSTIC BY CONSTRUCTION.** A firm types whatever it
practises into a free-text box. Nothing in the code knows or cares.

---

## 2. Why that settles it, and settles it the other way

**Scoping Privacy to practice area would be scoping to something this platform
cannot observe, cannot validate and cannot control.**

Three consequences, and the third is decisive:

1. **The current answer is unknowable.** No query can tell you whether a live
   SAIRNlaw firm is doing family law today, because the field is free text and
   the seeds are sample data.
2. **The answer can change with no code change and no deploy.** A firm types
   "Immigration" into the box on Monday and the platform is handling asylum
   matters on Tuesday. A scope decision that a customer can invalidate by typing
   is not a scope decision.
3. **THE DATA IS ALREADY IN SCOPE REGARDLESS.** Whatever the practice area,
   SAIRNlaw stores the following about identified natural persons:

| Resource | What it holds | Why it is a Privacy question on its own |
|---|---|---|
| **`law_pimedical`** | **personal-injury MEDICAL records** | health information about an identified individual. This is the sharpest resource in the app and it is not conditional on any practice area |
| `law_trusttx`, `law_opaccounts` | client trust-account and operating-account transactions | other people's money, held in trust |
| `law_bankstatements` | bank statements | financial account data |
| `law_clients` | name, phone, email, address | direct identifiers |
| `law_portalmessages`, `law_portalesign` | client communications and signature records | attorney–client material and consent evidence |
| `law_picases` | personal-injury case records | injury and claim detail |
| `law_barcerts`, `law_clecredits` | attorney bar certifications and CLE credits | employee PII, a separate data subject from the client |

**RECOMMENDATION: SAIRNlaw is IN Privacy scope, on the strength of
`law_pimedical` and the financial-account resources alone, and the practice-area
question should be dropped rather than answered.** Family law and immigration
would each add sensitivity, but neither is needed to reach the conclusion, and
waiting on an answer that cannot be obtained would leave the scope undecided
indefinitely.

---

## 3. What this document deliberately does NOT do

**It does not map controls to Privacy criteria P1–P8.** That is the SOC 2
readiness work, it has not been done for any vertical, and per the 2026-09-15
measurement no SOC 2 readiness material exists on this platform at all — the only
occurrence of "SOC 2" in 1668 tracked files is a string inside the CTO advisor's
AI system prompt. **A P1–P8 mapping written here would be the first half of a
compliance document with no second half, which reads as coverage to exactly the
reader who most needs it not to.**

**It does not make a legal determination.** Whether `law_pimedical` engages HIPAA
(a law firm is generally not a covered entity, but may be a business associate),
and which state privacy statutes apply, are legal questions. Nothing here is
legal advice.

**It does not claim the other verticals were scoped.** The framing of the
original question implied this was the last vertical to scope. Measured: **no
vertical has a Privacy scoping document.** SAIRNlaw is the first, which makes it
the precedent rather than the exception, and the method below is the part worth
copying.

---

## 4. The method, because it generalises

The mistake this document avoided was answering the question as asked. *"Is
family law in scope?"* presumes the app knows what a matter is about. It does
not.

**SCOPE FROM THE SCHEMA, NOT FROM THE SALES DESCRIPTION.** What an app is *for*
is a claim somebody wrote; what it *stores* is in `api/_resources/*.js` and can
be read. For every remaining vertical, the question that has an answer is:

> which resources hold identifiers, health data, financial-account data or
> communications about a natural person — and is that conditional on how the
> customer uses the app, or true of every deployment?

Where the answer is "true of every deployment", the vertical is in scope and no
further investigation is needed. Where it is genuinely conditional, **the
conditionality itself is the finding** — because it means the platform cannot
tell which of its customers are in scope, and that is worth knowing before an
auditor asks.

---

## 5. What would change this conclusion

Recorded so the decision has a named trigger rather than becoming permanent by
default:

- **`law_pimedical` being removed**, or being re-scoped to hold no health
  information. It is currently the single strongest reason for the conclusion.
- **A decision to enumerate `practice_area`** as a validated list, which would
  for the first time make the practice-area question answerable — and would
  immediately raise whether a firm is permitted to select an area the platform
  has not scoped.
- **Anything that makes the medical or financial resources reachable without an
  employee session.** Today they are gated; that gating is load-bearing for this
  conclusion and is not restated here — see the role-gate work.

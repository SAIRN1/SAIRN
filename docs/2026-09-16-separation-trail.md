# Hover auditor separation — the audit trail from real git history

Generated **2026-09-16 18:25:36 UTC** by `tools/hover_separation_audit.py --report`, from
`main` at **`1cba902d8840`**.

Regenerate it, and check it, with:

```
python tools/hover_separation_audit.py --report trail.md --csv trail.csv
```

---

## Read this before any number below

**Git cannot prove the negative here, and this document does not claim it does.**

All five roles on this platform commit through **one git identity**, so a commit
cannot be attributed by its author field. Attribution below is derived from
co-changed bookkeeping files — a commit that also touches
`.claude/claims/<session>.json` or `SAIRN-ACTIVE-WORK-<session>.md` names its
session — and from commits that touch **only** the auditor's own directory.

That leaves **3498 of 5488 commits (63.7%) UNATTRIBUTED**. A commit in which the
auditor wrote platform code would land in exactly that bucket **by construction**.

So the honest statement of what follows is:

> Of every commit that CAN be attributed, none shows the hover auditor writing
> outside its own scope — corroborated by a second, structurally different
> source (the auditor's own hash-chained log). It is not a proof that no such
> commit exists.

---

## Attribution across 5488 commits

| attributed to | commits | share |
|---|---:|---:|
| UNATTRIBUTED | 3498 | 63.7% |
| hank | 583 | 10.6% |
| fourth | 503 | 9.2% |
| cc | 471 | 8.6% |
| cody | 409 | 7.5% |
| hover | 24 | 0.4% |

`UNATTRIBUTED` is not a sixth agent. It is the part of history this method
cannot speak about, stated as a number rather than omitted.

---

## The auditor's commits — all 24, in full

**This list is the proof.** A count would be a summary of it, and a summary
cannot be checked. Every commit the auditor is known to have made is here,
with what it touched.

| sha | UTC | files | outside its scope | subject |
|---|---|---:|---:|---|
| `8165d1ba` | 2026-09-14 18:30 | 1 | **0** | chore(skills): mirror sairn-hover-auditor into the repo, matching every other sairn-prefix |
| `de6ad052` | 2026-09-14 18:43 | 1 | **0** | docs(skill): rotation gets four anti-predictability sub-rules, item 89's look-elsewhere ch |
| `d7ac0424` | 2026-09-14 19:17 | 1 | **0** | docs(skill): risk-limiting-audit sampling weight, coverage-scope discipline, and registere |
| `a7519a48` | 2026-09-14 19:36 | 2 | **0** | docs(skill): seven real precedents -- SOX/PCAOB, Knight Capital, IOLTA, Madoff, IRS -- spl |
| `2f7d33bc` | 2026-09-14 19:49 | 2 | **0** | docs(skill): four more precedents -- Trail of Bits stats, Stanford evidence-citation, Boei |
| `cec12db5` | 2026-09-14 20:04 | 2 | **0** | docs(skill): SpaceX/NASA contrast case and calibration-industry algorithm |
| `3472eb1b` | 2026-09-14 20:11 | 2 | **0** | docs(skill): Lloyd's Register -- differentiated cadence within one item, and the real inde |
| `ce3b7fd9` | 2026-09-14 20:19 | 2 | **0** | docs(skill): METR sleeper agents / entity-based assessment, CAICT false-alignment -- direc |
| `145395bc` | 2026-09-14 20:27 | 2 | **0** | docs(skill): Kepler/Flyspeck scale limit and loophole-free Bell tests -- close explanation |
| `955681f2` | 2026-09-14 20:34 | 2 | **0** | docs(skill): the Audit Risk Model -- separating Inherent Risk from Control Risk in rotatio |
| `75da838d` | 2026-09-14 20:42 | 2 | **0** | docs(skill): Marzullo's Algorithm and NTP stratum -- the formal answer to Debate, and prov |
| `f3a8cd17` | 2026-09-14 20:53 | 2 | **0** | docs(skill): GLI, RICOCHET, Patriot missile -- three new precedents; Marzullo/stratum conf |
| `d64d92ca` | 2026-09-14 21:36 | 2 | **0** | docs(skill): F1 scrutineering, UL, TUV, ACFE, Toyota Jidoka, Amazon, FedEx/UPS -- thirteen |
| `9afe0bd5` | 2026-09-14 21:47 | 2 | **0** | docs(skill): security-testing capability -- Rules of Engagement first, then threat modelin |
| `36905dbe` | 2026-09-14 21:59 | 2 | **0** | docs(skill): Elastic bug-bounty triage, LIGO blind injection, Trail of Bits smart-contract |
| `ab35632e` | 2026-09-14 22:17 | 2 | **0** | docs(skill): chaos engineering, Common Criteria/EAL, Project Zero, xz-utils backdoor, STRI |
| `3db61815` | 2026-09-14 22:44 | 2 | **0** | docs(skill): reconcile five real gaps from tonight's security research, verify Rules of En |
| `fe2e0ae2` | 2026-09-14 23:22 | 2 | **0** | docs(skill): ten new items -- secrets scanning, CodeQL, SLSA, MITRE ATT&CK, and a new non- |
| `85fd9948` | 2026-09-14 23:34 | 2 | **0** | docs(skill): DORA metrics and CMMI -- critiquing the build method itself, not just its out |
| `5fb3a776` | 2026-09-14 23:47 | 2 | **0** | docs(skill): Anthropic's RSP and formal equivalence checking -- a self-referential precede |
| `aa3ec361` | 2026-09-16 05:10 | 1 | **0** | docs(hover-auditor): 730 lines of the auditor's own standing rules, uncommitted through a  |
| `23eb3044` | 2026-09-16 12:36 | 1 | **0** | docs(hover-auditor): VAR's clear-and-obvious-error standard for Debate, and a real EQA cad |
| `3e2c0c72` | 2026-09-16 13:02 | 1 | **0** | docs(hover-auditor): disclose the SessionStart-hook propagation fix and its one real resid |
| `b00fa93c` | 2026-09-16 13:33 | 1 | **0** | docs(hover-auditor): three new standing methods -- bug-class rotation, claim-collision sca |

Span: **2026-09-14 18:30** to **2026-09-16 13:33** UTC.

---

## The second source: the auditor's own hash-chained log

A record and its own verifier share a failure, so the chain below is re-derived
independently by this tool rather than by calling the log's own `--verify`.

| | |
|---|---|
| entries | 172 |
| hash chain, re-derived independently | **INTACT** |
| SHAs the log claims as its own | 33 |
| …that resolve in this clone | 16 |
| …of those, out of scope | **0** |
| …that do NOT resolve here | 17 |

The unresolvable SHAs are **explained by measurement, not by a plausible story**:
the log names both ends of a rewrite ("Committed a, pushed b"), and in every
such pair the local sha is absent while the pushed one is present — which is
what a rebase-before-push produces. Any that remain unpaired are listed as
unexplained in the tool's own output and are why it exits 2 rather than 0.

---

## Verdict

**No violation found in what could be checked — and part of the check did
not run.** That is not a clean bill, and it is written this way on purpose:

- 2 sha(s) the self-log claims are unresolvable in this clone and unpaired: 0cd86d0b, 23b0ffef

Tool exit code: **2** (0 clean, 1 violation, 2 could-not-run).

---

## Checking this document rather than believing it

`--csv` writes the **complete** per-commit table — every commit, its attribution
and the METHOD that attributed it, so a reader can see which rows rest on a
bookkeeping file, which on a signature, and which on nothing at all.

The enforcement that sits beside this report, rather than describing it:

- `tools/hover_auditor_scope_gate.py` — refuses the commit before it exists (local)
- `.github/workflows/hover-separation.yml` — the same question on GitHub's side,
  off the author's machine, where its verdict is a status rather than an honour system


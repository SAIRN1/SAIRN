# SAIRN Technologies — fact sheet

**Derived 2026-09-28 for use 2026-09-29.** Counts only. Every figure carries the
exact command that produced it, so any of them can be re-run in front of the
person asking.

> ## ⚠ RUN THIS BEFORE YOU PRINT THE SHEET
>
> From `C:\Users\marsh\Documents\SAIRN-hank`:
>
>     python tools/fact_sheet_regenerates.py --update
>
> That REWRITES every figure below from its own command and stamps the time. It
> never touches a figure it cannot derive — a derivation that fails leaves the
> old number standing and exits non-zero, so "refreshed" and "refreshed as far
> as it could" are never the same answer. **If it exits non-zero, read what it
> says before printing.**
>
> To CHECK without changing anything, drop `--update`: exit 0 means every number
> below is still exactly true, and any other exit prints the figure, the old
> value and the new one.
>
> **It is not a formality: 22 figures had moved in the twenty minutes between two
> runs on 2026-09-28**, because four other engineers push to this repository
> continuously. Commits, defects and review obligations all move hourly. **The
> commits figure is stale again the moment anything is committed, including this
> refresh itself** — so run it last, immediately before printing.

**Figures refreshed 2026-09-29 09:08 by `python tools/fact_sheet_regenerates.py --update`.**

**No file names, no customer data, no credentials, no methodology detail.**
Figures that cannot be derived are marked **UNAVAILABLE** with the reason — a
number nobody can reproduce is worse than an absent one.

---

## Platform scale

| Figure | Value | Derived by | Date |
|---|---|---|---|
| Applications and pages, total | **22** | `git ls-files '*.html' \| grep -v '^archive/' \| grep -v '^docs/' \| wc -l` | 2026-09-28 |
| **Vertical business applications** | **16** | classified from each file's own `<title>`; see below | 2026-09-28 |
| Consumer applications | **1** | same | 2026-09-28 |
| Other pages (satellites of a parent app) | **5** | same | 2026-09-28 |
| Registered data resources | **391** | `python tools/criticality_tier_check.py` → `RESOURCE_ROWS` | 2026-09-28 |
| Database schema files | **259** | `git ls-files 'sql/*.sql' \| wc -l` | 2026-09-28 |

**Panels — 465 across all 22, and the method differs by application because the
applications do.** There is no single definition that holds across 22
independently-built single-file applications, so each was counted by **its own
convention**, and both methods are stated:

| Convention | Applications | Panels | How counted |
|---|---|---|---|
| CSS class marks the panel | 15 | **426** | distinct element ids carrying the panel class |
| A named navigation function | 3 | **34** | distinct targets that function is called with |
| Single-purpose public page | 4 | **4** | one view each; no navigation exists |
| **Total** | **22** | **465** | |

The three navigation-function applications resolve to 17, 15 and 2 panels.
**Two of them were cross-checked two ways** — navigation targets against
page-container ids — and agreed exactly or to within one wrapper element.

**465 is a FLOOR, not a ceiling,** and the judgement is named: a panel is counted
only where the application marks one. A sub-view reached without a navigation
call is not counted.

---

## Engineering activity

| Figure | Value | Derived by | Date |
|---|---|---|---|
| Commits since 2026-05-15 | **7,094** | `git log --oneline --since=2026-05-15 \| wc -l` | 2026-09-28 |
| First commit in repository | **2026-06-22** | `git log --reverse --format=%ad --date=short \| head -1` | 2026-09-28 |
| Most recent commit | **2026-09-28** | `git log -1 --format=%ad --date=short` | 2026-09-28 |
| Elapsed development span | **98 days / 14.0 weeks** | first to most recent commit, above | 2026-09-28 |
| Commits per week (mean) | **507** | 7,094 ÷ 14.0 | 2026-09-28 |
| Commits per day (mean) | **72** | 7,094 ÷ 98 | 2026-09-28 |

**WHY THE HISTORY STARTS 2026-06-22, AND WHAT THE REAL SPAN IS.** Building began
before version control, and the repository's own first commit proves it:

| Evidence | Finding |
|---|---|
| The root commit's contents | **one file, 29,780 lines** |
| Its message | about **fixing** syntax errors, 94 of 106 script blocks passing |
| Number of root commits | **1** — no merged second history |
| Shallow clone or grafts | **none** — the history is not truncated |

A 29,780-line application with 106 script blocks arriving in a single commit,
under a message about repairing it, is **weeks of prior work being placed under
version control** — not the start of development. There is no squash marker and
no graft: this is a new repository over an existing codebase.

| Span | Value | Basis |
|---|---|---|
| Under version control | **98 days / 14.0 weeks** | first commit 2026-06-22 to 2026-09-28 |
| **True build span** | **130 days / 18.6 weeks** | earliest dated artifact 2026-05-21 to 2026-09-28 |
| Before version control | **32 days / 4.6 weeks** | the difference |

**The earliest dated project artifact is the provisional patent filing,
2026-05-21.** Nothing in the repository dates the work earlier, so 18.6 weeks is
a *lower bound* on the true span: the 4.6 pre-repository weeks are **bounded, not
measured**, and any figure covering them would be an estimate rather than a
count.

---

## Two lines to say out loud

> **"Roughly 510 commits a week, every week, for fourteen weeks."**
> 7,094 commits ÷ 14.0 weeks under version control = **507 per week**, 72 per day.
> Over the full 18.6-week build span the average is **381 per week** — lower, and
> stated because commits before 2026-06-22 do not exist to be counted, so the
> higher number is the one with evidence behind it.

> **"About 140 defects caught per week, by our own review and tooling."**
> 390 defects ÷ 2.71 weeks since the register opened 2026-09-09 = **144 per
> week**, 21 per day. **This counts defects CAUGHT, not shipped** — and 197 of
> the 390 were in the tooling and tests rather than in the product.

---

## Verification and quality apparatus

| Figure | Value | Derived by | Date |
|---|---|---|---|
| Automated test suites, total | **819** | sum of the three rows below | 2026-09-28 |
| — JavaScript suites | **230** | `git ls-files 'tests/*.js' 'tests/**/*.js' \| wc -l` | 2026-09-28 |
| — Endpoint suites | **241** | `git ls-files 'api/*.test.js' 'api/_lib/*.test.js' \| wc -l` | 2026-09-28 |
| — Python probes | **348** | `git ls-files 'tests/*.py' 'tests/**/*.py' \| wc -l` | 2026-09-28 |
| Verification tools and checkers | **275** | `git ls-files tools/ \| grep -E '\.(py\|js\|cjs\|sh)$' \| xargs -n1 basename \| sort -u \| wc -l` | 2026-09-28 |
| — of which classified as checkers | **185** | `python tools/tooling_inventory.py --check` | 2026-09-28 |
| — generators | **19** | same | 2026-09-28 |
| Checks on a recurring schedule | **66** | report-only registry count, same command | 2026-09-28 |
| Checks wired into commit/push hooks | **14** | same | 2026-09-28 |
| Tools invoked by a test | **183** | same | 2026-09-28 |
| Recorded decisions NOT to automate a check | **80** | same | 2026-09-28 |
| Live probes against deployed software | **47** | `python tools/live_probe_residue_audit.py` | 2026-09-28 |
| — of which write, not just read | **9** | same | 2026-09-28 |

**One command in this table was wrong on the first pass and is corrected here**,
because the whole point of the table is that the command produces the number. A
bare `git ls-files tools/` returns **290** — it counts 14 data files and one
configuration file that are not tools. **275** is the count of executable tool
files, deduplicated by name. Both numbers are real; only one answers the
question, and a fact sheet whose command disagrees with its figure is the exact
defect it exists to prevent.


---

## Defects found and recorded

Every entry is a defect found in this codebase by this team's own review and
tooling, recorded with its cause and its fix. **This is a record of defects
caught, not of defects shipped.**

| Figure | Value |
|---|---|
| **Defects registered, total** | **390** |
| By severity — critical | 27 |
| By severity — high | 182 |
| By severity — moderate | 146 |
| By severity — low | 35 |
| By layer — in product code | 193 |
| By layer — in tooling | 128 |
| By layer — in tests | 69 |

| Detection method | Count |
|---|---|
| Code review | 169 |
| Independent review by a second engineer | 88 |
| Static checkers | 55 |
| Live verification against deployed software | 17 |
| Control probes | 20 |
| Mutation testing | 15 |
| Fault injection | 12 |
| Hover audit (independent adversarial pass) | 8 |
| User report | 6 |

    python tools/defect_register.py          # all of the above
    # first record: 2026-09-09

**What this figure is and is not.** 390 is the count since the register opened on
**2026-09-09** — 19 days. It is not a lifetime total and it is not a bug count for
shipped software: the majority were found before reaching a user, and **197 of
the 390 are in tooling or tests rather than in the product.**

---

## Independent review

| Figure | Value | Derived by | Date |
|---|---|---|---|
| Review obligations raised | **197** | `docs/tier-a-reviews.json` record count | 2026-09-28 |
| **Review obligations discharged** | **173** | same, status `reviewed` | 2026-09-28 |
| Currently open | **24** | same, status `open` | 2026-09-28 |
| Highest-criticality resources under mandatory review | **273** | `python tools/criticality_tier_check.py` → `TIER_A` | 2026-09-28 |

Every change touching a highest-criticality resource raises an obligation that
**must be discharged by an engineer who is not its author** — the tool refuses a
record whose reviewer is its own author.

---

## Intellectual property

| Figure | Value |
|---|---|
| **Number of provisional filings** | **UNAVAILABLE — see below** |
| Filing dates recorded in the repository | **one: 2026-05-21** |
| Non-provisional deadline (filing + 12 months) | **2027-05-21** |
| Months remaining as at 2026-09-29 | **just under 8** |

**SEARCHED, NOT ASSUMED.** There is **no filing receipt and no patent ledger
anywhere in the repository** — no application numbers, no per-filing records, and
nothing in any schema or seed file. The only statement of the filings is a single
sentence, quoted second-hand in a design document describing what a confidential
business-context record contains:

> *"provisional patents filed May 21 2026. Non-provisional deadline May 21 2027."*

**So the count cannot be given.** The word is plural, which bounds it at **two or
more**, and that is the only bound the repository supports. A specific number
would be invented.

**One useful cross-check does hold:** the quoted deadline (2027-05-21) equals the
quoted filing date plus exactly 12 months, so the filing-plus-twelve-months rule
and the recorded deadline agree. There being only one filing date recorded, there
is only one deadline to list.

> **⚠ Before any company conversation.** The filing *date*, the *deadline*, and
> "two or more" are safe to state. **The inventions themselves must not be
> described** ahead of the non-provisional deadline — premature disclosure is a
> direct risk to the patents, which is a harder failure than an inaccurate
> summary. Say *"provisional patents filed May 2026, non-provisional due May
> 2027"* and nothing about what they cover.
>
> **If a number is asked for, the honest answer is that it is not to hand** —
> better than a guess that later turns out wrong in a room where it was used to
> establish credibility.

### The line to say, word for word

> **"Provisional patents were filed May 2026 — the non-provisional deadline is
> May 2027. I'd have to confirm the exact count before I gave you a number."**

**That sentence is the whole answer and it is safe to say to anyone.** It states
the two facts the repository supports, it commits to nothing it cannot, and *"I'd
have to confirm"* is the part that matters: it is true, it is what any competent
person says about a filing detail they are not holding, and it closes the subject
without inviting a follow-up about what the filings cover.

**The three things NOT to say, and the reason for each:**

| Do not say | Why |
|---|---|
| **"two patents"**, or any number | The repository supports *"two or more"* and nothing narrower. A specific number would be invented, and it would be invented in a room where it was used to establish credibility. |
| anything about **what they cover** | Premature disclosure is a direct risk to the patents ahead of the non-provisional deadline. That is a harder failure to undo than an incomplete answer. |
| **"patent-pending technology"** as a product claim | It attaches the filings to a specific capability, which is the disclosure above by another route. |

**If pressed for a count in the room:** *"More than one. I'm not going to guess at
the exact figure."* Then move on. **Do not** offer to look it up during the
meeting — there is no filing receipt and no patent ledger anywhere in the
repository, so the answer is not available from a laptop, and saying you will
check and then not being able to is worse than declining.

**What "confirm" actually means afterwards:** the count lives with the filing
attorney or in the USPTO correspondence, neither of which is in this repository.
`python tools/fact_sheet_regenerates.py` cannot check this row and says so — it is
listed in the tool's own *figures I do not check* output as a quoted sentence
rather than a computation.

---

## Independent audit logs

**H1 and H2 log lengths: UNAVAILABLE from this clone.** The independent audit
role keeps its record in a separate working copy, and a build agent reading into
it is the boundary the separation controls exist to prevent. The figure is
derivable **from that clone** and not from this one.

---

## How to check any of this

Every command above runs in seconds against the repository and prints the figure
it claims. Three things a reader should press on, because they are the weakest:

1. **Panels — 465 is a floor.** Counted by each application's own convention;
   a sub-view with no navigation call is not counted.
2. **Defects — 19 days of recording**, and 197 of 390 are in tooling or tests
   rather than in the product.
3. **The build span — 18.6 weeks is a lower bound.** The 4.6 weeks before the
   repository existed are bounded by a dated artifact, not measured.

All three are stated that way above rather than rounded up.

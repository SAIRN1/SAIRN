# SAIRN Technologies — fact sheet

**Derived 2026-09-28 for use 2026-09-29.** Counts only. Every figure carries the
exact command that produced it, so any of them can be re-run in front of the
person asking.

**No file names, no customer data, no credentials, no methodology detail.**
Figures that cannot be derived are marked **UNAVAILABLE** with the reason — a
number nobody can reproduce is worse than an absent one.

---

## Platform scale

| Figure | Value | Derived by | Date |
|---|---|---|---|
| Applications built | **22** | `git ls-files '*.html' \| grep -v '^archive/' \| grep -v '^docs/' \| wc -l` | 2026-09-28 |
| Registered data resources | **390** | `python tools/criticality_tier_check.py` → `RESOURCE_ROWS` | 2026-09-28 |
| Database schema files | **259** | `git ls-files 'sql/*.sql' \| wc -l` | 2026-09-28 |

**Panels per app — PARTIALLY AVAILABLE, and the limit is stated rather than
smoothed over.** There is no single definition that holds across 22
independently-built single-file applications: some mark a panel with a CSS class,
others switch views through their own named function. Counting by the CSS-class
convention yields **426 panels across the 16 applications that use it**; the
other 6 use a different convention and are **not counted**, so 426 is a **floor
for 16 apps**, not a platform total.

    # the 16-app floor
    python - <<'EOF'
    import re, io, subprocess
    out = subprocess.run(['git','ls-files','*.html'], capture_output=True, text=True).stdout
    apps = [f for f in out.split() if not f.startswith(('archive/','docs/'))]
    tot = 0
    for f in sorted(apps):
        s = io.open(f, encoding='utf-8', errors='replace').read()
        a = len(set(re.findall(r'id="([a-z0-9\-]+)"[^>]*class="[^"]*\bpanel\b', s)))
        b = len(set(re.findall(r'class="[^"]*\bpanel\b[^"]*"[^>]*id="([a-z0-9\-]+)"', s)))
        tot += max(a, b)
    print(tot)
    EOF

**A platform-wide panel total is UNAVAILABLE.** Deriving one requires deciding
per app what counts as a panel, which is a judgement and not a command.

---

## Engineering activity

| Figure | Value | Derived by | Date |
|---|---|---|---|
| Commits since 2026-05-15 | **6,874** | `git log --oneline --since=2026-05-15 \| wc -l` | 2026-09-28 |
| First commit in repository | **2026-06-22** | `git log --reverse --format=%ad --date=short \| head -1` | 2026-09-28 |
| Most recent commit | **2026-09-28** | `git log -1 --format=%ad --date=short` | 2026-09-28 |
| Elapsed development span | **98 days / 14.0 weeks** | first to most recent commit, above | 2026-09-28 |
| Commits per week (mean) | **491** | 6,874 ÷ 14.0 | 2026-09-28 |
| Commits per day (mean) | **70** | 6,874 ÷ 98 | 2026-09-28 |

**Note on the window.** The requested start date is 2026-05-15, but the earliest
commit in the repository is **2026-06-22**, so the count covers the repository's
entire history and the per-week figure is computed over the **real 14.0-week
span** rather than the 19.6 weeks since 2026-05-15. Using the requested window
would understate the rate by about a quarter.

---

## Verification and quality apparatus

| Figure | Value | Derived by | Date |
|---|---|---|---|
| Automated test suites, total | **798** | sum of the three rows below | 2026-09-28 |
| — JavaScript suites | **227** | `git ls-files 'tests/*.js' 'tests/**/*.js' \| wc -l` | 2026-09-28 |
| — Endpoint suites | **237** | `git ls-files 'api/*.test.js' 'api/_lib/*.test.js' \| wc -l` | 2026-09-28 |
| — Python probes | **334** | `git ls-files 'tests/*.py' 'tests/**/*.py' \| wc -l` | 2026-09-28 |
| Verification tools and checkers | **266** | `git ls-files tools/ \| grep -E '\.(py\|js\|cjs\|sh)$' \| xargs -n1 basename \| sort -u \| wc -l` | 2026-09-28 |
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
bare `git ls-files tools/` returns **281** — it counts 14 data files and one
configuration file that are not tools. **266** is the count of executable tool
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
| **Defects registered, total** | **358** |
| By severity — critical | 27 |
| By severity — high | 168 |
| By severity — moderate | 133 |
| By severity — low | 30 |
| By layer — in product code | 182 |
| By layer — in tooling | 114 |
| By layer — in tests | 62 |

| Detection method | Count |
|---|---|
| Code review | 153 |
| Independent review by a second engineer | 81 |
| Static checkers | 53 |
| Live verification against deployed software | 16 |
| Control probes | 15 |
| Mutation testing | 14 |
| Fault injection | 12 |
| Hover audit (independent adversarial pass) | 8 |
| User report | 6 |

    python tools/defect_register.py          # all of the above
    # first record: 2026-09-09

**What this figure is and is not.** 358 is the count since the register opened on
**2026-09-09** — 19 days. It is not a lifetime total and it is not a bug count for
shipped software: the majority were found before reaching a user, and **176 of
the 358 are in tooling or tests rather than in the product.**

---

## Independent review

| Figure | Value | Derived by | Date |
|---|---|---|---|
| Review obligations raised | **188** | `docs/tier-a-reviews.json` record count | 2026-09-28 |
| **Review obligations discharged** | **159** | same, status `reviewed` | 2026-09-28 |
| Currently open | **29** | same, status `open` | 2026-09-28 |
| Highest-criticality resources under mandatory review | **267** | `python tools/criticality_tier_check.py` → `TIER_A` | 2026-09-28 |

Every change touching a highest-criticality resource raises an obligation that
**must be discharged by an engineer who is not its author** — the tool refuses a
record whose reviewer is its own author.

---

## Intellectual property

| Figure | Value |
|---|---|
| Provisional patents filed | **date confirmed, COUNT UNAVAILABLE** |
| Filing date | **2026-05-21** |
| Non-provisional deadline | **2027-05-21** |

**Why the count is unavailable:** the repository holds no filings record stating
a number. The date is recorded, the quantity is not.

> **⚠ Before any company conversation.** The filing *date* and the *deadline* are
> safe to state. **The inventions themselves must not be described** ahead of the
> non-provisional deadline — premature disclosure is a direct risk to the patents,
> which is a harder failure than an inaccurate summary. Say "provisional patents
> filed, non-provisional due May 2027" and nothing about what they cover.

---

## Independent audit logs

**H1 and H2 log lengths: UNAVAILABLE from this clone.** The independent audit
role keeps its record in a separate working copy, and a build agent reading into
it is the boundary the separation controls exist to prevent. The figure is
derivable **from that clone** and not from this one.

---

## How to check any of this

Every command above runs in seconds against the repository and prints the figure
it claims. Two things a reader should press on, because they are the weakest:

1. **Panels** — a floor for 16 of 22 apps, not a total.
2. **Defects** — 19 days of recording, and 176 of 358 are in tooling or tests.

Both are stated that way above rather than rounded up.

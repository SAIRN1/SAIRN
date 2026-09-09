# Graphify: deciding the scope before rebuilding

**Written 2026-09-09 (Fourth) for index row "Rebuild graphify's knowledge
graph, properly scoped — Decide scope first; the last attempt was unscoped".**

The row is one line and carries no record of what the last attempt did. It
turns out there is one, on disk, and reading it changes the question.

---

## 1. A build already exists — in exactly one clone

`Documents/SAIRN-cody/graphify-out/`, dated 2026-08-24. Absent from `hank`,
`cc` and `fourth`. It is gitignored (`.gitignore:14-15`, and the wildcard there
is deliberate so a renamed rebuild directory is caught too), so it is per-clone
by design and invisible to every other session.

Measured, not estimated:

| | |
|---|---|
| Nodes / links | 1,906 / 2,260 |
| Files in the manifest | **293** |
| By extension | `.js` 119, `.sql` 106, `.json` 48, `.py` 19, `.cjs` 1 |
| `.html` files | **zero** |
| `docs/` files | **zero** |
| Built at commit | `acaa600c` |
| Commits since | **1,527** |

## 2. So the last attempt was not unscoped — it was scoped, silently, to the wrong third

`.gitignore:9` records the rebuild command it was made with:

    graphify extract <clone> --code-only --force --out <clone>

`--code-only` is why there is no HTML and no prose. That is a defensible flag
in the abstract and it is close to the worst possible choice **here**, because
of what this repo is made of:

| Top-level | Tracked bytes | Files | In the graph? |
|---|---|---|---|
| `docs/` | 19.0 MB | 467 | no |
| `archive/` | 18.3 MB | 168 | no |
| root (the 11 single-file apps) | 12.0 MB | 93 | no |
| `api/` | 4.6 MB | 284 | yes |
| `sql/` | 3.5 MB | 305 | yes |
| `tests/` | 1.1 MB | 105 | partly |
| `tools/` | 1.0 MB | 82 | yes |

**The graph covers the layer that is already the easiest to navigate.** `api/`,
`sql/` and `tools/` are hundreds of small, well-named files where `grep` and
`Glob` genuinely work. It excludes `stonedesk.html` (2.5 MB), `sairncode.html`
(896 KB) and nine more single-file apps, and it excludes every document.

That is the finding: the row says "unscoped", and the honest correction is that
it *was* scoped, by a flag whose effect nobody checked afterwards.

## 3. The question that has to be answered first: what is it for

Three candidate purposes. They do not share a corpus, and picking a corpus
without picking a purpose is how the last attempt happened.

**(A) "Where does this backend behaviour live?"** — corpus `api/` + `sql/` +
`tools/`. This is the existing build. It is the cheapest to produce and the
lowest value, because the alternative to it is ripgrep over well-named small
files, and ripgrep is already fast, always current, and never confidently
wrong.

**(B) "What is the structure inside a 2.5 MB single-file app?"** — corpus the
eleven root `*.html` files. This is where the navigation problem actually is:
`stonedesk.html` has hundreds of inline `<script>` blocks, panels, and shared
helpers, and this project's own standing rules exist because of it — *grep
before creating a storage key*, *the duplicate-global check added after the
June 2026 outage*, *HTML-parser-based script extraction, not `grep -c
'<script'`*. Every one of those is a graph question.

**The blocker is that nobody has established graphify can extract this shape at
all.** A 2.5 MB HTML file with inline JS is not the input these extractors are
usually pointed at, and `--code-only` may have excluded HTML precisely because
it does not handle it. **That is a probe, not a plan**: run it against one app
and look at the node count before committing to eleven.

**(C) "Has somebody already done this, and is this row still true?"** — corpus
`docs/` (467 files) + the four `SAIRN-ACTIVE-WORK-*.md` + `SAIRN-OPEN-WORK-INDEX.md`.

This is the one with a demonstrated, priced failure attached. The duplicated
SAIRNfreedom gates cost about four hours in one night. `sairn_claim.py` exists
as a mitigation for it and its own documentation says it is *not a lock* and
only narrows the window. And in the course of writing this document's two
companions today, **three open index rows turned out to describe work already
run** — two of them for two weeks — because the run was recorded in a resolved
row and in a SQL file, and nobody went back to the open row that asked for it.

A queryable graph over the prose is the only one of these three whose value is
already evidenced by real incidents rather than argued from first principles.

## 4. The durability problem, which applies to all three

The output is gitignored, so it is per-clone. Four clones means four graphs at
four different commits, and the current one is **1,527 commits stale**. A stale
graph that answers confidently is precisely the failure shape this repo keeps
recording — a claim that was true when written, read later as a fact.

Whatever corpus is chosen, the rebuild needs a staleness rule, and the cheap
version is mechanical rather than remembered: **store `built_at_commit`
(graphify already does) and refuse to answer — or warn loudly — when
`git rev-list --count <built_at_commit>..HEAD` exceeds some threshold.**
`graphify <path> --update` does incremental re-extraction of changed files
only, which makes a per-session refresh plausible instead of a full rebuild.

Committing the output instead of gitignoring it would fix the four-clones
problem and create a worse one: a multi-MB generated artefact in every diff,
regenerated at different commits by different sessions, conflicting constantly.
The `.gitignore` comment already reasoned through this. Leave it ignored.

## 5. Recommendation

**Do (C) first, narrowly, and treat (B) as a probe rather than a project.**

1. **Build (C) over `docs/` + the four work logs + the index.** Prose, no code.
   It is the corpus where a wrong answer is cheap — nobody ships a bad answer
   from it, they just go and check — and where a right answer demonstrably
   saves hours. Success criterion, stated before building so it can fail
   honestly: *ask it the three questions this session answered by hand today —
   "was the service_role TRUNCATE sweep run?", "is the DELETE revoke done?",
   "what is still unmeasured on license_keys?" — and see whether it gets them
   right.* If it cannot, the corpus is wrong or the tool is, and that is worth
   knowing for the price of one build.

2. **Then probe (B) on one file.** Point it at `sairnlaw.html` (392 KB — big
   enough to be representative, small enough to fail cheaply), not
   `stonedesk.html`. If the node count is plausible and the inline script blocks
   come out as structure rather than one blob, scoping the other ten is a
   real decision. If not, (B) is closed and that is a useful answer too.

3. **Do not rebuild (A).** It is the existing build, it is 1,527 commits stale,
   and its corpus is the one where ripgrep already wins. Delete
   `SAIRN-cody/graphify-out/` when (C) lands so that a stale graph cannot answer
   a question in the one clone that still has it.

4. **Leave `archive/` out of every option.** 18.3 MB and 168 files of
   deliberately-superseded code, including a 1,230-line archived skill whose own
   index entry says *read it for provenance, nothing else*. Putting it in a
   graph that answers "how does this work" is inviting a confident answer from
   a codebase that was retired on purpose.

**One thing I cannot tell you and will not estimate:** what a build costs.
Graphify's extraction is LLM-backed in its richer modes, and I have no measured
figure for this corpus. Step 1 above is small enough (467 prose files) to be
the measurement, and the number it produces should be written down before
anyone points it at 12 MB of application HTML.

# BUILD SPEC — the fixture lock for `tools/text_gate_literal_sweep.py` (priority row 11) — 2026-10-14, fourth b15

**ROUTED TO cc (`tools/`).** Nothing outside `docs/` is written here. **I do
not edit the tool: `tools/` is cc's.**

**WHY THIS ROW AND NOT ANOTHER.** Row 11 of
`docs/2026-10-14-fourth-b14-fixture-priority-25.md` is the one entry the owner
map attributes to **fourth**, and the fixture it needs is the exact defect my
own b13 bad-input arm shipped with: **a fixture satisfied by a token inside a
comment.** This tool's entire subject is that class, so a version of it with no
fixture is the sharpest instance of the gap on the list.

**AND IT IS CURRENTLY REPORTING A REGRESSION NOBODY HAS TRIAGED:**

```
CMD python tools/text_gate_literal_sweep.py             -> exit 1
    215 tool(s) read text AND match patterns against it.
      MASKED     : 102
      BY-DESIGN  : 2
    REGRESSION -- unverified raw text gates rose from 82 to 111.
CMD python -c "json.load(open('docs/text-gate-literal-coverage.json'))"
    text_gates 157, masked 73, by_design 2, raw_unverified 82
CMD git log -1 --format='%h %cI' -- docs/text-gate-literal-coverage.json
    a7d76bdf 2026-09-27T22:40:37-04:00
```

**The pin is 17 days old and the population grew from 157 text gates to 215.**
The exit 1 is doing its job; **the regression is 29 more raw gates against a
pin from before 58 new text gates existed**, and triaging that is a separate
piece of work from locking the criteria. **Both are cc's, and the fixture
should land first** — re-pinning a tool whose classifier is unlocked pins
whatever the classifier currently believes.

---

## 1. WHAT THE TOOL DOES, in the terms the fixture has to lock

| function | what it decides | file:line |
|---|---|---|
| `classify()` | per `tools/*.py`: **RAW**, **MASKED**, **BY-DESIGN**, or *not a text gate at all* | `tools/text_gate_literal_sweep.py:115` |
| `READS_TEXT` | does the tool read file text | `:63` |
| `MATCHES` | does it match patterns against it | `:73` |
| `MASKS` | does it mask literals/comments, or parse | `:80` |
| `BY_DESIGN` | the named exceptions, with reasons | `:88` |
| `CouldNotTell` | the **third state**, exit 2 | raised at `:111`, `:122`, `:133` |
| the verdict | raw count vs the pin ⇒ exit 0/1 | `:197` onward |

**The population is `tools/*.py` only** (`:108-112`) — so the sweep does not
see `tests/`, `api/` or `.githooks/`. Not a defect; a scope, and the fixture
must not assume otherwise.

---

## 2. THE FIXTURE — `--fixtures`, 14 arms, each naming the input it must refuse

**Add a `--fixtures` arm** beside the existing `--list`, `--empirical` and
`--baseline`. It must run **without touching the real `tools/` directory**:
point `classify()` at a temp directory of synthetic tool files. That is the one
structural change the fixture needs — **`tools()` at `:108` hard-codes
`REPO/tools`**, so it needs a parameter (default unchanged) or the classifier
needs to take a list of paths. **Nothing else about the tool should move.**

| # | synthetic input | must classify as | why this arm exists |
|---:|---|---|---|
| **1** | a tool that reads text and calls `re.search` straight over it | **RAW** | the base case |
| **2** | a tool that reads text and strips comments/literals first | **MASKED** | the base case's opposite |
| **3** | a tool that **parses** (`ast.parse`, a tokeniser) rather than scanning | **MASKED** | parsing is the stronger form and must not read as RAW |
| **4** | a tool named in `BY_DESIGN` | **BY-DESIGN**, and the arm asserts a **non-empty reason** comes back with it | a by-design exception with no reason is a skip-list entry |
| **5** | **BAD INPUT:** a tool whose *only* mention of masking is **inside a comment or a docstring** — e.g. a docstring reading *"this does not strip literals"* | **RAW** | **THE ARM THIS WHOLE DOCUMENT IS ABOUT.** `MASKS` (`:80`) is a regex over raw source, so prose about masking can credit a tool that does none. **This is the b13 A1 defect, in the tool whose subject is that defect.** |
| **6** | **BAD INPUT:** a tool that reads text but never matches | **excluded from the population**, not RAW | a non-gate counted as a raw gate inflates the number the exit code is computed from |
| **7** | **BAD INPUT:** a tool that matches patterns but never reads a file | **excluded** | same, other direction |
| **8** | **BAD INPUT:** an unreadable file in the directory | **exit 2 COULD NOT TELL** | `:122` already does this; the arm stops a later "just skip it" |
| **9** | **BAD INPUT:** a directory where **nothing** matches read-text-and-match | **exit 2**, with the message naming that the SHAPE MOVED | `:133` — the subtlest fail-open in the tool: zero findings and zero population look identical in a count |
| **10** | **BAD INPUT:** no `tools/` directory at all | **exit 2** | `:111` |
| **11** | raw count **above** the pin | **exit 1**, and the message names both numbers | the live case today, 82 → 111 |
| **12** | raw count **equal to** the pin | **exit 0** | the boundary — `<=`, not `<` |
| **13** | raw count **below** the pin | **exit 0**, and the arm asserts it does **not** silently re-pin | a tool that re-pins on improvement cannot report a later regression |
| **14** | **CONTROL:** the real `tools/` directory, classified | **exit 0 or 1, never 2** | an exit 2 on the real repo means the classifier stopped recognising its own population, which is arm 9 in the wild |

**Arms 6, 7, 12, 13 and 14 are the over-refusal guards.** Arms **5 and 9 are
the two that would catch a silent failure**; the rest catch a loud one.

### The decoy arms — `--empirical`, which already exists and is unlocked

`DECOY_PY` (`:144`) and `DECOY_SQL` (`:155`) are files in which **every line is
a comment or a string**. The empirical half feeds them to each gate.

| # | arm | must happen |
|---:|---|---|
| **E1** | a gate that reports **anything** about `DECOY_PY` | recorded as **fooled** |
| **E2** | **CONTROL:** a gate fed a file containing a **real** finding in real code | reports it — **otherwise "fooled: 0" and "broken: all" are the same observation** |
| **E3** | a gate that crashes on the decoy | **its own state, not "clean"** |

**E2 is the arm that is missing in spirit today:** `empirically_probed` in the
pin is an **empty list**, so the empirical half has never been baselined, and a
pass from it currently proves nothing about whether the probe can see anything
at all.

---

## 3. WHAT THE FIXTURE MUST NOT DO

* **It must not write `docs/text-gate-literal-coverage.json`.** `--baseline`
  writes the pin; `--fixtures` must be read-only apart from its own temp
  directory. A fixture that re-pins is the detector blessing its own fix.
* **It must not need the network or the real repo** — arms 1–13 are synthetic.
* **It must not assert the raw COUNT.** 111 today, and a number in a fixture
  rots in a week. Assert the **classification of a known input** and the
  **relation** between count and pin.
* **It must not widen `MASKS`.** If arm 5 fails — and I expect it to —
  the fix is a narrower, code-aware test, not a bigger regex. **Specified
  rather than left: a regex that reads prose cannot be fixed by more regex.**

## 4. AFTER THE FIXTURE, AND NOT BEFORE: the 111-vs-82 triage

1. Re-run and get the current list (`--list`).
2. For each of the 29 new raw gates, the question is the tool's own words
   (`:48-52`): *could a decoy in a literal change this tool's verdict?* Answer
   **per tool**, by its author.
3. Those that are correctly raw go in `BY_DESIGN` **with a reason** — the arm-4
   shape — and the pin is re-cut **in the same commit**, which the tool's own
   message already demands.
4. **The 58-gate growth in the population is the real story** and belongs in
   the commit message: the pin was cut when 157 tools read text; 215 do now.

## 5. WHAT THIS SPEC DOES NOT CLAIM

* **It does not say the tool is wrong.** It says nothing locks its classifier,
  and its pin is 17 days behind a population that grew by 37%.
* **It does not predict arm 5 passes.** I expect it to **fail on first run**,
  which is the point: a fixture that passes immediately has not been shown to
  fail.
* **It does not do the triage.** Four steps in §4, all cc's, all after the
  fixture.
* **It does not touch `tools/`.** Row 11 is mine on the priority list and the
  code is cc's; this document is the only part I can write.

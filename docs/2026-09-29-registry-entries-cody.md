# Report-only registry entries for three checkers — paste-ready, not edited in

**2026-09-29 (Cody).** Three checkers exist with controls declared on both ends
and **none of them is in `tools/report_only_checks.py`**, so nothing runs them on
a cadence and `checker_control_check.promoted()` — which reads that registry and
nothing else — does not count their pairs.

**Why this is a document and not an edit.** Michael directed that the registry
entries be delivered as paste-ready text rather than edited in. That direction
stands on its own; it is **not** a conflict workaround, and at the time of
writing `tools/report_only_checks.py` carries **no live claim**. The unclaimed
state is reported here rather than acted on, which is the honest version of
"blocked": nothing stopped the edit except a decision, and the decision is
Michael's.

**What the reader has to do:** paste each block into the `REGISTRY` list in
`tools/report_only_checks.py`, then run `python tools/report_only_checks.py
--list` to confirm the count moved by three.

---

## 1. `assertion_label_shape_check.py`

```python
    {
        'tool': 'assertion_label_shape_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-29, report-only and it must STAY report-only. It '
                    'reports a TEST ARM whose label claims a universal while '
                    'its comparison is one-sided, and the repair is to tighten '
                    'the assertion -- but a GATE HERE WOULD BE CLEARED BY '
                    'REWORDING THE LABEL, which makes the honest fix the '
                    'expensive one and the dishonest fix a two-word edit. '
                    'Control: tests/run_assertion_label_shape_probe.py (29 '
                    'arms, both directions, with a known-bad JavaScript arm and '
                    'its silent half).',
        'catches': 'a test arm labelled "every / all / no X" that is actually '
                   'asserting a floor -- `>= 4` under a label claiming every '
                   'answer carries the limits',
        'why_it_matters': 'ITS FIRST LIVE JAVASCRIPT RUN FOUND ONE IN THE '
                          'AUTHOR\'S OWN SUITE. api/_lib/sc-denial-reconcile.'
                          'test.js asserted `limits.length >= 4` under the '
                          'label "the limits travel with EVERY answer"; the '
                          'module publishes five, so one could be dropped -- '
                          'including the limit saying no probability is '
                          'computed, the single claim that app has explicitly '
                          'refused elsewhere -- and the arm stayed green. The '
                          'two tiers are printed SEPARATELY and the output says '
                          'they are not added together: CONFIRMED is a finding, '
                          'ADVISORY is the exhaustive word sitting in the '
                          'rationale rather than the claim, and one number over '
                          'both would be a score nobody agreed. Python goes '
                          'through `ast`; JavaScript goes through a balanced '
                          'scan over a comment-stripped, string-blanked copy, '
                          'and a file whose two copies differ in length is '
                          'REFUSED under COULD NOT RUN rather than counted '
                          'clean',
    },
```

## 2. `entry_point_scope_check.py`

```python
    {
        'tool': 'entry_point_scope_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-29, report-only. Static, seconds, and its '
                    'population moves the moment a tool grows a flag or a '
                    'subcommand -- which is exactly the change nobody '
                    'announces. Control: tests/run_entry_point_scope_probe.py '
                    '(33 arms), which reconstructs the REAL pre-fix shape of '
                    'tier_a_review_gate.py in memory and demands the tool '
                    'report it, so a clean sweep is evidence rather than '
                    'decoration.',
        'catches': 'a tool whose several real-data entry points enumerate '
                   'DIFFERENT MEMBERS OF ONE POPULATION FAMILY -- the copy a '
                   'human invokes is not the copy that enforces',
        'why_it_matters': 'THE NAMED INSTANCE COST A REAL SESSION A REAL PUSH. '
                          'tier_a_review_gate.py answered from the WORKING TREE '
                          'on a bare run and from a merge-base commit range in '
                          'the push hook; a session was told "No file in this '
                          'change names a Tier A resource" and was then DENIED '
                          'by the same tool naming seven. Both answers were '
                          'true about what they read and neither was about the '
                          'question asked. The criterion is NOT "two doors '
                          'differ" -- a door that reads no scope accessor at '
                          'all is answering a different question and is allowed '
                          'to, which is why the fixed tool must stay silent. '
                          'It reads dispatch tables as well as flags, and it '
                          'ABLATES that layer on every run rather than claiming '
                          'it: claim_provenance.py has four subcommand doors '
                          'and no flag anywhere, and was reported as having one',
    },
```

## 3. `parse_zero_third_state_check.py`

```python
    {
        'tool': 'parse_zero_third_state_check.py',
        'mode': 'once',
        'verdict': by_exit,
        'promoted': '2026-09-29, report-only and it PROPOSES rather than '
                    'applies (discipline 11 -- a detector that blesses its own '
                    'fix is the fail-open one step later). Some of the corpora '
                    'it names are ALLOWED to be empty: an outgoing-file list is '
                    'empty on a clean push and must not fail, so every proposed '
                    'guard needs a human decision before it lands. Control: '
                    'tests/run_parse_zero_third_state_probe.py (22 arms).',
        'catches': 'a checker whose corpus enumeration returns nothing, which '
                   'it then reports as a clean sweep -- "read 0 file(s) / '
                   'CLEAN"',
        'why_it_matters': 'IT IS THE COVERAGE "0 of 0 is not 100%" FAILURE '
                          'MOVED DOWN A LEVEL, and it is silent in every '
                          'direction: the git ls-files pattern stops matching '
                          'after a directory move, the subprocess fails and '
                          'returns an empty string, an extension changes. None '
                          'of those is a repo with nothing wrong in it and none '
                          'of them prints an error. Five real sites on the day '
                          'it was built, all fixed, including one that printed '
                          'COULD NOT MEASURE and returned exit 0 -- so every '
                          'reader of the exit code saw a pass and the only '
                          'reader that mattered never read the text. THE '
                          'COULD-NOT-TELL FIGURE IS PUBLISHED RATHER THAN '
                          'FOLDED INTO CLEARED: it judges a small minority of '
                          'tools/, and "no corpus variable I could find" and '
                          '"safe" are different statements',
    },
```

---

## What each entry is claiming, in one line, so a reviewer can disagree with it

| tool | it is report-only because | if it were a gate |
|---|---|---|
| `assertion_label_shape_check.py` | the repair is to tighten an assertion | the gate clears by **rewording the label** — two words, and the arm still asserts a floor |
| `entry_point_scope_check.py` | it is a static approximation with named blind spots, and a tool is allowed two doors answering two questions | the gate clears by collapsing a legitimate second door |
| `parse_zero_third_state_check.py` | some corpora are legitimately empty | the gate breaks every clean push, because an outgoing-file list is empty when there is nothing to ship |

## Verification before pasting

Each block's claims were run, not recalled:

    python tools/assertion_label_shape_check.py       # 811 of 811 suite files
    python tests/run_assertion_label_shape_probe.py   # 29 arms
    python tools/entry_point_scope_check.py           # 74 of 257 tools
    python tests/run_entry_point_scope_probe.py       # 33 arms
    python tools/parse_zero_third_state_check.py      # 7 of 257 tools, now clean
    python tests/run_parse_zero_third_state_probe.py  # 22 arms

**Do not quote those figures from here — they move.** Run the commands.

#!/usr/bin/env python
r"""tooling_inventory.py -- GENERATE docs/TOOLING-INVENTORY.md from the wiring.

    python tools/tooling_inventory.py            # write the document
    python tools/tooling_inventory.py --check    # is the document still true?

WHY THIS IS A GENERATOR AND NOT A DOCUMENT.

docs/2026-09-09-tooling-inventory.md was hand-derived, correct on the day, and
STALE WITHIN THREE DAYS. Its headline said 77 tools, 3 report-only and 28
unwired checkers. Measured 2026-09-12: 97 tools and 26 report-only. Nine
checkers were promoted and twelve more were built in between, and nothing about
the document knew. That is the same claim-in-two-places failure this repo keeps
recording -- applied to the inventory of the safety net, which is the one
document whose staleness is hardest to notice, because a tool that does not run
produces no output to contradict it.

So the only honest version is derived, and `--check` is what makes it stay true.
Same treatment as docs/traceability-matrix.md for the same reason.

WHAT IS DERIVED AND WHAT IS NOT.

Derived, every run, from the repo:
  * the tool list          -- `git ls-files tools/`
  * BLOCKING               -- PreToolUse hooks in .claude/settings.json, plus
                              every tools/<name> the push gate shells out to
                              (it is the thing that can call deny())
  * REPORT-ONLY            -- REGISTRY in tools/report_only_checks.py, plus
                              PostToolUse hooks
  * ADVISORY               -- SessionStart / UserPromptSubmit hooks
  * SUITE-ONLY             -- referenced by something under tests/, so it runs,
                              but only ever against fixtures
  * UNWIRED                -- referenced by none of the above
  * `catches`              -- for the 26 report-only tools it is read straight
                              out of REGISTRY, which already carries it

NOT derived, and it cannot be: what a tool catches, for everything that is not
in REGISTRY. That is judgement and lives in PURPOSES below. The generator
REFUSES to run if a tool has no entry, and refuses if PURPOSES names a tool
that no longer exists -- so the hand-written half cannot drift in either
direction without failing loudly.

LIMIT, stated rather than discovered: "BLOCKING" means the tool is reachable
from something that can refuse. It does not mean every one of its findings
blocks -- the push gate has report-only checks INSIDE it (5 and 7 were promoted
from exactly that state), and this cannot see which. Read the gate for that.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join('docs', 'TOOLING-INVENTORY.md')
SETTINGS = os.path.join('.claude', 'settings.json')
GATE = os.path.join('tools', 'sairn_push_gate_hook.py')

# ── THE HAND-WRITTEN HALF ───────────────────────────────────────────────────
# One line per tool that REGISTRY does not already describe. Kept here rather
# than in the document so the document stays fully generated, and so a missing
# entry is an ERROR rather than a blank cell nobody notices.
#
# `kind` is the thing a reader most needs: CHECKER means it answers a
# pass/fail question about this codebase; LIBRARY means it is imported or
# shelled out to by something else; GENERATOR means it writes a file;
# LIVE means it makes a real network or database request, so it cannot be wired
# into a hook without making every push talk to the outside world.
PURPOSES = {
    # --- invoked by a hook or by the push gate -----------------------------
    'sairn_push_gate_hook.py': ('CHECKER', 'the ten numbered push checks; the only tool that calls deny()'),
    'git_push_master_guard.py': ('CHECKER', 'a push aimed at `master`, which is stale'),
    'redaction_check.py': ('CHECKER', 'credential shapes in what is about to be written, and in what a push ships'),
    'html_script_check.py': ('CHECKER', 'a script block that no longer parses, after a Write or Edit'),
    'deploy_verify_notify.py': ('CHECKER', 'a push whose deploy never reached the live site'),
    'report_only_checks.py': ('LIBRARY', 'the report-only registry and its runner -- the 26 entries above'),
    'session_lock_check.py': ('CHECKER', 'a second session in the same clone, at start and on every prompt'),
    'sairn_claim_hook.py': ('CHECKER', "another session's active claim on the work about to start"),
    'employee_auth_guard_check.py': ('CHECKER', 'a SQL file writing credential rows with no recoverability guard (gate check 2)'),
    'sairn_sql_preflight.py': ('CHECKER', 'SQL referencing a column or table the live schema does not have (gate check 3)'),
    'sairn_load_state_check.py': ('LIVE', 'live seed content differing from the repo seed (gate check 1)'),
    'sairn_seam_check.py': ('CHECKER', 'an endpoint dropping a field the engine reads (gate check 4)'),
    'sairn_reachability_check.py': ('CHECKER', 'a feature no user can reach (gate check 5)'),
    'preauth_oracle_check.py': ('CHECKER', 'an endpoint that answers before it authenticates (gate check 7)'),
    # NOT gate check 9, and the stale inventory said it was. Check 9 runs the
    # test files named in the gate's own GUARD_TESTS list directly; nothing in
    # the repo references this tool at all. Corrected here because a wrong claim
    # about what guards a push is the exact failure this document exists to stop.
    'verify_review_gates.py': ('CHECKER', 'review-gate evidence in a claims ledger -- referenced by NOTHING in this repo'),
    # --- checkers nothing invokes ------------------------------------------
    'cleanup_residue_check.py': ('CHECKER', 'rows a cleanup SQL file claims to have removed and did not'),
    'licence_recoverability_check.py': ('LIVE', 'a licence with credential rows and zero active provisioners'),
    'local_only_collection_check.py': ('CHECKER', 'a collection written only to localStorage that never reaches a server'),
    'missing_dom_target_check.py': ('CHECKER', 'a getElementById target that appears as no id in the file'),
    'reclassification_sweep.py': ('LIVE', 'a statutory rule whose source has been reclassified'),
    'rf_claim_gate_live_probe.py': ('LIVE', "SAIRNroofing's claim gate, against the deployed endpoint"),
    'rf_roundtrip_probe.py': ('LIVE', 'a SAIRNroofing write read back through the real API'),
    'probe_public_book_guardian.py': ('LIVE', "the public booking endpoint's guards, live"),
    'stonedesk_storefront_live_check.py': ('LIVE', 'whether sql/stonedesk_public_surface_schema.sql was really run, by probing the three public endpoints -- the instruction "confirm by re-probing, not by the editor reporting success", mechanised'),
    'sairn_ai_fact_scan.py': ('CHECKER', 'a number an AI panel states that no function computes'),
    'sairn_app_map_check.py': ('LIVE', "an app absent from Guardian's own app map, and a route that 404s"),
    'sairn_dead_function_sweep.py': ('CHECKER', 'a function with no caller anywhere'),
    'sairn_reachability_probe.py': ('CHECKER', 'the rendered-DOM half of reachability, from a browser snapshot'),
    'sairn_stale_snapshot_scan.py': ('CHECKER', 'a panel rendering from a snapshot nothing refreshes'),
    'sairnlaw_citation_audit.py': ('LIVE', 'a legal citation whose source no longer says what the rule claims'),
    'schema_provisioning_check.py': ('LIVE', 'a resource the app writes to whose table was never created'),
    'va_rule_currency.py': ('LIVE', 'a Virginia rule whose published source has moved on'),
    'waf_rule_check.py': ('LIVE', 'a WAF rule that would block a real request the product makes'),
    'write_path_fault_scan.py': ('CHECKER', 'a server write whose result is read on the success path only, or not at all'),
    'sairn_build_load_gates.py': ('GENERATOR', 'SUPERSEDED -- its header says so; a generated gate goes stale by design'),
    # --- libraries and generators -----------------------------------------
    'jscomments.py': ('LIBRARY', 'the one comment stripper every scanner should use'),
    'sairn_http.py': ('LIBRARY', 'browser-shaped HTTP, raising Challenged rather than letting a 403 look like an answer'),
    'sairn_source_fetch.py': ('LIBRARY', 'fetching a primary source with its retrieval date recorded'),
    'extract_scripts.py': ('LIBRARY', 'script blocks out of an app file, HTML-parser based'),
    'extract_panels.py': ('LIBRARY', 'panel containers out of an app file'),
    'outline.py': ('LIBRARY', 'a function/section outline of a large file'),
    'js_code_only_diff.py': ('LIBRARY', 'a diff with comment-only changes removed'),
    'run_all_tests.py': ('LIBRARY', 'every .js and .py under tests/, plus api/**/*.test.js'),
    'run_semgrep.py': ('LIBRARY', 'the .semgrep rules, when semgrep is installed'),
    'install_git_hooks.py': ('LIBRARY', 'points core.hooksPath at .githooks -- per clone, once'),
    'sairn_claim.py': ('LIBRARY', 'claim / release / check / list on the work-claim files'),
    'gh_push.py': ('LIBRARY', 'a push whose arrival on the remote is queried back'),
    'gh_verify.py': ('LIBRARY', 'whether a commit is really on the remote'),
    'load_deadline_seed.py': ('LIVE', 'loads a deadline seed into a live licence'),
    'sairn_dom_snapshot.js': ('LIBRARY', 'a rendered-DOM snapshot, run in the browser'),
    'strict_args_harness.js': ('LIBRARY', 'proves the engine really discards a mutated parameter under strict mode'),
    'verify-session-token-app-scope.js': ('LIBRARY', 'the semgrep rule body for the app-scope check'),
    'posthook.cjs': ('LIBRARY', 'the Node half of a PostToolUse hook'),
    'fetch_blocked_doc.sh': ('LIBRARY', 'fetches a document a plain request cannot reach'),
    # DELETED from here 2026-09-12: it is in report_only_checks.py's REGISTRY,
    # which already carries its `catches`. Two descriptions of one tool can
    # disagree, and REGISTRY is the copy that actually runs. Found by this file's
    # own probe, section C -- the duplication existed for one commit.
}
for _p in ('gen_ma_calendar.py', 'gen_ma_seed.py', 'gen_mn_calendar.py', 'gen_mn_seed.py',
           'gen_mo_calendar.py', 'gen_mo_seed.py', 'gen_nj_calendar.py', 'gen_nv_calendar.py',
           'gen_ok_calendar.py', 'gen_or_calendar.py', 'gen_sc_calendar.py',
           'gen_ut_calendar.py', 'gen_va_calendar.py', 'gen_va_seed.py'):
    PURPOSES[_p] = ('GENERATOR', 'a court-holiday calendar or deadline seed for one state')


def git(*args):
    r = subprocess.run(['git', '-C', REPO] + list(args), capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def tool_files():
    out = []
    for f in git('ls-files', 'tools/').split('\n'):
        f = f.strip()
        if f.endswith(('.py', '.js', '.cjs', '.sh')) and '__pycache__' not in f:
            out.append(os.path.basename(f))
    return sorted(set(out))


def hooked():
    """{tool: [event, ...]} from .claude/settings.json."""
    out = {}
    try:
        d = json.load(io.open(os.path.join(REPO, SETTINGS), encoding='utf-8'))
    except Exception:
        return out
    for ev, lst in (d.get('hooks') or {}).items():
        for entry in lst:
            for hk in entry.get('hooks', []):
                for m in re.finditer(r'tools/([\w.\-]+)', hk.get('command', '') or ''):
                    out.setdefault(m.group(1), []).append(ev)
    return out


def gate_invokes():
    """Tools the push gate shells out to -- reachable from deny()."""
    src = io.open(os.path.join(REPO, GATE), encoding='utf-8', errors='replace').read()
    return sorted(set(re.findall(r"'([\w.\-]+\.py)'", src))
                  & set(tool_files()))


def gate_checks():
    src = io.open(os.path.join(REPO, GATE), encoding='utf-8', errors='replace').read()
    found = {}
    for m in re.finditer(r'#\s*──+\s*CHECK (\d+):\s*(.+?)\s*[─]*\s*$', src, re.M):
        found[int(m.group(1))] = m.group(2).strip().rstrip('-').strip()
    return [(n, found[n]) for n in sorted(found)]


def _roc():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'roc', os.path.join(REPO, 'tools', 'report_only_checks.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def registry():
    return [(r['tool'], r.get('promoted', '?'), ' '.join(str(r.get('catches', '')).split()))
            for r in _roc().REGISTRY]


def not_promoted():
    r"""{tool: why} from report_only_checks.py's NOT_PROMOTED list.

    ADDED 2026-09-12, because the first version of this file DID NOT READ IT and
    the headline number was wrong as a result. It counted 13 checkers as "pointed
    at by nobody"; SIX of those are on this list with a recorded reason -- a
    read-list whose own output refuses to be quoted bare, a tool needing a browser
    snapshot, two with open owned findings. Somebody had already decided each one,
    in writing, in the file this generator was already importing.

    That is the mirror of the SUITE-ONLY mistake in the same file: there the count
    OVERSTATED coverage, here it OVERSTATED the gap. Same root cause both times --
    a source of truth that existed and was not read. A number that calls a
    deliberate decision an unaddressed gap is how a reader stops believing the
    number.

    Entries can name several tools separated by commas; split so each is findable.
    """
    out = {}
    for tools_str, why in _roc().NOT_PROMOTED:
        for name in [s.strip() for s in tools_str.split(',')]:
            if name:
                out[name] = ' '.join(str(why).split())
    return out


def suite_refs(tools):
    r"""Tools a file under tests/ actually INVOKES or IMPORTS -- not merely names.

    The first version accepted any mention, and that over-classified in the
    OPTIMISTIC direction, which is the one this document must never fail in:
    SUITE-ONLY reads as "this runs", UNWIRED reads as "nothing runs it". Measured
    before tightening -- three tools moved, all three LIVE and all three named
    only inside a LIST of tools in tests/sairn_http_challenge.py:
    licence_recoverability_check.py, load_deadline_seed.py, sairn_app_map_check.py.
    Their verdict is unchanged (unwired is correct for a LIVE tool) but the COUNT
    was wrong, and the count is what this file exists to state.
    """
    refs = {}
    for root, dirs, files in os.walk(os.path.join(REPO, 'tests')):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if not f.endswith(('.py', '.js')):
                continue
            try:
                txt = io.open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
            except IOError:
                continue
            for t in tools:
                if t not in txt:
                    continue
                stem = re.escape(t.rsplit('.', 1)[0])
                esc = re.escape(t)
                invoked = (
                    ('tools/' + t) in txt
                    or re.search(r"'tools'\s*,\s*'" + esc + r"'", txt)
                    or re.search(r'(?:^|' + chr(10) + r')\s*import\s+' + stem + (chr(92) + 'b'), txt)
                    or re.search(r'spec_from_file_location\([^)]*' + esc, txt)
                    or re.search(r"require\(['\"][^'\"]*" + stem, txt))
                if invoked:
                    refs.setdefault(t, set()).add(f)
    return {k: sorted(v) for k, v in refs.items()}


def classify():
    tools = tool_files()
    hk = hooked()
    gi = set(gate_invokes())
    reg = dict((t, (p, c)) for t, p, c in registry())
    suite = suite_refs(tools)

    nop = not_promoted()

    cls = {}
    for t in tools:
        evs = hk.get(t, [])
        if 'PreToolUse' in evs or t in gi:
            cls[t] = 'BLOCKING'
        elif t in reg or 'PostToolUse' in evs:
            cls[t] = 'REPORT-ONLY'
        elif evs:
            cls[t] = 'ADVISORY'
        elif t in nop:
            # A RECORDED DECISION IS NOT A GAP. Checked before SUITE-ONLY and
            # UNWIRED on purpose: several of these also have a probe, and
            # reporting one as "the suite runs it on fixtures" buries the fact
            # that somebody already decided not to wire it, and why.
            cls[t] = 'DECIDED'
        elif t in suite:
            cls[t] = 'SUITE-ONLY'
        else:
            cls[t] = 'UNWIRED'
    return tools, cls, hk, gi, reg, suite


def purpose(t, reg):
    if t in reg:
        return 'CHECKER', reg[t][1]
    return PURPOSES[t]


def missing_purposes(tools, reg):
    absent = [t for t in tools if t not in reg and t not in PURPOSES]
    extra = [t for t in PURPOSES if t not in tools]
    return absent, extra


def build():
    tools, cls, hk, gi, reg, suite = classify()
    absent, extra = missing_purposes(tools, reg)
    if absent or extra:
        lines = ['REFUSING to generate -- the hand-written half has drifted.', '']
        if absent:
            lines += ['%d tool(s) in tools/ with no PURPOSES entry. A blank cell in this'
                      % len(absent),
                      'document is exactly how the last one went stale, so this is an error:']
            lines += ['    ' + t for t in absent]
        if extra:
            lines += ['', '%d PURPOSES entr(y/ies) naming a tool that no longer exists:' % len(extra)]
            lines += ['    ' + t for t in extra]
        return None, '\n'.join(lines)

    order = ['BLOCKING', 'REPORT-ONLY', 'ADVISORY', 'DECIDED', 'SUITE-ONLY', 'UNWIRED']
    counts = dict((k, sum(1 for t in tools if cls[t] == k)) for k in order)
    kinds = {}
    for t in tools:
        kinds.setdefault(purpose(t, reg)[0], []).append(t)

    W = []
    A = W.append
    A('# The tooling inventory -- what exists, what it catches, what actually runs')
    A('')
    A('**GENERATED by `python tools/tooling_inventory.py`. Do not hand-edit.**')
    A('Run `--check` to find out whether it still matches the repo; a mismatch is a')
    A('finding, not a document somebody forgot.')
    A('')
    A('Every classification below is derived from `.claude/settings.json`,')
    A('`tools/sairn_push_gate_hook.py`, `tools/report_only_checks.py`\'s own REGISTRY,')
    A('`tests/`, and `git ls-files tools/` -- never from a prior inventory.')
    A('')
    A('**Why it is generated.** `docs/2026-09-09-tooling-inventory.md` was')
    A('hand-derived, correct on the day, and **stale within three days**: it said 77')
    A('tools, 3 report-only and 28 unwired checkers. Nine checkers were promoted and')
    A('twelve more built in the three days after. Nothing about the document knew,')
    A('and a tool that does not run produces no output to contradict it -- which')
    A('makes this the one inventory whose staleness is hardest to notice.')
    A('')
    A('---')
    A('')
    A('## The headline')
    A('')
    A('**%d files in `tools/`.** By what actually invokes them:' % len(tools))
    A('')
    A('| Status | Count | Meaning |')
    A('|---|---:|---|')
    MEAN = {
        'BLOCKING': 'reachable from something that can refuse a push or a tool call',
        'REPORT-ONLY': 'runs automatically on every push, never blocks',
        'ADVISORY': 'session-start or prompt hooks, informational',
        'SUITE-ONLY': 'run by `tests/`, so proved to WORK -- on fixtures. Never pointed at the codebase',
        'DECIDED': 'deliberately NOT promoted, with a reason recorded in report_only_checks.py',
        'UNWIRED': 'nothing runs these at all',
    }
    for k in order:
        A('| **%s** | %d | %s |' % (k, counts[k], MEAN[k]))
    A('')
    A('By what they are, independent of wiring:')
    A('')
    A('| Kind | Count |')
    A('|---|---:|')
    for k in sorted(kinds):
        A('| %s | %d |' % (k, len(kinds[k])))
    A('')
    unwired_checkers = [t for t in tools if cls[t] == 'UNWIRED'
                        and purpose(t, reg)[0] == 'CHECKER']
    suite_checkers = [t for t in tools if cls[t] == 'SUITE-ONLY'
                      and purpose(t, reg)[0] == 'CHECKER']
    live_unwired = [t for t in tools if cls[t] in ('UNWIRED', 'SUITE-ONLY')
                    and purpose(t, reg)[0] == 'LIVE']
    A('**%d tool(s) are DECIDED -- deliberately not promoted, with the reason'
      % counts['DECIDED'])
    A('recorded in `report_only_checks.py`.** They are listed below with those')
    A('reasons and are NOT counted as gaps. The first version of this document did')
    A('not read that list and reported six of them as unaddressed.')
    A('')
    _act = len(unwired_checkers) + len(suite_checkers)
    if _act == 0:
        # THE ZERO CASE GETS ITS OWN WORDING. A document that reads as broken at
        # zero -- "The 0, by name" under a sentence about which group is worse --
        # is one people stop trusting at exactly the moment it has good news.
        A('**The number to act on: ZERO.** Every checker that answers a question')
        A('about this codebase is now either promoted to report-only or carries a')
        A('recorded reason for not being. That was 13 on 2026-09-12 before the')
        A('pass that closed it: four were promoted (`checkblocks.py`,')
        A('`comment_sensitivity_check.py`, `criticality_tier_check.py`,')
        A('`soup_register_check.py`), three were recorded as deliberate, and six')
        A('had already been decided in a list this document was not reading.')
        A('')
        A('**That is not the same as being covered.** It means nothing is')
        A('unexamined. A promoted checker reports; it does not block, and several')
        A('of the DECIDED entries are decisions to look later.')
        A('')
    else:
        A('**The number to act on: %d checker(s) that answer a question about this'
          % _act)
        A('codebase and are pointed at it by nobody** -- %d wired nowhere at all, and %d'
          % (len(unwired_checkers), len(suite_checkers)))
        A('that the suite runs against FIXTURES only. The second group is the worse one:')
        A('a green probe on an unpointed checker is the most convincing possible form of')
        A('"we are covered", and it is coverage of the tool rather than of the code.')
        A('')
    if _act:
        A('The %d, by name, so this is actionable rather than a statistic:' % _act)
        A('')
        A('| Tool | Status | What it catches |')
        A('|---|---|---|')
        for t in sorted(unwired_checkers + suite_checkers):
            A('| `%s` | %s | %s |' % (t, cls[t], purpose(t, reg)[1]))
        A('')
    A('**Separately, %d tool(s) make a LIVE network or database request.** Those are' % len(live_unwired))
    A('correctly manual: wiring one into a hook would make every push talk to the')
    A('outside world. Unwired is the right state for them and is not a finding.')
    A('')
    A('---')
    A('')
    A('## BLOCKING (%d)' % counts['BLOCKING'])
    A('')
    A('Two entry points, and they are not the same one. `.claude/settings.json`')
    A('PreToolUse fires on a Claude Code **tool call**; `.githooks/pre-push` fires on')
    A('the **git operation**, so a push from a Python subprocess cannot spell its way')
    A('around it. The second exists because the first missed exactly that on')
    A('2026-09-01. Per clone, once: `python tools/install_git_hooks.py`.')
    A('')
    A('| Tool | Kind | What it catches |')
    A('|---|---|---|')
    for t in sorted(t for t in tools if cls[t] == 'BLOCKING'):
        k, c = purpose(t, reg)
        A('| `%s` | %s | %s |' % (t, k, c))
    A('')
    A('### The push gate\'s own numbered checks')
    A('')
    A('Derived from the `CHECK n:` blocks in `tools/sairn_push_gate_hook.py`, which is')
    A('the only source that moves when one is added.')
    A('')
    A('| # | Check |')
    A('|---:|---|')
    for n, title in gate_checks():
        A('| %d | %s |' % (n, title))
    A('')
    A('---')
    A('')
    A('## REPORT-ONLY (%d)' % counts['REPORT-ONLY'])
    A('')
    A('Run by `tools/report_only_checks.py` as a PostToolUse hook on every push.')
    A('`catches` is read out of that file\'s own REGISTRY, so it cannot disagree with')
    A('what runs. They are on a promotion path: blocking only once each has been')
    A('quiet in practice.')
    A('')
    A('| Tool | Promoted | What it catches |')
    A('|---|---|---|')
    for t, p, c in sorted(registry()):
        A('| `%s` | %s | %s |' % (t, p, c))
    A('')
    # THE COUNT ABOVE IS NOT THE LENGTH OF THAT TABLE, and saying so beats letting
    # a reader add it up and find 26 under a heading that says 29. Three tools are
    # PostToolUse hooks in their own right rather than registry entries.
    _ro_hooks = sorted(t for t in tools if cls[t] == 'REPORT-ONLY' and t not in reg)
    A('And %d that are PostToolUse hooks in their own right, not registry entries:'
      % len(_ro_hooks))
    A('')
    A('| Tool | Kind | What it catches |')
    A('|---|---|---|')
    for t in _ro_hooks:
        k, c = purpose(t, reg)
        A('| `%s` | %s | %s |' % (t, k, c))
    A('')
    A('---')
    A('')
    A('## DECIDED -- not promoted, on purpose (%d)' % counts['DECIDED'])
    A('')
    A('**These are not gaps.** Each carries a recorded reason in')
    A("`tools/report_only_checks.py`'s `NOT_PROMOTED` list -- a read-list whose own")
    A('output refuses to be quoted bare, a tool needing a browser snapshot, one with')
    A('an open owned finding, a live network probe. The first version of this')
    A('document did not read that list and counted six of them as unaddressed, which')
    A('is how a reader stops believing the number.')
    A('')
    A('| Tool | Kind | Why not promoted |')
    A('|---|---|---|')
    _nop = not_promoted()
    for t in sorted(t for t in tools if cls[t] == 'DECIDED'):
        kind = purpose(t, reg)[0]
        A('| `%s` | %s | %s |' % (t, kind, _nop.get(t, '?')))
    A('')
    A('---')
    A('')
    for k in ('ADVISORY', 'SUITE-ONLY', 'UNWIRED'):
        A('## %s (%d)' % (k, counts[k]))
        A('')
        if k == 'SUITE-ONLY':
            A('`tests/` names these, so they are executed on every push -- against')
            A('fixtures. Nothing points them at the real codebase.')
            A('')
        if k == 'UNWIRED':
            A('Nothing runs these. Read the Kind column before calling any of it a')
            A('finding: a LIBRARY is imported by something else and a LIVE tool is')
            A('correctly manual. Only `CHECKER` rows here are a gap.')
            A('')
        A('| Tool | Kind | What it catches | Probe under tests/ |')
        A('|---|---|---|---|')
        for t in sorted(t for t in tools if cls[t] == k):
            kind, c = purpose(t, reg)
            pr = ', '.join('`%s`' % f for f in suite.get(t, [])[:2]) or '&mdash;'
            A('| `%s` | %s | %s | %s |' % (t, kind, c, pr))
        A('')
        A('---')
        A('')
    A('## How to re-derive this')
    A('')
    A('    python tools/tooling_inventory.py --check   # does the doc still match?')
    A('    python tools/tooling_inventory.py           # rewrite it')
    A('')
    A('The generator refuses to run if a tool in `tools/` has no entry in its')
    A('`PURPOSES` map, and refuses if `PURPOSES` names a tool that is gone. A blank')
    A('cell is how the last inventory went stale, so both directions are errors')
    A('rather than omissions.')
    A('')
    A('**What this cannot tell you**, said here rather than found out: `BLOCKING`')
    A('means a tool is reachable from something that can refuse. It does not mean')
    A('every one of its findings blocks -- the push gate carries report-only checks')
    A('INSIDE it, and checks 5 and 7 were promoted out of exactly that state.')
    return '\n'.join(W) + '\n', None


def main(argv):
    doc, err = build()
    if err:
        print(err)
        return 2
    path = os.path.join(REPO, DOC)
    if '--check' in argv:
        try:
            cur = io.open(path, encoding='utf-8').read()
        except IOError:
            print('FAIL: %s does not exist. Run the generator.' % DOC)
            return 1
        if cur == doc:
            print('OK: %s matches the repo.' % DOC)
            return 0
        print('FAIL: %s no longer matches the repo -- a tool was added, promoted, '
              'wired or removed and the document was not regenerated. That is a '
              'finding, not a document somebody forgot.\n    python tools/tooling_inventory.py' % DOC)
        return 1
    io.open(path, 'w', encoding='utf-8', newline='').write(doc)
    print('wrote %s (%d lines)' % (DOC, doc.count('\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

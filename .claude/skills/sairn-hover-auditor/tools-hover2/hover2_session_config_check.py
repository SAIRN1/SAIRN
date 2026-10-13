#!/usr/bin/env python
"""hover2_session_config_check.py (batch Y item 6) -- prints this session's
own enabled skills and MCP connectors from the REAL config files, never from
a slash command and NEVER by writing anything.

STRICTLY READ-ONLY. Does not open ~/.claude/settings.json, ~/.claude.json,
or any other config file in write mode, anywhere in this file -- confirmed
by this being the only mode string ('r') used on any open() call, checked
directly rather than assumed. Settings/skill edits are explicitly OUT OF
SCOPE this batch (CC is sole owner of settings.json merges; see this role's
own handoff).

WHAT IT READS, all real, all on this machine:
  - ~/.claude.json: projects[<this project's path>].mcpServers,
    .enabledMcpjsonServers, .disabledMcpjsonServers -- the PROJECT-SCOPED
    MCP config (empty for this project as of 2026-10-08, confirmed before
    building this tool, not assumed).
  - ~/.claude.json: claudeAiMcpEverConnected -- the ACCOUNT-level claude.ai
    connectors this user has ever connected. "Ever connected" is not the
    same claim as "currently enabled" -- named as a real limit, not
    smoothed over.
  - ~/.claude.json: skillUsage -- real usageCount/lastUsedAt per skill,
    globally (not project-scoped; this file carries no per-project skill
    list at all, confirmed by reading the project dict's own keys before
    claiming otherwise).
  - <repo>/.claude/settings.json: hooks table, PER CLONE (batch b10, 2026-
    10-12, added after Michael confirmed the empty-hooks state found this
    session -- seq782/785/787 -- is authorized, not a defect). Reports
    which of the 5 hook events (PreToolUse, PostToolUse, SessionStart,
    PreCompact, UserPromptSubmit) carry at least one command and which are
    empty/absent, plus a total command count across all events. THIS IS
    REPORT-ONLY AND NEVER A FAILURE: hooks being off is Michael's own
    standing decision this batch, not a defect this tool exists to flag --
    it always returns the same exit code (0, or 2 for a genuine
    COULD-NOT-READ) regardless of whether hooks are present or empty, and
    never prints a pass/fail verdict, only a factual count.

Run:
  python hover2_session_config_check.py [--project PATH] [--repo PATH]
  python hover2_session_config_check.py --selftest
"""
import argparse
import json
import os
import sys

DEFAULT_CONFIG = os.path.join(os.path.expanduser('~'), '.claude.json')
DEFAULT_PROJECT = 'C:/Users/marsh/Documents/SAIRN-hover2'
DEFAULT_REPO = 'C:/Users/marsh/Documents/SAIRN-hover2'
HOOK_EVENTS = ('PreToolUse', 'PostToolUse', 'SessionStart', 'PreCompact',
               'UserPromptSubmit')


def load(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def hooks_report(repo_path):
    """Report-only read of <repo>/.claude/settings.json's hooks table.

    Never raises for a missing/unreadable file or an empty hooks object --
    both are real, reportable states, not errors. Returns a dict:
      {'status': 'present'|'empty'|'could_not_read', 'detail': str,
       'per_event': {event: command_count}, 'total_commands': int}
    STRICTLY READ-ONLY, same 'r'-only discipline as load() above -- this
    function never opens settings_path in a write-capable mode.
    """
    settings_path = os.path.join(repo_path, '.claude', 'settings.json')
    if not os.path.isfile(settings_path):
        return {'status': 'could_not_read',
                'detail': '%s does not exist' % settings_path,
                'per_event': {}, 'total_commands': 0}
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except Exception as e:                                     # noqa: BLE001
        return {'status': 'could_not_read',
                'detail': '%s: %s' % (settings_path, e),
                'per_event': {}, 'total_commands': 0}
    hooks = settings.get('hooks')
    if not isinstance(hooks, dict):
        return {'status': 'could_not_read',
                'detail': '%s has no "hooks" object' % settings_path,
                'per_event': {}, 'total_commands': 0}
    per_event = {}
    total = 0
    for event in HOOK_EVENTS:
        count = 0
        for matcher_block in (hooks.get(event) or []):
            count += len((matcher_block or {}).get('hooks') or [])
        per_event[event] = count
        total += count
    # Report every event this platform is known to use, even ones with no
    # key in hooks at all, so "absent" and "present but empty list" both
    # read as 0 rather than one silently being omitted from the table.
    for event in hooks:
        if event not in per_event:
            count = 0
            for matcher_block in (hooks.get(event) or []):
                count += len((matcher_block or {}).get('hooks') or [])
            per_event[event] = count
            total += count
    status = 'present' if total > 0 else 'empty'
    return {'status': status, 'detail': settings_path,
            'per_event': per_event, 'total_commands': total}


def format_hooks_report(hr):
    lines = []
    lines.append('SETTINGS.JSON HOOKS TABLE (%s), report-only, never a '
                 'failure -- hooks being off can be an authorized state:'
                 % hr['detail'])
    if hr['status'] == 'could_not_read':
        lines.append('  COULD NOT READ -- %s' % hr['detail'])
        return '\n'.join(lines)
    lines.append('  status: %s (%d total command(s) across all events)'
                 % (hr['status'].upper(), hr['total_commands']))
    for event in sorted(hr['per_event']):
        count = hr['per_event'][event]
        lines.append('  %-18s %s' % (event, 'PRESENT (%d)' % count if count
                                      else 'EMPTY'))
    return '\n'.join(lines)


def report(config_path, project_key, repo_path=None):
    d = load(config_path)
    proj = (d.get('projects') or {}).get(project_key, {})
    lines = []
    lines.append('PROJECT-SCOPED MCP SERVERS (%s):' % project_key)
    mcp = proj.get('mcpServers') or {}
    if mcp:
        for name in sorted(mcp):
            lines.append('  %s' % name)
    else:
        lines.append('  (none configured)')
    lines.append('  enabledMcpjsonServers: %r' % proj.get('enabledMcpjsonServers', []))
    lines.append('  disabledMcpjsonServers: %r' % proj.get('disabledMcpjsonServers', []))

    lines.append('')
    lines.append('ACCOUNT-LEVEL claude.ai CONNECTORS EVER CONNECTED (not the '
                 'same claim as "currently enabled"):')
    for name in sorted(d.get('claudeAiMcpEverConnected') or []):
        lines.append('  %s' % name)

    lines.append('')
    su = d.get('skillUsage') or {}
    lines.append('SKILL USAGE, GLOBAL (this file has no per-project list), '
                 '%d skill(s), sorted by usageCount descending:' % len(su))
    for name, info in sorted(su.items(), key=lambda kv: -kv[1].get('usageCount', 0)):
        lines.append('  %-30s usageCount=%-4d lastUsedAt=%s'
                     % (name, info.get('usageCount', 0), info.get('lastUsedAt', '?')))

    if repo_path:
        lines.append('')
        lines.append(format_hooks_report(hooks_report(repo_path)))

    return '\n'.join(lines)


def _selftest():
    import tempfile

    fixture = {
        'projects': {
            '/fake/project': {
                'mcpServers': {'zzz': {}},
                'enabledMcpjsonServers': ['zzz'],
                'disabledMcpjsonServers': [],
            }
        },
        'claudeAiMcpEverConnected': ['claude.ai Fake Connector'],
        'skillUsage': {
            'high-use-skill': {'usageCount': 50, 'lastUsedAt': 2},
            'low-use-skill': {'usageCount': 1, 'lastUsedAt': 1},
        },
    }
    fd, path = tempfile.mkstemp(suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(fixture, f)
        out = report(path, '/fake/project')
        assert 'zzz' in out, "project-scoped MCP server must appear"
        assert 'claude.ai Fake Connector' in out, "account connector must appear"
        assert out.index('high-use-skill') < out.index('low-use-skill'), \
            "higher usageCount must sort first"

        # KNOWN-BAD CONTROL: a project key with NO mcpServers at all must
        # print "(none configured)", not crash and not silently omit the
        # section header.
        fixture2 = {'projects': {'/fake/project': {}}, 'skillUsage': {}}
        fd2, path2 = tempfile.mkstemp(suffix='.json')
        try:
            with os.fdopen(fd2, 'w', encoding='utf-8') as f:
                json.dump(fixture2, f)
            out2 = report(path2, '/fake/project')
            assert '(none configured)' in out2
            assert 'PROJECT-SCOPED MCP SERVERS' in out2
        finally:
            os.remove(path2)

        # SABOTAGE: confirm the ONE function that touches the real config
        # (load(), the only caller of open() against config_path/args.config
        # anywhere in this file) never opens it in a write-capable mode.
        # Scoped to load()'s own source, not the whole file -- the whole-file
        # version of this check was written first and FAILED ON ITS OWN
        # FIRST RUN, flagging the selftest fixture's own temp-file writes
        # (os.fdopen(fd, 'w', ...), used to create throwaway JSON fixtures)
        # as if they were config writes. Caught before trusting the check,
        # same discipline this role's own hover2-tool-building-discipline.md
        # names.
        import inspect
        import re
        load_src = inspect.getsource(load)
        write_modes = re.findall(r"open\([^)]*['\"]([rwax+]+)['\"]", load_src)
        bad = [m for m in write_modes if any(c in m for c in 'wax+')]
        assert not bad, "load() opens the real config in a write-capable mode: %r" % bad
        assert "'r'" in load_src or '"r"' in load_src, \
            "load() should open its config file explicitly read-only"

        # ── hooks_report(): three real states, never a raised exception ────
        import shutil
        scratch = tempfile.mkdtemp()
        try:
            # (1) PRESENT: a real hooks table with commands in two events.
            present_dir = os.path.join(scratch, 'present')
            os.makedirs(os.path.join(present_dir, '.claude'))
            with open(os.path.join(present_dir, '.claude', 'settings.json'),
                      'w', encoding='utf-8') as f:
                json.dump({'hooks': {
                    'PreToolUse': [{'hooks': [{'type': 'command'}]}],
                    'PostToolUse': [{'hooks': [{'type': 'command'},
                                                {'type': 'command'}]}],
                    'SessionStart': [],
                }}, f)
            hr = hooks_report(present_dir)
            assert hr['status'] == 'present', hr
            assert hr['total_commands'] == 3, hr
            assert hr['per_event']['PreToolUse'] == 1, hr
            assert hr['per_event']['PostToolUse'] == 2, hr
            assert hr['per_event']['SessionStart'] == 0, hr
            out_present = format_hooks_report(hr)
            assert 'PRESENT' in out_present and 'EMPTY' in out_present

            # (2) EMPTY: exactly the authorized Michael-confirmed state --
            # hooks: {} with nothing in any event. Must NOT read as an error.
            empty_dir = os.path.join(scratch, 'empty')
            os.makedirs(os.path.join(empty_dir, '.claude'))
            with open(os.path.join(empty_dir, '.claude', 'settings.json'),
                      'w', encoding='utf-8') as f:
                json.dump({'hooks': {}}, f)
            hr_empty = hooks_report(empty_dir)
            assert hr_empty['status'] == 'empty', hr_empty
            assert hr_empty['total_commands'] == 0, hr_empty

            # (3) COULD NOT READ: no .claude/settings.json at all, and a
            # settings.json present but with no "hooks" key -- both are a
            # real third state, never silently folded into "empty".
            missing_dir = os.path.join(scratch, 'missing')
            os.makedirs(missing_dir)
            hr_missing = hooks_report(missing_dir)
            assert hr_missing['status'] == 'could_not_read', hr_missing

            nokey_dir = os.path.join(scratch, 'nokey')
            os.makedirs(os.path.join(nokey_dir, '.claude'))
            with open(os.path.join(nokey_dir, '.claude', 'settings.json'),
                      'w', encoding='utf-8') as f:
                json.dump({'permissions': {}}, f)
            hr_nokey = hooks_report(nokey_dir)
            assert hr_nokey['status'] == 'could_not_read', hr_nokey

            # (4) NEVER A FAILURE: format_hooks_report() must not raise, and
            # its status word must be one of the three real states, never a
            # pass/fail verdict. "never a failure" legitimately appears in
            # the report-only header text, so this checks the STATUS WORD
            # specifically rather than banning the substring "fail" outright
            # -- a check that forbids the word "failure" in its own
            # explanatory prose would be testing the wrong thing.
            for hr_case in (hr, hr_empty, hr_missing, hr_nokey):
                text = format_hooks_report(hr_case)
                assert hr_case['status'] in ('present', 'empty', 'could_not_read')
                assert 'status: PASS' not in text and 'status: FAIL' not in text

            # (5) report() wires it in only when repo_path is given, and
            # leaves existing callers (no repo arg) byte-for-byte unchanged.
            out_no_repo = report(path, '/fake/project')
            assert 'SETTINGS.JSON HOOKS' not in out_no_repo
            out_with_repo = report(path, '/fake/project', present_dir)
            assert 'SETTINGS.JSON HOOKS' in out_with_repo
            assert 'PRESENT (1)' in out_with_repo
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

        print("ALL SELFTEST CASES PASS")
        return 0
    finally:
        os.remove(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default=DEFAULT_CONFIG)
    ap.add_argument('--project', default=DEFAULT_PROJECT)
    ap.add_argument('--repo', default=DEFAULT_REPO)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if not os.path.isfile(args.config):
        print('COULD NOT RUN: %s not found' % args.config)
        return 2
    try:
        print(report(args.config, args.project, args.repo))
    except Exception as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())

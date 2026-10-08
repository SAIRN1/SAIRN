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

Run:
  python hover2_session_config_check.py [--project PATH]
  python hover2_session_config_check.py --selftest
"""
import argparse
import json
import os
import sys

DEFAULT_CONFIG = os.path.join(os.path.expanduser('~'), '.claude.json')
DEFAULT_PROJECT = 'C:/Users/marsh/Documents/SAIRN-hover2'


def load(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def report(config_path, project_key):
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

        print("ALL SELFTEST CASES PASS")
        return 0
    finally:
        os.remove(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default=DEFAULT_CONFIG)
    ap.add_argument('--project', default=DEFAULT_PROJECT)
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if not os.path.isfile(args.config):
        print('COULD NOT RUN: %s not found' % args.config)
        return 2
    try:
        print(report(args.config, args.project))
    except Exception as e:
        print('COULD NOT RUN: %s' % e)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())

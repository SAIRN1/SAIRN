"""Read-only, print-only audit of skills and MCP servers CONFIGURED FOR THIS
PROJECT -- never edits anything. Built H1 batch X (b6) item 7.

Scope is deliberately narrow and stated explicitly in the output: a
project-scoped MCP server is one declared in this repo's own `.mcp.json` or
in `.claude/settings.json`'s `mcpServers` key. Every `mcp__*` tool visible in
a live session that is NOT backed by either file (a claude.ai account
connector, a Chrome extension bridge) is an ACCOUNT-level integration, not a
project one, and this tool says so rather than silently treating "visible in
this session" as "configured by this project" -- those are different claims.

Skill reporting: counts `.claude/skills/<name>` (git-tracked, project-level)
and checks for a `skillOverrides` key in BOTH settings.json files (the real,
documented key found via official-docs check this same batch -- see hover's
chain log seq1193, which corrects an earlier search that looked for the
wrong key names). Reports which skills carry a non-default override, if any;
reports zero overrides as a real, checked fact, not an absence of search.

This role does not and will not write to .mcp.json or settings.json -- this
is a report, never a config change.
"""
import json
import os
import sys

EXIT_CLEAN, EXIT_COULD_NOT_RUN = 0, 2


def project_mcp_servers(repo):
    """{source_path: {name: config}} for every project-scoped MCP server
    declaration found -- .mcp.json and settings.json's mcpServers key, both
    checked, absence of either reported explicitly rather than skipped."""
    found = {}
    mcp_json = os.path.join(repo, '.mcp.json')
    if os.path.isfile(mcp_json):
        try:
            d = json.load(open(mcp_json, encoding='utf-8'))
            found[mcp_json] = d.get('mcpServers', d) if isinstance(d, dict) else {}
        except Exception as e:
            found[mcp_json] = {'COULD_NOT_PARSE': str(e)}
    settings = os.path.join(repo, '.claude', 'settings.json')
    if os.path.isfile(settings):
        try:
            d = json.load(open(settings, encoding='utf-8'))
            if isinstance(d, dict) and 'mcpServers' in d:
                found[settings + '#mcpServers'] = d['mcpServers']
        except Exception as e:
            found[settings + '#mcpServers'] = {'COULD_NOT_PARSE': str(e)}
    return found


def skill_overrides(repo, home):
    """{source_path: {skill: state}} for every skillOverrides entry found in
    either settings.json -- project-level and user-level, both checked."""
    found = {}
    for label, path in (('project', os.path.join(repo, '.claude', 'settings.json')),
                         ('user', os.path.join(home, '.claude', 'settings.json'))):
        if not os.path.isfile(path):
            continue
        try:
            d = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            found[label + ':' + path] = {'COULD_NOT_PARSE': str(e)}
            continue
        if isinstance(d, dict) and 'skillOverrides' in d:
            found[label + ':' + path] = d['skillOverrides']
    return found


def project_skill_count(repo):
    d = os.path.join(repo, '.claude', 'skills')
    if not os.path.isdir(d):
        return 0, []
    names = sorted(n for n in os.listdir(d)
                   if os.path.isdir(os.path.join(d, n)))
    return len(names), names


def build_report(repo, home):
    mcp = project_mcp_servers(repo)
    non_empty_mcp = {k: v for k, v in mcp.items() if v}
    overrides = skill_overrides(repo, home)
    non_empty_overrides = {k: v for k, v in overrides.items() if v}
    n_skills, names = project_skill_count(repo)
    lines = []
    if non_empty_mcp:
        for src, servers in non_empty_mcp.items():
            lines.append('PROJECT MCP SERVERS (%s): %s' % (src, sorted(servers)))
    else:
        lines.append('PROJECT MCP SERVERS: 0 -- checked %s and %s, neither '
                      'declares any. Every mcp__* tool visible in a live '
                      'session is an ACCOUNT-level connector, not a '
                      'project-scoped one.'
                      % (os.path.join(repo, '.mcp.json'),
                         os.path.join(repo, '.claude', 'settings.json')))
    lines.append('PROJECT SKILLS: %d tracked under .claude/skills/ (%s)'
                 % (n_skills, ', '.join(names[:5]) + (', ...' if n_skills > 5 else '')))
    if non_empty_overrides:
        for src, ov in non_empty_overrides.items():
            lines.append('SKILL OVERRIDES (%s): %s' % (src, ov))
    else:
        lines.append('SKILL OVERRIDES: 0 declared in either settings.json '
                     '-- all skills default to "on" (auto-invocable).')
    return '\n'.join(lines)


def run_selftest():
    import tempfile
    failures = []

    # Fixture 1: a project with an .mcp.json declaring one server.
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, '.claude', 'skills', 'foo'))
        os.makedirs(os.path.join(d, '.claude', 'skills', 'bar'))
        json.dump({'mcpServers': {'test-server': {'command': 'x'}}},
                  open(os.path.join(d, '.mcp.json'), 'w'))
        mcp = project_mcp_servers(d)
        if not any('test-server' in v for v in mcp.values() if isinstance(v, dict)):
            failures.append('F1: .mcp.json server not detected')
        n, names = project_skill_count(d)
        if n != 2 or names != ['bar', 'foo']:
            failures.append('F2: skill count/names wrong: %r %r' % (n, names))

    # Fixture 2: no .mcp.json, no mcpServers key -- must report empty, not crash.
    with tempfile.TemporaryDirectory() as d:
        mcp = project_mcp_servers(d)
        if any(v for v in mcp.values()):
            failures.append('F3: phantom MCP server reported on empty project')

    # Fixture 3: settings.json declares skillOverrides -- must surface it.
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, '.claude'))
        json.dump({'skillOverrides': {'accessibility': 'off'}},
                  open(os.path.join(d, '.claude', 'settings.json'), 'w'))
        with tempfile.TemporaryDirectory() as home:
            ov = skill_overrides(d, home)
            if not any(v.get('accessibility') == 'off' for v in ov.values()
                       if isinstance(v, dict)):
                failures.append('F4: skillOverrides not detected')

    # MUST-FAIL control: a corrupted settings.json must not be silently
    # treated as "no overrides" -- it must surface COULD_NOT_PARSE.
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, '.claude'))
        open(os.path.join(d, '.claude', 'settings.json'), 'w').write('{not json')
        with tempfile.TemporaryDirectory() as home:
            ov = skill_overrides(d, home)
            if not any('COULD_NOT_PARSE' in v for v in ov.values() if isinstance(v, dict)):
                failures.append('F5 (must-fail control): corrupted settings.json '
                                'was silently swallowed, not reported')

    if failures:
        print('SELFTEST FAILED:')
        for f in failures:
            print('  -', f)
        return EXIT_COULD_NOT_RUN
    print('SELFTEST: 5/5 passed')
    return EXIT_CLEAN


def main(argv):
    if '--selftest' in argv:
        return run_selftest()
    repo = argv[1] if len(argv) > 1 else r'C:\Users\marsh\Documents\SAIRN-hover'
    home = os.path.expanduser('~')
    print(build_report(repo, home))
    return EXIT_CLEAN


if __name__ == '__main__':
    sys.exit(main(sys.argv))

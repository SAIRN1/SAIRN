# OWNER: cody
"""tools/session_surface_check.py -- what is actually loaded into this session's
surface: skills, their model-invocation gating, and the MCP servers.

── WHY THIS EXISTS ──────────────────────────────────────────────────────────
A session's capability surface is invisible from inside it. The skills list and
the MCP tool list arrive in the prompt before the first turn, nothing in the repo
records what they were, and a handoff that says "I did not load X" cannot be
checked later. Two measurements from 2026-10-08 are the reason:

  * 62 skills on disk, and only 16 had EVER been invoked across 30 transcripts
    and 124,706 lines -- so 46 were carrying description text into every session
    for nothing.
  * 10 MCP servers reachable, and only TWO had ever been called:
    claude-in-chrome (386 calls) and claude_ai_Vercel (15). Eight had zero.

── WHAT IT IS NOT ───────────────────────────────────────────────────────────
It is NOT `/context` and NOT `/mcp`. Those are client-side commands a model turn
cannot invoke, and this tool does not pretend to replace them -- it reads what is
on DISK and what the transcripts SHOW, which is a different and smaller claim.
It cannot see: the live prompt, the actual token cost, or whether a reachable
server is currently authenticated.

It writes nothing. Every count carries its denominator.
"""

import argparse
import collections
import glob
import io
import json
import os
import re
import sys

HOME = os.path.expanduser('~')
SKILL_GLOBS = [os.path.join(HOME, '.claude', 'skills', '*', 'SKILL.md')]
CLAUDE_JSON = os.path.join(HOME, '.claude.json')
SETTINGS = os.path.join(HOME, '.claude', 'settings.json')
CRITERIA_VERSION = '2026-10-08.1'

# Servers this account can reach. Derived from ~/.claude.json's own
# claudeAiMcpEverConnected list plus the locally-bundled browser server, because
# there is no mcpServers map on this machine -- the claude.ai integrations are
# account-level and are not configured in any file here. That is a finding in its
# own right and --json carries it.
LOCAL_SERVERS = ['claude-in-chrome']


def _read(path):
    try:
        return io.open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return None


def skills():
    """[{name, bytes, gated, path}] for every skill on disk."""
    out = []
    for pat in SKILL_GLOBS:
        for p in sorted(glob.glob(pat)):
            body = _read(p)
            if body is None:
                out.append({'name': os.path.basename(os.path.dirname(p)),
                            'bytes': None, 'gated': None, 'path': p,
                            'note': 'UNREADABLE -- not counted either way'})
                continue
            fm = body.split('---', 2)
            front = fm[1] if len(fm) > 2 else body[:800]
            out.append({
                'name': os.path.basename(os.path.dirname(p)),
                'bytes': len(body.encode('utf-8')),
                'gated': bool(re.search(r'^disable-model-invocation:\s*true',
                                        front, re.M)),
                'path': p,
            })
    return out


def servers():
    """Reachable MCP servers, and where that list comes from."""
    ever = []
    raw = _read(CLAUDE_JSON)
    source = 'claudeAiMcpEverConnected in ~/.claude.json'
    if raw:
        try:
            ever = json.loads(raw).get('claudeAiMcpEverConnected') or []
        except Exception:                                   # noqa: BLE001
            source = 'UNREADABLE ~/.claude.json -- the list is COULD-NOT-TELL'
    names = [e.replace('claude.ai ', 'claude_ai_').replace(' ', '_')
             for e in ever]
    return sorted(set(names + LOCAL_SERVERS)), source


def usage(transcripts_dir):
    """(skill_counter, server_counter, files, lines, unparseable) from transcripts.

    Streamed line by line and never loaded whole: the largest transcript here is
    11.6 MB, and a truncated read is indistinguishable from a complete one. A line
    that will not parse is COUNTED, because "0 uses" and "I could not read it" are
    different answers.
    """
    sk, sv = collections.Counter(), collections.Counter()
    files = lines = bad = 0
    if not os.path.isdir(transcripts_dir):
        return sk, sv, 0, 0, 0

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get('type') == 'tool_use' and obj.get('name'):
                yield obj
            for v in obj.values():
                for x in walk(v):
                    yield x
        elif isinstance(obj, list):
            for v in obj:
                for x in walk(v):
                    yield x

    for fn in sorted(os.listdir(transcripts_dir)):
        if not fn.endswith('.jsonl'):
            continue
        files += 1
        with io.open(os.path.join(transcripts_dir, fn), encoding='utf-8',
                     errors='replace') as fh:
            for line in fh:
                lines += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:                           # noqa: BLE001
                    bad += 1
                    continue
                for tu in walk(rec):
                    name = tu.get('name') or ''
                    if name == 'Skill':
                        s = (tu.get('input') or {}).get('skill')
                        if s:
                            sk[s] += 1
                    elif name.startswith('mcp__'):
                        parts = name.split('__')
                        if len(parts) > 2:
                            sv[parts[1]] += 1
    return sk, sv, files, lines, bad


def report(session, as_json=False, no_usage=False):
    sks = skills()
    svs, svs_source = servers()
    tdir = os.path.join(HOME, '.claude', 'projects',
                        'C--Users-marsh-Documents-SAIRN-%s' % session)
    if no_usage:
        sk_used, sv_used, files, lines, bad = (collections.Counter(),
                                              collections.Counter(), -1, -1, -1)
    else:
        sk_used, sv_used, files, lines, bad = usage(tdir)

    readable = [s for s in sks if s['bytes'] is not None]
    gated = [s for s in readable if s['gated']]
    never = [s for s in readable if sk_used.get(s['name'], 0) == 0]
    unused_srv = [s for s in svs if sv_used.get(s, 0) == 0]

    if as_json:
        print(json.dumps({
            'criteria_version': CRITERIA_VERSION,
            'session': session,
            'transcripts': {'dir': tdir, 'files': files, 'lines': lines,
                            'unparseable': bad},
            'skills': {'on_disk': len(sks), 'unreadable': len(sks) - len(readable),
                       'gated': len(gated), 'never_invoked': len(never),
                       'invoked': sorted(sk_used.items(), key=lambda x: -x[1])},
            'mcp': {'reachable': svs, 'source': svs_source,
                    'used': sorted(sv_used.items(), key=lambda x: -x[1]),
                    'zero_calls': unused_srv,
                    'note': ('there is no mcpServers map and no .mcp.json on this '
                             'machine -- the claude.ai integrations are '
                             'account-level, so they CANNOT be disabled from a '
                             'settings file. /mcp in the client is the only lever.')},
        }, indent=2))
        return 0

    print('SESSION SURFACE -- session %s (criteria %s)' % (session, CRITERIA_VERSION))
    print('  NOT /context and NOT /mcp: this reads DISK and TRANSCRIPTS, which is')
    print('  a smaller claim. It cannot see the live prompt or its token cost.')
    print()
    if files < 0:
        print('TRANSCRIPTS: NOT READ (--no-usage). Every "never invoked" below is')
        print('  COULD-NOT-TELL rather than zero, and no usage count is printed.')
    else:
        print('TRANSCRIPTS: %d file(s), %d line(s), %d unparseable'
              % (files, lines, bad))
    if files == 0:
        print('  NONE FOUND at %s -- every "never invoked" below is '
              'COULD-NOT-TELL, not zero.' % tdir)
    print()
    print('SKILLS: %d on disk, %d unreadable, %d gated with '
          'disable-model-invocation, %d never invoked'
          % (len(sks), len(sks) - len(readable), len(gated), len(never)))
    for s in sorted(sk_used.items(), key=lambda x: -x[1]):
        print('  invoked  %-44s %4d' % (s[0], s[1]))
    big = sorted((s for s in never), key=lambda s: -(s['bytes'] or 0))[:8]
    if big:
        print('  largest NEVER invoked (description text every session pays for):')
        for s in big:
            print('    %8d b  %-36s %s' % (s['bytes'], s['name'],
                                           'GATED' if s['gated'] else ''))
    print()
    print('MCP SERVERS: %d reachable, %d with zero calls' % (len(svs), len(unused_srv)))
    print('  source of the reachable list: %s' % svs_source)
    for s in sorted(sv_used.items(), key=lambda x: -x[1]):
        print('  used     %-36s %5d call(s)' % (s[0], s[1]))
    for s in unused_srv:
        print('  ZERO     %-36s' % s)
    print('  THEY CANNOT BE DISABLED FROM A SETTINGS FILE: there is no mcpServers')
    print('  map and no .mcp.json here -- the claude.ai integrations are')
    print('  account-level. /mcp in the client is the only lever.')
    return 0


def selftest():
    ok = True
    n = neg = 0

    def arm(label, cond, detail=''):
        nonlocal ok, n, neg
        n += 1
        if label.startswith('NEGATIVE'):
            neg += 1
        print(('  ok   ' if cond else '  FAIL ') + label
              + ('' if cond else '\n         %s' % str(detail)[:200]))
        if not cond:
            ok = False

    print('SESSION SURFACE -- selftest (criteria %s)' % CRITERIA_VERSION)
    sks = skills()
    arm('skills() finds more than one skill on disk', len(sks) > 1, len(sks))
    arm('every entry carries a name and a gated verdict',
        all(s.get('name') and 'gated' in s for s in sks), sks[:1])
    gated = [s for s in sks if s.get('gated')]
    arm('at least one skill is detected as GATED, so the frontmatter parse is '
        'not blind', len(gated) >= 1, [s['name'] for s in gated][:6])
    arm('NEGATIVE: and not EVERY skill is reported gated, so the parse is not '
        'answering true to everything',
        len(gated) < len(sks), '%d of %d' % (len(gated), len(sks)))

    svs, src = servers()
    arm('servers() returns the locally-bundled browser server at minimum',
        'claude-in-chrome' in svs, svs)
    arm('...and names where the reachable list came from', bool(src), src)

    # usage() against a directory that does not exist must be COULD-NOT-TELL
    sk, sv, files, lines, bad = usage(os.path.join(HOME, 'no-such-dir-xyz'))
    arm('NEGATIVE: usage() over a MISSING transcripts dir reports 0 FILES rather '
        'than silently returning empty counters that read as "never used"',
        files == 0 and not sk and not sv, (files, len(sk), len(sv)))
    print('  criteria lock: %d arms, %d of them negative (criteria %s)'
          % (n, neg, CRITERIA_VERSION))
    return ok


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--session', default='cody')
    # ── THE HOOK PATH MUST NOT WALK 197 MB OF TRANSCRIPTS ──────────────────
    # The usage half is the expensive half: 30 files, 124k lines. A SessionStart
    # hook that costs seconds every session is a hook somebody removes, which is
    # the same failure as a warning that fires on everything. --no-usage reports
    # the surface without the history and SAYS the history was not read, so the
    # missing counts cannot be mistaken for zeros.
    ap.add_argument('--no-usage', action='store_true',
                    help='skip the transcript walk -- for the SessionStart hook')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest:
        return 0 if selftest() else 1
    return report(a.session, a.json, a.no_usage)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

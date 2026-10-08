# OWNER: hank
"""hank_session_start_check.py -- what is ACTUALLY loaded into this session.

    python tools/hank_session_start_check.py
    python tools/hank_session_start_check.py --json

EXIT 0 it could read everything it needs. EXIT 2 COULD NOT RUN -- never 0.

── WHY THIS EXISTS ─────────────────────────────────────────────────────────
Every skill and every connector costs context on EVERY turn, and nothing at
session start says how many there are. `/context`, `/mcp` and `/skill-doctor`
answer this -- and they are CLIENT-SIDE SLASH COMMANDS a model turn cannot
invoke, so a session that wants the number has to derive it from the files.
That is what this does.

── WHAT IT CAN AND CANNOT SEE, SAID UP FRONT ───────────────────────────────
SKILLS are directories on disk and are fully readable, including whether each
carries `disable-model-invocation: true` -- which is the difference between a
skill the model may reach for and one only a human may type.

MCP SERVERS SPLIT IN TWO, and conflating them is the trap:

  LOCAL      `mcpServers` in ~/.claude.json, globally and per project. These are
             declared in a file, so they can be counted AND edited.
  ACCOUNT    claude.ai connectors and the Chrome extension. They appear in the
             tool list as `mcp__claude_ai_*` and `mcp__claude-in-chrome__*` and
             they are NOT IN ANY LOCAL FILE. Nothing a model turn can edit will
             disable one; it is done in the claude.ai account or the extension.

So a report of "0 MCP servers" taken from the config is TRUE AND MISLEADING,
because ten connectors may still be loaded. This prints both halves and says
which is which.

── AND IT REFUSES RATHER THAN REPORTING ZERO ───────────────────────────────
A skills directory that cannot be read is COULD NOT RUN, not "no skills". An
empty count and an unreadable source are different answers and only one of them
is good news.
"""
import io
import json
import os
import sys

HOME = os.path.expanduser('~')
SKILLS = os.path.join(HOME, '.claude', 'skills')
SETTINGS = os.path.join(HOME, '.claude', 'settings.json')
CLAUDE_JSON = os.path.join(HOME, '.claude.json')
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The connector families that appear in the tool list but in no local file.
# Listed by PREFIX so a new tool in a known family does not look like a new
# connector, and so this stays honest about being a hand-kept list.
ACCOUNT_CONNECTOR_PREFIXES = (
    'mcp__claude-in-chrome__',
    'mcp__claude_ai_Vercel__',
    'mcp__claude_ai_Gmail__',
    'mcp__claude_ai_Google_Drive__',
    'mcp__claude_ai_Claude_Docs__',
    'mcp__claude_ai_Canva__',
    'mcp__claude_ai_Notion__',
    'mcp__claude_ai_Stripe__',
    'mcp__claude_ai_Netlify__',
    'mcp__claude_ai_Ironclad_Contracts__',
)


def frontmatter(path):
    try:
        raw = io.open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    if not raw.startswith('---'):
        return ''
    parts = raw.split('---', 2)
    return parts[1] if len(parts) >= 3 else ''


def read_skills():
    if not os.path.isdir(SKILLS):
        return None, '%s is not a directory' % SKILLS
    out = []
    for name in sorted(os.listdir(SKILLS)):
        p = os.path.join(SKILLS, name, 'SKILL.md')
        if not os.path.isfile(p):
            continue
        fm = frontmatter(p)
        if fm is None:
            out.append({'name': name, 'model_invocable': None,
                        'note': 'SKILL.md UNREADABLE'})
            continue
        out.append({'name': name,
                    'model_invocable': 'disable-model-invocation' not in fm,
                    'note': '' if fm else 'no frontmatter'})
    if not out:
        return None, ('no SKILL.md found under %s. Zero skills is not a clean '
                      'answer -- the population this counts is empty.' % SKILLS)
    return out, None


def read_local_mcp():
    if not os.path.isfile(CLAUDE_JSON):
        return None, '%s is absent' % CLAUDE_JSON
    try:
        d = json.load(io.open(CLAUDE_JSON, encoding='utf-8'))
    except ValueError as e:
        return None, '%s is not valid JSON (%s)' % (CLAUDE_JSON, e)
    glob = sorted(d.get('mcpServers') or {})
    projects = {}
    for path, cfg in (d.get('projects') or {}).items():
        names = sorted((cfg or {}).get('mcpServers') or {})
        dis = (cfg or {}).get('disabledMcpjsonServers') or []
        en = (cfg or {}).get('enabledMcpjsonServers') or []
        if names or dis or en:
            projects[path] = {'servers': names, 'enabled': en, 'disabled': dis}
    return {'global': glob, 'projects': projects}, None


def main(argv):
    skills, s_err = read_skills()
    mcp, m_err = read_local_mcp()
    if s_err or m_err:
        sys.stderr.write('COULD NOT RUN: %s\n'
                         % '; '.join(x for x in (s_err, m_err) if x))
        sys.stderr.write('Nothing is reported. An unreadable source and an '
                         'empty one are different answers.\n')
        return 2

    invocable = [s for s in skills if s['model_invocable'] is True]
    disabled = [s for s in skills if s['model_invocable'] is False]
    unknown = [s for s in skills if s['model_invocable'] is None]

    if '--json' in argv:
        print(json.dumps({'skills': skills, 'local_mcp': mcp,
                          'account_connector_prefixes':
                              list(ACCOUNT_CONNECTOR_PREFIXES)}, indent=1))
        return 0

    print('SESSION START -- what is loaded, derived from files because '
          '/context, /mcp')
    print('and /skill-doctor are client-side and a model turn cannot invoke '
          'them.')
    print('')
    print('SKILLS in %s' % SKILLS)
    print('  total with a SKILL.md        : %d' % len(skills))
    print('  MODEL-INVOCABLE              : %d  <- these cost context on every '
          'turn' % len(invocable))
    print('  disable-model-invocation     : %d  (human can still type them)'
          % len(disabled))
    for s in disabled:
        print('      %s' % s['name'])
    if unknown:
        print('  UNREADABLE                   : %d  -- NOT counted either way'
              % len(unknown))
        for s in unknown:
            print('      %-32s %s' % (s['name'], s['note']))
    print('')
    print('MCP -- LOCAL, declared in %s' % CLAUDE_JSON)
    print('  global mcpServers            : %d  %s'
          % (len(mcp['global']), mcp['global'] or ''))
    if mcp['projects']:
        for path, info in sorted(mcp['projects'].items()):
            print('  %-28s %s' % (path[-28:], info))
    else:
        print('  per-project mcpServers       : none declared anywhere')
    print('')
    print('MCP -- ACCOUNT-LEVEL, in NO local file and NOT editable from here')
    print('  %d connector family(ies) appear in the tool list:'
          % len(ACCOUNT_CONNECTOR_PREFIXES))
    for p in ACCOUNT_CONNECTOR_PREFIXES:
        print('      %s' % p)
    print('  THESE ARE THE EXPENSIVE ONES AND THE CONFIG ABOVE CANNOT SEE '
          'THEM.')
    print('  Reporting "0 MCP servers" from the config alone would be true and')
    print('  misleading. Disable them in the claude.ai account (connectors) or')
    print('  in the Chrome extension -- not in any file this tool can write.')
    print('')
    print('LIMITS, printed on every run:')
    print('  * the connector list above is HAND-KEPT. A connector enabled on the')
    print('    account after this was written will not appear, and this tool')
    print('    cannot tell that from one being disabled.')
    print('  * it counts what is ON DISK. A skill the harness failed to load is')
    print('    counted here and absent from the session.')
    print('  * it measures nothing about COST. /skill-doctor does that and is')
    print('    client-side; the count is a proxy, not a token figure.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

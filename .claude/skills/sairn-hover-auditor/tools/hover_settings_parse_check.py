#!/usr/bin/env python
"""hover_settings_parse_check.py -- fail CLOSED when a Claude Code settings file in this clone cannot be parsed, or names a hook script that is not there.

WHY (finding 1825, b116): .claude/settings.local.json carries the PreToolUse deny hook and the Stop hook. A manual edit left it without the closing
brace of its root object; Claude Code skips a settings file it cannot parse, so for about twelve and a half hours (batches b112 and b113) NO hook was
loaded, and nothing said so. A check that only fires when somebody reads a finding does not close that. This fails on the PARSE ERROR ITSELF.

    python hover_settings_parse_check.py [--clone DIR]     # exit 0 all present files parse and every hook script exists
                                                           # exit 1 a file does not parse, or a hook names a missing script
                                                           # exit 2 COULD NOT RUN (a file exists and cannot be read, no clone)
    python hover_settings_parse_check.py --selftest

Checked: DIR/.claude/settings.json, DIR/.claude/settings.local.json, ~/.claude/settings.json, ~/.claude/settings.local.json. A file that does not
exist is skipped (it is optional); a file that exists and is empty does NOT parse. It runs in hover_done_line.py (a batch is NOT DONE while a
settings file is broken). A SessionStart hook cannot do this job from inside the same file: the file that fails to parse is the one that would load it.
WHAT IT CANNOT DO: it cannot tell whether Claude Code accepted the hook; it checks that the file parses and the script exists.
"""
import json
import os
import re
import shlex
import sys
import tempfile


def _check_file(path):
    """-> (state, detail); state 'ok' | 'absent' | 'bad' | 'unreadable'."""
    if not os.path.isfile(path):
        return 'absent', ''
    try:
        with open(path, 'rb') as f:
            raw = f.read()
    except OSError as e:
        return 'unreadable', str(e)
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError as e:
        return 'bad', 'not valid UTF-8: %s' % e
    try:
        data = json.loads(text)
    except ValueError as e:
        hint = ''
        opens, closes = text.count('{'), text.count('}')
        if opens > closes:
            hint = ' (%d more { than } -- a closing brace is missing, most likely the root object\'s)' % (opens - closes)
        return 'bad', 'does not parse as JSON: %s%s' % (e, hint)
    if not isinstance(data, dict):
        return 'bad', 'parses, but the top level is not an object'
    missing = []
    hooks = data.get('hooks') or {}
    if isinstance(hooks, dict):
        for event, blocks in hooks.items():
            for blk in (blocks or []):
                for h in (blk.get('hooks') or []) if isinstance(blk, dict) else []:
                    cmd = h.get('command') if isinstance(h, dict) else None
                    if not isinstance(cmd, str):
                        continue
                    try:
                        parts = shlex.split(cmd, posix=True)
                    except ValueError:
                        parts = cmd.split()
                    scripts = [p for p in parts if re.search(r'\.(py|js|sh|cmd|bat)$', p, re.I)]
                    for sc in scripts[:1]:
                        if not os.path.isfile(os.path.expanduser(sc)):
                            missing.append('%s hook names %s, which does not exist' % (event, sc))
    if missing:
        return 'bad', '; '.join(missing)
    return 'ok', ''


def check(clone):
    home = os.path.expanduser('~')
    paths = [os.path.join(clone, '.claude', 'settings.json'), os.path.join(clone, '.claude', 'settings.local.json'),
             os.path.join(home, '.claude', 'settings.json'), os.path.join(home, '.claude', 'settings.local.json')]
    results = [(p,) + _check_file(p) for p in paths]
    return results


def main(argv):
    if '--selftest' in argv:
        return selftest()
    clone = argv[argv.index('--clone') + 1] if '--clone' in argv and argv.index('--clone') + 1 < len(argv) else os.getcwd()
    if not os.path.isdir(clone):
        print('COULD NOT RUN: %s is not a directory' % clone)
        return 2
    rc = 0
    for path, state, detail in check(clone):
        if state == 'absent':
            continue
        if state == 'ok':
            print('ok    %s' % path)
        elif state == 'unreadable':
            print('COULD NOT READ %s: %s' % (path, detail))
            rc = max(rc, 2)
        else:
            print('FAIL  %s: %s' % (path, detail))
            print('      Claude Code SKIPS a settings file it cannot parse: every hook and permission in it is silently off.')
            rc = 1 if rc != 2 else 2
    if rc == 0:
        print('settings files present all parse and every hook script exists.')
    return rc


def selftest():
    ok = bad = 0

    def ck(name, cond):
        nonlocal ok, bad
        print('  %s %s' % ('ok  ' if cond else 'FAIL', name))
        ok, bad = (ok + 1, bad) if cond else (ok, bad + 1)

    root = tempfile.mkdtemp(prefix='hover_settings_chk_')
    d = os.path.join(root, '.claude')
    os.makedirs(d)
    script = os.path.join(root, 'hook.py')
    open(script, 'w').write('#')
    good = json.dumps({'permissions': {'allow': []}, 'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': [
        {'type': 'command', 'command': 'python "%s" --clone x' % script.replace('\\', '/')}]}],
        'Stop': [{'hooks': [{'type': 'command', 'command': 'python "%s" --stop-hook' % script.replace('\\', '/')}]}]}}, indent=4)
    local = os.path.join(d, 'settings.local.json')
    open(local, 'w').write(good)
    st, _ = _check_file(local)
    ck('S1 a valid file with real hook scripts is ok', st == 'ok')
    open(local, 'w').write(good.rstrip()[:-1].rstrip())          # the b112 shape: the root's closing brace is missing
    st, det = _check_file(local)
    ck('S2 KNOWN-BAD CONTROL: the exact failure of 2026-10-29 (root closing brace missing) is BAD and says a brace is missing',
       st == 'bad' and 'closing brace is missing' in det)
    open(local, 'w').write('')
    ck('S3 an empty file that exists does NOT parse', _check_file(local)[0] == 'bad')
    open(local, 'w').write('[1, 2]')
    ck('S4 valid JSON that is not an object is BAD', _check_file(local)[0] == 'bad')
    open(local, 'w').write(good.replace(script.replace('\\', '/'), os.path.join(root, 'gone_hook.py').replace('\\', '/')))
    st, det = _check_file(local)
    ck('S5 KNOWN-BAD CONTROL: a hook that names a missing script is BAD and names the event', st == 'bad' and 'does not exist' in det and 'PreToolUse' in det)
    ck('S6 a file that does not exist is skipped, not an error', _check_file(os.path.join(d, 'nope.json'))[0] == 'absent')
    open(local, 'w').write(good)
    open(os.path.join(d, 'settings.json'), 'w').write('{"a": 1')
    ck('S7 main() exits 1 when ANY present settings file is broken, even if the other is fine',
       main(['--clone', root]) == 1)
    open(os.path.join(d, 'settings.json'), 'w').write('{"a": 1}')
    ck('S8 main() exits 0 when every present file parses and the scripts exist',
       main(['--clone', root]) == 0)
    ck('S9 main() exits 2 (could not run) for a clone that is not a directory', main(['--clone', os.path.join(root, 'nope')]) == 2)
    print('%d ok, %d failed' % (ok, bad))
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

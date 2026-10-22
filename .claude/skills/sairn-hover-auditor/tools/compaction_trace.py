#!/usr/bin/env python
"""compaction_trace.py -- b77 dispatch item 6. ONE command that prints the facts
to log when an auto-compaction has fired in a hover window. Read-only; writes
nothing and calls no git.

  python compaction_trace.py                 newest compact_boundary in this clone's transcripts
  python compaction_trace.py --session ID    the newest one in that session's transcript

WHAT IT REPORTS, because the dispatch named each one:
  * the exact timestamp (UTC and local) and what the transcript's OWN
    compact_boundary record says: trigger, preTokens, postTokens, durationMs;
  * the gap since the last timestamped event before it (idle time);
  * the context percentage of the DECLARED window for that session -- never an
    assumed 85. A session with no declared window gets no percentage, only the
    raw token count, and the script says so;
  * Claude Code version, OS build, the terminal host (the process chain of THIS
    process, which is the live window's -- not necessarily the window that
    compacted), whether Windows recorded sleep/resume or lock events around the
    instant, and every autoCompact-type key in the settings files and the
    environment (hooks excluded).
Where a fact cannot be read it prints COULD NOT TELL and why, never a blank.
"""
import datetime as dt
import glob
import json
import os
import subprocess
import sys

HOME = os.path.expanduser('~')
PROJ = os.path.join(HOME, '.claude', 'projects', 'C--Users-marsh-Documents-SAIRN-hover')
CLONE = os.path.join(HOME, 'Documents', 'SAIRN-hover')


def parse_ts(s):
    return dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=dt.timezone.utc)


def last_boundary(path):
    """(boundary_event, previous timestamped event, previous assistant context) for
    the LAST real compact_boundary in the file, or None. 'Real' means a system
    event with that subtype -- not a line that merely mentions the word."""
    found = None
    prev = None
    ctx = None
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get('type') == 'system' and e.get('subtype') == 'compact_boundary':
                found = (e, prev, ctx)
                continue
            ts = e.get('timestamp')
            if ts and e.get('type') in ('user', 'assistant', 'system', 'attachment'):
                prev = (ts, e.get('type'), e.get('subtype'))
            u = (e.get('message') or {}).get('usage') if e.get('type') == 'assistant' else None
            if u:
                ctx = (int(u.get('input_tokens') or 0) + int(u.get('cache_read_input_tokens') or 0)
                       + int(u.get('cache_creation_input_tokens') or 0), ts)
    return found


def declared_window(session_id):
    try:
        with open(os.path.join(CLONE, '.git', 'sairn-context-window'), encoding='utf-8') as fh:
            for raw in fh:
                parts = raw.split()
                if len(parts) == 2 and parts[0] == session_id:
                    return int(parts[1])
    except OSError:
        pass
    return None


def ps(cmd):
    try:
        r = subprocess.run(['powershell.exe', '-NoProfile', '-Command', cmd],
                           capture_output=True, text=True, timeout=90)
        return (r.stdout or '').strip(), (r.stderr or '').strip()
    except Exception as ex:                              # noqa: BLE001
        return '', 'COULD NOT RUN powershell: %s' % ex


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return (r.stdout or r.stderr or '').strip()
    except Exception as ex:                              # noqa: BLE001
        return 'COULD NOT RUN %s: %s' % (cmd[0], ex)


def compact_keys(node, path=''):
    """Every key whose name contains 'compact' (any case), with its scalar value;
    the 'hooks' subtree is skipped, because the dispatch asked for keys SEPARATE
    from hooks."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = path + '/' + str(k)
            if str(k) == 'hooks':
                continue
            if 'compact' in str(k).lower() and not isinstance(v, (dict, list)):
                out.append('%s = %r' % (p, v))
            out.extend(compact_keys(v, p))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(compact_keys(v, '%s[%d]' % (path, i)))
    return out


def main(argv):
    session = argv[argv.index('--session') + 1] if '--session' in argv else None
    files = sorted(glob.glob(os.path.join(PROJ, '*.jsonl')))
    if session:
        files = [f for f in files if os.path.basename(f) == session + '.jsonl']
    best = None
    for f in files:
        lb = last_boundary(f)
        if lb and (best is None or lb[0]['timestamp'] > best[1][0]['timestamp']):
            best = (f, lb)
    if not best:
        print('NO compact_boundary event found in %d transcript(s) under %s.' % (len(files), PROJ))
        print('That is the answer for these files; it is not a failure to look.')
        return 1
    path, (b, prev, ctx) = best
    meta = b.get('compactMetadata') or {}
    when = parse_ts(b['timestamp'])
    local = when.astimezone()
    sid = b.get('sessionId')
    print('COMPACTION TRACE (read-only), run at %s local' % dt.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z'))
    print('TRANSCRIPT   %s' % path)
    print('BOUNDARY     %s UTC = %s local' % (b['timestamp'], local.strftime('%Y-%m-%d %H:%M:%S %z')))
    print('RECORD SAYS  trigger=%s preTokens=%s postTokens=%s durationMs=%s version=%s'
          % (meta.get('trigger'), meta.get('preTokens'), meta.get('postTokens'),
             meta.get('durationMs'), b.get('version')))
    if prev:
        gap = (when - parse_ts(prev[0])).total_seconds()
        print('IDLE GAP     last timestamped event before it: %s %s %s at %s -> %d s (%.1f min) before the boundary'
              % (prev[1], prev[2] or '', '', prev[0], gap, gap / 60.0))
    else:
        print('IDLE GAP     COULD NOT TELL: no timestamped event before the boundary')
    if ctx:
        print('LAST TURN    prompt of the last assistant turn before it: %d tokens (at %s)' % ctx)
    win = declared_window(sid)
    pre = meta.get('preTokens')
    if win and pre:
        print('CONTEXT %%    %d of DECLARED window %d = %.1f%%  (the dispatch asked not to assume 85; the 85 line is %d)'
              % (pre, win, 100.0 * pre / win, int(0.85 * win)))
    else:
        print('CONTEXT %%    COULD NOT STATE: no window is declared for session %s in .git/sairn-context-window. '
              'Raw preTokens=%s; the percentage depends on a window nobody declared.' % (sid, pre))
    cli = run(['cmd.exe', '/c', 'claude --version']).splitlines()
    print('CLAUDE CODE  version in the record: %s | installed CLI: %s' % (b.get('version'), cli[0] if cli else 'COULD NOT TELL'))
    print('OS BUILD     %s' % ' '.join(l.strip() for l in run(['cmd.exe', '/c', 'ver']).splitlines() if l.strip()).split('(c)')[0].strip())
    chain, err = ps('$p=%d; for($i=0;$i -lt 9 -and $p;$i++){ $x=Get-CimInstance Win32_Process -Filter ("ProcessId="+$p); if(-not $x){break}; ("{0} {1}" -f $x.ProcessId,$x.Name); $p=$x.ParentProcessId }' % os.getpid())
    print('TERMINAL HOST (process chain of THIS process, the live window; the compacted window may differ):')
    print('             ' + (' <- '.join(l.strip() for l in chain.splitlines()) if chain else 'COULD NOT TELL: %s' % err))
    print('             env: WT_SESSION=%s TERM_PROGRAM=%s TERM=%s SESSIONNAME=%s'
          % (os.environ.get('WT_SESSION', '(unset)'), os.environ.get('TERM_PROGRAM', '(unset)'),
             os.environ.get('TERM', '(unset)'), os.environ.get('SESSIONNAME', '(unset)')))
    lo = (local - dt.timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
    hi = (local + dt.timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
    pw, perr = ps('$s=[datetime]"%s"; $e=[datetime]"%s"; Get-WinEvent -FilterHashtable @{LogName="System"; StartTime=$s; EndTime=$e; Id=1,12,13,41,42,107,109,506,507} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -match "Kernel-Power|Power-Troubleshooter|Kernel-General" } | Sort-Object TimeCreated | ForEach-Object { "{0:yyyy-MM-dd HH:mm:ss} id={1} {2}" -f $_.TimeCreated,$_.Id,$_.ProviderName }' % (lo, hi))
    print('SLEEP/RESUME (System log, %s to %s local; ids 1,12,13,41,42,107,109,506,507): %s'
          % (lo, hi, ('\n             ' + pw.replace('\n', '\n             ')) if pw else 'none recorded' if not perr else 'COULD NOT TELL: %s' % perr))
    lk, lerr = ps('$s=[datetime]"%s"; $e=[datetime]"%s"; try { Get-WinEvent -FilterHashtable @{LogName="Security"; StartTime=$s; EndTime=$e; Id=4800,4801} -ErrorAction Stop | Sort-Object TimeCreated | ForEach-Object { "{0:yyyy-MM-dd HH:mm:ss} id={1}" -f $_.TimeCreated,$_.Id } } catch { "NOTE: " + $_.Exception.Message }' % (lo, hi))
    print('LOCK/UNLOCK  (Security log ids 4800/4801, same window): %s'
          % (lk.replace('\n', '; ') if lk else 'none returned (auditing may be off or the log unreadable without elevation: NOT proof the screen stayed unlocked)'))
    print('AUTOCOMPACT-TYPE KEYS (hooks excluded):')
    print('             env CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=%s CLAUDE_CODE_AUTO_COMPACT_WINDOW=%s DISABLE_AUTO_COMPACT=%s DISABLE_COMPACT=%s'
          % tuple(os.environ.get(k, '(unset)') for k in ('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE',
                                                         'CLAUDE_CODE_AUTO_COMPACT_WINDOW',
                                                         'DISABLE_AUTO_COMPACT', 'DISABLE_COMPACT')))
    for label, p in (('user settings.json', os.path.join(HOME, '.claude', 'settings.json')),
                     ('project settings.json', os.path.join(CLONE, '.claude', 'settings.json')),
                     ('project settings.local.json', os.path.join(CLONE, '.claude', 'settings.local.json')),
                     ('~/.claude.json', os.path.join(HOME, '.claude.json'))):
        try:
            with open(p, encoding='utf-8') as fh:
                ks = compact_keys(json.load(fh))
            print('             %s: %s' % (label, '; '.join(ks) if ks else 'no key containing "compact" outside hooks'))
        except Exception as ex:                          # noqa: BLE001
            print('             %s: COULD NOT READ (%s)' % (label, ex))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

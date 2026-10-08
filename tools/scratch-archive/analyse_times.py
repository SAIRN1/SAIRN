import calendar, collections, io, os, re, sys, time

rows = collections.OrderedDict()
n = 0
empty = 0
for line in io.open(sys.argv[1], encoding='utf-8', errors='replace'):
    if line.startswith('#') or line.startswith('utc'):
        continue
    p = line.rstrip('\n').split('\t')
    if len(p) < 3:
        continue
    ts, pid, cmd = p[0], p[1], p[2]
    n += 1
    if not cmd.strip():
        empty += 1
    m = re.search(r'(tests[' + re.escape(os.sep) + r'/][^\s]+|api[' + re.escape(os.sep) + r'/][^\s]+)', cmd)
    key = m.group(1).replace(os.sep, '/') if m else ('<no file> pid ' + pid)
    try:
        t = calendar.timegm(time.strptime(ts, '%Y-%m-%dT%H:%M:%SZ'))
    except ValueError:
        continue
    if key not in rows:
        rows[key] = [t, t]
    else:
        rows[key][1] = t

print('samples parsed        :', n)
print('samples with EMPTY cmd:', empty, '(%.0f%%)' % (100.0 * empty / max(n, 1)))
print('distinct subjects     :', len(rows))
named = sorted(((v[1] - v[0] + 15, k) for k, v in rows.items()
                if k.startswith('tests/') or k.startswith('api/')), reverse=True)
print('distinct REAL test files observed :', len(named))
print()
if named:
    print('%8s  %s' % ('seconds', 'file'))
    for secs, k in named[:15]:
        print('%8d%s  %s' % (secs, '  TIMEOUT>900' if secs > 900 else '', k))
else:
    print('NO TEST FILE WAS EVER OBSERVED -- the watcher recorded only these:')
    for k, v in list(rows.items())[:8]:
        print('   %-28s observed %5ds' % (k, v[1] - v[0] + 15))

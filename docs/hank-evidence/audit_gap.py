import io
import os
import re
import subprocess

R = r'C:\Users\marsh\Documents\SAIRN-hank'
API = os.path.join(R, 'api')
SQL = os.path.join(R, 'sql')

auth = [f for f in sorted(os.listdir(API)) if re.match(r'^[a-z-]+-auth\.js$', f)]
# the allowlist in api/_lib/audit.js
al = io.open(os.path.join(API, '_lib', 'audit.js'), encoding='utf-8').read()
m = re.search(r'const AUDIT_TABLES = \{([^}]*)\}', al)
allowed = re.findall(r'(\w+_audit_log)', m.group(1)) if m else []

# every audit-log table that has a create statement anywhere in sql/
ddl = {}
for f in sorted(os.listdir(SQL)):
    if not f.endswith('.sql'):
        continue
    s = io.open(os.path.join(SQL, f), encoding='utf-8', errors='replace').read()
    for t in re.findall(r'create table if not exists (?:public\.)?(\w*audit_log)\b', s):
        ddl.setdefault(t, f)

print('ALLOWLISTED IN api/_lib/audit.js (%d): %s' % (len(allowed), ', '.join(allowed)))
print('AUDIT-LOG TABLES WITH A create STATEMENT IN sql/ (%d):' % len(ddl))
for t, f in sorted(ddl.items()):
    print('    %-28s %s' % (t, f))
print()
hdr = '%-18s %-10s %-12s %-26s %s' % ('auth file', 'setup?', 'writeAudit', 'AUDIT_TABLE const', 'verdict')
print(hdr)
print('-' * 100)
need = []
for f in auth:
    s = io.open(os.path.join(API, f), encoding='utf-8').read()
    has_setup = "action === 'setup'" in s
    wa = 'writeAuditLog' in s
    mt = re.search(r"AUDIT_TABLE\s*=\s*'(\w+)'", s)
    tbl = mt.group(1) if mt else ''
    i = s.find("action === 'setup'")
    blk = ''
    if i >= 0:
        j = s.find('if (action ===', i + 10)
        blk = s[i:j if j != -1 else len(s)]
    attributed = bool(re.search(r'writeAuditLog\(', blk) or re.search(r'\baudit\(', blk)
                      or 'created_by' in blk)
    if not has_setup:
        v = 'no setup action'
    elif attributed:
        v = 'ALREADY ATTRIBUTED'
    elif tbl and tbl in allowed:
        v = 'table exists + allowlisted -- CODE ONLY'
    elif tbl:
        v = 'has a table const NOT allowlisted'
    else:
        v = 'NEEDS A TABLE (migration)'
        need.append(f)
    print('%-18s %-10s %-12s %-26s %s' % (f, has_setup, wa, tbl or '-', v))
print()
print('NEEDS A MIGRATION: %d' % len(need))
print('    ' + ', '.join(need))
print()
# for each of those, what is the app id and the natural table name
print('%-18s %-16s %-26s %s' % ('auth file', 'app id', 'proposed table', 'DDL already in sql/?'))
print('-' * 92)
for f in need:
    s = io.open(os.path.join(API, f), encoding='utf-8').read()
    ma = re.search(r"APP\s*=\s*'([a-z]+)'", s)
    app = ma.group(1) if ma else '(APP const not found)'
    t = '%s_audit_log' % app
    print('%-18s %-16s %-26s %s' % (f, app, t, ddl.get(t, 'NO')))

"""
missing_dom_target_check.py -- flags any getElementById('X') call site
where no element with id="X" actually exists anywhere in stonedesk.html.

A function can have entirely correct logic and still be dead on arrival
if its DOM target was never built -- this hit four times in one session
(inventory's #inv-form, remakes' #remake-form/#remake-list, safety's
#safe-incident-list/#safe-training-list/#safe-inspection-list/
#safe-checklist-items, and the customers kanban board's
#cust-kanban-cols), each only found by manually tracing a function and
checking markup by hand. This is the mechanical version of the check
sairn-software-architect now requires before wiring any render function:
"grep the HTML for that id first."

Method: (1) collect every literal id="X" (or id='X') appearing anywhere
in the raw file, including inside JS-generated HTML strings -- a render
function that builds another element's container via innerHTML still
counts as "the id exists", since it's created before anything tries to
getElementById it, and duplicate_global_check.py/other checks already
cover different failure classes; (2) collect every literal
getElementById('X') / getElementById("X") call site; (3) flag any
getElementById target with zero matching id="X" anywhere in the file.

Known limitation: only resolves STRING-LITERAL targets on both sides.
`getElementById(someVariable)` and `id="` + a JS template literal cannot
be resolved statically and are silently skipped, not flagged as missing
-- this mirrors the same limitation already accepted in this session's
manual traces and in key_collision_check.py.
"""
import sys, re
from collections import defaultdict

GET_BY_ID_RE = re.compile(r'getElementById\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)')
ID_ATTR_RE = re.compile(r'\bid\s*=\s*[\'"]([^\'"]+)[\'"]')


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'stonedesk.html'
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    lines = html.split('\n')

    existing_ids = set()
    for m in ID_ATTR_RE.finditer(html):
        existing_ids.add(m.group(1))

    calls = defaultdict(list)  # id -> [line, ...]
    for i, line_text in enumerate(lines, 1):
        for m in GET_BY_ID_RE.finditer(line_text):
            calls[m.group(1)].append(i)

    missing = {tid: lns for tid, lns in calls.items() if tid not in existing_ids}

    print("TOTAL_GETELEMENTBYID_CALLS:%d" % sum(len(v) for v in calls.values()))
    print("DISTINCT_TARGETS:%d" % len(calls))
    print("EXISTING_IDS_IN_FILE:%d" % len(existing_ids))
    print("MISSING_TARGETS:%d" % len(missing))
    for tid in sorted(missing):
        lns = missing[tid]
        print("MISSING: id=\"%s\" referenced at line(s) %s -- never appears as id=\"%s\" anywhere in the file"
              % (tid, ', '.join(str(l) for l in lns[:5]) + ('...' if len(lns) > 5 else ''), tid))

    sys.exit(1 if missing else 0)


if __name__ == '__main__':
    main()

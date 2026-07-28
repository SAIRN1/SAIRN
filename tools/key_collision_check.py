"""
key_collision_check.py -- flags any localStorage key written by more than
one DISTINCT BACKING VARIABLE across stonedesk.html.

This is the mechanical enforcement of sairn-software-architect's rule
(added 2026-07-27): "grep for the storage key before creating it." Every
real collision bug found this session (sd_customers, sd_inventory,
sd_remakes, sd_safety) was exactly this pattern -- two independent,
differently-shaped in-memory variables (e.g. an IIFE's private `data`
array vs. a separate global `sdCustomers`) both serialized to the same
key, because the second feature never checked whether the key already
had an owner.

Method: extract every <script> block (reusing extract_scripts.py's real
HTML-parser-based extraction), scan each tracking brace depth (skipping
strings/comments), and capture every
`localStorage.setItem('KEY', JSON.stringify(VAR))` (or bare
`localStorage.setItem('KEY', VAR)`) call's VAR. A key is flagged only
when 2+ DISTINCT NAMED variables write it -- this is the actual signature
of a real collision. Multiple *functions* writing the SAME variable to
the SAME key (e.g. an add/edit/delete trio all calling
`localStorage.setItem('sd_intake', JSON.stringify(intakeSubmissions))`)
is normal CRUD on one cohesive data model, not a bug, and is deliberately
NOT flagged -- an earlier function-name-based version of this check
flagged 9 keys that were all this exact false-positive shape before this
was corrected. Inline literal resets (`'{}'`, `'[]'`, or an inline object/
array literal) are tracked separately and never counted as a competing
variable, since clearing state to empty isn't a competing shape.

Known limitation: dynamic keys (localStorage.setItem(someVar, ...)) are
not resolved -- only string-literal key names are tracked. This mirrors
the same limitation accepted in this session's manual traces.
"""
import sys, os, re
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_scripts import ScriptExtractor

FUNC_DECL_RE = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')
FUNC_EXPR_RE = re.compile(r'([A-Za-z_$][\w$.]*)\s*=\s*function\s*\(')
SETITEM_RE = re.compile(
    r'localStorage\.setItem\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*'
    r'(?:JSON\.stringify\s*\(\s*([A-Za-z_$][\w$.]*)|([A-Za-z_$][\w$.]*)|(\{|\[|[\'"]))'
)


def scan_block(content, base_line):
    depth = 0
    i = 0
    n = len(content)
    line = base_line
    func_stack = []  # [name, depth_of_body_open_brace_or_None]
    results = []  # (key, enclosing_fn, line)

    while i < n:
        c = content[i]
        if c == '\n':
            line += 1
            i += 1
            continue
        if c == '/' and i + 1 < n and content[i+1] == '/':
            j = content.find('\n', i)
            if j == -1:
                break
            i = j
            continue
        if c == '/' and i + 1 < n and content[i+1] == '*':
            j = content.find('*/', i+2)
            if j == -1:
                break
            line += content.count('\n', i, j)
            i = j + 2
            continue
        if c in ("'", '"', '`'):
            quote = c
            j = i + 1
            while j < n:
                if content[j] == '\\':
                    j += 2
                    continue
                if content[j] == quote:
                    break
                j += 1
            line += content.count('\n', i, j)
            i = j + 1
            continue

        m = FUNC_DECL_RE.match(content, i)
        if m:
            func_stack.append([m.group(1), None])
            i = m.end()
            continue
        m2 = FUNC_EXPR_RE.match(content, i)
        if m2:
            func_stack.append([m2.group(1), None])
            i = m2.end()
            continue
        m3 = SETITEM_RE.match(content, i)
        if m3:
            key = m3.group(1)
            var = m3.group(2) or m3.group(3)  # named variable, if any
            is_literal = m3.group(4) is not None  # '{', '[', or a quote -- inline reset, not a competing var
            fn = func_stack[-1][0] if func_stack else '(top-level)'
            results.append((key, fn, var, is_literal, line))
            i = m3.end()
            continue

        if c == '{':
            depth += 1
            if func_stack and func_stack[-1][1] is None:
                func_stack[-1][1] = depth
            i += 1
            continue
        if c == '}':
            if func_stack and func_stack[-1][1] == depth:
                func_stack.pop()
            depth -= 1
            i += 1
            continue
        i += 1
    return results


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'stonedesk.html'
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    parser = ScriptExtractor()
    parser.feed(html)

    all_writes = []
    for start_line, end_line, content in parser.blocks:
        all_writes.extend(scan_block(content, start_line))

    by_key_vars = defaultdict(set)      # key -> set of distinct NAMED variables
    by_key_all = defaultdict(list)      # key -> list of (fn, var_or_literal_marker, line)
    for key, fn, var, is_literal, line in all_writes:
        label = var if var else ('(inline literal reset)' if is_literal else '(unresolved)')
        by_key_all[key].append((fn, label, line))
        if var:  # only named variables count toward collision detection
            by_key_vars[key].add(var)

    collisions = {k: v for k, v in by_key_vars.items() if len(v) > 1}

    print("TOTAL_KEY_WRITES:%d" % len(all_writes))
    print("DISTINCT_KEYS:%d" % len(by_key_all))
    print("COLLISIONS:%d" % len(collisions))
    for key in sorted(collisions):
        print("COLLISION: %s -> distinct backing variables: %s" % (key, sorted(collisions[key])))
        for fn, label, line in by_key_all[key]:
            print("    %s() writes %s @ line %d" % (fn, label, line))

    sys.exit(1 if collisions else 0)


if __name__ == '__main__':
    main()

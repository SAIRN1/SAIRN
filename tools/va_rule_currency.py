"""Pull the per-rule 'Last amended by Order dated ...; effective ...' line that
the published Virginia Rules print at the foot of each rule.

Scoped STRICTLY between one rule heading and the next, so a rule with no line of
its own reports nothing rather than inheriting its neighbour's date. That
distinction is the whole point: a wrong effective_from is worse than a blank one.

Usage: python tools/va_rule_currency.py <rules.txt> <rule> [rule ...]
"""
import re
import sys

HEAD = re.compile(r'^Rule (\d+[A-Z]?:\d+[A-Z]?)\.')
AMEND = re.compile(r'Last (?:amended|updated) by Order dated ([^;]+); effective ([^.]+)\.')

MONTHS = {m: i + 1 for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June', 'July',
     'August', 'September', 'October', 'November', 'December'])}


def iso(text):
    m = re.match(r'\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})', text.strip())
    if not m:
        return None
    return '%04d-%02d-%02d' % (int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))


def main():
    path, wanted = sys.argv[1], sys.argv[2:]
    lines = open(path, encoding='utf-8', errors='replace').read().splitlines()

    starts = [(i, m.group(1)) for i, line in enumerate(lines)
              for m in [HEAD.match(line)] if m]

    for idx, (start, name) in enumerate(starts):
        if name not in wanted:
            continue
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        found = [AMEND.search(l) for l in lines[start:end]]
        found = [f for f in found if f]
        if not found:
            print('%-6s  (no amendment line between this rule and the next)' % name)
            continue
        for f in found:
            print('%-6s  order %-22s effective %-22s -> %s'
                  % (name, f.group(1).strip(), f.group(2).strip(), iso(f.group(2))))


if __name__ == '__main__':
    main()

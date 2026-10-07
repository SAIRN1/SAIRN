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
    # ── A MISSING ARGUMENT IS A REFUSAL, NOT A TRACEBACK (2026-10-07) ─────
    # This read sys.argv[1] directly, so a bare run raised IndexError and
    # exited 1. On this platform EXIT 1 MEANS FINDINGS and exit 2 means COULD
    # NOT RUN -- so a sweep reading exit codes could not tell "needs an
    # argument" from "found something", while 67 other tools say so plainly.
    # Measured 2026-10-07: 8 of 315 tools behaved this way; six were fixed at
    # 47d69604 and this is the seventh.
    #
    # OWNERSHIP: docs/tool-owner-map.json records this file as
    # `"basis": "NONE", "owner": null` -- not UNKNOWN, but NO OWNER AT ALL: no
    # `# OWNER:` line and no claim has ever named it. It was left out of the
    # earlier six because routing was the safe default; a file with no owner
    # cannot be ROUTED to anyone, so leaving it was not deferring the decision,
    # it was declining to make one. Taken here under this session's claim and
    # said out loud rather than fixed quietly. The eighth, tools/gh_push.py:182,
    # IS owned -- the map says `cc`, basis LAST_CLAIM 812857c0 -- and is routed,
    # not touched.
    #
    # TWO ARGUMENTS ARE REQUIRED, NOT ONE. `wanted` is sys.argv[2:], and an
    # empty `wanted` is not an error that raises: the `name not in wanted` test
    # at the loop head matches nothing, so the tool prints NOTHING and exits 0.
    # Silent success on a run that examined no rule is worse than the traceback
    # this is replacing -- a caller cannot tell it from "every rule is clean".
    if len(sys.argv) <= 2:
        sys.stderr.write(
            'COULD NOT RUN: %s. Nothing was read.\n'
            % ('no rules file given' if len(sys.argv) <= 1
               else 'a rules file was given but no rule to look for')
            + 'usage: python tools/va_rule_currency.py <rules.txt> <rule> [rule ...]\n'
              '  e.g. python tools/va_rule_currency.py va_rules.txt 1:4 3A:11\n'
              '  Prints the "Last amended by Order dated ...; effective ..." line\n'
              '  that belongs to each named rule, scoped strictly between that\n'
              '  rule heading and the next so nothing inherits its neighbour.\n')
        sys.exit(2)
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

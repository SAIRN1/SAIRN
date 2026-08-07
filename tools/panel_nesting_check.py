"""
panel_nesting_check.py -- flags any panel-X div that is NOT a direct
sibling of every other panel-X div.

div_balance_check.py only verifies that the TOTAL count of open and close
divs matches -- it does not verify actual nesting structure, and a file
can have perfectly balanced totals while still having real divs nested in
the wrong place. This is exactly how panel-crm went undetected: it ended
up nested one level inside #page-field-quote (a missing closing </div> in
an unrelated ~100-line span earlier in the file), rendering at 0x0 forever,
while div_balance_check.py reported PASS the whole time because the
overall open/close totals still matched.

All panel-X divs are meant to be siblings under the same parent
(.panel-wrap) -- that's what makes the .panel/.panel.active show/hide CSS
mechanism work at all. If one panel is nested inside another (or inside
some other leftover container), showPanel()/sbNav() can apply the
'active' class correctly and it will still never become visible, because
a display:none ancestor hides everything inside it regardless of the
child's own class/display state.

Method: parse the full document with a real HTML parser (not naive
<script> or <div> counting), tracking nesting depth of every element.
Record the depth at which each <div id="PREFIXpanel-X"> opens. The correct
depth is whatever the majority (mode) of panels share -- flag any panel
whose depth differs from that majority, and name its actual parent
element so the trapped location is immediately visible.

Panel-ID prefix is DETECTED PER FILE, not hardcoded (fixed 2026-08-07,
was CONFIRMED REAL GAP, now closed): the original version hardcoded
`pid.startswith('panel-')`, which silently returned NO_PANELS_FOUND on
sairnscape.html -- an app with 11 real, structurally fine panels, just
namespaced `id="scp-panel-X"` instead of StoneDesk/SAIRNbiz/SAIRNgrounds'
bare `id="panel-X"`. Confirmed by manually re-running the same
depth-mapping logic with the prefix hardcoded to 'scp-panel-': 11 panels,
0 trapped, matching what a human inspection of the file already showed.
A single silent zero is exactly the kind of blind spot
sairn-portfolio-triage's own "Scanner Portability" section warns about --
this fix generalizes the same way that section's other two fixes did:
stop assuming one app's convention, detect the real one from the file
being scanned.

Detection method: first pass, collect the id of every <div> whose id
matches `(PREFIX)panel-(NAME)` (case-insensitive, PREFIX may be empty).
The most common PREFIX across those matches is treated as this file's
real panel-id prefix -- majority vote, not a fixed guess, so it works
whether an app uses bare `panel-X` or a namespaced `app-panel-X`. If no
div id matches the pattern at all, NO_PANELS_FOUND is still a real,
honest result (the app genuinely doesn't use this convention), not a
detection failure.
"""
import sys, re
from collections import Counter
from html.parser import HTMLParser

VOID_ELEMENTS = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
PANEL_ID_RE = re.compile(r'^(.*?)panel-([a-zA-Z0-9_]+)$', re.IGNORECASE)


class PanelPrefixScanner(HTMLParser):
    """Pass 1: find every div id shaped like PREFIXpanel-NAME, and tally
    the PREFIX part so the real, in-use prefix can be detected by
    majority vote instead of assumed."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.in_script = False
        self.prefix_counts = Counter()

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'script':
            self.in_script = True
        if self.in_script or tag.lower() != 'div':
            return
        pid = dict(attrs).get('id', '')
        m = PANEL_ID_RE.match(pid)
        if m:
            self.prefix_counts[m.group(1)] += 1

    def handle_endtag(self, tag):
        if tag.lower() == 'script':
            self.in_script = False


def detect_panel_prefix(html):
    scanner = PanelPrefixScanner()
    scanner.feed(html)
    if not scanner.prefix_counts:
        return None
    prefix, _ = scanner.prefix_counts.most_common(1)[0]
    return prefix + 'panel-'


class PanelDepthMapper(HTMLParser):
    def __init__(self, panel_id_prefix):
        super().__init__(convert_charrefs=False)
        self.stack = []  # list of (tag, id_or_class)
        self.panels = {}  # panel_id -> (depth, line, parent_desc)
        self.in_script = False
        self.panel_id_prefix = panel_id_prefix

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        if tag.lower() == 'script':
            self.in_script = True
        if self.in_script:
            return
        d = dict(attrs)
        pid = d.get('id', '')
        if tag.lower() in VOID_ELEMENTS:
            return
        if pid.startswith(self.panel_id_prefix):
            parent_desc = '%s#%s' % self.stack[-1] if self.stack else '(document root)'
            self.panels[pid] = (len(self.stack), line, parent_desc)
        ident = pid or ('.' + d.get('class', '').split(' ')[0] if d.get('class') else tag)
        self.stack.append((tag, ident))

    def handle_endtag(self, tag):
        if tag.lower() == 'script':
            self.in_script = False
            return
        if self.in_script:
            return
        if tag.lower() in VOID_ELEMENTS:
            return
        if self.stack:
            self.stack.pop()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'stonedesk.html'
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    panel_id_prefix = detect_panel_prefix(html)
    if panel_id_prefix is None:
        print("NO_PANELS_FOUND")
        sys.exit(1)

    parser = PanelDepthMapper(panel_id_prefix)
    parser.feed(html)

    if not parser.panels:
        print("NO_PANELS_FOUND")
        sys.exit(1)

    print("DETECTED_PANEL_ID_PREFIX:%r" % panel_id_prefix)

    # FIXED 2026-07-30 (was hardcoded to StoneDesk's own container class
    # names, {'div#.app-body','div#.panel-wrap'} -- broke completely on
    # any other app: SAIRNbiz's real safe parent is `main#main`,
    # SAIRNcode's is `div#.container`, neither matches StoneDesk's names,
    # so every panel in both apps was flagged TRAPPED (20/20 each) even
    # though both apps are structurally fine. Confirmed by direct
    # cross-check: SAIRNbiz's key-collision scan is 0/0 real (verified
    # independently via grep, not just trusted), so a tool this
    # unreliable on the SAME file for a different check was a real red
    # flag, not just a suspicion.
    #
    # Generalized, app-agnostic method: a parent shared by 2+ panels is
    # a real structural pattern (whether that's one single-shell app, or
    # StoneDesk's known app-body/panel-wrap split -- both containers get
    # many panels each, so neither looks like an outlier). Only a parent
    # that NO OTHER panel shares -- a true singleton -- is treated as
    # trapped, since that's what an actual "nested one level inside an
    # unrelated leftover container" bug produces: a panel with a parent
    # unlike every other panel's. This reproduces the original
    # panel-crm-inside-page-field-quote catch (a genuine singleton
    # parent) without needing to know any app's real class names ahead
    # of time.
    parents = [p for d, l, p in parser.panels.values()]
    parent_counts = Counter(parents)
    majority_parent = parent_counts.most_common(1)[0][0]
    safe_count = sum(1 for p in parents if parent_counts[p] >= 2)

    trapped = {pid: info for pid, info in parser.panels.items() if parent_counts[info[2]] < 2}
    shell_split = {pid: info for pid, info in parser.panels.items()
                   if parent_counts[info[2]] >= 2 and info[2] != majority_parent}

    print("TOTAL_PANELS:%d" % len(parser.panels))
    print("SAFE_SHELL_PARENT_PANELS:%d (any parent shared by 2+ panels)" % safe_count)
    print("TRAPPED_PANELS (singleton parent, shared by no other panel):%d" % len(trapped))
    for pid in sorted(trapped):
        depth, line, parent = trapped[pid]
        print("TRAPPED: %s at line %d -- actual parent: %s" % (pid, line, parent))
    if shell_split:
        print("NOTE: %d panels have a real (2+-panel, safe) parent that isn't the majority one "
              "(both/all safe, still visible) -- likely a separate, real structural imbalance "
              "elsewhere worth its own look, but not a hidden-panel bug:" % len(shell_split))
        for pid in sorted(shell_split):
            depth, line, parent = shell_split[pid]
            print("  %s at line %d -- parent: %s" % (pid, line, parent))

    sys.exit(1 if trapped else 0)


if __name__ == '__main__':
    main()

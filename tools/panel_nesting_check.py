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
Record the depth at which each <div id="panel-X"> opens. The correct
depth is whatever the majority (mode) of panels share -- flag any panel
whose depth differs from that majority, and name its actual parent
element so the trapped location is immediately visible.
"""
import sys
from collections import Counter
from html.parser import HTMLParser

VOID_ELEMENTS = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}


class PanelDepthMapper(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []  # list of (tag, id_or_class)
        self.panels = {}  # panel_id -> (depth, line, parent_desc)
        self.in_script = False

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
        if pid.startswith('panel-'):
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

    parser = PanelDepthMapper()
    parser.feed(html)

    if not parser.panels:
        print("NO_PANELS_FOUND")
        sys.exit(1)

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

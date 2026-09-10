"""Every third-party component this platform runs must appear in the SOUP register.

    python tools/soup_register_check.py            # report, exit 1 on drift
    python tools/soup_register_check.py --quiet    # exit code only

WHY THIS EXISTS. `docs/SOUP-REGISTER.md` is Software of Unknown Provenance --
name, version, tier, what a hostile version could do, and a real stated reason
it is trusted. A register maintained by remembering goes stale, and this repo
has that written down in six other places: the Guardian App File Map went wrong
seven times, the skill counts drifted three ways in one file, and the cleanup
files' NOT RUN labels were wrong on at least six.

So the register is DERIVED-CHECKED rather than trusted. This reads the real
sources -- `package.json`, `package-lock.json`, and every root `*.html` -- and
reports:

  * a dependency or CDN script that is running and NOT in the register;
  * a register entry naming something no longer present;
  * a VERSION that has moved since the entry was written.

It reports and exits non-zero. It does not edit the register: what a component
is trusted FOR is a judgement, and a tool that regenerated this file would
delete exactly the part that matters. Same reasoning as
`tools/sairn_app_map_check.py`, which derives the verifiable half of the app map
and refuses to rewrite the colour and app_id it cannot derive.

BROWSER SCRIPTS ARE THE HALF AN npm AUDIT DOES NOT SEE, and on this platform
they were the weaker half: no Subresource Integrity on any of them, two on a
floating major. All four are pinned and hashed as of 2026-09-10. They are
checked here for that reason.

WHAT THIS TOOL GOT WRONG ON ITS FIRST DAY, kept because it is the reason for
half the code below. It reported `CLEAN -- every running component is in the
register` while a FOURTH CDN script was running and unregistered:
`tesseract.js@5`, a floating major, in `sairnlaw.html`, a page holding
privileged client matter records. It was missed because it is injected from JS
rather than written as a `<script src>` tag -- and that one property made it
invisible to three separate checks at once: Semgrep's `missing-integrity`,
StoneDesk's own Layer 12 SRI walk, and this register check. A register derived
from a source that cannot see a component is not derived, it is narrowed.

So this now reads BOTH shapes, and the three checks that were report-only
because the no-SRI state was "recorded and owned" now FAIL -- that state is
closed, and a note is the wrong signal for a regression.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(REPO, 'docs', 'SOUP-REGISTER.md')


def read(path):
    with io.open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def root_html():
    out = subprocess.run(['git', 'ls-files', '*.html'], cwd=REPO,
                         capture_output=True, text=True).stdout
    return [f for f in out.split('\n') if f and '/' not in f]


def declared_deps():
    """Direct npm dependencies and their INSTALLED versions.

    The declared range (`^13.3.2`) and the installed version (13.3.2) are
    different facts and the register records the installed one -- a range is a
    promise about the future, and what is running is what matters.
    """
    pkg = json.loads(read(os.path.join(REPO, 'package.json')))
    lock = json.loads(read(os.path.join(REPO, 'package-lock.json')))
    packages = lock.get('packages', {})
    out = {}
    for name in (pkg.get('dependencies') or {}):
        entry = packages.get('node_modules/' + name, {})
        out[name] = entry.get('version')
    return out


def cdn_scripts():
    """Every external script a root app loads, static OR injected, with SRI state.

    Two shapes, because this platform ships both and the second one is what
    slipped through:

      static    <script src="https://..." integrity="sha384-...">
      injected  var s = document.createElement('script');
                s.src = 'https://...'; s.integrity = 'sha384-...';

    THE HONEST LIMIT of the injected half: it pairs a `.src` assignment with the
    variable a literal `document.createElement('script')` bound in the same
    file. A script element built any other way -- returned from a helper, held
    in an object property, named by a computed string -- is NOT seen. That is a
    real gap and it is stated rather than papered over; it is narrower than the
    gap it replaces, not zero. If a loader like that gets written, this docstring
    is the thing that should have said so first.
    """
    found = {}

    def note(url, app, has_sri):
        rec = found.setdefault(url, {'apps': [], 'sri': has_sri})
        rec['apps'].append(app)
        # One app with SRI and one without is not "has SRI".
        rec['sri'] = rec['sri'] and has_sri

    for f in root_html():
        src = read(os.path.join(REPO, f))
        for m in re.finditer(r'<script[^>]*\ssrc="(https?://[^"]+)"([^>]*)>', src):
            note(m.group(1), f, 'integrity=' in m.group(2))
        for var in set(re.findall(
                r'\b([A-Za-z_$][\w$]*)\s*=\s*document\.createElement\(\s*[\'"]script[\'"]\s*\)',
                src)):
            v = re.escape(var)
            has_sri = re.search(r'\b%s\s*\.\s*integrity\s*=' % v, src) is not None
            for m in re.finditer(r'\b%s\s*\.\s*src\s*=\s*[\'"](https?://[^\'"]+)[\'"]' % v, src):
                note(m.group(1), f, has_sri)
    return found


def cdn_version(url):
    """The pinned version in a CDN URL, or None if the URL states none.

    Returns the literal text, floating majors included -- `2` and `2.116.0` are
    both versions and the difference between them is the whole point.
    """
    m = re.search(r'/npm/(?:@[^/@]+/)?[^/@]+@([^/]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/libs/[^/]+/([^/]+)/', url)
    if m:
        return m.group(1)
    return None


def package_name(url):
    """The component name a CDN URL is serving, for matching against the register."""
    m = re.search(r'/npm/((?:@[^/@]+/)?[^/@]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/libs/([^/]+)/', url)
    if m:
        return m.group(1)
    return url


COMPONENT_SECTIONS = ('server-side', 'browser-side')


def register_rows(reg):
    """Component names from the two component tables only.

    A backticked first cell means "component" under `## Server-side` and
    `## Browser-side`, and means nothing anywhere else in the document -- the
    entries themselves carry explanatory tables whose rows are not components.
    """
    names, section = [], ''
    for line in reg.split('\n'):
        if line.startswith('## '):
            section = line[3:].strip().lower()
        elif line.startswith('### '):
            # An entry's own heading ends the table; its prose tables are not
            # part of it.
            section = ''
        elif section.startswith(COMPONENT_SECTIONS):
            m = re.match(r'\| `([^`]+)` \|', line)
            if m:
                names.append(m.group(1))
    return names


def main(argv):
    quiet = '--quiet' in argv
    if not os.path.exists(REGISTER):
        print('MISSING: docs/SOUP-REGISTER.md does not exist. Nothing to check '
              'against -- this is a hard fail, not a clean run.')
        return 2
    reg = read(REGISTER)
    problems = []
    notes = []

    deps = declared_deps()
    for name, version in sorted(deps.items()):
        if ('`%s`' % name) not in reg:
            problems.append('npm dependency NOT in the register: %s@%s' % (name, version))
            continue
        if version and version not in reg:
            problems.append('%s is installed at %s and the register does not name '
                            'that version -- an entry written against a different '
                            'version is a claim about software nobody is running'
                            % (name, version))

    cdn = cdn_scripts()
    for url, rec in sorted(cdn.items()):
        name = package_name(url)
        where = ', '.join(sorted(set(rec['apps'])))
        if ('`%s`' % name) not in reg:
            problems.append('CDN script NOT in the register: %s (loaded by %s)'
                            % (name, where))
        if not rec['sri']:
            # FAILS, and used to be a report-only note. The note was right while
            # every CDN script lacked SRI and the register owned that with an
            # open-work row -- a check that is red on a recorded, owned state
            # teaches people to ignore it. That state closed on 2026-09-10 when
            # all four were hashed, so from here a missing integrity attribute
            # is a REGRESSION, and a note is the wrong signal for a regression.
            problems.append('no Subresource Integrity on %s (loaded by %s) -- a '
                            'host allowed by CSP is a statement about where a '
                            'file may come from, not about which file arrived'
                            % (name, where))
        ver = cdn_version(url)
        if ver is None:
            problems.append('%s is loaded with NO version in the URL (%s) -- '
                            'whatever the CDN serves today is what runs' % (name, where))
        elif '.' not in ver:
            problems.append('%s is pinned to `@%s`, a FLOATING major (%s) -- any '
                            'future publish under that major, including a '
                            'compromised one, runs here unreviewed' % (name, ver, where))
        elif ver not in reg:
            problems.append('%s is loaded at %s and the register does not name '
                            'that version -- an entry written against a different '
                            'version is a claim about software nobody is running'
                            % (name, ver))

    # The other direction: an entry for something that is gone. A register that
    # only grows is a register that starts lying about what is running.
    #
    # SCOPED TO THE TWO COMPONENT TABLES, and it was not on day one. This walked
    # every `| `name` |` row in the whole file, so the first prose table added
    # below -- a breakdown of tesseract's sub-resources -- was read as a
    # component entry and reported as a stale one. Same family as the
    # split-on-`|` lesson in CLAUDE.md: a row's meaning comes from the table it
    # is in, and a matcher that ignores the table gets it wrong eventually.
    for name in register_rows(reg):
        if name in deps:
            continue
        if any(package_name(u) == name for u in cdn):
            continue
        problems.append('register names `%s`, which is no longer a declared '
                        'dependency or a loaded CDN script -- remove the entry '
                        'or say why it is still here' % name)

    if not quiet:
        print('SOUP register check')
        print('  npm direct dependencies : %d' % len(deps))
        print('  CDN scripts in root apps: %d' % len(cdn))
        for n in notes:
            print('  NOTE: %s' % n)
        if problems:
            print('\n%d DRIFT FINDING(S):' % len(problems))
            for p in problems:
                print('  - %s' % p)
            print('\nUpdate docs/SOUP-REGISTER.md. Adding an entry means answering '
                  'its five questions, not pasting a name: tier, what a hostile '
                  'version could do, what bounds it, and why writing it here '
                  'ourselves would be worse.')
        else:
            print('  CLEAN -- every running component is in the register, and every '
                  'register entry is still running.')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

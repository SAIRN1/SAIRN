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
they are the weaker half: two CDN scripts, no Subresource Integrity on either,
one on a floating major. They are checked here for that reason.
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
    """Every <script src="http(s)://..."> in a root app, with SRI status."""
    found = {}
    for f in root_html():
        src = read(os.path.join(REPO, f))
        for m in re.finditer(r'<script[^>]*\ssrc="(https?://[^"]+)"([^>]*)>', src):
            url, rest = m.group(1), m.group(2)
            rec = found.setdefault(url, {'apps': [], 'sri': 'integrity=' in rest})
            rec['apps'].append(f)
            # One app with SRI and one without is not "has SRI".
            rec['sri'] = rec['sri'] and ('integrity=' in rest)
    return found


def package_name(url):
    """The component name a CDN URL is serving, for matching against the register."""
    m = re.search(r'/npm/((?:@[^/@]+/)?[^/@]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/libs/([^/]+)/', url)
    if m:
        return m.group(1)
    return url


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
        if ('`%s`' % name) not in reg:
            problems.append('CDN script NOT in the register: %s (loaded by %s)'
                            % (name, ', '.join(sorted(set(rec['apps'])))))
        if not rec['sri']:
            # REPORTED, not a failure. Both current entries lack SRI and the
            # register says so with its own open-work row; making this fail
            # would mean the check is red on a state that is already recorded
            # and owned, which teaches people to ignore it.
            notes.append('no Subresource Integrity on %s (loaded by %s)'
                         % (name, ', '.join(sorted(set(rec['apps'])))))

    # The other direction: an entry for something that is gone. A register that
    # only grows is a register that starts lying about what is running.
    for m in re.finditer(r'^\| `([^`]+)` \|', reg, re.M):
        name = m.group(1)
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

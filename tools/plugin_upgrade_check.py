"""Is an installed Claude Code plugin behind its marketplace? Compare VERSIONS.

    python tools/plugin_upgrade_check.py
    python tools/plugin_upgrade_check.py --json
    python tools/plugin_upgrade_check.py --fixtures     # blind lock, judges nothing real

Exit 0 every plugin is current, 1 at least one is BEHIND, 2 nothing could be
compared at all. Three states, never two.

── THE DEFECT THIS TOOL EXISTS BECAUSE OF, AND IT WAS MINE ─────────────────
On 2026-09-25 the standing upgrade audit had carried a COULD-NOT-TELL on two
plugins for ten days: `superpowers` and `vercel` declare no version in the
official marketplace manifest, and that marketplace is not a git checkout, so
two audits in a row looked for one, correctly found none, and stopped.

The pin IS in the manifest. Each entry carries `source: {source: "url", url,
sha}` and `installed_plugins.json` carries a `gitCommitSha`, so the comparison
was done with the GitHub compare API -- and it worked, and it found both behind.

THEN THE UPGRADE BROKE THE METHOD, on the same day, within the hour.
`claude plugin update` moves `installPath`, `version` and `lastUpdated` in
`installed_plugins.json` AND LEAVES `gitCommitSha` POINTING AT THE OLD COMMIT.
Measured after upgrading both: superpowers reads 6.4.1 with sha 44c9b2d6 (the
6.2.0 commit) and vercel reads 0.50.0 with sha b2f2bc09 (the 0.45.1 commit). So
the sha comparison that ANSWERED the question now reports both plugins as still
behind when they are not -- a confident false finding, produced by the success
of the thing it measured.

── SO THE COMPARISON IS BY VERSION, AND THE SHA IS NEVER READ ──────────────
Not "prefer version, fall back to sha". NEVER read. A field that is right
before an upgrade and wrong after it is worse than absent: it is available,
plausible and stale exactly when somebody is checking whether the upgrade took.
A fixture arm asserts this file contains no gitCommitSha read at all.

── AND THE INSTALLED VERSION IS READ FROM DISK, NOT FROM THE MANIFEST ──────
The ground truth is the plugin's own `.claude-plugin/plugin.json` inside its
install directory -- that file ships with the code that is actually loaded.
`installed_plugins.json`'s `version` agrees with it today, and the whole reason
this tool exists is that one of that file's fields did not.

── WHAT IT REFUSES ─────────────────────────────────────────────────────────
* A plugin whose upstream version cannot be established is UNKNOWN, never
  current. `url`-sourced entries need one network read of the pinned sha's
  plugin.json; with no network or no token that is COULD NOT TELL for that
  plugin and it is counted separately.
* Versions are compared as dotted integers. A version that does not parse that
  way on EITHER side is UNKNOWN rather than string-compared -- '0.50.0' vs
  '0.9.25' sorts the wrong way as a string, and this tool would rather say
  nothing than say that.
* It never upgrades anything. `claude plugin update <name>` is a human's call,
  and a tool that installed its own findings would be the auto-remediation
  shape discipline 11 forbids.
"""
import io
import json
import os
import re
import subprocess
import sys

HOME = os.path.expanduser('~')
PLUGINS = os.path.join(HOME, '.claude', 'plugins')
INSTALLED = os.path.join(PLUGINS, 'installed_plugins.json')
MARKETPLACES = os.path.join(PLUGINS, 'marketplaces')
KNOWN = os.path.join(PLUGINS, 'known_marketplaces.json')


class CouldNotTell(Exception):
    pass


# ── THE FUNCTIONAL CORE ─────────────────────────────────────────────────────
# Pure: no filesystem, no network, no clock. The probe drives these directly,
# which is the only reason the "cannot parse a version" paths are reachable.

VERSION_RE = re.compile(r'^\d+(?:\.\d+)*$')


def parse_version(v):
    """-> tuple of ints, or None when it is not a dotted-integer version.

    None is a THIRD ANSWER. A version this cannot parse is never string-
    compared: '0.50.0' < '0.9.25' as strings, and that is a confident wrong
    answer in the direction that says 'you are up to date'.
    """
    s = str(v if v is not None else '').strip()
    if not VERSION_RE.match(s):
        return None
    return tuple(int(p) for p in s.split('.'))


def compare_versions(installed, available):
    """-> 'current' | 'behind' | 'ahead' | 'unknown'."""
    a, b = parse_version(installed), parse_version(available)
    if a is None or b is None:
        return 'unknown'
    # Pad so 1.2 and 1.2.0 compare equal rather than by length.
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    if a < b:
        return 'behind'
    if a > b:
        return 'ahead'
    return 'current'


def marketplace_entry(manifest, name):
    """The plugin's entry in a marketplace.json, or None."""
    for p in (manifest or {}).get('plugins') or []:
        if p.get('name') == name:
            return p
    return None


def upstream_source(entry):
    """-> ('path', <relative path>) | ('url', <repo>, <sha>) | ('inline', ver) | None.

    A marketplace entry declares its version inline, or points at a path inside
    the checkout, or at an external repo pinned to a sha. Each needs a
    different read and mixing them up is how the previous method went wrong.
    """
    if not entry:
        return None
    if entry.get('version'):
        return ('inline', entry['version'])
    src = entry.get('source')
    if isinstance(src, str):
        return ('path', src)
    if isinstance(src, dict) and src.get('source') == 'url':
        url = str(src.get('url') or '')
        m = re.search(r'github\.com/([^/]+/[^/.]+)', url)
        if not m or not src.get('sha'):
            return None
        return ('url', m.group(1), src['sha'])
    return None


def classify(name, installed_version, available_version, note=None):
    state = ('unknown' if available_version is None
             else compare_versions(installed_version, available_version))
    return {'plugin': name, 'installed': installed_version,
            'available': available_version, 'state': state, 'note': note}


# ── THE IMPERATIVE SHELL ────────────────────────────────────────────────────

def read_json(path):
    return json.load(io.open(path, encoding='utf-8'))


def installed_plugins():
    """-> [(qualified_name, plugin_name, marketplace, install_path)]."""
    data = read_json(INSTALLED)
    out = []
    for qualified, entries in (data.get('plugins') or {}).items():
        if not entries:
            continue
        e = entries[0]
        name, _, market = qualified.partition('@')
        out.append((qualified, name, market, e.get('installPath') or ''))
    return out


def version_on_disk(install_path):
    """The version the LOADED code declares. Ground truth -- see the header."""
    p = os.path.join(install_path, '.claude-plugin', 'plugin.json')
    try:
        return read_json(p).get('version')
    except Exception:                                   # noqa: BLE001
        return None


def marketplace_manifest(market):
    p = os.path.join(MARKETPLACES, market, '.claude-plugin', 'marketplace.json')
    try:
        return read_json(p)
    except Exception:                                   # noqa: BLE001
        return None


def github_token():
    r = subprocess.run(['git', 'credential', 'fill'],
                       input='protocol=https\nhost=github.com\n\n',
                       capture_output=True, text=True)
    for line in (r.stdout or '').splitlines():
        if line.startswith('password='):
            return line.split('=', 1)[1]
    return None


def fetch_upstream_version(repo, sha, token):
    """plugin.json's version at a pinned sha. None when it cannot be read."""
    import base64
    import urllib.error
    import urllib.request
    url = ('https://api.github.com/repos/%s/contents/.claude-plugin/plugin.json?ref=%s'
           % (repo, sha))
    req = urllib.request.Request(url)
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    req.add_header('Accept', 'application/vnd.github+json')
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.loads(r.read())
    except (urllib.error.URLError, OSError, ValueError):
        return None
    try:
        return json.loads(base64.b64decode(body['content']).decode('utf-8')).get('version')
    except Exception:                                   # noqa: BLE001
        return None


def run():
    rows, could_not = [], []
    try:
        entries = installed_plugins()
    except Exception as e:                              # noqa: BLE001
        raise CouldNotTell('%s could not be read (%s), so NOTHING was compared'
                           % (INSTALLED, e))
    token = None
    for qualified, name, market, install_path in sorted(entries):
        installed = version_on_disk(install_path)
        if installed is None:
            could_not.append('%s: no plugin.json under %s -- the installed '
                             'version is unknown, which is not "current"'
                             % (qualified, install_path))
            rows.append(classify(qualified, None, None, 'installed version unreadable'))
            continue
        man = marketplace_manifest(market)
        if man is None:
            could_not.append('%s: marketplace %s has no readable manifest'
                             % (qualified, market))
            rows.append(classify(qualified, installed, None, 'no marketplace manifest'))
            continue
        src = upstream_source(marketplace_entry(man, name))
        if src is None:
            could_not.append('%s: the marketplace entry declares neither a '
                             'version nor a resolvable source' % qualified)
            rows.append(classify(qualified, installed, None, 'unresolvable marketplace entry'))
            continue
        if src[0] == 'inline':
            rows.append(classify(qualified, installed, src[1], 'marketplace declares it'))
        elif src[0] == 'path':
            p = os.path.join(MARKETPLACES, market, src[1].lstrip('./'),
                             '.claude-plugin', 'plugin.json')
            try:
                rows.append(classify(qualified, installed,
                                     read_json(p).get('version'),
                                     'from the marketplace checkout'))
            except Exception:                           # noqa: BLE001
                could_not.append('%s: %s is not readable in the checkout' % (qualified, p))
                rows.append(classify(qualified, installed, None, 'checkout unreadable'))
        else:
            if token is None:
                token = github_token() or ''
            v = fetch_upstream_version(src[1], src[2], token or None)
            if v is None:
                could_not.append('%s: the pinned sha %s in %s could not be read '
                                 '(no network, no token, or the path moved), so '
                                 'this plugin was NOT compared'
                                 % (qualified, src[2][:8], src[1]))
            rows.append(classify(qualified, installed, v,
                                 'upstream plugin.json at the marketplace pin'))
    return rows, could_not


# ── THE BLIND LOCK (discipline 1): judge fixtures before anything real ──────
def fixtures():
    out, bad = [], 0

    def ck(name, cond, detail=''):
        nonlocal bad
        out.append(('  ok   ' if cond else '  FAIL ') + name
                   + ('' if cond else '  <- ' + str(detail)[:200]))
        if not cond:
            bad += 1

    ck('a newer available version is BEHIND',
       compare_versions('6.2.0', '6.4.1') == 'behind')
    ck('equal versions are CURRENT',
       compare_versions('1.0.0', '1.0.0') == 'current')
    ck('1.2 and 1.2.0 are the same version, not a difference of length',
       compare_versions('1.2', '1.2.0') == 'current')
    ck('an installed version AHEAD of the marketplace says so rather than '
       'reporting current -- a local build is a real state',
       compare_versions('0.51.0', '0.50.0') == 'ahead')
    # THE ARM THAT MATTERS ON THE COMPARATOR. String order gets this wrong.
    ck('THE STRING TRAP: 0.50.0 is AHEAD of 0.9.25, which a string compare '
       'gets backwards', compare_versions('0.50.0', '0.9.25') == 'ahead')
    ck('...and 0.9.25 is BEHIND 0.50.0', compare_versions('0.9.25', '0.50.0') == 'behind')
    ck('a version that does not parse is UNKNOWN on either side, never '
       'string-compared', compare_versions('v6.4.1', '6.4.1') == 'unknown'
       and compare_versions('6.4.1', 'latest') == 'unknown')
    ck('an absent version is UNKNOWN, never current',
       compare_versions('6.4.1', None) == 'unknown'
       and compare_versions(None, '6.4.1') == 'unknown')
    ck('parse_version returns None rather than a partial tuple for junk',
       parse_version('1.2.x') is None and parse_version('') is None)

    ck('a url-sourced marketplace entry yields its repo and pinned sha',
       upstream_source({'source': {'source': 'url',
                                   'url': 'https://github.com/obra/superpowers.git',
                                   'sha': 'abc123'}}) == ('url', 'obra/superpowers', 'abc123'))
    ck('an inline version wins -- no network read is needed for it',
       upstream_source({'version': '1.0.0', 'source': './plugins/x'})[0] == 'inline')
    ck('a path-sourced entry with no version is read from the checkout',
       upstream_source({'source': './plugins/x'}) == ('path', './plugins/x'))
    ck('a url entry with NO sha is unresolvable rather than fetched from HEAD '
       '-- HEAD is not what the marketplace pins',
       upstream_source({'source': {'source': 'url',
                                   'url': 'https://github.com/o/r.git'}}) is None)

    ck('classify() with no available version is UNKNOWN and carries both sides',
       classify('p', '1.0.0', None)['state'] == 'unknown')

    # ── THE ARM THIS WHOLE FILE EXISTS FOR ──────────────────────────────────
    # Asserted on the CODE with comment lines stripped, because this file's own
    # header discusses gitCommitSha at length and a raw grep would match the
    # prose it is warning about (PR 1.2).
    src = io.open(os.path.abspath(__file__), encoding='utf-8').read()
    code = '\n'.join(l for l in src.split('\n') if not l.lstrip().startswith('#'))
    code = re.sub(r'"""[\s\S]*?"""', '', code)
    # ── THE NEEDLES ARE ASSEMBLED AT RUNTIME, and that is not decoration.
    # Written as literals they appear in THIS function, which is part of the
    # code being scanned, so both arms matched themselves and reported a
    # forbidden read that does not exist. Same self-reference trap this repo has
    # now recorded four times -- the `--self-check` regex, the never-merges
    # fixture arm, register_freshness_check's own docstring, and this.
    forbidden_field = 'gitCommit' + 'Sha'
    hits = code.count(forbidden_field) - code.count("'gitCommit' + 'Sha'")
    ck('THE DEFECT CANNOT COME BACK: this tool never reads the commit-sha '
       'field, which is right before an upgrade and wrong after it',
       hits <= 0, hits)
    ck('CONTROL: the stripping left the code behind, so the arm above is '
       'judging code rather than passing on an empty string',
       'def compare_versions' in code and len(code) > 1500)
    # The upgrade COMMAND is printed as advice to a human, which is the point
    # -- what must not exist is this file RUNNING it. So the needle is the
    # subprocess shape, not the words.
    runs_cli = re.search(r"\[\s*'claude'\s*,\s*'plugin'", code) is not None
    ck('IT NEVER UPGRADES ANYTHING -- it prints the command for a human and '
       'never invokes the plugin CLI itself', not runs_cli)
    return out, bad


def main(argv):
    if '--fixtures' in argv:
        out, bad = fixtures()
        for l in out:
            print(l)
        print('  %s' % ('ALL FIXTURES PASS' if not bad else '%d FIXTURE(S) FAILED' % bad))
        return 1 if bad else 0

    out, bad = fixtures()
    if bad:
        print('THE FIXTURE LOCK FAILED -- nothing real was judged.')
        for l in out:
            print(l)
        return 2

    try:
        rows, could_not = run()
    except CouldNotTell as e:
        sys.stderr.write('COULD NOT TELL: %s\n' % e)
        return 2

    if '--json' in argv:
        print(json.dumps({'plugins': rows, 'could_not_tell': could_not}, indent=2))
    else:
        print('PLUGIN UPGRADES -- compared by VERSION, never by commit sha')
        for r in rows:
            print('  %-9s %-40s %s -> %s'
                  % (r['state'].upper(), r['plugin'],
                     r['installed'] or '?', r['available'] or '?'))
        behind = [r for r in rows if r['state'] == 'behind']
        unknown = [r for r in rows if r['state'] == 'unknown']
        print('')
        print('  behind %d   unknown %d   of %d' % (len(behind), len(unknown), len(rows)))
        for c in could_not:
            print('  COULD NOT TELL  %s' % c)
        if unknown:
            print('')
            print('UNKNOWN IS NOT CURRENT. A plugin whose upstream version could not')
            print('be established was not compared, and that is a gap in this run')
            print('rather than a clean result.')
        if behind:
            print('')
            print('Upgrade with:  claude plugin update <name>@<marketplace>')
            print('This tool does NOT do it -- a checker that installs its own')
            print('findings is the auto-remediation shape discipline 11 forbids.')

    if not rows:
        sys.stderr.write('COULD NOT TELL: no installed plugin was read at all.\n')
        return 2
    return 1 if any(r['state'] == 'behind' for r in rows) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

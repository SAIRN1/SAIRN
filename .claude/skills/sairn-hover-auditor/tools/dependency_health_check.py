"""dependency_health_check.py -- bus-factor / maintainer-health scanner for
SAIRN's own third-party dependency tree.

WHY THIS EXISTS. Directly motivated by CVE-2024-3094 (the xz-utils
backdoor): the compromised library was a single-maintainer, low-traffic
dependency, and that structural fragility -- one burned-out person, real and
sustained pressure to accept help -- was the actual opening the attack
patiently exploited over years. This checks a real risk category nothing
else on this platform covers: the health of a THIRD-PARTY dependency,
not SAIRN's own code.

WHAT THIS IS NOT. A vulnerability scanner (no CVE lookup here) and not a
license auditor. It answers one narrow question per dependency: if this
package's current maintainer(s) vanished tomorrow, is there anyone else
positioned to keep it honest? A locator, not a detector -- report-only,
same convention as this platform's own checkers.

    python dependency_health_check.py [path/to/package.json]

Reads live data from the public npm registry (no auth required). Exit 0
report printed, 2 if package.json cannot be read or the registry is
unreachable for every dependency (could-not-check is never folded into
clean, same standing rule as every checker on the platform this audits).
"""
import json
import sys
import urllib.request
import urllib.error
import urllib.parse

REGISTRY = 'https://registry.npmjs.org/'

# Thresholds are a judgement call, stated so a reader can disagree with the
# number rather than just the verdict.
LOW_MAINTAINER_COUNT = 2       # fewer than this = single/near-single point of failure
STALE_DAYS = 365                # no publish in this long = worth a second look


def fetch_json(url, timeout=15):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8')), None
    except urllib.error.HTTPError as e:
        return None, 'HTTP %d' % e.code
    except Exception as e:                                    # noqa: BLE001
        return None, str(e)


def analyse_package(name):
    meta, err = fetch_json(REGISTRY + urllib.parse.quote(name, safe='@/'))
    if meta is None:
        return {'name': name, 'could_not_check': err}

    maintainers = meta.get('maintainers') or []
    latest = (meta.get('dist-tags') or {}).get('latest')
    time_map = meta.get('time') or {}
    latest_published = time_map.get(latest) if latest else None

    flags = []
    if len(maintainers) < LOW_MAINTAINER_COUNT:
        flags.append('LOW_MAINTAINER_COUNT: %d listed on npm (%s)' % (
            len(maintainers), ', '.join(m.get('name', '?') for m in maintainers) or 'none'))

    repo = meta.get('repository') or {}
    repo_url = repo.get('url') if isinstance(repo, dict) else repo

    return {
        'name': name,
        'maintainer_count': len(maintainers),
        'maintainers': [m.get('name') for m in maintainers],
        'latest_version': latest,
        'latest_published': latest_published,
        'repository': repo_url,
        'flags': flags,
    }


def main(argv):
    pkg_path = argv[0] if argv else 'package.json'
    try:
        pkg = json.load(open(pkg_path, encoding='utf-8'))
    except Exception as e:                                    # noqa: BLE001
        print('COULD NOT CHECK: cannot read %s (%s). Nothing was checked, '
              'and that is not the same as nothing being wrong.' % (pkg_path, e))
        return 2

    deps = sorted((pkg.get('dependencies') or {}).keys())
    if not deps:
        print('COULD NOT CHECK: %s declares no dependencies. ZERO TARGETS IS '
              'NOT A CLEAN SWEEP -- confirm that is actually true rather than '
              'a parsing miss.' % pkg_path)
        return 2

    print('DEPENDENCY HEALTH -- bus-factor / maintainer-health scan, motivated by CVE-2024-3094')
    print('  package.json : %s' % pkg_path)
    print('  dependencies : %d declared (direct only; this does not walk transitive deps)' % len(deps))
    print()

    results = []
    could_not = []
    for name in deps:
        r = analyse_package(name)
        results.append(r)
        if r.get('could_not_check'):
            could_not.append(r)

    for r in results:
        if r.get('could_not_check'):
            print('  ? %-30s COULD NOT CHECK -- %s' % (r['name'], r['could_not_check']))
            continue
        flag_str = '; '.join(r['flags']) if r['flags'] else 'no flags'
        marker = '!' if r['flags'] else ' '
        print('  %s %-30s maintainers=%d  latest=%s (%s)  %s' % (
            marker, r['name'], r['maintainer_count'], r['latest_version'],
            (r['latest_published'] or 'unknown')[:10], flag_str))

    print()
    flagged = [r for r in results if r.get('flags')]
    print('  %d of %d dependencies flagged for low maintainer count (< %d).' % (
        len(flagged), len(results), LOW_MAINTAINER_COUNT))
    print('  WHAT THIS DOES NOT CHECK: transitive dependencies (a direct dep')
    print('  with many maintainers can still pull in a fragile one two levels')
    print('  down), commit-activity/contributor-count on the actual source repo')
    print('  (only npm registry maintainer metadata is read here), and Python')
    print('  dependencies (no requirements.txt exists in this repo today).')
    print()
    print('  A SINGLE FLAG DOES NOT MEAN A SINGLE PERSON. npm "maintainers" is')
    print('  PUBLISH-ACCESS accounts, not headcount -- a corporate publisher')
    print('  (e.g. a company shipping under one service account) reads')
    print('  identically here to an independent solo maintainer, and those are')
    print('  very different bus-factor situations. Read a LOW_MAINTAINER_COUNT')
    print('  flag as "worth a human look," not as "this is the xz situation."')

    if could_not:
        print()
        print('COULD NOT CHECK (%d) -- this is NOT folded into the clean count above:' % len(could_not))
        for r in could_not:
            print('  ? %s: %s' % (r['name'], r['could_not_check']))
        return 2

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

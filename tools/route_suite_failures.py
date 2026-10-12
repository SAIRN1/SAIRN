#!/usr/bin/env python
# OWNER: cody
"""Route a triaged suite-failure population to an owning APP and, only where a
declaration exists, an owning AGENT.

    python tools/route_suite_failures.py                      # report, writes nothing
    python tools/route_suite_failures.py --out <dir>           # + tsv/json/markdown
    python tools/route_suite_failures.py --triage <path.tsv>   # another triage run
    python tools/route_suite_failures.py --fixtures            # criteria lock alone

Exit 0 on a derivation that completed, 2 COULD NOT RUN. REPORT ONLY -- it never
edits the repo, and a BARE RUN WRITES NOTHING AT ALL: output files are produced
only under an explicit --out.

── WHY THE APP, AND NOT AN AGENT ────────────────────────────────────────────
Built for batch 27 item 1 (cody), carrying over the method H1 arrived at in
`.claude/skills/sairn-hover-auditor/routing/2026-10-08-routed-field-findings.md`
for the same problem one population earlier. Its finding, re-checked here and
still true: THIS PLATFORM HAS NO DURABLE PER-AGENT APP ASSIGNMENT. Naming a
build agent as a row's owner without a declaration behind it is a fabricated
claim wearing the word "proposed". What IS derivable is the SAIRN app, and the
app is the unit the claim system already routes on.

So: the app column is derived, an agent is named only from a declaration, and
where neither resolves the tool says which of the two it could not do rather
than picking one.

── THE APP IS DERIVED FROM THE REGISTRY, NOT FROM A NAME PREFIX ─────────────
`api/_resources/index.js` is loaded through node and asked for
OWNER_BY_RESOURCE and APP_NAMES. That is a structurally different route to the
same map than the auditor's own `resource_app_map()` -- independence by
different method (cross-domain discipline 6) -- and it keeps a build agent out
of the auditor's clone, which is a boundary, not a preference.

NODE IS A HARD DEPENDENCY AND ITS ABSENCE IS EXIT 2, NEVER A SKIPPED COLUMN.
Without the registry there is no derived app column, and a routing table whose
app column silently became "PLATFORM for everything" would report a population
of platform probes that was never measured. CLAUDE.md's rule, stated for
exactly this: "could not run" is a third state and is never folded into
"passed".

── THE GENERIC-NAME TRAP, WHICH THIS TOOL WAS CAUGHT BY FIRST ───────────────
13 of the registry's ~398 resource names carry no app prefix and are ordinary
English words -- customers, employees, invoices, jobs, locations, memory,
profile, properties, quotes, remnants, schedule, slabs, subcontractors. Matched
on a word boundary they route platform probes to apps on the strength of a word
in a comment: the first version of this tool sent
`tests/hover_separation_ci_probe.py` to sairngrounds because "quotes" appears
in its prose, and `tests/run_dependency_graph_probe.py` to sairnscape because
"schedule" does. A quoted-literal-only rule still caught
`tests/run_cron_liveness_probe.py`, whose 'jobs' and 'schedule' are GitHub
Actions YAML keys.

GENERIC NAMES ARE THEREFORE NOT EVIDENCE AT ALL, and the prefixed/generic split
is read off the registry (`"_" in name`) rather than typed into an exclusion
list that the next registered resource would silently fall outside of. The
FIXTURES below pin that in both directions, and they run on the DEFAULT PATH
and print beside the real result -- a criteria lock that only runs under a flag
is a control with a shorter name.

── WHAT IT CANNOT SEE, said here rather than discovered later ───────────────
  * WHETHER A ROW'S FAILURE IS THE APP'S FAULT. The app column says which app's
    resources a suite exercises. A suite over sairncare resources can fail for a
    reason that lives entirely in shared tooling.
  * WHETHER AN "UNOWNED" FILE REALLY HAS NO AUTHOR. UNOWNED means neither the
    owner map nor any claim FILES list names the path. It is a gap in the
    record.
  * STRENGTH OF A MAP OWNER. It prints the map's own `basis` and does not rank
    it; `docs/tool-owner-map.json`'s `_basis_vocabulary` is where
    CLAIM_SUBJECT_ONLY is declared weaker than LAST_CLAIM, and this tool repeats
    that label rather than quietly treating the two alike.
"""
import argparse
import collections
import csv
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# Resource names with no app-distinguishing prefix. NOT a hand-written list --
# it is computed as `"_" not in name` over the live registry. Named in the
# docstring for the reader; never hardcoded.


def die(msg):
    sys.stdout.write("COULD NOT RUN: %s\n" % msg)
    sys.stdout.write("Nothing was derived. That is not a clean run and not an empty one.\n")
    sys.exit(2)


# ── the registry, through node ──────────────────────────────────────────────
_NODE_SNIPPET = (
    "const m=require(process.argv[1]);"
    "process.stdout.write(JSON.stringify({byResource:m.OWNER_BY_RESOURCE,apps:m.APP_NAMES}));"
)


def load_registry(repo=REPO):
    """resource name -> app, plus the declared app names. Exit 2 if node or the
    registry is unavailable -- never a partial map."""
    idx = os.path.join(repo, "api", "_resources", "index.js")
    if not os.path.isfile(idx):
        die("api/_resources/index.js is not present at %s, so the app column "
            "cannot be derived at all" % idx)
    try:
        p = subprocess.run(["node", "-e", _NODE_SNIPPET, idx],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
    except FileNotFoundError:
        die("`node` is not on PATH. The app column is derived by loading "
            "api/_resources/index.js, and there is no fallback -- a guessed "
            "prefix map is the defect this tool exists to avoid")
    except subprocess.TimeoutExpired:
        die("`node` did not return within 120s loading api/_resources/index.js")
    if p.returncode != 0:
        die("node exited %d loading api/_resources/index.js: %s"
            % (p.returncode, (p.stderr or "").strip()[:400]))
    try:
        d = json.loads(p.stdout)
    except ValueError:
        die("node produced output that is not JSON: %r" % p.stdout[:200])
    if not d.get("byResource"):
        die("api/_resources/index.js loaded but OWNER_BY_RESOURCE is empty")
    return d["byResource"], list(d.get("apps") or [])


class AppDeriver(object):
    """Classifies ONE file path + its source text to an app, or says which kind
    of unresolvable it is. Evidence order, strongest first:

        path-token            an app name appears in the path itself
        prefixed-resource-ref app-prefixed resource names in the file
        generic-only          ONLY unprefixed generic names -> not evidence
        no-app-evidence       nothing -> a platform/tooling probe
    """

    def __init__(self, res_app, apps):
        self.res_app = res_app
        self.app_tokens = {a.lower(): a for a in apps}
        self.prefixed = sorted((n for n in res_app if "_" in n), key=len, reverse=True)
        self.generic = sorted(n for n in res_app if "_" not in n)
        self.pre_re = (re.compile(r"\b(" + "|".join(map(re.escape, self.prefixed)) + r")\b")
                       if self.prefixed else None)
        self.gen_re = (re.compile(r"['\"](" + "|".join(map(re.escape, self.generic)) + r")['\"]")
                       if self.generic else None)

    def _apps_of(self, names):
        d = {}
        for n in names:
            d.setdefault(self.res_app[n], set()).add(n)
        return d

    def classify(self, path, src):
        pre = self._apps_of(set(self.pre_re.findall(src))) if self.pre_re else {}
        gen = self._apps_of(set(self.gen_re.findall(src))) if self.gen_re else {}
        low = path.lower().replace("\\", "/")
        path_apps = sorted({a for t, a in self.app_tokens.items() if t in low})

        if len(path_apps) == 1:
            allapps = sorted(set(pre) | set(gen))
            tot = sum(len(v) for v in pre.values()) + sum(len(v) for v in gen.values())
            return (path_apps[0], "path-token",
                    "path names %s; file references %d resource(s) across %d app(s): %s"
                    % (path_apps[0], tot, len(allapps), ", ".join(allapps) or "none"))
        if len(path_apps) > 1:
            return ("MULTI", "path-token", "path names %s" % ", ".join(path_apps))

        if len(pre) == 1:
            app = next(iter(pre))
            return (app, "prefixed-resource-ref",
                    "%d prefixed resource(s): %s"
                    % (len(pre[app]), ", ".join(sorted(pre[app])[:5])))
        if len(pre) > 1:
            tot = sum(len(v) for v in pre.values())
            return ("MULTI", "prefixed-resource-ref",
                    "%d prefixed resources across %d apps: %s"
                    % (tot, len(pre), ", ".join(sorted(pre))))

        if gen:
            names = sorted(n for v in gen.values() for n in v)
            return ("PLATFORM", "generic-only",
                    "the only registered names quoted here are unprefixed generic "
                    "words (%s) -- not evidence of an app" % ", ".join(names)[:160])

        return ("PLATFORM", "no-app-evidence",
                "the path names no app and the file references no app-prefixed "
                "registered resource -- a platform/tooling probe")

    @staticmethod
    def confidence(app, basis, detail):
        if app in ("PLATFORM", "MULTI", "UNRESOLVED"):
            return "n/a"
        if basis == "path-token":
            return "HIGH"
        m = re.match(r"(\d+) prefixed resource", detail)
        n = int(m.group(1)) if m else 0
        if n >= 3:
            return "HIGH"
        if n == 2:
            return "MODERATE"
        return "LOW -- one resource mention only"


# ── the criteria lock ───────────────────────────────────────────────────────
# Hand-built sources with an expected verdict each, INCLUDING cases the deriver
# must REFUSE to resolve. A synthetic registry, so the lock does not move when
# a resource is registered. The two MUST-NOT-RESOLVE fixtures are the ones that
# matter: they are the real defect this tool shipped and had removed.
_FIX_REG = {
    "alf_mar": "sairncare", "alf_incidents": "sairncare", "alf_op_audits": "sairncare",
    "sf_ledger": "sairnfreedom", "sd_customers": "stonedesk",
    "quotes": "sairngrounds", "schedule": "sairnscape", "jobs": "sairngrounds",
}
_FIX_APPS = ["sairncare", "sairnfreedom", "stonedesk", "sairngrounds", "sairnscape"]
FIXTURES = [
    ("tests/sairncare/test-op-audit.js", "nothing at all here",
     "sairncare", "path-token",
     "the path names an app even with no resource reference"),
    ("tests/probe.py", "checks alf_mar and alf_incidents and alf_op_audits",
     "sairncare", "prefixed-resource-ref",
     "three prefixed resources from one app"),
    ("tests/probe.py", "checks alf_mar and sf_ledger",
     "MULTI", "prefixed-resource-ref",
     "prefixed resources from two apps is MULTI, not the first one seen"),
    ("tests/hover_separation_ci_probe.py", "the panel shows quotes to the user",
     "PLATFORM", "no-app-evidence",
     "MUST NOT RESOLVE: a bare generic word in prose is not a resource "
     "reference. This exact file was mis-routed to sairngrounds"),
    ("tests/run_cron_liveness_probe.py", "steps = wf['jobs']; 'schedule' in trig",
     "PLATFORM", "generic-only",
     "MUST NOT RESOLVE: 'jobs' and 'schedule' as QUOTED literals are still "
     "generic. This exact file was mis-routed to MULTI"),
    ("tests/run_index_duplicate_probe.py", "no resource is named in this file",
     "PLATFORM", "no-app-evidence",
     "a platform probe stays PLATFORM"),
    ("tests/probe.py", "writes sd_customers only",
     "stonedesk", "prefixed-resource-ref",
     "one prefixed resource resolves, and must be reported LOW"),
    ("tests/sairncare/sairnfreedom_thing.js", "x",
     "MULTI", "path-token",
     "two app names in one path is MULTI, not a coin toss"),
]


def run_fixtures():
    """(passed, total, failures). Runs on the DEFAULT PATH and prints beside
    the real result, so a clean line is visibly earned."""
    d = AppDeriver(_FIX_REG, _FIX_APPS)
    fails = []
    for path, src, want_app, want_basis, why in FIXTURES:
        app, basis, _detail = d.classify(path, src)
        if app != want_app or basis != want_basis:
            fails.append("%s -- expected %s/%s, got %s/%s (%s)"
                         % (path, want_app, want_basis, app, basis, why))
    # the confidence ladder, pinned too
    for app, basis, detail, want in (
            ("sairncare", "path-token", "path names sairncare; ...", "HIGH"),
            ("sairncare", "prefixed-resource-ref", "3 prefixed resource(s): a, b, c", "HIGH"),
            ("sairncare", "prefixed-resource-ref", "2 prefixed resource(s): a, b", "MODERATE"),
            ("stonedesk", "prefixed-resource-ref", "1 prefixed resource(s): a",
             "LOW -- one resource mention only"),
            ("PLATFORM", "no-app-evidence", "", "n/a")):
        got = AppDeriver.confidence(app, basis, detail)
        if got != want:
            fails.append("confidence(%s,%s) expected %s, got %s" % (app, basis, want, got))
    total = len(FIXTURES) + 5
    return total - len(fails), total, fails


# ── agent-owner evidence ───────────────────────────────────────────────────
def load_owner_map(repo=REPO):
    p = os.path.join(repo, "docs", "tool-owner-map.json")
    if not os.path.isfile(p):
        die("docs/tool-owner-map.json is absent, so no owner can be derived "
            "from the map half of the evidence")
    d = json.load(open(p, encoding="utf-8"))
    return d.get("tools") or {}, d.get("_meta") or {}


def load_claim_files(repo=REPO):
    """path -> (all sessions that ever declared it, sessions holding it ACTIVE).

    Every claim record is walked INDIVIDUALLY. A single regex over the whole
    file finds one `FILES:` list and silently drops the other ~300, which is
    the shape that made the first run of this derivation disagree with hank's
    for reasons that had nothing to do with either method.
    """
    d = os.path.join(repo, ".claude", "claims")
    if not os.path.isdir(d):
        die(".claude/claims is absent, so the claim half of the evidence "
            "cannot be read")
    ever, active = {}, {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        sess = fn[:-5]
        try:
            rec = json.load(open(os.path.join(d, fn), encoding="utf-8"))
        except ValueError:
            continue
        for c in rec.get("claims") or []:
            m = re.search(r"FILES:\s*(.*)", c.get("task") or "")
            if not m:
                continue
            for tok in re.split(r"[\s,]+", m.group(1)):
                tok = tok.strip().strip('"').strip("`")
                if not tok:
                    continue
                if "/" not in tok and not tok.endswith((".py", ".js", ".json", ".md", ".txt")):
                    continue
                ever.setdefault(tok, set()).add(sess)
                if c.get("status") == "active":
                    active.setdefault(tok, set()).add(sess)
    return ever, active


def derive_owner(path, om_tools, claim_ever, claim_active):
    """Owner from the two DECLARATION-GRADE sources only. An active-work mention
    is deliberately not one of them -- see mentions_in_active_work()."""
    ev, owner = [], None
    e = om_tools.get(path)
    if e and e.get("owner"):
        owner = e["owner"]
        basis = e.get("basis", "?")
        also = e.get("also_claimed_by") or []
        ev.append("map(%s%s)" % (basis, (", also " + "+".join(also)) if also else ""))
        if basis == "CONTESTED" and also:
            owner = owner + "+" + "+".join(also) + " (CONTESTED)"
    if path in claim_ever:
        act = sorted(claim_active.get(path, ()))
        hist = sorted(s for s in claim_ever[path] if s not in act)
        bits = []
        if act:
            bits.append("ACTIVE " + "+".join(act))
        if hist:
            bits.append("historical " + "+".join(hist))
        ev.append("claimFILES(%s)" % "; ".join(bits))
        if not owner:
            owner = "+".join(act or hist)
    if not owner:
        return "UNOWNED", "no map entry and no claim FILES declaration"
    return owner, "; ".join(ev)


def load_active_work(repo=REPO):
    out = {}
    for f in sorted(os.listdir(repo)):
        if f.startswith("SAIRN-ACTIVE-WORK-") and f.endswith(".md"):
            key = f[len("SAIRN-ACTIVE-WORK-"):-len(".md")]
            out[key] = open(os.path.join(repo, f), encoding="utf-8", errors="replace").read()
    return out


def mentions_in_active_work(path, aw):
    """A WEAKER signal, returned separately and never promoted to an owner. H1
    used this grep as a NEGATIVE check -- zero matches meant nobody had picked
    a finding up. A path appearing somewhere inside a 1MB standing document is
    not a declaration of scope."""
    return sorted(k for k, text in aw.items() if path in text)


# ── main ───────────────────────────────────────────────────────────────────
def build(triage, repo=REPO):
    res_app, apps = load_registry(repo)
    deriver = AppDeriver(res_app, apps)
    om_tools, om_meta = load_owner_map(repo)
    claim_ever, claim_active = load_claim_files(repo)
    aw = load_active_work(repo)

    if not os.path.isfile(triage):
        die("triage file %s not found" % triage)
    rows = []
    with open(triage, encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f, delimiter="\t")
        if not rdr.fieldnames or "verdict" not in rdr.fieldnames or "test" not in rdr.fieldnames:
            die("%s has no `verdict`/`test` columns -- this is not a triage TSV"
                % triage)
        for r in rdr:
            if r.get("verdict") == "REAL":
                rows.append(r)
    if not rows:
        die("%s holds zero REAL rows. An empty population is reported as COULD "
            "NOT RUN rather than as a clean routing table" % triage)

    out = []
    for r in rows:
        path = r["test"]
        full = os.path.join(repo, path.replace("/", os.sep))
        if os.path.isfile(full):
            src = open(full, encoding="utf-8", errors="replace").read()
            app, basis, detail = deriver.classify(path, src)
        else:
            app, basis, detail = ("UNRESOLVED", "file-absent",
                                  "path is not on disk at this HEAD")
        owner, obasis = derive_owner(path, om_tools, claim_ever, claim_active)
        mentions = mentions_in_active_work(path, aw)
        if owner != "UNOWNED":
            route = owner
        elif app not in ("PLATFORM", "MULTI", "UNRESOLVED"):
            route = "next claim on %s" % app
        elif app == "PLATFORM":
            route = "next claim on platform tooling"
        else:
            route = "next claim naming this path"
        out.append(dict(
            suite=path, kind=r.get("kind", ""), rc=r.get("rc", ""),
            seconds=r.get("seconds", ""),
            app=app, app_basis=basis,
            app_confidence=AppDeriver.confidence(app, basis, detail),
            app_detail=detail,
            owner=owner, owner_basis=obasis,
            mentioned_in_active_work=("+".join(mentions) if mentions else "none"),
            route_to=route, suite_reason=r.get("suite_reason", ""),
        ))
    return out, om_meta, res_app, apps


def hank_owners(repo=REPO):
    """Hank's independent derivation of the same question, for an agreement
    number. Only the `### <owner> -- N REAL` region counts: a level-2 heading
    resets, because without that the last owner section stayed in scope across
    the CASCADE and TIMEOUT tables and credited their rows to it."""
    p = os.path.join(repo, "docs", "2026-10-08-hank-suite-failure-owners.md")
    if not os.path.isfile(p):
        return None
    cur, d = None, {}
    for line in open(p, encoding="utf-8"):
        if line.startswith("## "):
            cur = None
            continue
        m = re.match(r"###\s+(.+?)\s+(?:--|\u2014)\s*\d+\s+REAL", line)
        if m:
            cur = m.group(1).strip().strip("*`")
            continue
        if cur and line.startswith("| `"):
            parts = line.split("|")
            if len(parts) > 2:
                d[parts[1].strip().strip("`")] = cur
    return d


def md_cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def write_outputs(out, outdir):
    os.makedirs(outdir, exist_ok=True)
    tsv = os.path.join(outdir, "suite-failure-routing.tsv")
    with open(tsv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, delimiter="\t", fieldnames=list(out[0]))
        w.writeheader()
        for o in out:
            w.writerow(o)
    md = os.path.join(outdir, "suite-failure-routing.body.md")
    byapp = {}
    for o in out:
        byapp.setdefault(o["app"], []).append(o)
    order = ([a for a in sorted(byapp) if a not in ("PLATFORM", "MULTI", "UNRESOLVED")]
             + [a for a in ("MULTI", "PLATFORM", "UNRESOLVED") if a in byapp])
    n = len(out)
    with open(md, "w", encoding="utf-8", newline="\n") as f:
        for app in order:
            grp = sorted(byapp[app], key=lambda o: o["suite"])
            f.write("### %s -- %d of %d\n\n" % (app, len(grp), n))
            f.write("| suite | kind | rc | app basis / confidence | owner (declared) "
                    "| owner basis | mentioned in active-work | route to |\n")
            f.write("|---|---|---:|---|---|---|---|---|\n")
            for o in grp:
                f.write("| `%s` | %s | %s | %s / %s | %s | %s | %s | %s |\n" % (
                    md_cell(o["suite"]), o["kind"], o["rc"],
                    md_cell(o["app_basis"]), md_cell(o["app_confidence"]),
                    ("**%s**" % o["owner"]) if o["owner"] != "UNOWNED" else "UNOWNED",
                    md_cell(o["owner_basis"]), md_cell(o["mentioned_in_active_work"]),
                    md_cell(o["route_to"])))
            f.write("\n")
    js = os.path.join(outdir, "suite-failure-routing.json")
    json.dump(out, open(js, "w", encoding="utf-8"), indent=1)
    return tsv, md, js


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--triage", default=os.path.join(
        REPO, "docs", "2026-10-08-cody-suite-86-triage.tsv"))
    ap.add_argument("--out", default=None,
                    help="directory for the tsv/json/markdown. WITHOUT IT NOTHING "
                         "IS WRITTEN -- a bare run is a report")
    ap.add_argument("--fixtures", action="store_true",
                    help="run the criteria lock alone and stop")
    a = ap.parse_args(argv)

    passed, total, fails = run_fixtures()
    print("criteria lock: %d/%d fixtures classify correctly, on hand-built "
          "sources only" % (passed, total))
    for msg in fails:
        print("  LOCK FAILURE: %s" % msg)
    if fails:
        die("the criteria lock does not hold, so no routing verdict below would "
            "mean anything")
    if a.fixtures:
        return 0

    out, om_meta, res_app, apps = build(a.triage)
    print("registry: %d resources, %d declared app name(s), %d owning at least one"
          % (len(res_app), len(apps), len(set(res_app.values()))))
    print("owner map: criteria %s, %s tool entries"
          % (om_meta.get("criteria"), om_meta.get("tools")))
    print("triage: %s -- %d REAL row(s)" % (a.triage, len(out)))

    print("\nBY APP (derived)")
    for k, v in sorted(collections.Counter(o["app"] for o in out).items(),
                       key=lambda kv: (kv[0] in ("MULTI", "PLATFORM", "UNRESOLVED"), -kv[1], kv[0])):
        g = [o for o in out if o["app"] == k]
        own = sum(1 for o in g if o["owner"] != "UNOWNED")
        print("  %-14s %3d   owner declared %2d   UNOWNED %2d" % (k, v, own, v - own))

    print("\nBY DECLARED OWNER")
    for k, v in collections.Counter(o["owner"] for o in out).most_common():
        print("  %-24s %3d" % (k, v))

    print("\nAPP CONFIDENCE")
    for k, v in collections.Counter(o["app_confidence"] for o in out).most_common():
        print("  %-34s %3d" % (k, v))

    un = [o for o in out if o["owner"] == "UNOWNED"]
    men = sum(1 for o in un if o["mentioned_in_active_work"] != "none")
    print("\nUNOWNED: %d of %d. Mentioned in some active-work file: %d; "
          "mentioned nowhere: %d" % (len(un), len(out), men, len(un) - men))

    h = hank_owners()
    if h is None:
        print("\nHANK CROSS-CHECK: docs/2026-10-08-hank-suite-failure-owners.md "
              "is absent -- NOT RUN, which is not agreement")
    else:
        both = agree = 0
        differ = []
        for o in out:
            ho = h.get(o["suite"])
            if ho is None:
                continue
            both += 1
            if set(o["owner"].split("+")) == set(ho.split("+")):
                agree += 1
            else:
                differ.append((o["suite"], o["owner"], ho))
        print("\nHANK CROSS-CHECK (independent derivation, a different suite run)")
        print("  in both tables %d, agree %d, differ %d" % (both, agree, len(differ)))
        for s, mine, theirs in differ:
            print("    %s: here=%s hank=%s" % (s, mine, theirs))

    if a.out:
        tsv, md, js = write_outputs(out, a.out)
        print("\nwrote %s\nwrote %s\nwrote %s" % (tsv, md, js))
    else:
        print("\nNo --out given, so NOTHING WAS WRITTEN. This is a report.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

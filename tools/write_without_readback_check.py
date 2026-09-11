"""Every resource an app WRITES to the server should also be READ back.

WHY THIS EXISTS. Twice on 2026-09-04/05 an app was found writing real business
records to Postgres and never reading any of them back, so the data was on the
server and unreachable: a second workstation, or the same one after a browser
data clear, opened an empty app.

  SAIRNbiz   -- 17 localStorage collections, ONE reached a server.
  SAIRNlaw   -- 20 resources written across 31 call sites, exactly one read
                (shared_knowledge). No hydrate function of any name existed.

Both were invisible for months. Neither was found by a tool; the first came
from reading an index row and the second from a hunch while closing it. This is
the tool, so the third one is found by a machine.

IT CATCHES ONE OF THOSE TWO, AND THE MEASUREMENT SAID SO RATHER THAN THE
INTENTION. Run against sairnlaw.html at the commit before its hydrate landed it
exits 1 and names all nineteen. Run against sairnbiz.html at the commit before
ITS backup landed it says nothing at all -- correctly, by its own rules, and
uselessly: SAIRNbiz was not writing to a server through a wrapper, it was
writing to localStorage and stopping. "Written to the server and never read
back" and "never written to the server at all" are different defects, and this
one only sees the first. The second needs a different check, comparing an app's
localStorage collections against the resources it registers; that is not built
and is not implied here.

It also catches the narrower shape that hid the SAIRNlaw case in plain sight: a
resource written by the client but never registered, which fails at the
allowlist on every save. A name written and neither read nor registered is the
loudest signal this can produce.

-- WHAT IT DOES --------------------------------------------------------------
Per app HTML file, it collects the resource names passed to a data wrapper as
'write' and as 'read', resolves the common LOOP shapes so a generic hydrate
counts as reading everything it iterates, and reports write names with no read.

-- WHAT IT CANNOT SEE, said here rather than discovered later ------------------
  * A write whose resource is a VARIABLE. Every current app passes a literal,
    but a future one need not, and such a write is invisible here.
  * A wrapper whose name does not end in `Data(` AND is not called with an
    object literal carrying action/resource. Those two shapes are what the
    platform uses; a third would be invisible, and the SCANNED-BY-NAME line on
    every run says so, so an absence is not read as a pass.
  * A read loop built from anything other than a flat array of strings, an
    array of pairs, or Object.keys(<object literal>). Anything else resolves
    to COULD NOT TELL for that file, which is NOT a pass -- the exit code says
    so.
  * A binding more than the hops listed in _is_actually_read(). Each hop is a
    place to be wrong; a fourth would be guessing rather than following.

-- WIDENED 2026-09-05, IN BOTH DIRECTIONS AT ONCE -----------------------------
It reported COULD NOT TELL for the two largest apps, and the row said to READ
those loops rather than loosen anything. Both were read: SAIRNbuild drives its
write guard and its hydrate off ONE list; StoneDesk's lineage writer is a
one-hop function whose three call sites match its read loop exactly. Both are
now resolved from that evidence.

THE PART WORTH KEEPING IS WHAT HAPPENED IN BETWEEN. Making generic WRITES
visible immediately produced ten "written and never read back" findings across
SAIRNbiz and StoneDesk -- every one FALSE. They are read through wrappers this
file cannot see by name (`sbBackupFetch('read', key)`, `pcRead(resource)`).
Widening one side of a comparison manufactures accusations, so the read side
was widened in the same change, and two negative controls now pin the traps
that created: a write-guard list must not count as a read set merely because
it overlaps the write set it defines, and a callback body must be brace-matched
rather than sliced, or it swallows an unrelated loop's read of a variable that
happens to share a name.
  * Whether the read is ever CALLED. A hydrate that exists and is never invoked
    reads clean here. tools/sairn_reachability_check.py is the tool for that
    question, and this one says so rather than implying coverage it lacks.

FIRST RUN, MEASURED RATHER THAN ASSUMED: proven to go RED on sairnlaw.html at
the commit before its hydrate landed, and clean on it afterwards. A checker
that has only ever returned clean is a checker whose behaviour nobody knows.
"""
import os
import re
import sys

# Resources that are shared platform infrastructure rather than an app's own
# record set. They are written without a matching per-app read by design --
# shared_knowledge is a write-only topic sink, memory/profile are read through
# their own bespoke paths. Listing them by name, not by prefix: a silent
# category exclusion is how a real resource hides.
PLATFORM_RESOURCES = {
    'shared_knowledge', 'memory', 'profile', 'employees', 'render_usage',
    'employee_profile', 'style_profile', 'exec_context', 'supplier_lead_times',
}

WRITE_RE = re.compile(r"\w*Data\(\s*'write'\s*,\s*'(\w+)'")
# A GENERIC WRITE IS AS INVISIBLE AS A GENERIC READ, and that blind spot is
# what produced both COULD NOT TELL results on 2026-09-05. Resolved 2026-09-05
# after reading both loops by hand -- see resolve_generic_writes().
WRITE_VAR_RE = re.compile(r"\w*Data\(\s*'write'\s*,\s*([A-Za-z_$][\w$]*)\s*,")
READ_LIT_RE = re.compile(r"\w*Data\(\s*'read'\s*,\s*'(\w+)'")
READ_VAR_RE = re.compile(r"\w*Data\(\s*'read'\s*,\s*([A-Za-z_$][\w$]*)")
WRAPPER_RE = re.compile(r"function\s+(\w*Data)\s*\(")

# THE OBJECT-LITERAL CALL SHAPE, ADDED 2026-09-05 AFTER IT PRODUCED TWO FALSE
# POSITIVES ON ITS FIRST REAL RUN. SAIRNcare does not call a positional
# wrapper; it posts a body:
#
#   alfPostRaw({ action: 'read', resource: 'alf_op_audits', app_id: ..., ... })
#
# so alf_op_audits and alf_staff_credentials were reported as never read back
# when both are read on every panel refresh. Matching only the positional shape
# is how a checker invents work.
#
# WORSE, AND THE PART WORTH REMEMBERING: the "hand verification" that confirmed
# those two findings used the SAME positional grep as the tool, so it
# reproduced the tool's blind spot instead of testing it. A check that shares
# the checker's assumption verifies nothing.
READ_OBJ_RE = re.compile(r"action:\s*'read'\s*,\s*resource:\s*'(\w+)'")
WRITE_OBJ_RE = re.compile(r"action:\s*'write'\s*,\s*resource:\s*'(\w+)'")


def strip_comments(src):
    """Line comments only. Enough for this: every call site is code, and a
    commented-out example must not count as coverage."""
    return '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))


def _literal_body(src, name, opener, closer):
    """The text of the array/object literal assigned to `name`, or None."""
    m = re.search(r'\b(?:var|let|const)\s+' + re.escape(name) + r'\s*=\s*' + re.escape(opener), src)
    if not m:
        return None
    start = src.index(opener, m.start())
    depth = 0
    for i in range(start, min(len(src), start + 40000)):
        if src[i] == opener:
            depth += 1
        elif src[i] == closer:
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    return None


def _function_body(src, params_start):
    """Body of the function whose parameter list is open at `params_start`.

    `params_start` is an index INSIDE the parameter list (the callers' regexes
    end just after the first parameter's comma), so the depth starts at 1.
    Returns None rather than guessing if the parens do not close or no brace
    follows them -- an unresolvable shape must stay invisible, which costs a
    missed write, not an invented one.
    """
    depth, i = 1, params_start
    while i < len(src) and depth:
        if src[i] == '(':
            depth += 1
        elif src[i] == ')':
            depth -= 1
        i += 1
    if depth:
        return None
    j = src.find('{', i)
    if j < 0 or j - i > 200:
        return None
    return _callback_body(src, j + 1)


def resolve_generic_writes(src):
    """Resource names a GENERIC write loop provably covers.

    ADDED 2026-09-05, after this checker reported COULD NOT TELL for the two
    largest apps and the row told the next session to READ the loops rather
    than loosen anything. Both were read by hand first; these two resolvers
    encode what the reading found, and nothing wider.

    The blind spot was symmetric and that is why it was confusing: a generic
    READ was already reported honestly, but a generic WRITE was simply not
    seen, so the app's write set was whatever literals happened to remain --
    and then the real read list looked like an unrelated constant, because it
    overlapped a write set that was missing 30 of its 32 names.

    ── SHAPE A: the write is GUARDED BY MEMBERSHIP IN A DECLARED LIST ────────
    SAIRNbuild hooks st() and pushes only keys it is told to sync:

        var BLD_SYNCED = ['bld_jobs', ...];
        var _bldSyncOn = {};
        BLD_SYNCED.forEach(function(k){ _bldSyncOn[k] = true; });
        function bldSyncCollection(key, ...) {
          if (!_bldSyncOn[key] || bldSeeding) return;
          ... bldData('write', key, r) ...
        }

    The guard IS the write set, and the same constant drives bldHydrateAll()'s
    read. One list on both sides is the strongest coverage evidence there is --
    stronger than the name overlap this file already relies on elsewhere.

    ── SHAPE B: the generic writer is a FUNCTION whose callers pass literals ─
    StoneDesk's lineage sync:

        async function sdLineageSyncOne(resource, rec) { ... sdData('write', resource, rec) ... }
        sdLineageSyncOne('sd_slab_history', rec);   // and sd_blocks, sd_bundles

    Following one hop to the call sites is not dataflow analysis; the argument
    is a literal at every site or this returns nothing for it.

    WHAT THIS DELIBERATELY DOES NOT DO: it does not guess. A generic write it
    cannot resolve is still invisible, which leaves the app's write set short
    and can only ever produce a COULD NOT TELL or a false clean on the READ
    side -- never a false accusation. The names it resolves are printed, the
    same disclosure the read sets already carry, so a wrong resolution is
    visible rather than implied.
    """
    resolved = set()
    # Shape A -- a membership guard built from a declared list.
    for gm in re.finditer(r'\b(\w+)\.forEach\(\s*function\s*\(\s*(\w+)\s*\)\s*\{\s*'
                          r'(\w+)\s*\[\s*\2\s*\]\s*=\s*true', src):
        list_name, guard = gm.group(1), gm.group(3)
        # A GATE CAN BE POSITIVE (2026-09-09). This required `!MAP[`, which is
        # SAIRNbuild's shape (`if (!_bldSyncOn[key]) return;`). StoneDesk gates
        # the same list the other way round --
        #   var synced = (typeof SD_SYNCED_ON !== 'undefined') && SD_SYNCED_ON[key];
        #   if (synced) { sdSyncCollection(key, data, prev); }
        # -- so SD_SYNCED, the real 21-name write set of the platform's largest
        # app, was skipped entirely, and two of its names (sd_email_threats,
        # sd_templates) appear nowhere else in the file. The question the `!`
        # was standing in for is whether the map is CONSULTED at all, so ask
        # that directly: more than one `MAP[` means somewhere other than the
        # `MAP[k] = true` that built it. A map nothing reads still fails.
        if len(re.findall(re.escape(guard) + r'\s*\[', src)) < 2:
            continue                      # the map exists but nothing gates on it
        body = _literal_body(src, list_name, '[', ']')
        if body:
            resolved |= set(re.findall(r"'(\w+)'", body))
    # Shape B -- one hop to a generic writer's call sites.
    for fm in re.finditer(r'\b(?:async\s+)?function\s+(\w+)\s*\(\s*(\w+)\s*,', src):
        fn, param = fm.group(1), fm.group(2)
        # A FIXED-SIZE WINDOW IS NOT A BODY -- the same lesson _callback_body()
        # already carries for the READ side, and it was live on the WRITE side
        # the whole time. A 4,000-character slice from `function st(key,data)`
        # runs 1,708 characters past the end of st() into its NEIGHBOUR
        # sdSyncCollection(key,...), which does contain `sdData('write',key,r)`.
        # Every parameter is named `key`, so st() was accepted as a generic
        # writer and all 68 of its `st('literal', ...)` call sites -- i.e. every
        # localStorage write in stonedesk.html -- were counted as server writes.
        # stRaw() was caught the same way at 1,257 characters, and stRaw() is
        # `localStorage.setItem` and nothing else: it has no server path at all.
        # That produced 50 "written and never read back" findings against the
        # flagship app, EVERY ONE FALSE -- against this function's own docstring
        # promise that it "can only ever produce a COULD NOT TELL or a false
        # clean on the READ side -- never a false accusation."
        body = _function_body(src, fm.end())
        if body is None:
            continue
        if not re.search(r"\w*Data\(\s*'write'\s*,\s*" + re.escape(param) + r'\s*,', body):
            continue
        for cm in re.finditer(r'(?<![\w$.])' + re.escape(fn) + r"\(\s*'(\w+)'\s*,", src):
            resolved.add(cm.group(1))
    return resolved


def resolve_generic_reads(src):
    """Resource names a GENERIC read provably covers, by the same two shapes.

    ADDED 2026-09-05, IN THE SAME PASS AND FOR A REASON WORTH RECORDING. The
    write resolver above made three apps' real write sets visible for the first
    time, and the moment it did, this checker reported 10 resources as "written
    and never read back" across SAIRNbiz and StoneDesk. Every one was FALSE.
    They are all read -- through wrappers this file could not see, because it
    identifies a data call by the NAME pattern `\\w*Data(`:

        sbBackupFetch('read', key, null)      // SAIRNbiz, posts to DATA_API itself
        pcRead('sd_quote_requests')           // StoneDesk, forwards to sdData

    The tool's header already disclosed the name assumption. What it did not
    say is that the assumption was load-bearing for the RESULT, not just the
    coverage: making writes visible without making these reads visible would
    have shipped nine invented findings about a business's AP, budgets,
    payroll and invoices. **A resolver that only widens one side of a
    comparison manufactures accusations.** Both sides moved in the same commit.

    Two shapes, mirroring the write side:
      * a forwarder -- `function pcRead(resource){ ... sdData('read', resource ...) }`
        -- resolved one hop to its call sites' literals;
      * a declared list iterated with `.map(function(key){ ... 'read' ... key ... })`,
        which is how every hydrate-all in this platform is written.

    Unresolvable stays unresolvable and still reports COULD NOT TELL.
    """
    names = set()
    # Shape B-mirror: a one-hop forwarder whose parameter becomes the resource.
    for fm in re.finditer(r'\b(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', src):
        fn, params = fm.group(1), [p.strip() for p in fm.group(2).split(',') if p.strip()]
        if not params:
            continue
        tail = src[fm.end():fm.end() + 1200]
        for idx, p in enumerate(params):
            if re.search(r"\w*Data\(\s*'read'\s*,\s*" + re.escape(p) + r'\b', tail):
                for cm in re.finditer(r'(?<![\w$.])' + re.escape(fn) + r'\(([^)]*)\)', src):
                    args = [a.strip() for a in cm.group(1).split(',')]
                    if idx < len(args):
                        lit = re.fullmatch(r"'(\w+)'", args[idx])
                        if lit:
                            names.add(lit.group(1))
                break
    # Shape A-mirror: a declared list mapped over, with a read inside the body.
    for mm in re.finditer(r'\b(\w+)\.map\(\s*function\s*\(\s*(\w+)\s*\)\s*\{', src):
        list_name, var = mm.group(1), mm.group(2)
        body = src[mm.end():mm.end() + 1500]
        if not re.search(r"'read'\s*,\s*" + re.escape(var) + r'\b', body):
            continue
        lit = _literal_body(src, list_name, '[', ']')
        if lit:
            names |= set(re.findall(r"'(\w+)'", lit))
    return names


def declared_read_sets(src, writes):
    """Resource lists the app declares for a generic read loop.

    THE VARIABLE AT A READ CALL SITE IS ALMOST ALWAYS A FUNCTION PARAMETER --
    `LEG_SYNC_RESOURCES.map(function (key) { return sdnData('read', key); })`,
    or a for-loop index into a list of pairs, or a second hop through a helper
    like scSyncOneResource(resource). Following that properly needs dataflow
    this does not have, and guessing at it would be worse than saying so.

    So it works from the other end: any array or object literal whose entries
    OVERLAP THE APP'S OWN WRITE SET by at least two names is treated as a
    declared read set. The overlap requirement is what keeps an unrelated
    constant list out -- a list of colours or panel ids shares nothing with the
    resources this app writes.

    NAME CASE IS NOT PART OF THE TEST, and that was measured rather than
    assumed. An earlier version required SCREAMING_CASE and reported all 30 of
    SAIRNgrounds' resources as never read back -- a false positive, because
    grdSyncFromServer() builds its list in a local `var resources=[[...]]`
    inside the function. A checker that cries wolf on a whole app is worse than
    none.

    THE RESIDUAL RISK, in the direction that matters: a list that is NOT a read
    set but happens to contain two or more of the app's resource names would be
    counted as coverage that does not exist. That is why the set NAMES are
    printed on every run -- so a wrong resolution is visible rather than
    implied.

    Returns (names, sets_found).
    """
    names, found = set(), []
    for m in re.finditer(r'\b(?:var|let|const)\s+(\w+)\s*=\s*([\[{])', src):
        var, opener = m.group(1), m.group(2)
        body = _literal_body(src, var, opener, ']' if opener == '[' else '}')
        if not body:
            continue
        if opener == '[':
            entries = set(re.findall(r"'(\w+)'", body))
            pairs = re.findall(r"\[\s*'(\w+)'\s*,\s*'\w+'\s*\]", body)
            if pairs:
                entries = set(pairs)
        else:
            entries = set(re.findall(r"[{,]\s*'?(\w+)'?\s*:", body))
        overlap = entries & writes
        if len(overlap) >= 2 and _is_actually_read(src, var):
            names |= overlap
            found.append(var)
    return names, found


def _callback_body(src, start):
    """The text of a callback body that begins just after its opening brace.

    A FIXED-SIZE WINDOW IS NOT A BODY, and a negative control proved it: a
    1,500-character slice after `LIST.forEach(function(k){ _on[k]=true; })`
    ran straight past the callback and swallowed an UNRELATED loop's
    `apData('read', k)` further down the file, so a write-guard was accepted as
    a read set. Brace-matching is the difference between reading a body and
    reading whatever happens to be nearby.
    """
    depth = 1
    for i in range(start, min(len(src), start + 20000)):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return src[start:i]
    return src[start:start + 20000]


def _is_actually_read(src, var):
    """Is this list DEMONSTRABLY the thing a generic read iterates?

    TIGHTENED 2026-09-05, AND THE TIGHTENING WAS FORCED BY MY OWN CHANGE. The
    overlap-by-two rule above already carried a stated residual risk: "a list
    that is NOT a read set but happens to contain two or more of the app's
    resource names would be counted as coverage that does not exist."

    resolve_generic_writes() made that risk certain rather than residual. The
    Shape-A write guard is BUILT FROM a declared list, so that list now
    overlaps the write set completely, by construction -- every write-side
    constant would have been accepted as a read set and the check would have
    gone permanently green on exactly the apps it was widened to cover. A probe
    fixture caught it: a list that is written and never read came back clean.

    So overlap is no longer sufficient. The list must be seen feeding a read:
    indexed straight into one, or iterated with the loop variable passed as the
    resource. Everything the platform actually writes matches one of those.
    """
    if re.search(r"'read'\s*,\s*" + re.escape(var) + r'\s*\[', src):
        return True
    for m in re.finditer(re.escape(var) + r'\.(?:map|forEach)\(\s*function\s*\(\s*(\w+)\s*\)\s*\{', src):
        v = m.group(1)
        body = _callback_body(src, m.end())
        if re.search(r"'read'\s*,\s*" + re.escape(v) + r'\b', body):
            return True
    # A `for (var i...)` loop that indexes the list inside the read argument
    # itself -- apData('read', resources[i][0]) -- so there is no callback
    # parameter to follow.
    if re.search(r"'read'\s*,\s*" + re.escape(var) + r'\s*\[\s*\w+\s*\]', src):
        return True
    # Everything else goes the other way round: start from the variable that IS
    # the resource argument of a read, and ask whether it was bound from this
    # list. Four bindings cover every app on the platform, and each one was
    # read out of a real file rather than imagined:
    #
    #   var resource = DNT_SYNC_RESOURCES[i][0];        (SAIRNdental)
    #   var res = pairs[i]; ... 'read', res[0]          (StoneDesk)
    #   var resources = Object.keys(SC_RESOURCE_STORAGE_KEYS);  (SAIRNcode)
    #   LIST.map(function (key) { ... 'read', key ... }) (handled above)
    #
    # ALIASES ARE FOLLOWED ONE HOP, not chased. A binding this cannot see keeps
    # the list unresolved, which is the safe direction: it costs a COULD NOT
    # TELL, never a false clean.
    aliases = {var}
    for al in re.finditer(r'\b(?:var|let|const)\s+(\w+)\s*=\s*(?:Object\.keys\(\s*)?' +
                          re.escape(var) + r'\s*\)?\s*;', src):
        aliases.add(al.group(1))
    read_args = set(re.findall(r"'read'\s*,\s*([A-Za-z_$][\w$]*)", src))
    for a in aliases:
        for rv in read_args:
            # var rv = ALIAS[i]  /  ALIAS[i][0]
            if re.search(r'\b(?:var|let|const)\s+' + re.escape(rv) + r'\s*=\s*' +
                         re.escape(a) + r'\s*\[', src):
                return True
            # ALIAS.map/forEach(function (rv) { ... 'read', rv ... })
            #
            # THE READ MUST BE INSIDE THAT BODY. Matching the parameter NAME
            # anywhere was tried and a negative control caught it in minutes: a
            # write-guard built as `LIST.forEach(function(k){_on[k]=true;})`
            # was accepted as a read set because some OTHER list's read loop
            # also happened to call its parameter `k`. Two loops sharing a
            # one-letter variable is not evidence of anything.
            for it in re.finditer(re.escape(a) + r'\.(?:map|forEach)\(\s*function\s*\(\s*' +
                                  re.escape(rv) + r'\s*\)\s*\{', src):
                if re.search(r"'read'\s*,\s*" + re.escape(rv) + r'\b',
                             _callback_body(src, it.end())):
                    return True
        # var res = ALIAS[i]; ... 'read', res[0]
        for am in re.finditer(r'\b(?:var|let|const)\s+(\w+)\s*=\s*' + re.escape(a) +
                              r'\s*\[\s*\w+\s*\]', src):
            if re.search(r"'read'\s*,\s*" + re.escape(am.group(1)) + r'\s*\[', src):
                return True
        # ONE MORE HOP, and the last one: the iteration hands each name to a
        # per-resource function whose parameter is what reaches the read --
        #   resources.map(function (r) { return scSyncOneResource(r); })
        #   async function scSyncOneResource(resource) { ... 'read', resource ... }
        # SAIRNcode is the only app shaped this way, and without this it is a
        # COULD NOT TELL. Stopping here is deliberate: each hop is a place to
        # be wrong, and a fourth would be guessing rather than following.
        for im in re.finditer(re.escape(a) + r'\.(?:map|forEach)\(\s*function\s*\(\s*(\w+)\s*\)\s*\{',
                              src):
            iv = im.group(1)
            body = src[im.end():im.end() + 600]
            for cm in re.finditer(r'(\w+)\(\s*' + re.escape(iv) + r'\s*\)', body):
                callee = cm.group(1)
                fm2 = re.search(r'\b(?:async\s+)?function\s+' + re.escape(callee) +
                                r'\s*\(\s*(\w+)', src)
                if fm2 and re.search(r"'read'\s*,\s*" + re.escape(fm2.group(1)) + r'\b',
                                     src[fm2.end():fm2.end() + 3000]):
                    return True
    return False


def read_coverage(src, writes):
    """(names read, unresolved variable names, declared sets used).

    A variable read whose set cannot be resolved is a REASON, never silent
    coverage -- but the reason is now RAISED BY audit(), not here, because
    whether it matters depends on the answer. Changed 2026-09-05: an
    unresolved generic read alongside FULL coverage is not a could-not-tell,
    it is a question that got answered another way. Reporting it anyway made
    every forwarding wrapper permanently unresolvable even when every write it
    performs is demonstrably read back, which is a check that can never go
    green rather than one that is strict.
    """
    names = (set(READ_LIT_RE.findall(src)) | set(READ_OBJ_RE.findall(src))
             | resolve_generic_reads(src))
    var_reads = set(READ_VAR_RE.findall(src))
    declared, found = declared_read_sets(src, writes)
    unresolved = sorted(var_reads) if var_reads and not declared else []
    if declared:
        names |= declared
    return names, unresolved, found


def audit(path):
    src = strip_comments(open(path, encoding='utf-8', errors='replace').read())
    writes = (set(WRITE_RE.findall(src)) | set(WRITE_OBJ_RE.findall(src))
              | resolve_generic_writes(src)) - PLATFORM_RESOURCES
    if not writes:
        return None
    reads, unresolved, declared = read_coverage(src, writes)
    missing = sorted(writes - reads)
    # COULD NOT TELL only where it is actually true: an unresolved generic read
    # AND something still unaccounted for. With NOTHING missing there is
    # nothing this could not tell -- the question got answered another way,
    # and reporting it anyway made every forwarding wrapper permanently
    # unresolvable even where every write it performs is demonstrably read
    # back. Where something IS missing, BOTH are reported: the names, and the
    # note that an unresolved loop might cover them. Suppressing the names in
    # that case was tried and reverted the same hour -- it silenced the real
    # pre-fix SAIRNlaw finding, which is the case this whole tool exists for.
    reasons = []
    if unresolved and missing:
        reasons.append('a generic read loop exists (%s) but no declared list '
                       "overlaps this app's write set" % ', '.join(unresolved))
    wrappers = sorted(set(WRAPPER_RE.findall(src)))
    return {
        'file': os.path.basename(path),
        'writes': writes,
        'reads': reads,
        'missing': missing,
        'reasons': reasons,
        'declared': declared,
        'wrappers': wrappers,
    }


# ── THE DEFAULT TARGET LIST IS ANCHORED TO THE REPO, NOT THE CWD (2026-09-11)
# `os.listdir('.')` is relative to wherever this is run from. From `docs/` it
# returned nothing and this tool printed an empty table, `none` under WRITTEN
# AND NEVER READ BACK, `none` under COULD NOT TELL, and exit 0 -- the only one
# of four cwd-relative checkers tried that way with no count anywhere in its
# output. The FILES SCANNED line below closed the disclosure half; this closes
# the cause. An explicit path argument stays CWD-relative on purpose.
#
# Display is unaffected: records carry `os.path.basename(path)`, so an absolute
# target still prints as `stonedesk.html`.
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    targets = argv[1:] or sorted(
        os.path.join(REPO, f) for f in os.listdir(REPO) if f.endswith('.html'))
    results = [r for r in (audit(t) for t in targets) if r]
    bad, unsure = [], []
    print('SCANNED-BY-NAME: only calls to a wrapper matching \\w*Data( are seen.')
    print('%-24s %-7s %-7s %s' % ('app', 'writes', 'read', 'declared read set(s)'))
    for r in sorted(results, key=lambda x: x['file']):
        print('%-24s %-7d %-7d %s' % (r['file'], len(r['writes']),
                                      len(r['writes'] & r['reads']),
                                      ', '.join(r['declared']) or '(literal reads only)'))
        if r['missing']:
            bad.append(r)
        if r['reasons']:
            unsure.append(r)

    print('\n=== WRITTEN AND NEVER READ BACK ===')
    if not bad:
        print('  none')
    for r in bad:
        print('  %s' % r['file'])
        for n in r['missing']:
            print('      %s' % n)

    print('\n=== COULD NOT TELL -- NOT A PASS ===')
    if not unsure:
        print('  none')
    for r in unsure:
        for why in r['reasons']:
            print('  %-24s %s' % (r['file'], why))

    # ── HOW MANY FILES THIS ACTUALLY LOOKED AT (2026-09-10) ──────────────────
    # The default target list is `*.html` RELATIVE TO THE CURRENT DIRECTORY, so
    # running this from anywhere but the repo root scans nothing -- and every
    # line above then reads as good news: an empty table, "none" under WRITTEN
    # AND NEVER READ BACK, "none" under COULD NOT TELL, exit 0. Measured from
    # `docs/` during the tools/ half of the self-referential-guard sweep; it
    # was the only one of four checkers tried that way with no count anywhere
    # in its output. The two zeros here are what make the difference visible.
    print('\nFILES SCANNED: %d (of %d target(s) named or globbed)'
          % (len(results), len(targets)))
    if not results:
        print('      ZERO files were scanned, so nothing above is a pass. The '
              'default target')
        print('      list is `*.html` in the CURRENT directory -- run this from '
              'the repo root.')
    print('\nNOTE: this cannot tell whether a read is ever CALLED. A hydrate that')
    print('      exists and is never invoked reads clean here -- see')
    print('      tools/sairn_reachability_check.py for that question.')
    return 1 if (bad or unsure) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

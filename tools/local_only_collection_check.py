"""Every business COLLECTION an app keeps should reach a server somehow.

WHY THIS EXISTS, and why it is a SECOND tool rather than a wider first one.
tools/write_without_readback_check.py was built on 2026-09-05 from two real
incidents and its own header says, in as many words, that it catches ONE of
them:

  SAIRNlaw  -- 20 resources written to the server, exactly one read back.
               CAUGHT. The tool goes red on sairnlaw.html at 3d869e1c^.
  SAIRNbiz  -- 17 localStorage collections, ONE of which reached a server.
               NOT CAUGHT, and correctly so by its own rules: SAIRNbiz was
               not writing through a wrapper and reading nothing back, it was
               writing to localStorage and STOPPING.

"Written to the server and never read back" and "never written to a server at
all" are different defects with different shapes, and the first tool says so
rather than implying coverage it lacks. This is the second one.

BOTH REAL CASES WERE FOUND BY HAND. SAIRNbiz's seventeen came off an index row
somebody wrote; SAIRNbuild's thirty-seven came from a session reading the file.
Neither was found by a machine, and that is the whole argument for this.

-- WHAT IT DOES --------------------------------------------------------------
Per app HTML file:
  1. discovers the app's own localStorage SETTER by reading it (a function
     whose first parameter is handed to localStorage.setItem), rather than
     assuming it is called st();
  2. collects the keys written through it AND by a bare localStorage.setItem,
     resolving three key shapes -- a literal, a SCREAMING_CASE constant, and a
     constant prefix joined to a literal suffix (SAIRNmechanical writes every
     one of its collections as mechSt(APP_ID+'_quotes', ...));
  3. keeps only the ones that look like a RECORD COLLECTION rather than device
     state -- see collection_keys() for the test and what it lets through;
  4. resolves the SIX ways this platform actually connects a local key to a
     server, every one of them read off a real app rather than imagined:
     the same name, the name with a `_list`/`_obj` suffix dropped, the name
     with its app prefix dropped, a [resource, key] pair list, a declared
     synced-keys list gating a generic write hook, and a server call sharing
     a variable with the local write;
  5. reports collections with no route to a server at all, and separately
     reports the ones it could not decide.

IT COUNTS RECORD COLLECTIONS, NOT localStorage KEYS, and the difference shows
up the moment anyone compares it to a hand count. SAIRNbiz's index row says
seventeen collections; this finds eleven, because six of the seventeen are
settings, counters and flags rather than record sets. The eleven are a subset,
the numbers are not interchangeable, and the probe asserts the subset.

-- THE COUNT IS A FLOOR, NOT A TOTAL, AND THE REPORT SAYS SO PER FILE ---------
The `unclassified` column counts keys that ARE written, are NOT device state,
and whose shape this could not read. It exists because the first version simply
dropped them, which made a partial count look like a complete one:

  * SAIRNcode reads every one of its forty collections as
    `var s = getItem('sc_claims'); if (s) return JSON.parse(s); ... return [];`
    -- the default is a `return` several statements away, so nothing here sees
    it, and a LIVE APP WITH FORTY STORES resolved to zero collections.
  * StoneDesk's dominant shape is `JSON.parse(getItem(k)||'null')||SEED`. Its
    own SAFE_DEMO_KEYS list names about thirty collections this still does not
    count, on top of the thirty-seven it does.

Both are honest could-not-reads and both are printed. Widening to those shapes
is a separate pass with its own verification -- widening one side of a
comparison without the other is how the sibling checker manufactured ten false
findings in an hour, and that lesson is three days old.

-- WHAT IT CANNOT SEE, said here rather than discovered later ------------------
  * An app that writes NOTHING this can read exits NON-ZERO and is named under
    NOTHING TO CHECK. An app that writes storage but yields no classified
    collection is the same case and is treated the same way -- a zero from a
    scanner nobody has watched fire is not a result.
  * A key connected to a server by a mapping this does not model resolves to
    COULD NOT TELL for that file, which is NOT a pass -- the exit code says so.
    The fix is to read the mapping and teach it, the same standard the read-back
    checker's two could-not-tells were held to.
  * Whether the write is ever CALLED, and whether the row comes BACK. The first
    is tools/sairn_reachability_check.py; the second is
    tools/write_without_readback_check.py. Running this alone proves a route
    exists, not that it works.
  * A collection held in a variable and never persisted at all is invisible
    here -- this only sees what reaches localStorage.

PROVEN ON REAL HISTORY, NOT ONLY ON ITSELF, by tests/local_only_probe.py.
Against sairnbiz.html at 48c122df^ it names TEN of eleven collections; against
the same file after that commit, exactly ONE -- sb_incidents, which really is
still open and has its own index row. Against sairnbuild.html at 1f1705e^ it
names TWENTY-NINE; afterwards, none. THE FIX IS WHAT CHANGES THE ANSWER, which
is the bar tools/discarded_verdict_check.py set and the reason a checker that
has only ever returned clean is a checker whose behaviour nobody knows.
"""
import os
import re
import sys

# Keys that are device state, not a business record, no matter what shape they
# are stored in. Named individually rather than by prefix: a silent category
# exclusion is how a real collection hides. Anything matched here is not even
# counted, so the totals stay honest.
DEVICE_STATE = {
    'license_key', 'licence_key', 'demo_cleared', 'seeded', 'theme', 'sidebar',
    'last_sync', 'session', 'session_token', 'trial_start', 'lic_fingerprint',
}
DEVICE_STATE_SUFFIX = (
    '_license_key', '_licence_key', '_seeded', '_demo_cleared', '_theme',
    '_session', '_session_token', '_token', '_trial_start', '_fingerprint',
    '_last_sync', '_lastsync', '_collapsed', '_prefs', '_pref', '_ui',
    # AN OUTBOUND QUEUE IS LOCAL BY DEFINITION and reporting one as "kept on
    # the device and sent nowhere" is exactly backwards -- its whole job is to
    # hold rows on the device UNTIL they reach the server. Added 2026-09-08
    # when resolving constant keys made SAIRNdental's dnt_pending_writes and
    # SAIRNsenior's sen_evv_queue visible for the first time and both were
    # reported as findings. Named, not a prefix rule: a silent category
    # exclusion is how a real collection hides.
    '_queue', '_pending_writes', '_outbox',
)

# How close a server call has to be to a local write for the two to count as
# one action. 300 characters is roughly the statement block around a save --
# `st(key, rows); closeModal(); render(); syncRows(rows);` -- and is narrow
# enough that a function doing unrelated server work elsewhere does not excuse
# a key. Tuned against the six keys the unscoped version wrongly cleared.
WINDOW = 300

# `\w*Data(` WAS TOO NARROW AND IT COST A FALSE ACCUSATION (2026-09-10).
# stonedesk-hr.html sends both its collections to the server through
# hrCall('write', 'sd_hr_employees', ...) -- a wrapper that does not end in
# `Data`, so neither name was harvested and the page was reported as 2 of 2
# collections kept on the device. Its localStorage write is an explicit CACHE,
# commented as one, beside a real server write.
#
# The shape that is actually the platform convention is ACTION-FIRST --
# f('write'|'read', '<resource>', payload) -- not a particular function name,
# so that is what is matched. Deliberately still a LITERAL resource and still
# an exact two-argument prefix: this widens which FUNCTION counts, not what a
# server call looks like.
WRITE_LIT_RE = re.compile(r"\w+\(\s*'write'\s*,\s*'(\w+)'")
WRITE_OBJ_RE = re.compile(r"action:\s*'write'\s*,\s*resource:\s*'(\w+)'")
READ_LIT_RE = re.compile(r"\w+\(\s*'read'\s*,\s*'(\w+)'")
FN_RE = re.compile(r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)')


def strip_comments(src):
    """Line comments only. Every call site here is code, and a commented-out
    example must not count as coverage."""
    return '\n'.join(l for l in src.split('\n') if not l.strip().startswith('//'))


def _body(src, at, limit=40000, opener='{'):
    closer = {'{': '}', '[': ']'}[opener]
    open_at = src.find(opener, at)
    if open_at < 0:
        return ''
    depth = 0
    for i in range(open_at, min(len(src), open_at + limit)):
        if src[i] == opener:
            depth += 1
        elif src[i] == closer:
            depth -= 1
            if depth == 0:
                return src[at:i + 1]
    return ''


def find_setter(src):
    """The app's own localStorage setter, by READING it rather than assuming.

    Most apps call it st(); SAIRNscape calls it scpSt(), SAIRNmechanical
    mechSt(), StoneDesk has st() and stRaw(). Hardcoding 'st' would silently
    check nothing in three apps -- the same shape as a guard that hardcodes
    `owner` and passes SAIRNcode clean forever.
    """
    names = []
    for m in FN_RE.finditer(src):
        params = [p.strip() for p in m.group(2).split(',') if p.strip()]
        if not params:
            continue
        body = _body(src, m.start())
        if body and re.search(r'localStorage\.setItem\(\s*' + re.escape(params[0]) + r'\b', body):
            names.append(m.group(1))
    return names


def is_device_state(key):
    k = key.lower()
    if k in DEVICE_STATE:
        return True
    # Strip the app prefix (dnt_, sb_, bld_, ...) before the exact-name test,
    # so dnt_license_key is recognised the same as license_key.
    tail = k.split('_', 1)[1] if '_' in k else k
    if tail in DEVICE_STATE:
        return True
    return any(k.endswith(s) for s in DEVICE_STATE_SUFFIX)


def collection_keys(src, setters):
    """Keys that hold a RECORD COLLECTION rather than a single setting.

    THE TEST IS THE READ, NOT THE WRITE, and that is deliberate. A write's
    argument is usually a variable (st('dnt_charges_list', list)) and says
    nothing about shape. The matching read almost always carries a default --
    ld('dnt_charges_list', []) for a list, ld('dnt_settings_obj', {}) for a
    record -- and THAT is the app telling you what it thinks the key holds.

    A key written but never read with a default falls back to the write: a
    literal [] or a variable named like a list. Anything else is left out
    rather than guessed at, because a checker that cries wolf on an entire app
    is worse than no checker -- nobody runs it twice.
    """
    # A KEY HELD IN A CONSTANT IS STILL A KEY, added 2026-09-08 after this tool
    # demonstrated the blind spot on code written an hour after it shipped.
    # SAIRNdental's new outbound queue writes st(DNT_PENDING_KEY, q) and the
    # first version could not see it -- harmless there, because a queue is not
    # a business collection, but SAIRNfreedom writes FORTY-TWO collections that
    # way (K_MEMBERS, K_LEDGER, K_TICKETS, ...) and StoneDesk another fifteen.
    # SAIRNfreedom did not appear in the report at all: it produced no keys, so
    # it produced no row, and an app writing forty-two collections read as an
    # app with nothing to check. Constants assigned a string literal are now
    # resolved, and main() prints a NOTHING TO CHECK line for any file that
    # still yields none, so a file can never silently leave the table.
    # PER STATEMENT, NOT PER DECLARATOR. `var K_POST='sf_post', K_OFFICERS=
    # 'sf_officers', ...` is one `var` with forty-two declarators in
    # SAIRNfreedom, and a regex anchored on the keyword sees only the first --
    # which is why the first version of this fix found three of its collections
    # instead of forty-two, and the count is what said so.
    #
    # SCREAMING_CASE ONLY, AND NO TRAILING UNDERSCORE. Both restrictions come
    # from false positives this produced on StoneDesk before it shipped:
    #   * a lowercase `var key='custom_'` is a REASSIGNED LOCAL, not a
    #     constant, and taking its first declaration made `custom_` look like a
    #     collection key;
    #   * `PLAN_KEY='sairn_action_plans_'` is a key PREFIX -- the code writes
    #     st(PLAN_KEY+id, ...) -- and a trailing underscore is never a whole
    #     key on this platform.
    # Both would have been reported as records kept on the device, in the
    # flagship app, beside twelve findings that are real. A checker's false
    # positives are borrowed against the credibility of its true ones.
    const = {}
    for m in re.finditer(r'\b(?:var|let|const)\s', src):
        stmt = src[m.end():m.end() + 4000].split(';', 1)[0]
        for name, val in re.findall(r'([A-Z][A-Z0-9_]*)\s*=\s*[\'"]([\w.-]+)[\'"]', stmt):
            if not val.endswith('_'):
                const.setdefault(name, val)

    def _keys_written_by(pattern):
        found = set()
        for m in re.finditer(pattern, src):
            arg = m.group(1)
            if arg.startswith("'"):
                found.add(arg.strip("'"))
            elif arg in const:
                found.add(const[arg])
        return found

    # A THIRD KEY SHAPE: a constant PREFIX joined to a literal suffix.
    # SAIRNmechanical writes mechSt(APP_ID+'_quotes', ...) for every one of its
    # collections, so without this it resolves ZERO keys while calling its
    # setter eight times -- an app with a storage layer reading as an app with
    # nothing in it.
    def _joined(pattern):
        found = set()
        for m in re.finditer(pattern, src):
            head, tail = m.group(1), m.group(2)
            if head in const:
                found.add(const[head] + tail)
        return found

    keys = set()
    for name in setters:
        keys |= _keys_written_by(re.escape(name) + r"\(\s*('[\w.-]+'|[A-Za-z_$][\w$]*)\s*,")
        keys |= _joined(re.escape(name) + r"\(\s*([A-Z][A-Z0-9_]*)\s*\+\s*'([\w.-]+)'\s*,")
    # THE BARE-setItem FALLBACK RUNS EVEN WHEN A SETTER EXISTS, corrected
    # 2026-09-08. It used to run only when there was none, so an app with a
    # wrapper AND direct calls had the direct ones ignored -- SAIRNmechanical
    # writes five collections through localStorage.setItem and four through
    # mechSt().
    keys |= _keys_written_by(r"localStorage\.setItem\(\s*('[\w.-]+'|[A-Za-z_$][\w$]*)\s*,")
    keys |= _joined(r"localStorage\.setItem\(\s*([A-Z][A-Z0-9_]*)\s*\+\s*'([\w.-]+)'\s*,")

    # The shape test accepts either the literal key or the constant that holds
    # it, so a collection read as ld(K_MEMBERS, []) is recognised the same as
    # ld('sf_members', []).
    def _alias(k):
        return [k] + [n for n, v in const.items() if v == k]

    array_default = set(re.findall(r"\w*\(\s*'([\w.-]+)'\s*,\s*\[\s*\]\s*\)", src))
    for name, val in const.items():
        if re.search(r"\w*\(\s*" + re.escape(name) + r"\s*,\s*\[\s*\]\s*\)", src):
            array_default.add(val)
    # THE RAW READ, for apps with no ld() wrapper at all. SAIRNcode reads every
    # one of its forty collections as
    #   JSON.parse(localStorage.getItem('sc_claims') || '[]')
    # so the wrapper-shaped test above never fired and the ENTIRE APP resolved
    # to zero collections -- a live app with forty stores reading as "nothing
    # to check". Found by asking why it was absent from the table, not by the
    # tool saying anything.
    array_default |= set(re.findall(
        r"localStorage\.getItem\(\s*'([\w.-]+)'\s*\)\s*\|\|\s*'\[\s*\]'", src))
    for name, val in const.items():
        if re.search(r"localStorage\.getItem\(\s*" + re.escape(name) + r"\s*\)\s*\|\|\s*'\[\s*\]'", src):
            array_default.add(val)
    for m in re.finditer(r"localStorage\.getItem\(\s*([A-Z][A-Z0-9_]*)\s*\+\s*'([\w.-]+)'\s*\)\s*\|\|\s*'\[\s*\]'", src):
        if m.group(1) in const:
            array_default.add(const[m.group(1)] + m.group(2))
    listish_write = set()
    for name in setters:
        for m in re.finditer(re.escape(name) + r"\(\s*('[\w.-]+'|[A-Za-z_$][\w$]*)\s*,\s*([A-Za-z_$][\w$]*)\s*\)", src):
            arg, var = m.group(1), m.group(2).lower()
            key = arg.strip("'") if arg.startswith("'") else const.get(arg)
            if key and (var.endswith('s') or 'list' in var or 'rows' in var or 'arr' in var):
                listish_write.add(key)
    # ── AN APP WITH NO WRAPPER STILL WRITES COLLECTIONS (2026-09-10) ────────
    # The loop above only sees apps that HAVE a named setter. Three apps do not
    # -- sairncash, sairncode and sairnroofing all call localStorage.setItem
    # directly -- so `setters` came back empty, nothing was ever classified,
    # and all three sat permanently in the "WROTE STORAGE, RESOLVED NO
    # COLLECTIONS -- could not read these, NOT a pass" bucket. A standing
    # unknown on three live apps, one of which (SAIRNcode) is a medical coding
    # product holding claims, denials, providers and A/R.
    #
    # It is the SAME heuristic, applied to the bare call instead of a wrapper,
    # and the JSON.stringify() form these apps actually use:
    #     localStorage.setItem('sc_claims', JSON.stringify(list))
    # Nothing is loosened -- the listish-variable test is unchanged, so a
    # non-list write is still not called a collection.
    for m in re.finditer(
            r"localStorage\.setItem\(\s*('[\w.-]+'|[A-Za-z_$][\w$]*)\s*,\s*"
            r"(?:JSON\.stringify\(\s*)?([A-Za-z_$][\w$]*)\s*[),]", src):
        arg, var = m.group(1), m.group(2).lower()
        key = arg.strip("'") if arg.startswith("'") else const.get(arg)
        if key and (var.endswith('s') or 'list' in var or 'rows' in var or 'arr' in var):
            listish_write.add(key)

    out = {}
    unclassified = set()
    for k in keys:
        if is_device_state(k):
            continue
        if k in array_default or k in listish_write:
            out[k] = 'list'
        else:
            # WRITTEN, NOT DEVICE STATE, AND THIS COULD NOT TELL WHETHER IT
            # HOLDS RECORDS. Counted and reported rather than dropped, because
            # dropping it is what makes a partial count look like a total.
            # StoneDesk is the case that forced this: its dominant read shape
            # is `JSON.parse(getItem(k)||'null')||SEED`, which no test here
            # recognises, and its own SAFE_DEMO_KEYS list names about thirty
            # collections this still does not count. Its number is a FLOOR.
            unclassified.add(k)
    return out, unclassified


NAME_SUFFIXES = ('_list', '_obj', '_arr', '_rows', '_data', '_cache')


def name_candidates(key):
    """Server names this local key could reasonably BE.

    THREE NAMING CONVENTIONS ARE IN USE AND ALL THREE ARE REAL, read off the
    apps rather than chosen:

      verbatim        SAIRNbiz -- `sb_invs` on disk is `sb_invs` on the server,
                      deliberately, because its sync hook keys off the storage
                      key directly.
      suffixed        SAIRNdental -- `dnt_charges_list` on disk is `dnt_charges`
                      on the server.
      prefix stripped StoneDesk -- `sd_slabs` on disk is `slabs` on the server
                      (`sdData('read','slabs',{})`).

    Testing only the first would report every SAIRNdental and StoneDesk
    collection as local-only, which is the false positive that would have sunk
    this on its first run -- a checker that cries wolf on an entire app is one
    nobody runs twice.
    """
    out = {key}
    for s in NAME_SUFFIXES:
        if key.endswith(s):
            out.add(key[:-len(s)])
    for k in list(out):
        if '_' in k:
            out.add(k.split('_', 1)[1])
    return out


def _server_calling_functions(src):
    """Function names whose body reaches a server at all, by any mechanism.

    Deliberately broad, because this set is only ever used to EXCUSE a key, and
    the cost of missing one is a false accusation. Covers the wrapper call, the
    raw fetch carrying an action/resource envelope, and a direct Supabase
    table call -- StoneDesk uses the last one for its intake table and nothing
    that looks at resource names would ever see it.
    """
    reaches = set()
    bodies = {}
    for m in FN_RE.finditer(src):
        body = _body(src, m.start())
        if body:
            bodies[m.group(1)] = body
    direct = re.compile(r"\w*Data\(\s*'(?:read|write)'|action:\s*'(?:read|write)'\s*,\s*resource:|\.from\(")
    for name, body in bodies.items():
        if direct.search(body):
            reaches.add(name)
    # One hop: a function that calls one of those reaches a server too.
    for name, body in bodies.items():
        if name in reaches:
            continue
        for other in reaches:
            if re.search(r'\b' + re.escape(other) + r'\s*\(', body):
                reaches.add(name)
                break
    return reaches, bodies


def covered_keys(src, local_keys, known_names, setters=()):
    """Every route this platform actually uses to get a local key to a server.

    Each route is one the apps really use, read off them rather than imagined.
    `known_names` is the union of the app's registered resources and every
    resource name the file names in a server call.
    """
    covered = {}
    for k in local_keys:
        hit = name_candidates(k) & known_names
        if hit:
            covered[k] = "named resource '%s'" % sorted(hit)[0]

    # PAIR LIST -- [ 'resource', 'key' ] in either order, anywhere in the file.
    # SAIRNdental's DNT_SYNC_RESOURCES is the canonical shape.
    for a, b in re.findall(r"\[\s*'([\w.-]+)'\s*,\s*'([\w.-]+)'\s*\]", src):
        if b in local_keys and a in known_names:
            covered.setdefault(b, "pair list with '%s'" % a)
        if a in local_keys and b in known_names:
            covered.setdefault(a, "pair list with '%s'" % b)

    # SYNCED LIST -- a declared list whose members gate a generic write hook.
    # SAIRNbuild's BLD_SYNCED and SAIRNbiz's SB_SYNCED are both this shape; the
    # list IS the write set, and the same constant drives the read.
    for gm in re.finditer(r'\b(\w+)\.forEach\(\s*function\s*\(\s*(\w+)\s*\)\s*\{\s*'
                          r'(\w+)\s*\[\s*\2\s*\]\s*=\s*true', src):
        list_name, guard = gm.group(1), gm.group(3)
        if not re.search(r'!\s*' + re.escape(guard) + r'\s*\[', src):
            continue
        m = re.search(r'\b(?:var|let|const)\s+' + re.escape(list_name) + r'\s*=\s*\[', src)
        if not m:
            continue
        body = _body(src, m.start())
        for k in re.findall(r"'([\w.-]+)'", body or ''):
            if k in local_keys:
                covered.setdefault(k, 'synced list %s' % list_name)

    # SIBLING SYNC -- the local write and the server call sit in the same
    # function, under names that have nothing to do with each other.
    #
    # THIS ROUTE EXISTS BECAUSE OF TWO REAL FALSE POSITIVES, both caught by
    # reading the call sites before this shipped rather than after:
    #   SAIRNbiz  st('sb_emps',emps) sits beside syncEmps(emps), which posts
    #             resource:'employees'. No name test connects sb_emps to
    #             employees, and it is genuinely synced.
    #   StoneDesk st('sd_intake', ...) sits beside sb.from(INTAKE_TABLE)
    #             .update(...), where INTAKE_TABLE is 'intake_submissions'.
    # SIBLING SYNC IS THE WEAK ROUTE AND IT IS TREATED AS ONE.
    #
    # THE TEST IS A SHARED VARIABLE, NOT PROXIMITY, and both weaker versions
    # were tried and rejected against the real files rather than reasoned away:
    #
    #   whole function  excused any key written anywhere inside a function that
    #                   touched a server anywhere. It silently cleared six
    #                   genuinely local-only keys -- SAIRNbuild's integrations
    #                   and SAIRNdental's vendor tables -- in bodies long enough
    #                   to contain both.
    #   a 300-char window
    #                   still cleared three of SAIRNbuild's inside bldSeedRows(),
    #                   where a SEED sits beside a server call and is not a sync
    #                   at all, and cleared StoneDesk's sd_photos because
    #                   `st('sd_customers',...)` happens to be the line above it.
    #
    # A route that over-covers produces a FALSE CLEAN, the one direction this
    # must not fail in. So the local write and the server call have to be about
    # THE SAME DATA: `st('sb_emps',emps)` beside `syncEmps(emps)`.
    #
    # Anything the window suggests but the variable does not confirm is a
    # COULD NOT TELL, reported and exiting non-zero -- never a quiet pass.
    reaches, bodies = _server_calling_functions(src)
    # ── THE STORAGE SETTER IS NOT A SERVER CALL, EVEN ONCE IT HOOKS ONE ─────
    # (2026-09-10.) Once st() gained a sync hook -- SAIRNvet, SAIRNfreedom and
    # StoneDesk all now push from inside it -- st() joined `reaches` through the
    # one-hop rule. And then EVERY one-line `saveX(){ return st('key', list); }`
    # wrapper cleared itself: the `shares` test looks for a server-calling
    # function called with the same variable, and `st('key', list)` IS that,
    # because st is now in the set. The LOCAL WRITE was matching as its own
    # server call.
    # MEASURED: it cleared sv_examrooms_turnover, a key deliberately EXCLUDED
    # from SV_SYNCED and pushed by nothing, and a live 400 from the deployed
    # allowlist proves it is not backed up. A false CLEAN, which is the one
    # direction this route's own header says it must not fail in.
    #
    # AND THE DEEPER HALF, WHICH THE st() HOOK ONLY EXPOSED: A ONE-LINE WRAPPER
    # WAS CLEARING ITSELF ON ITS OWN SIGNATURE. _body() includes the
    # declaration line, so for
    #     function saveExamRoomTurnoverLog(list){ return st('sv_...', list); }
    # the window contains `saveExamRoomTurnoverLog(list)` -- the PARAMETER LIST
    # -- and the `shares` test, which looks for a server-calling function called
    # with the same variable, matched the function's own header. Any wrapper
    # that reached `reaches` therefore excused every key it wrote, by existing.
    #
    # Two exclusions, both narrow: the app's own storage SETTER is not a server
    # call however many hooks it grows, and A FUNCTION IS NOT EVIDENCE ABOUT
    # ITSELF. Removed here rather than inside _server_calling_functions() so
    # that broad-by-design set stays broad for every other route.
    reaches = reaches - set(setters)
    near = re.compile(r"\w*Data\(\s*'(?:read|write)'|action:\s*'(?:read|write)'\s*,\s*resource:|\.from\(")
    unsure = {}
    for fname, body in bodies.items():
        if fname not in reaches:
            continue
        others = reaches - {fname}
        for k in local_keys:
            if k in covered:
                continue
            for m in re.finditer(r"\(\s*'" + re.escape(k) + r"'\s*,\s*([A-Za-z_$][\w$]*)\s*\)", body):
                var = m.group(1)
                lo, hi = max(0, m.start() - WINDOW), m.end() + WINDOW
                window = body[lo:hi]
                if not (near.search(window) or any(
                        re.search(r'\b' + re.escape(o) + r'\s*\(', window) for o in others)):
                    continue
                shares = (others and re.search(
                    r'\b(?:' + '|'.join(sorted(map(re.escape, others), key=len, reverse=True)) +
                    r')\s*\([^)]*\b' + re.escape(var) + r'\b', window)) or re.search(
                    r'\b' + re.escape(var) + r'\s*=\s*(?:await\s+)?\w*(?:Data|Fetch|Sync|Load)\s*\(', body)
                if shares:
                    covered[k] = 'same data as a server call in %s()' % fname
                else:
                    unsure.setdefault(k, 'written near a server call in %s(), '
                                          'but nothing ties them to the same data' % fname)
                break
    return covered, {k: v for k, v in unsure.items() if k not in covered}


def registered_names(path):
    """Resources the platform has registered for this app.

    The REGISTRY IS THE STRONGEST EVIDENCE a route exists, and it lives outside
    the HTML, so a checker reading only the app file would miss it. An app with
    no registry file gets an empty set -- which is itself the finding in
    SAIRNvet's case, not an error.
    """
    app = os.path.splitext(os.path.basename(path))[0]
    reg = os.path.join(os.path.dirname(os.path.abspath(path)),
                       'api', '_resources', app + '.js')
    if not os.path.exists(reg):
        return set(), False
    # ONLY THE `resources: [...]` ARRAY, AND ONLY AFTER STRIPPING COMMENTS.
    # Reading every quoted lowercase word in the file was the first version and
    # it was badly wrong: these registries carry long prose comments, so words
    # like 'jobs', 'quotes', 'customers' and 'slabs' appear in sentences and
    # were being counted as registered resources. StoneDesk's sd_jobs and
    # SAIRNgrounds' grd_properties both cleared on a word in a comment.
    text = strip_comments(open(reg, encoding='utf-8', errors='replace').read())
    m = re.search(r'resources\s*:\s*\[', text)
    if not m:
        return set(), True
    body = _body(text, m.start(), opener='[')
    return set(re.findall(r"'([\w.-]+)'", body or '')), True


def declared_not_synced(path):
    """Storage keys the app's registry DECLARES it deliberately does not sync.

    ADDED 2026-09-10, and the reason is a fix that told the truth and read like
    a regression. The sibling-sync route had been clearing a wrapper on its own
    signature; correcting that surfaced seven keys at once -- SAIRNbuild's
    bld_settings/bld_integrations/bld_ai_chat, StoneDesk's sd_settings/
    sd_alert_settings/sd_ai_counts, SAIRNvet's sv_examrooms_turnover -- and
    EVERY ONE of them is a decision somebody had already written down, in prose,
    in the registry:

        //   bld_ai_chat -- an unbounded conversation transcript, not a
        //                  business record.

    Prose is not machine-readable, so the checker had no way to tell a decision
    from an oversight and reported both as "kept on the device and sent
    nowhere". That is accurate and useless: a checker that lists seven
    deliberate choices as findings is one people stop reading, which is how the
    eighth -- a real one -- gets missed.

    So the decisions become a DECLARATION the tool reads, the same move
    `extraActions` already makes in these files. Same rules as the resources
    array: comments stripped first, because these registries carry long prose
    and reading quoted words out of it is how an earlier version cleared
    sd_jobs on a sentence.

    AN APP WITH NO DECLARATION GETS AN EMPTY SET, which is the honest default:
    absent means undecided, not exempt.
    """
    app = os.path.splitext(os.path.basename(path))[0]
    reg = os.path.join(os.path.dirname(os.path.abspath(path)),
                       'api', '_resources', app + '.js')
    if not os.path.exists(reg):
        return set()
    text = strip_comments(open(reg, encoding='utf-8', errors='replace').read())
    m = re.search(r'notSynced\s*:\s*\[', text)
    if not m:
        return set()
    body = _body(text, m.start(), opener='[')
    return set(re.findall(r"'([\w.-]+)'", body or ''))


def scan(path):
    src = strip_comments(open(path, encoding='utf-8', errors='replace').read())
    setters = find_setter(src)
    local, unclassified = collection_keys(src, setters)
    if not local and not unclassified:
        return None
    reg, has_reg = registered_names(path)
    named = set(WRITE_LIT_RE.findall(src)) | set(WRITE_OBJ_RE.findall(src))
    named |= set(READ_LIT_RE.findall(src))
    named |= set(re.findall(r"action:\s*'read'\s*,\s*resource:\s*'(\w+)'", src))
    covered, unsure = covered_keys(src, local, reg | named, setters)
    not_synced = declared_not_synced(path)
    all_uncovered = [k for k in local if k not in covered and k not in unsure]
    # DECLARED IS NOT THE SAME AS COVERED, and they are reported separately
    # rather than merged. A declared key still reaches no server; what the
    # declaration changes is whether that is news.
    declared = sorted(set(k for k in all_uncovered if k in not_synced)
                      | set(k for k in unsure if k in not_synced))
    uncovered = sorted(k for k in all_uncovered if k not in not_synced)
    # A DECLARED KEY IS NOT A COULD-NOT-TELL EITHER. bld_ai_chat and
    # sd_ai_counts land in `unsure` rather than `uncovered` -- they sit beside a
    # real server call that happens not to share their variable -- and leaving
    # them there would keep the exit code non-zero forever on two keys somebody
    # already decided. sd_intake stays a could-not-tell, correctly: it is NOT
    # declared, because it really is server-backed by a route this cannot see.
    unsure = {k: v for k, v in unsure.items() if k not in not_synced}
    return {
        'file': os.path.basename(path),
        'setters': setters,
        'registry': has_reg,
        'total': len(local),
        'covered': covered,
        'unsure': unsure,
        'uncovered': uncovered,
        'declared': declared,
        'unclassified': sorted(unclassified),
    }


def main(argv):
    targets = argv[1:]
    if not targets:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        targets = sorted(
            os.path.join(root, f) for f in os.listdir(root) if f.endswith('.html'))
    scanned = [(t, scan(t)) for t in targets]
    rows = [r for _, r in scanned if r]
    empty = [os.path.basename(t) for t, r in scanned if not r]
    print('SCANNED-BY-NAME: the storage setter is discovered per file and named '
          'below. A file with no setter and no bare setItem collection is '
          'reported as NOTHING TO CHECK, not as clean.')
    print()
    print('%-24s %-16s %6s %8s %10s %11s %12s' % (
        'app', 'setter', 'colls', 'covered', 'local-only', 'cannot-tell', 'unclassified'))
    for r in rows:
        print('%-24s %-16s %6d %8d %10d %11d %12d' % (
            r['file'], ','.join(r['setters']) or '(bare setItem)',
            r['total'], len(r['covered']), len(r['uncovered']), len(r['unsure']),
            len(r['unclassified'])))
    print()
    print('UNCLASSIFIED means a key is written, is not device state, and this could')
    print('not tell whether it holds records. A file with a high count has a FLOOR,')
    print('not a total -- its real number of collections is larger than `colls`.')

    if empty:
        # PRINTED, NOT OMITTED. The first version dropped these files from the
        # output entirely, so an app whose keys this could not read looked
        # exactly like an app with nothing to find -- and SAIRNfreedom, with
        # forty-two collections behind constants, was one of them.
        print()
        print('NOTHING TO CHECK (no collection keys resolved -- this is NOT a clean result):')
        for f in empty:
            print('  ' + f)

    print()
    print('=== KEPT ON THE DEVICE AND SENT NOWHERE ===')
    found = False
    for r in rows:
        if not r['uncovered']:
            continue
        found = True
        print('  %s -- %d of %d collections have NO route to a server:'
              % (r['file'], len(r['uncovered']), r['total']))
        for k in r['uncovered']:
            print('      %s' % k)
    if not found:
        print('  none')

    print()
    print('=== DECLARED NOT SYNCED -- a decision on file, not a finding ===')
    print('    (each key below reaches no server AND its app registry says so')
    print('     in a notSynced list. Still local; just not news. A key that is')
    print('     local and NOT declared is in the section above.)')
    shown = False
    for r in rows:
        if not r.get('declared'):
            continue
        shown = True
        print('  %s -- %d declared: %s' % (r['file'], len(r['declared']),
                                           ', '.join(r['declared'])))
    if not shown:
        print('  none')

    print()
    print('=== COULD NOT TELL -- NOT A PASS ===')
    unsure_any = False
    for r in rows:
        for k, why in sorted(r['unsure'].items()):
            unsure_any = True
            print('  %s %s -- %s' % (r['file'], k, why))
    if not unsure_any:
        print('  none')

    print()
    print('=== HOW THE COVERED ONES GET THERE (printed so a wrong resolution is visible) ===')
    for r in rows:
        if not r['covered']:
            continue
        by = {}
        for k, how in r['covered'].items():
            by.setdefault(how.split(" with ")[0], []).append(k)
        print('  %-24s %s' % (r['file'], '; '.join(
            '%s: %d' % (h, len(v)) for h, v in sorted(by.items()))))

    print()
    print('NOTE: a route existing is not the same as it working. Whether the write '
          'is ever CALLED is tools/sairn_reachability_check.py; whether the row '
          'comes BACK is tools/write_without_readback_check.py.')
    # A FILE THAT WRITES STORAGE AND YIELDS NO CLASSIFIED COLLECTION IS A
    # COULD-NOT-READ, not a pass. SAIRNcode is the case: forty stores, zero
    # resolved, and the first version exited 0 on it.
    blind = [r['file'] for r in rows if not r['total'] and r['unclassified']]
    if blind:
        print()
        print('WROTE STORAGE, RESOLVED NO COLLECTIONS -- could not read these, NOT a pass:')
        for f in blind:
            print('  ' + f)
    return 1 if (found or unsure_any or blind) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

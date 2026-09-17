#!/usr/bin/env python
"""log_cluster.py -- group log and error messages by MEANING, not by exact text.

    python tools/log_cluster.py --validate     # measure the model first
    python tools/log_cluster.py --self-check   # fixtures only
    python tools/log_cluster.py                # validate, then cluster the corpus

Exit 0 answered / 1 the model is not trustworthy at any threshold / 2 could not run.

── WHAT THIS IS, SAID PLAINLY BEFORE ANY NUMBER ────────────────────────────
This is **template extraction plus character-n-gram TF-IDF cosine**. It is NOT a
neural sentence embedding and it cannot recognise that "the licence store is
unreachable" and "could not reach the credential service" are the same event
when they share no vocabulary. **Saying so first is the point**: a tool that
called itself semantic and then matched on spelling would be the fabricated-
capability shape this repository removes on sight.

**WHAT IT DOES DO IS THE MAJORITY OF THE REAL PROBLEM.** Most "same error, new
wording" in production logs is one TEMPLATE with different parameters --
different ids, counts, hostnames, durations. Templating first is what industrial
log clustering does (Drain, Spell, LogMine) and it converts the hard semantic
question into an easy structural one for exactly the cases that recur. The
n-gram layer then absorbs residual drift: a reworded prefix, a renamed field, a
British/American spelling.

── THE VALIDATION IS NOT OPTIONAL AND IT RUNS FIRST ────────────────────────
**LOG LINES ARE UNUSUALLY HOSTILE TO SIMILARITY SCORING** and this is the trap
the whole tool is built around. They share enormous boilerplate -- the same
prefixes, the same "is required", the same "could not", the same app name -- so
two messages about completely different subjects routinely score far above the
threshold somebody would pick by intuition. **A threshold chosen from nothing
produces clusters that look meaningful and are not.**

So `--validate` measures the model against a labelled corpus BEFORE anything is
clustered, reports the false-positive rate at every candidate threshold, and
**refuses to cluster at all if no threshold separates the two populations**.
Clustering on an unvalidated threshold is the one thing this file will not do.

── HOW THE LABELS ARE DERIVED, AND WHY THAT IS HONEST ──────────────────────
Hand-labelling 2,000 strings is not something to claim was done. The labels come
from structure instead:

  RELATED   -- the SAME message string appearing in two different files (real
               duplicates), and pairs that reduce to the SAME template.
  UNRELATED -- messages from two different APPS whose templates differ.

**BOTH LABELS ARE IMPERFECT AND THE DIRECTION OF THE ERROR IS STATED.** Two
messages from different apps CAN describe the same underlying condition, so some
"unrelated" pairs are really related -- which means the measured false-positive
rate is an **UPPER BOUND**, not a point estimate. That is the safe direction: the
model is judged more harshly than the truth. The opposite framing would flatter
it, which is why it is not used.

── WHAT IT CANNOT SEE, STATED RATHER THAN DISCOVERED ───────────────────────
Genuine synonymy with no shared substring. Messages built at runtime from pieces
this never sees as one string. Any message under about 15 characters, where
n-gram overlap is noise. And it has no notion of severity: two messages can
cluster correctly and mean very different things about how urgent they are.
"""
import io
import itertools
import math
import os
import random
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXIT_OK, EXIT_UNTRUSTWORTHY, EXIT_COULD_NOT = 0, 1, 2

NGRAM = 3
DIM = 4096
MIN_LEN = 15
# Candidate thresholds. Deliberately spanning the range somebody would pick by
# eye (0.70-0.85) so the report can SHOW what those choices cost.
THRESHOLDS = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.92, 0.95]
# The alarm is set TIGHTER than the failure point (convention 4): a threshold is
# only recommended if its measured false-positive rate is at or under this.
MAX_FP_RATE = 0.02

# ── TEMPLATING ────────────────────────────────────────────────────────────
# Order matters: the most specific patterns first, or a UUID becomes three
# numbers. Each replacement is a NAMED placeholder rather than a blank, because
# a template that erases what kind of thing was removed cannot be read back.
_SUBS = [
    (re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I), '<uuid>'),
    (re.compile(r'\b[0-9a-f]{32,}\b', re.I), '<hash>'),
    (re.compile(r'\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\S*', re.I), '<ts>'),
    (re.compile(r'\b\d{4}-\d{2}-\d{2}\b'), '<date>'),
    (re.compile(r'\bhttps?://\S+'), '<url>'),
    (re.compile(r'\b[\w.-]+@[\w.-]+\.\w+\b'), '<email>'),
    (re.compile(r'(?<![\w<])[/\\][\w./\\-]{3,}'), '<path>'),
    (re.compile(r'\b\d+(?:\.\d+)?\s*(ms|s|kb|mb|gb|bytes?)\b', re.I), '<size>'),
    # SHORT MIXED IDs, ADDED AFTER THE BLIND LOCK CAUGHT THEM. `3f2a-11` is not
    # a uuid, not a hash and not a number, so it survived templating and pulled
    # two instances of one template apart -- that fixture scored 0.800 where the
    # same template with different NUMBERS scored 1.000. A token carrying both
    # letters and digits is an identifier in every log this platform writes.
    (re.compile(r'\b(?=[\w-]*\d)(?=[\w-]*[A-Za-z])[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\b'), '<id>'),
    (re.compile(r'\b\d+\b'), '<n>'),
    (re.compile(r"'[^']*'"), '<q>'),
    (re.compile(r'"[^"]*"'), '<q>'),
]


def templatise(text):
    """A log line with its VARIABLE parts replaced by named placeholders."""
    t = str(text)
    for rx, rep in _SUBS:
        t = rx.sub(rep, t)
    t = re.sub(r'\s+', ' ', t).strip().lower()
    return t


# ── THE EMBEDDING ─────────────────────────────────────────────────────────
def _grams(text):
    s = ' ' + text + ' '
    return [s[i:i + NGRAM] for i in range(max(0, len(s) - NGRAM + 1))]


def embed(text):
    """Hashed character-n-gram vector, sublinear TF, L2-normalised.

    SUBLINEAR TF (1 + log f) RATHER THAN RAW COUNTS, and it matters here more
    than in prose: a log line that repeats a token -- a list of ids, a path with
    repeated segments -- would otherwise let one repeated feature dominate the
    whole vector and pull unrelated lines together.
    """
    vec = {}
    for g in _grams(templatise(text)):
        h = hash(g) % DIM
        vec[h] = vec.get(h, 0) + 1
    if not vec:
        return {}
    out = {k: 1.0 + math.log(v) for k, v in vec.items()}
    norm = math.sqrt(sum(v * v for v in out.values()))
    if norm == 0:
        return {}
    return {k: v / norm for k, v in out.items()}


def similarity(a, b):
    """Cosine of two embeddings. Both are unit vectors, so this is the dot."""
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


# ── THE CORPUS AND ITS LABELS ─────────────────────────────────────────────
_MSG_PATTERNS = [
    re.compile(r"message:\s*'([^']{15,140})'"),
    re.compile(r"console\.error\('([^']{15,140})'"),
]


def harvest(root='api'):
    """(app, file, message) for every literal message string under `root`."""
    out = []
    base = os.path.join(REPO, root)
    if not os.path.isdir(base):
        return out
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '__pycache__')]
        for fn in sorted(files):
            if not fn.endswith('.js') or fn.endswith('.test.js'):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, REPO).replace(os.sep, '/')
            try:
                src = io.open(p, encoding='utf-8', errors='replace').read()
            except Exception:                                      # noqa: BLE001
                continue
            app = fn.split('-')[0].split('.')[0]
            for rx in _MSG_PATTERNS:
                for m in rx.finditer(src):
                    msg = m.group(1).strip()
                    if len(msg) >= MIN_LEN:
                        out.append((app, rel, msg))
    return out


def labelled_pairs(corpus, limit=4000, seed=20260917):
    """(related, unrelated) pairs derived from STRUCTURE, not from judgement.

    Returns two lists of (a, b). See the header for why both labels are
    imperfect and why that makes the measured false-positive rate an upper
    bound rather than a point estimate.
    """
    rnd = random.Random(seed)
    by_msg = {}
    by_template = {}
    for app, rel, msg in corpus:
        by_msg.setdefault(msg, set()).add(rel)
        by_template.setdefault(templatise(msg), set()).add((app, msg))

    related = []
    # Same string, two files -- an unarguable duplicate.
    for msg, files in by_msg.items():
        if len(files) >= 2:
            related.append((msg, msg))
    # Same template, different text -- the case the tool exists for.
    for tpl, members in by_template.items():
        msgs = sorted({m for _a, m in members})
        if len(msgs) >= 2:
            for a, b in itertools.islice(itertools.combinations(msgs, 2), 3):
                related.append((a, b))

    # Different app AND different template. Sampled rather than exhaustive:
    # the full cross-product is millions of pairs and a sample of thousands
    # already pins the rate far tighter than the decision needs.
    by_app = {}
    for app, _rel, msg in corpus:
        by_app.setdefault(app, []).append(msg)
    apps = [a for a in sorted(by_app) if len(by_app[a]) >= 2]
    unrelated = []
    guard = 0
    while len(unrelated) < limit and guard < limit * 40 and len(apps) >= 2:
        guard += 1
        a1, a2 = rnd.sample(apps, 2)
        m1 = rnd.choice(by_app[a1])
        m2 = rnd.choice(by_app[a2])
        if templatise(m1) == templatise(m2):
            continue
        unrelated.append((m1, m2))
    return related[:limit], unrelated


def measure(related, unrelated):
    """Similarity distributions and the false-positive rate per threshold."""
    cache = {}

    def emb(t):
        if t not in cache:
            cache[t] = embed(t)
        return cache[t]

    rel_scores = [similarity(emb(a), emb(b)) for a, b in related]
    unrel_scores = [similarity(emb(a), emb(b)) for a, b in unrelated]
    rows = []
    for th in THRESHOLDS:
        fp = sum(1 for s in unrel_scores if s >= th)
        tp = sum(1 for s in rel_scores if s >= th)
        rows.append({
            'threshold': th,
            'fp': fp,
            'fp_rate': (fp / len(unrel_scores)) if unrel_scores else None,
            'tp': tp,
            'tp_rate': (tp / len(rel_scores)) if rel_scores else None,
        })
    return rel_scores, unrel_scores, rows


def known_false_positive():
    """The highest score among fixture pairs that are definitely UNRELATED.

    A hand-chosen pair that is definitely unrelated and scores high is worth
    more than a sampled rate, because it cannot be explained away as an
    unlucky draw. It is a FLOOR: no recommendation may sit at or below it.
    """
    return max([similarity(embed(a), embed(b))
                for _l, a, b, want in FIXTURES if want in ('low', 'boilerplate')]
               or [0.0])


def recommend(rows, known_fp=None):
    """The threshold, or None. ONE definition, called by main() AND the probe.

    A selection rule copied into a test is a second rule that can disagree with
    the first, which is the claim-in-two-places defect this repo keeps removing.
    """
    if known_fp is None:
        known_fp = known_false_positive()
    usable = [r for r in rows
              if r['fp_rate'] is not None and r['fp_rate'] <= MAX_FP_RATE
              and r['threshold'] > known_fp]
    if not usable:
        return None
    # Lowest measured false-positive rate; among ties the lowest threshold,
    # because a lower cut groups more at no measured cost. NOT on true-positive
    # rate -- see main() for why a flat metric selects by list order.
    return min(usable, key=lambda r: (round(r['fp_rate'], 6), r['threshold']))


def _pct(x):
    return '   --  ' if x is None else ('%6.2f%%' % (100.0 * x))


def _quantiles(xs):
    if not xs:
        return None
    s = sorted(xs)
    def q(p):
        return s[min(len(s) - 1, int(p * len(s)))]
    return {'min': s[0], 'p50': q(0.50), 'p90': q(0.90), 'p99': q(0.99), 'max': s[-1]}


# ── THE BLIND LOCK ────────────────────────────────────────────────────────
# Fixtures whose answer is known, locked before the tool ever ran on the real
# corpus, in BOTH directions -- a scorer that says everything is similar is as
# useless as one that says nothing is, and log text makes the first far easier
# to ship by accident.
FIXTURES = [
    ('same template, different numbers -> HIGH',
     'checked 4 job(s) -- 2 late', 'checked 17 job(s) -- 5 late', 'high'),
    ('same template, different ids -> HIGH',
     "licence 3f2a-11 is not active", "licence 99bb-04 is not active", 'high'),
    ('reworded prefix, same subject -> MEDIUM OR HIGH',
     'the licence could not be verified right now',
     'licence could not be verified at this time', 'medium'),
    ('SHARED BOILERPLATE, DIFFERENT SUBJECT -> must NOT be high',
     'app_id is required and must be a short identifier',
     'shopId is required and must be a short identifier', 'boilerplate'),
    ('completely different subjects -> LOW',
     'the slab could not be reserved because it is already on a job',
     'payroll tax rates are current for the 2026 filing year', 'low'),
    ('different subjects sharing an app name -> LOW',
     'stonedesk: the invoice total does not match its line items',
     'stonedesk: the CNC export refused a G-code request on purpose', 'low'),
]


def self_check(verbose=True):
    bad = []
    for label, a, b, want in FIXTURES:
        s = similarity(embed(a), embed(b))
        if want == 'high':
            ok = s >= 0.85
        elif want == 'medium':
            ok = s >= 0.55
        elif want == 'low':
            ok = s < 0.55
        else:                       # 'boilerplate' -- the trap the tool is about
            ok = True               # measured and PRINTED, never asserted away
        if verbose:
            note = ''
            if want == 'boilerplate':
                note = '   <- MEASURED, NOT ASSERTED: this is the false positive the header is about'
            print('  %-4s %-52s %.3f%s' % ('ok' if ok else 'FAIL', label, s, note))
        if not ok:
            bad.append('%s (%.3f)' % (label, s))
    return bad


def main(argv):
    print('THE BLIND LOCK -- fixtures whose answer is known, both directions')
    bad = self_check()
    if bad:
        print('\nCOULD NOT RUN: the scorer failed its own fixtures: %s' % ', '.join(bad))
        return EXIT_COULD_NOT
    if '--self-check' in argv:
        print('\nself-check clean.')
        return EXIT_OK

    corpus = harvest()
    print('\nCORPUS: %d message strings from %d files'
          % (len(corpus), len({f for _a, f, _m in corpus})))
    if len(corpus) < 50:
        print('COULD NOT RUN: too few messages to measure anything.')
        return EXIT_COULD_NOT

    related, unrelated = labelled_pairs(corpus)
    print('LABELLED PAIRS: %d related, %d unrelated' % (len(related), len(unrelated)))
    if len(related) < 20 or len(unrelated) < 200:
        print('COULD NOT RUN: the labelled set is too small to pin a rate.')
        return EXIT_COULD_NOT

    rel_scores, unrel_scores, rows = measure(related, unrelated)
    rq, uq = _quantiles(rel_scores), _quantiles(unrel_scores)
    print('')
    print('SIMILARITY DISTRIBUTIONS -- two numbers, never one')
    print('              min     p50     p90     p99     max')
    for name, q in (('related  ', rq), ('unrelated', uq)):
        print('  %s %7.3f %7.3f %7.3f %7.3f %7.3f'
              % (name, q['min'], q['p50'], q['p90'], q['p99'], q['max']))

    print('')
    print('FALSE POSITIVES PER THRESHOLD -- the table the threshold is chosen FROM')
    print('  thresh   FP      FP rate    TP      TP rate')
    for r in rows:
        print('  %6.2f  %5d   %s   %5d   %s'
              % (r['threshold'], r['fp'], _pct(r['fp_rate']),
                 r['tp'], _pct(r['tp_rate'])))

    usable = [r for r in rows if r['fp_rate'] is not None and r['fp_rate'] <= MAX_FP_RATE]
    print('')
    if not usable:
        print('NOT TRUSTWORTHY AT ANY TESTED THRESHOLD.')
        print('Every candidate lets more than %.0f%% of KNOWN-UNRELATED pairs'
              % (100 * MAX_FP_RATE))
        print('score as similar. Clustering on this would produce groups that look')
        print('meaningful and are not, so no clustering is offered. This is a')
        print('finding about the model, not about the logs.')
        return EXIT_UNTRUSTWORTHY

    # ── THE RELATED POPULATION IS DEGENERATE, AND THAT CHANGES THE RULE ───
    # Every related pair scores exactly 1.000, and it is not luck: the label
    # rule builds them from IDENTICAL strings and from pairs that reduce to the
    # SAME TEMPLATE -- and two messages with the same template have the same
    # embedding by construction. So the true-positive rate is 100% at every
    # threshold and CARRIES NO INFORMATION about where to cut.
    #
    # PICKING THE THRESHOLD ON TP RATE WOULD THEREFORE PICK THE FIRST ONE IN THE
    # LIST, which is exactly what the first version of this did -- it recommended
    # 0.60 with a 0.70% false-positive rate while 0.92 measured 0.00%, purely
    # because `max()` returns the earliest of equal values. A selection rule
    # driven by a flat metric is a selection rule driven by list order.
    #
    # So the choice is made on the ONLY axis that discriminates here: lowest
    # measured false-positive rate, and among ties the LOWEST threshold, because
    # a lower cut groups more without costing anything measurable.
    #
    # WHAT WOULD MAKE TP RATE MEAN SOMETHING is a related population that is
    # genuinely related and NOT template-identical -- the same incident reported
    # in two different wordings. That cannot be derived from structure; it needs
    # somebody to label it, and inventing those pairs here would be measuring
    # the tool against its author's idea of what it should match.
    # ── A KNOWN FALSE POSITIVE IS A FLOOR, NOT A FOOTNOTE ─────────────────
    # The instruction was to validate against KNOWN unrelated-pair false
    # positives before trusting the model, and this is where that binds. The
    # blind-lock fixture "app_id is required..." / "shopId is required..." is a
    # hand-chosen pair that is definitely unrelated and scores 0.91. Any
    # threshold at or below that WOULD CLUSTER THEM, whatever the sampled rate
    # says.
    #
    # THE ARM THAT FORCED THIS FOUND IT ON A SMALLER SAMPLE: 0.92 at 4000
    # unrelated pairs, 0.85 at 1500 -- below the known false positive. A
    # recommendation that moves with sample size has not converged, and taking
    # the lower one would have shipped the exact mistake the tool is about.
    known_fp = known_false_positive()
    best = recommend(rows, known_fp)
    if best is None:
        print('')
        print('NOT TRUSTWORTHY: every threshold meeting the sampled FP target is')
        print('at or below %.3f, which is what a KNOWN-UNRELATED fixture pair'
              % known_fp)
        print('actually scores. The sample says those thresholds are safe and a')
        print('pair somebody chose by hand says they are not. No clustering is')
        print('offered on that disagreement.')
        return EXIT_UNTRUSTWORTHY
    tp_flat = len({round(r['tp_rate'] or 0, 6) for r in rows}) == 1
    print('RECOMMENDED THRESHOLD: %.2f' % best['threshold'])
    print('  FLOORED at %.3f by a KNOWN-UNRELATED fixture pair -- the sampled'
          % known_fp)
    print('  rate alone would have allowed a lower cut that clusters it')
    print('  measured false-positive rate %s on %d known-unrelated pairs'
          % (_pct(best['fp_rate']), len(unrelated)))
    print('  measured true-positive rate  %s on %d known-related pairs'
          % (_pct(best['tp_rate']), len(related)))
    print('')
    if tp_flat:
        print('')
        print('THE TRUE-POSITIVE RATE IS FLAT AT EVERY THRESHOLD AND IS NOT A')
        print('SELECTION SIGNAL. Related pairs here are identical strings or')
        print('template-identical ones, which have the same embedding by')
        print('construction, so they score 1.000 everywhere. The threshold above')
        print('was chosen on false-positive rate alone. A related population that')
        print('is genuinely related and NOT template-identical would make this')
        print('number mean something, and it cannot be derived from structure.')
    print('')
    print('READ THE FP RATE AS AN UPPER BOUND, NOT A POINT ESTIMATE. Some pairs')
    print('labelled unrelated -- two apps, different templates -- genuinely')
    print('describe the same condition, so the model is being judged more harshly')
    print('than the truth. That is the safe direction and it is why the label')
    print('rule was chosen this way rather than the flattering one.')

    # ── ACCURACY AND STABILITY AS TWO NUMBERS, NEVER ONE (convention 2) ───
    # A rate measured once says how the model did on one sample. It does not say
    # whether the RECOMMENDATION would survive a different one -- and the arm
    # that produced the floor above found exactly that: 0.92 on 4000 pairs,
    # 0.85 on 1500.
    _r2, _u2 = labelled_pairs(corpus, limit=1500, seed=20260918)
    _, _, rows2 = measure(_r2, _u2)
    best2 = recommend(rows2, known_fp)
    print('')
    print('STABILITY: a second sample (different seed and size) recommends %s'
          % ('%.2f' % best2['threshold'] if best2 else 'NOTHING USABLE'))
    if best2 and abs(best2['threshold'] - best['threshold']) > 1e-9:
        print('  THE RECOMMENDATION MOVED. Treat the higher of the two as the')
        print('  answer: a threshold that is safe on one sample and not on')
        print('  another has not converged, and the safe direction is up.')
        best = max([best, best2], key=lambda r: r['threshold'])
        print('  using %.2f' % best['threshold'])
    elif best2:
        print('  UNCHANGED across both samples.')

    clusters = cluster([m for _a, _f, m in corpus], best['threshold'])
    multi = [c for c in clusters if len(c) > 1]
    print('')
    print('CLUSTERS at %.2f: %d total, %d with more than one member'
          % (best['threshold'], len(clusters), len(multi)))
    for c in sorted(multi, key=len, reverse=True)[:8]:
        print('  [%d] %s' % (len(c), c[0][:96]))
        for m in c[1:3]:
            print('      + %s' % m[:92])
    return EXIT_OK


def cluster(messages, threshold):
    """Greedy single-pass agglomeration against cluster REPRESENTATIVES.

    Single-pass and representative-based rather than full pairwise: the corpus
    is thousands of lines and this runs on every invocation, so an O(n^2) pass
    would make the tool something people skip. The cost is stated rather than
    hidden -- a message that belongs with a cluster it did not meet first can
    land in its own, so cluster COUNT is an upper bound on the number of
    distinct problems, never a lower one.
    """
    seen = []
    reps = []
    out = []
    for m in messages:
        e = embed(m)
        placed = False
        for i, r in enumerate(reps):
            if similarity(e, r) >= threshold:
                out[i].append(m)
                placed = True
                break
        if not placed:
            reps.append(e)
            out.append([m])
        seen.append(m)
    return out


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

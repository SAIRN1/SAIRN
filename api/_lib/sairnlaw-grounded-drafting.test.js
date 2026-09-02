// Grounded definitions on the two SINGLE-SHOT surfaces, driven verbatim from
// sairnlaw.html.
//
// WHY THE MECHANISM IS DIFFERENT FROM THE ASSISTANT'S. The AI Assistant closes
// its definition gap with a tool (see sairnlaw-define-tool.test.js). Drafting
// and document review cannot: both send one ai_generate call with NO `tools`
// field, so an instruction to call define_legal_term would order them to reach
// something that is not there -- a rule that reads as a guard and enforces
// nothing. These two retrieve FIRST and inject the real text.
//
// THE SPLIT THIS FILE PINS DOWN: the PROHIBITION is the guarantee, the
// INJECTION is only the coverage. Term extraction from free text is a
// heuristic and will miss things. Every test below that asserts a miss is
// asserting that a miss produces NO grounded material -- which forces the
// refusal the rule requires, rather than a fabrication. A missed extraction
// must cost a refusal, never a definition.
//
// Nothing here talks to Cornell LII. referenceFetch is stubbed and counted, so
// the rate-limit short-circuit is proven by the number of calls actually made
// rather than by reading the code.

const fs = require('fs');
const path = require('path');

const HTML = path.join(__dirname, '..', '..', 'sairnlaw.html');
const src = fs.readFileSync(HTML, 'utf8');

let pass = 0, fail = 0;
function check(name, actual, expected) {
  const a = JSON.stringify(actual), e = JSON.stringify(expected);
  if (a === e) { pass++; return; }
  fail++;
  console.log('FAIL  ' + name + '\n        expected ' + e + '\n        actual   ' + a);
}

function balanced(start, open, close) {
  let i = src.indexOf(open, start), depth = 0;
  if (i < 0) throw new Error('no ' + open);
  for (; i < src.length; i++) {
    if (src[i] === open) depth++;
    else if (src[i] === close) { depth--; if (!depth) return src.slice(start, i + 1); }
  }
  throw new Error('unbalanced');
}
function extractFn(sig) {
  const start = src.indexOf(sig);
  if (start < 0) throw new Error('not found: ' + sig);
  return balanced(start, '{', '}');
}
function extractVar(name) {
  const start = src.indexOf('var ' + name + ' =');
  if (start < 0) throw new Error('not found: var ' + name);
  const end = src.indexOf('\n', src.indexOf(';', start));
  return src.slice(start, end);
}
// The two array/object literals span lines, so take them by bracket balance.
function extractLiteral(name, open, close) {
  const start = src.indexOf('var ' + name + ' =');
  if (start < 0) throw new Error('not found: var ' + name);
  // balanced() slices from `start`, so the `var NAME =` prefix is already in
  // the returned text -- re-adding it here was the first version's bug.
  return balanced(start, open, close) + ';';
}

const PATTERNS = extractLiteral('LAW_DEFN_PATTERNS', '[', ']');
const STOPWORDS = extractLiteral('LAW_DEFN_STOPWORDS', '{', '}');
const ARTICLES = extractLiteral('LAW_DEFN_LEADING_ARTICLES', '{', '}');
const REJECT = extractLiteral('LAW_DEFN_LEADING_REJECT', '{', '}');
const MAXLOOKUPS = extractVar('LAW_DEFN_MAX_LOOKUPS');
const EXTRACT = extractFn('function lawExtractDefinitionCandidates(');
const GROUND = extractFn('async function lawGroundedDefinitions(');

function build(referenceFetch) {
  return new Function('referenceFetch',
    PATTERNS + '\n' + STOPWORDS + '\n' + ARTICLES + '\n' + REJECT + '\n' + MAXLOOKUPS + '\n' + EXTRACT + '\n' + GROUND +
    '\nreturn { lawExtractDefinitionCandidates: lawExtractDefinitionCandidates, lawGroundedDefinitions: lawGroundedDefinitions };'
  )(referenceFetch);
}
const W = build(async () => ({ ok: false, code: 'NOT_FOUND' }));
const ex = W.lawExtractDefinitionCandidates;

// ── extraction: it fires where the text marks a term as a term ───────────
check('an explicit "define X" is picked up',
  ex('Please define promissory estoppel.'), ['promissory estoppel']);
check('"what does X mean" is picked up',
  ex('what does res judicata mean?'), ['res judicata']);
check('"the meaning of X" is picked up',
  ex('Explain the meaning of laches.'), ['laches']);
check('"the doctrine of X" is picked up',
  ex('Address the doctrine of unconscionability.'), ['unconscionability']);
check('a quoted phrase is picked up, because that is how a document flags a term of art',
  ex('The clause uses "consequential damages" without defining it.'), ['consequential damages']);

// ── extraction: it does NOT fire on ordinary prose ───────────────────────
// A wider net would spend the rate limit on ordinary words and ground
// nothing. Precision beats recall here for the same reason a miss is safe.
check('an ordinary drafting request with no term marker extracts nothing',
  ex('Draft a demand letter to opposing counsel about the outstanding invoice and set a two-week deadline.'), []);
check('an empty or missing request extracts nothing',
  [ex(''), ex(null), ex(undefined)], [[], [], []]);
check('a bare stopword in quotes is rejected', ex('the clause says "the" repeatedly'), []);
check('a long quoted sentence is rejected rather than sent as a term',
  ex('It says "this agreement shall be governed by the laws of the state and any dispute arising"'), []);

// ── extraction: normalisation, all three found by running it on prose ───
// None of these was in the first version. Each was found by feeding the
// extractor sentences it had not been asserted against and reading what came
// back -- the same "check the output, do not trust the tool" step that found
// the scanner's own false positives.
check('a leading article is stripped, so "a novation" does not slug to a_novation',
  ex('What is a novation?'), ['novation']);
check('a possessive-led phrase is REJECTED, not stripped -- it is prose, not a term',
  ex('Our client wants a letter. What is our next step?'), []);
check('a conjunction ends a capture, so the first of two terms is not lost to length',
  ex('Explain the doctrine of laches and the meaning of estoppel.').sort(), ['estoppel', 'laches']);
check('the framing noun is stripped AFTER the article, so both patterns land on one term',
  ex('What is the doctrine of unclean hands or the defence of waiver?'), ['unclean hands']);
check('and that ordering is load-bearing -- article first, framing noun second',
  /LEADING_ARTICLES\[words\[0\]\][\s\S]{0,200}doctrine\|defence/.test(EXTRACT), true);

// ── extraction: capped and deduped ──────────────────────────────────────
check('the cap is two lookups, not however many the text names',
  ex('Define laches. Define estoppel. Define novation. Define waiver.').length, 2);
check('the same term named twice is looked up once',
  ex('Define laches and then explain the doctrine of laches.'), ['laches']);
check('the cap constant in the file is the one being asserted',
  /LAW_DEFN_MAX_LOOKUPS = 2/.test(MAXLOOKUPS), true);

// ── retrieval ───────────────────────────────────────────────────────────
const WEX = (term) => ({
  ok: true, term: term,
  paragraphs: ['P1 for ' + term + '.', 'P2.', 'P3.', 'P4 SHOULD BE DROPPED.'],
  crossReferences: [], source_name: 'Cornell LII Wex',
  source_url: 'https://www.law.cornell.edu/wex/' + term.replace(/ /g, '_'),
  retrieved_at: '2026-09-02T00:00:00.000Z'
});

(async () => {
  // Both terms retrieved.
  {
    let calls = [];
    const w = build(async (a, p) => { calls.push(p.term); return WEX(p.term); });
    const g = await w.lawGroundedDefinitions('Define laches. Define novation.');
    check('both candidates are looked up', calls, ['laches', 'novation']);
    check('the block carries the retrieved text for both',
      [/\[laches\] P1 for laches\./.test(g.block), /\[novation\] P1 for novation\./.test(g.block)], [true, true]);
    check('and each carries its real source url',
      /Source: Cornell LII Wex -- https:\/\/www\.law\.cornell\.edu\/wex\/laches/.test(g.block), true);
    check('only three paragraphs are injected, and the fourth is dropped not summarised',
      /P4 SHOULD BE DROPPED/.test(g.block), false);
    check('the block declares itself the only definitional material allowed',
      /ONLY definitional material you may rely on/.test(g.block), true);
    check('the user-facing note names what was grounded',
      g.note, 'Grounded from Cornell LII: laches, novation.');
  }

  // RATE LIMIT SHORT-CIRCUIT -- proven by the CALL COUNT, not by reading code.
  {
    let calls = [];
    const w = build(async (a, p) => { calls.push(p.term); return { ok: false, code: 'RATE_LIMITED', message: 'wait' }; });
    const g = await w.lawGroundedDefinitions('Define laches. Define novation.');
    check('a rate-limited first lookup stops the second being issued at all', calls, ['laches']);
    check('the block is empty', g.block, '');
    check('and the note says which term was rate-limited and which was not attempted',
      [/laches \(rate-limited by Cornell LII\)/.test(g.note), /novation \(not attempted/.test(g.note)], [true, true]);
  }

  // A term Wex does not hold.
  {
    const w = build(async () => ({ ok: false, code: 'NOT_FOUND' }));
    const g = await w.lawGroundedDefinitions('Define zzqq doctrine.');
    check('a term with no Wex entry produces NO grounded material', g.block, '');
    check('and says so rather than reporting nothing at all', /no Wex entry/.test(g.note), true);
  }

  // Nothing extracted at all -- the common case, and it must still be visible.
  {
    let calls = 0;
    const w = build(async () => { calls++; return WEX('x'); });
    const g = await w.lawGroundedDefinitions('Draft a retainer letter for a new client.');
    check('no candidate means no network call', calls, 0);
    check('the block is empty', g.block, '');
    check('and the user is still told that nothing was looked up, and why that is safe',
      [/nothing was looked up/.test(g.note), /refused rather than answered from memory/.test(g.note)], [true, true]);
  }

  // A transport failure is a miss, not a crash.
  {
    const w = build(async () => ({ error: { message: 'Network error: boom' } }));
    const g = await w.lawGroundedDefinitions('Define laches.');
    check('a transport failure produces no grounded material and is reported',
      [g.block, /laches \(lookup failed\)/.test(g.note)], ['', true]);
  }

  // ── the wiring: both surfaces must actually use it ─────────────────────
  const draft = extractFn('async function runAiDraft(');
  const review = extractFn('async function reviewDocument(');
  check('the drafting surface retrieves before generating',
    /var grounded=await lawGroundedDefinitions\(request\)/.test(draft), true);
  check('the review surface retrieves from the document text',
    /var grounded=await lawGroundedDefinitions\(d\.content_text\)/.test(review), true);
  check('both splice the rule AND the retrieved block into the system prompt',
    [/LAW_GROUNDED_DEFINITIONS_RULE\+grounded\.block/.test(draft),
     /LAW_GROUNDED_DEFINITIONS_RULE\+grounded\.block/.test(review)], [true, true]);
  check('both show the grounding outcome to the user rather than doing it invisibly',
    [/grounded\.note/.test(draft), /grounded\.note/.test(review)], [true, true]);
  check('both still carry the citation rule -- this adds a guard, it does not replace one',
    [/LAW_CITATION_RULE/.test(draft), /LAW_CITATION_RULE/.test(review)], [true, true]);
  check('the retrieval is inside the stale-response guard, so a superseded request cannot overwrite a newer one',
    /lawGroundedDefinitions\(request\);\s*\r?\n\s*if\(myDraftSeq!==lawDraftSeq\)return;/.test(draft), true);

  // ── the rule itself ───────────────────────────────────────────────────
  check('LAW_GROUNDED_DEFINITIONS_RULE exists', src.indexOf('var LAW_GROUNDED_DEFINITIONS_RULE=') !== -1, true);
  check('it states plainly that there are no tools in this request',
    /you have no tools available in this request/.test(src), true);
  check('it forbids the fallbacks in the words the model would otherwise reach for',
    [/general sense/.test(src), /roughly speaking/.test(src)], [true, true]);
  check('and it PROTECTS legitimate drafting -- a clause that defines a term for the parties is not a legal assertion',
    /you may write a contract clause that defines a term for the parties/.test(src), true);
  check('it also protects saying a document uses a term inconsistently',
    /uses a term inconsistently or ambiguously/.test(src), true);

  console.log((fail ? 'FAILED ' : 'PASS ') + pass + '/' + (pass + fail));
  if (fail) process.exit(1);
})();

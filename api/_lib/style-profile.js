// api/_lib/style-profile.js
// ---------------------------------------------------------------------------
// NEXUS per-user style profile — the observer, the merge, and the renderer.
//
// See docs/2026-09-02-nexus-style-profile-design.md for why this exists. Short
// version: the only per-person signal in any SAIRN system prompt today is a
// single hand-picked enum on the SHOP record, so two people at the same shop
// get byte-identical prompts. This observes how a person actually writes and
// folds it into a structured, persistent profile.
//
// THREE PURE FUNCTIONS AND NOTHING ELSE. No I/O, no model call, no clock, no
// randomness. That is what makes it testable to the standard the rest of this
// platform is held to, and it is why the client can run analyse() locally and
// post deltas instead of shipping the user's raw text anywhere.
//
//   analyse(text)            -> observation for ONE message
//   mergeObservation(p, o)   -> new profile, incrementally folded
//   renderStyleDirectives(p) -> the prompt block, or '' below the floor
//
// NOTHING HERE STORES RAW TEXT. A profile is running counts and a small term
// tally. There is no field a message could be reconstructed from, and
// style-profile.test.js asserts that against a sentence of known rare words.
// ---------------------------------------------------------------------------

'use strict';

// Below this many messages the profile renders NOTHING and the caller's
// existing behaviour stands. Two terse messages must not convince a model the
// user wants telegrams forever, and an early wrong directive is worse than no
// directive because it is invisible and sticky.
const MIN_SAMPLES = 5;

// Cap so one long paste cannot dominate the running averages.
const MAX_WORDS_PER_SAMPLE = 400;
const MAX_TERMS = 12;

const STOPWORDS = new Set(('a an and are as at be but by for from has have how i if in is it its of on or ' +
  'that the this to was were what when where which who will with you your me my we our us do does did ' +
  'can could should would need want get got make made just also then than there their they them so not ' +
  'no yes ok okay please thanks thank hi hey hello about into over under out up down all any some more ' +
  'most other new now here very really much many one two three').split(' '));

const HEDGES = /\b(maybe|perhaps|possibly|i think|i guess|sort of|kind of|might|probably|not sure|wondering)\b/gi;
const COURTESY = /\b(please|thanks|thank you|appreciate|sorry|could you|would you|if you don't mind)\b/gi;
// A leading bare verb is the cheapest reliable imperative signal in this domain.
const IMPERATIVE_START = /^(give|show|list|make|build|write|add|remove|fix|check|find|tell|explain|calculate|quote|price|compare|send|open|close|set|update|delete|run|generate|create|draft)\b/i;

function words(text) {
  return String(text || '').toLowerCase().match(/[a-z][a-z0-9'\-]{1,}/g) || [];
}

/**
 * Observation for a single message. Every field is a count or a boolean so
 * mergeObservation can fold it in without seeing any other message.
 */
function analyse(text) {
  const raw = String(text == null ? '' : text);
  const trimmed = raw.trim();
  const w = words(trimmed).slice(0, MAX_WORDS_PER_SAMPLE);
  const wordCount = w.length;

  // Sentence enders, floored at 1 so a fragment counts as one sentence rather
  // than dividing by zero.
  const sentences = Math.max(1, (trimmed.match(/[.!?]+(\s|$)/g) || []).length);

  const lines = trimmed.split('\n');
  const usesBullets = lines.some((l) => /^\s*[-*•]\s+\S/.test(l));
  const usesNumbered = lines.some((l) => /^\s*\d+[.)]\s+\S/.test(l));
  const usesMarkdown = /\*\*[^*]+\*\*|`[^`]+`|^#{1,6}\s/m.test(trimmed);

  // ALL-CAPS words of 3+ letters, excluding ones that are plainly acronyms by
  // being short. Emphasis and jargon are different signals and are counted
  // separately on purpose -- "THIS IS URGENT" is tone, "THH" is vocabulary.
  const capsTokens = trimmed.match(/\b[A-Z]{3,}\b/g) || [];
  const abbrevTokens = trimmed.match(/\b[A-Z]{2,5}\b/g) || [];

  const terms = {};
  for (const t of w) {
    if (STOPWORDS.has(t) || t.length < 4) continue;
    terms[t] = (terms[t] || 0) + 1;
  }

  return {
    samples: 1,
    words: wordCount,
    sentences: sentences,
    questions: /\?/.test(trimmed) ? 1 : 0,
    imperatives: IMPERATIVE_START.test(trimmed) ? 1 : 0,
    bullets: usesBullets ? 1 : 0,
    numbered: usesNumbered ? 1 : 0,
    markdown: usesMarkdown ? 1 : 0,
    caps_emphasis: capsTokens.length > 0 ? 1 : 0,
    hedges: (trimmed.match(HEDGES) || []).length,
    courtesies: (trimmed.match(COURTESY) || []).length,
    abbrevs: abbrevTokens.length,
    // Length buckets rather than a stored list, so a median can be approximated
    // without keeping every sample. Buckets are message-length bands in words.
    bucket: wordCount < 8 ? 'terse' : wordCount < 25 ? 'short' : wordCount < 70 ? 'medium' : 'long',
    terms: terms
  };
}

function emptyProfile() {
  return {
    version: 1,
    samples: 0,
    total_words: 0,
    total_sentences: 0,
    questions: 0,
    imperatives: 0,
    bullets: 0,
    numbered: 0,
    markdown: 0,
    caps_emphasis: 0,
    hedges: 0,
    courtesies: 0,
    abbrevs: 0,
    buckets: { terse: 0, short: 0, medium: 0, long: 0 },
    terms: {}
  };
}

/**
 * Fold one observation into a profile. Returns a NEW object; the input is not
 * mutated, because a caller that keeps the old one for comparison must be able
 * to trust it.
 */
function mergeObservation(profile, obs) {
  const p = Object.assign(emptyProfile(), profile || {});
  p.buckets = Object.assign({ terse: 0, short: 0, medium: 0, long: 0 }, p.buckets || {});
  p.terms = Object.assign({}, p.terms || {});
  if (!obs || !obs.samples) return p;

  p.samples += obs.samples;
  p.total_words += obs.words || 0;
  p.total_sentences += obs.sentences || 0;
  ['questions', 'imperatives', 'bullets', 'numbered', 'markdown', 'caps_emphasis',
    'hedges', 'courtesies', 'abbrevs'].forEach(function (k) {
    p[k] += obs[k] || 0;
  });
  if (obs.bucket && p.buckets[obs.bucket] !== undefined) p.buckets[obs.bucket] += 1;

  for (const t in (obs.terms || {})) {
    if (Object.prototype.hasOwnProperty.call(obs.terms, t)) {
      p.terms[t] = (p.terms[t] || 0) + obs.terms[t];
    }
  }
  // Keep the tally bounded, or a long-lived profile grows without limit and the
  // row stops fitting a sane payload cap.
  //
  // THE CAP IS 400 AND NOT 60 BECAUSE OF ORDER-INDEPENDENCE, which the tests
  // caught. Evicting mid-stream makes the surviving set depend on the order
  // messages arrived: a term dropped early never returns even if it would have
  // outranked a survivor by the end. At 60 that fired on an ordinary six-message
  // corpus and two identical users got different vocabularies. At 400 a real
  // profile never reaches the cap, so the stored tally is order-independent in
  // practice, and the trim is deterministic (count desc, then alphabetical) so
  // behaviour above the cap is at least reproducible for a given tally.
  // Perfect order-independence would mean never evicting, which is unbounded;
  // this is the trade, stated rather than hidden.
  const kept = Object.keys(p.terms).sort(function (a, b) { return p.terms[b] - p.terms[a] || a.localeCompare(b); }).slice(0, 400);
  const trimmedTerms = {};
  kept.forEach(function (t) { trimmedTerms[t] = p.terms[t]; });
  p.terms = trimmedTerms;

  p.version = 1;
  return p;
}

function ratio(n, d) { return d > 0 ? n / d : 0; }

/** Derived view. Separate from the stored shape so storage stays counts-only. */
function summarise(profile) {
  const p = Object.assign(emptyProfile(), profile || {});
  const s = p.samples || 0;
  const buckets = Object.assign({ terse: 0, short: 0, medium: 0, long: 0 }, p.buckets || {});
  const dominant = Object.keys(buckets).sort(function (a, b) { return buckets[b] - buckets[a]; })[0];
  return {
    samples: s,
    avg_words: s ? p.total_words / s : 0,
    avg_sentence_words: p.total_sentences ? p.total_words / p.total_sentences : 0,
    question_ratio: ratio(p.questions, s),
    imperative_ratio: ratio(p.imperatives, s),
    bullet_ratio: ratio(p.bullets, s),
    numbered_ratio: ratio(p.numbered, s),
    markdown_ratio: ratio(p.markdown, s),
    caps_ratio: ratio(p.caps_emphasis, s),
    hedge_per_msg: ratio(p.hedges, s),
    courtesy_per_msg: ratio(p.courtesies, s),
    abbrev_per_msg: ratio(p.abbrevs, s),
    dominant_length: s ? dominant : null,
    top_terms: Object.keys(p.terms)
      .sort(function (a, b) { return p.terms[b] - p.terms[a] || a.localeCompare(b); })
      .slice(0, MAX_TERMS)
  };
}

/**
 * The prompt block. Returns '' below the confidence floor -- deliberately, so
 * the caller's existing behaviour is untouched until there is real evidence.
 *
 * `managerOverride` is the value a manager set on sd_employee_profiles. Declared
 * intent outranks observation, and when they disagree the block says so rather
 * than silently picking one.
 */
function renderStyleDirectives(profile, managerOverride) {
  const p = Object.assign(emptyProfile(), profile || {});
  if ((p.samples || 0) < MIN_SAMPLES) return '';
  const s = summarise(p);
  const out = [];

  // Length. Stated as a target, not a statistic -- a number in a prompt invites
  // the model to reason about the number instead of obeying it.
  const target = Math.round(Math.max(30, Math.min(400, s.avg_words * 6)));
  if (s.dominant_length === 'terse' || s.dominant_length === 'short') {
    out.push('This user writes short. Answer in roughly ' + target + ' words or fewer; lead with the answer, no preamble.');
  } else if (s.dominant_length === 'long') {
    out.push('This user writes at length and expects the same. Around ' + target + ' words is appropriate; give reasoning, not just conclusions.');
  } else {
    out.push('Aim for roughly ' + target + ' words.');
  }

  if (s.bullet_ratio >= 0.3 || s.numbered_ratio >= 0.3) {
    out.push('They use lists themselves — structure answers as lists where it fits.');
  } else if (s.bullet_ratio < 0.1 && s.numbered_ratio < 0.1) {
    out.push('They write in prose, not lists — prefer connected sentences over bullets.');
  }
  if (s.markdown_ratio >= 0.3) out.push('They use markdown; formatting is welcome.');

  if (s.imperative_ratio >= 0.5) {
    out.push('They give direct instructions. Match that: no hedging, no "you might consider".');
  }
  if (s.hedge_per_msg >= 0.6) {
    out.push('They hedge when unsure — flag genuine uncertainty rather than sounding certain.');
  }
  if (s.courtesy_per_msg >= 0.6) {
    out.push('Their register is polite; stay warm rather than clipped.');
  } else if (s.courtesy_per_msg < 0.15 && s.imperative_ratio >= 0.3) {
    out.push('Their register is terse and businesslike; skip pleasantries.');
  }
  if (s.caps_ratio >= 0.3) out.push('They use capitals for emphasis; strong emphasis in replies reads as normal to them.');
  // 0.3, not 1.5. A trade user dropping THH or LF into a THIRD of their messages
  // is a strong signal; requiring 1.5 per message meant the terse fabricator
  // corpus -- the exact user this feature is for -- scored 0.33 and was told
  // nothing. Caught by the test, not by reading the number.
  if (s.abbrev_per_msg >= 0.3) out.push('They use trade abbreviations freely — do not expand them.');

  if (s.top_terms.length >= 3) {
    out.push('Vocabulary they actually use: ' + s.top_terms.slice(0, 8).join(', ') + '. Prefer their words over synonyms.');
  }

  let header = '\n\nHOW THIS PERSON WRITES (observed over ' + s.samples + ' messages — adjust, do not caricature):\n';
  let body = out.map(function (l) { return '- ' + l; }).join('\n');

  if (managerOverride) {
    body += '\n- A manager has explicitly set this person\'s preferred style to "' + String(managerOverride) +
      '". That is a deliberate instruction and OUTRANKS the observations above wherever they conflict.';
  }
  return header + body;
}

module.exports = {
  MIN_SAMPLES,
  analyse,
  emptyProfile,
  mergeObservation,
  summarise,
  renderStyleDirectives
};

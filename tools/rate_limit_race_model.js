// tools/rate_limit_race_model.js
//
//   node tools/rate_limit_race_model.js
//   node tools/rate_limit_race_model.js --requests 4 --limit 2
//   node tools/rate_limit_race_model.js --json
//
// EVERY INTERLEAVING OF THE RATE LIMITER'S COUNT-THEN-INSERT. Item 78, second
// target -- the token-deduction concurrency bug, from
// docs/spec/RateLimitConsume.tla.
//
// ── WHY A MODEL AND NOT A TEST ─────────────────────────────────────────────
// The defect is not in any single execution. Every individual request reads a
// count, compares it to a limit and inserts -- and every one of those, ALONE,
// is correct. A test that runs the function proves exactly that and nothing
// about the thing that is wrong. THE FAULT ONLY EXISTS IN THE INTERLEAVING.
//
// So this enumerates every schedule. For N requests the racy path has 2N steps
// with a per-request order constraint, which is small enough that EXHAUSTIVE IS
// NOT A SAMPLE -- it is a proof over that bound. It then EXHIBITS the violating
// schedule rather than asserting one exists.
//
// ── WHAT IT IS MODELLING, FROM THE FILE'S OWN HEADER ──────────────────────
//   "N simultaneous requests all read the SAME count, all decide they are
//    under the limit, and all insert -- 50 requests arriving at count 199
//    against a limit of 200 were ALL permitted."
//
// AND IT IS THE PATH RUNNING TODAY. sql/sairn_ai_rate_limit_consume_fn.sql has
// never been run, so the RPC does not exist and api/_lib/ai-rate-limit.js falls
// back to the original count-then-insert. The file reports mode 'observe-racy'
// for exactly this reason.
//
// Exit 0 when the model agrees with the spec -- racy violates the cap, locked
// does not. Exit 1 if either half disagrees, because then the model, the spec
// or the code has moved and none of the three can be trusted until somebody
// says which. Exit 2 if it could not run.

'use strict';

const EXIT_CLEAN = 0, EXIT_FINDING = 1, EXIT_COULD_NOT_RUN = 2;

/**
 * Every interleaving of `n` requests through the RACY path.
 *
 * Each request takes two steps -- READ then DECIDE -- and a request's DECIDE
 * may only follow its own READ. Everything else is free, which is precisely
 * what "Vercel runs these concurrently" means.
 */
function enumerateRacy(n, limit) {
  let worst = 0;
  let witness = null;
  let schedules = 0;

  // state: rows, seen[], phase[]  (0 = not read, 1 = read, 2 = done)
  function step(rows, seen, phase, trace) {
    let anyMoved = false;
    for (let r = 0; r < n; r++) {
      if (phase[r] === 0) {
        anyMoved = true;
        const s2 = seen.slice(), p2 = phase.slice();
        s2[r] = rows; p2[r] = 1;
        step(rows, s2, p2, trace.concat(['R' + r + '(sees ' + rows + ')']));
      } else if (phase[r] === 1) {
        anyMoved = true;
        const p2 = phase.slice();
        p2[r] = 2;
        // THE DECISION IS MADE AGAINST WHAT THIS REQUEST READ, which by now
        // may be arbitrarily out of date. Nothing re-checks it. That single
        // line is the whole defect.
        if (seen[r] < limit) {
          step(rows + 1, seen, p2, trace.concat(['W' + r + '(insert, rows=' + (rows + 1) + ')']));
        } else {
          step(rows, seen, p2, trace.concat(['X' + r + '(refuse)']));
        }
      }
    }
    if (!anyMoved) {
      schedules++;
      if (rows > worst) { worst = rows; witness = trace; }
    }
  }
  step(0, new Array(n).fill(-1), new Array(n).fill(0), []);
  return { worst: worst, witness: witness, schedules: schedules };
}

/**
 * Every interleaving of `n` requests through the LOCKED path.
 *
 * One atomic step each -- the advisory lock means no other request can observe
 * or act on the count in between -- so the only freedom left is the ORDER, and
 * order cannot change the outcome. Enumerated anyway rather than reasoned
 * about, because "it is obviously fine" is how the racy version shipped.
 */
function enumerateLocked(n, limit) {
  let worst = 0;
  let schedules = 0;
  function step(rows, remaining) {
    if (!remaining.length) { schedules++; if (rows > worst) worst = rows; return; }
    for (let i = 0; i < remaining.length; i++) {
      const rest = remaining.slice(0, i).concat(remaining.slice(i + 1));
      step(rows < limit ? rows + 1 : rows, rest);
    }
  }
  step(0, Array.from({ length: n }, (_, i) => i));
  return { worst: worst, schedules: schedules };
}

function main(argv) {
  const arg = (name, dflt) => {
    const i = argv.indexOf('--' + name);
    if (i === -1) return dflt;
    const v = Number(argv[i + 1]);
    return isFinite(v) ? v : dflt;
  };
  const n = arg('requests', 3);
  const limit = arg('limit', 2);
  if (!(n >= 1 && n <= 7) || !(limit >= 1)) {
    console.error('COULD NOT RUN: --requests must be 1..7 and --limit >= 1. '
      + 'Above seven the enumeration stops being something you wait for, and a '
      + 'bound nobody states is how a "exhaustive" claim becomes a sampled one.');
    return EXIT_COULD_NOT_RUN;
  }

  const racy = enumerateRacy(n, limit);
  const locked = enumerateLocked(n, limit);
  const racyViolates = racy.worst > limit;
  const lockedHolds = locked.worst <= limit;

  if (argv.indexOf('--json') !== -1) {
    console.log(JSON.stringify({
      requests: n, limit: limit,
      racy: { schedules: racy.schedules, worst: racy.worst, violates: racyViolates,
              witness: racy.witness },
      locked: { schedules: locked.schedules, worst: locked.worst, holds: lockedHolds }
    }, null, 2));
  } else {
    console.log('RATE LIMIT INTERLEAVINGS -- docs/spec/RateLimitConsume.tla');
    console.log('  requests in flight : %d', n);
    console.log('  limit              : %d', limit);
    console.log('');
    console.log('  RACY (count-then-insert -- THE PATH RUNNING TODAY, because');
    console.log('        sql/sairn_ai_rate_limit_consume_fn.sql has never been run)');
    console.log('    schedules enumerated : %d  (every one, not a sample)', racy.schedules);
    console.log('    worst-case recorded  : %d against a limit of %d', racy.worst, limit);
    if (racyViolates) {
      console.log('    CapHolds VIOLATED. The schedule that does it:');
      for (const s of racy.witness) console.log('      ' + s);
      console.log('    ^ every request read a count that was true when it read it.');
      console.log('      No individual step is wrong. That is why a test cannot');
      console.log('      find this and why it needed a specification.');
    }
    console.log('');
    console.log('  LOCKED (one RPC, pg_advisory_xact_lock)');
    console.log('    schedules enumerated : %d', locked.schedules);
    console.log('    worst-case recorded  : %d', locked.worst);
    console.log('    CapHolds %s', lockedHolds ? 'holds in every schedule' : 'VIOLATED');
    console.log('');
    // The overshoot is bounded by requests in flight, NOT by the window and not
    // by anything an operator sets. "It is racy" and "it is unbounded" are
    // different claims and the difference decides how urgent this is.
    console.log('  Overshoot is bounded by requests in flight (%d here), not by the',
                n);
    console.log('  window and not by any setting. Racy is not the same as unbounded.');
    console.log('');
    if (racyViolates && lockedHolds) {
      console.log('MODEL AGREES WITH THE SPEC: the racy path violates the cap and the');
      console.log('locked path does not. Nothing here says which is deployed -- read');
      console.log('the mode the endpoint returns: observe-racy / enforce-racy means');
      console.log('the fallback, and enforcing an approximate limit is the worst of');
      console.log('both worlds.');
    } else {
      console.log('MODEL DISAGREES WITH THE SPEC. Either the model, the spec or the');
      console.log('code has moved, and none of the three can be trusted until');
      console.log('somebody says which.');
    }
  }
  return (racyViolates && lockedHolds) ? EXIT_CLEAN : EXIT_FINDING;
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = { enumerateRacy, enumerateLocked, main };

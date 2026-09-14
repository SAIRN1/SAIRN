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
// WHICH PATH IS RUNNING TODAY IS NOT SOMETHING THIS FILE CAN SAY, and it used
// to say it anyway. It claimed sql/sairn_ai_rate_limit_consume_fn.sql "has
// never been run", sourced from db/schema_snapshot.json -- and that snapshot
// contains TABLES ONLY. 384 table->column entries, a _constraints map and a
// timestamp; no functions, no routines, nothing a CREATE FUNCTION would ever
// appear in. A zero there is NOT CAPTURED, not NOT RUN, and the two were
// folded together. Corrected 2026-09-14 (fourth), against my own claim.
//
// The deployed state is readable in exactly one place and this is not it: the
// mode the endpoint returns. 'observe-racy' / 'enforce-racy' means the fallback
// is live; 'observe' / 'enforce' means the RPC answered. Read that, or call the
// RPC directly with a service-role key. Neither is available from a clone with
// no credentials, which is why this file now declines to say.
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

/**
 * The locked path AGAIN, with the one thing the model above assumed.
 *
 * ── THE ASSUMPTION enumerateLocked() MAKES, WHICH IT NEVER CHECKS ──────────
 * It collapses each request into ONE atomic step, on the grounds that "the
 * advisory lock means no other request can observe or act on the count in
 * between". That is true of the WRITE. It is not automatically true of the
 * READ, and the difference is the transaction's SNAPSHOT.
 *
 * `pg_advisory_xact_lock` serialises ACQUISITION. It does not move the
 * snapshot. Under READ COMMITTED a fresh snapshot is taken per statement, so
 * the `select count(*)` after the lock sees everything committed before it and
 * the collapse is sound. Under REPEATABLE READ or SERIALIZABLE the snapshot is
 * taken once, at the transaction's first data statement, and a caller that
 * waited on the lock still counts against a snapshot from BEFORE the holder
 * committed. It then inserts, and the cap over-runs -- with the lock working
 * perfectly the entire time.
 *
 * So `sairn_ai_rate_limit_consume` is correct BECAUSE the isolation level is
 * read committed, and nothing in the function, the client or the spec said so.
 * This enumerator is what turns that from an unexamined assumption into a
 * stated, failing-if-violated precondition: it models exactly that schedule
 * and shows the cap break.
 */
function enumerateLockedStaleSnapshot(n, limit) {
  let worst = 0;
  let witness = null;
  let schedules = 0;

  // Each request: SNAP (take its snapshot) then RUN (acquire the lock, count
  // against its OWN snapshot, insert). RUN must follow that request's SNAP;
  // RUNs are serialised by the lock, SNAPs are free. That is the whole
  // difference from enumerateLocked(), which has no SNAP step at all.
  function step(rows, snap, phase, trace) {
    let moved = false;
    for (let r = 0; r < n; r++) {
      if (phase[r] === 0) {
        moved = true;
        const s2 = snap.slice(), p2 = phase.slice();
        s2[r] = rows; p2[r] = 1;
        step(rows, s2, p2, trace.concat(['S' + r + '(snapshot at ' + rows + ')']));
      } else if (phase[r] === 1) {
        moved = true;
        const p2 = phase.slice();
        p2[r] = 2;
        // The lock is HELD here and is doing its job. The count is still read
        // through this request's own snapshot.
        if (snap[r] < limit) {
          step(rows + 1, snap, p2,
               trace.concat(['L' + r + '(lock, counts ' + snap[r] + ', rows=' + (rows + 1) + ')']));
        } else {
          step(rows, snap, p2, trace.concat(['L' + r + '(lock, counts ' + snap[r] + ', refuse)']));
        }
      }
    }
    if (!moved) {
      schedules++;
      if (rows > worst) { worst = rows; witness = trace; }
    }
  }
  step(0, new Array(n).fill(-1), new Array(n).fill(0), []);
  return { worst: worst, witness: witness, schedules: schedules };
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
  const stale = enumerateLockedStaleSnapshot(n, limit);
  const racyViolates = racy.worst > limit;
  const lockedHolds = locked.worst <= limit;
  // A THIRD VERDICT, and it is about the ASSUMPTION rather than the code. If
  // this ever stops violating, the model has stopped modelling a stale
  // snapshot and the precondition below is no longer being demonstrated.
  const staleViolates = stale.worst > limit;

  if (argv.indexOf('--json') !== -1) {
    console.log(JSON.stringify({
      requests: n, limit: limit,
      racy: { schedules: racy.schedules, worst: racy.worst, violates: racyViolates,
              witness: racy.witness },
      locked: { schedules: locked.schedules, worst: locked.worst, holds: lockedHolds },
      lockedStaleSnapshot: { schedules: stale.schedules, worst: stale.worst,
                             violates: staleViolates, witness: stale.witness }
    }, null, 2));
  } else {
    console.log('RATE LIMIT INTERLEAVINGS -- docs/spec/RateLimitConsume.tla');
    console.log('  requests in flight : %d', n);
    console.log('  limit              : %d', limit);
    console.log('');
    console.log('  RACY (count-then-insert -- the fallback in');
    console.log('        api/_lib/ai-rate-limit.js. WHETHER IT IS THE PATH');
    console.log('        RUNNING TODAY is not knowable from this repo: the');
    console.log('        schema snapshot carries tables only and has never');
    console.log('        held a function. Read the mode the endpoint returns.)');
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
    console.log('  LOCKED, BUT WITH A SNAPSHOT TAKEN BEFORE THE LOCK');
    console.log('    ...which is what REPEATABLE READ or SERIALIZABLE gives you.');
    console.log('    The lock still serialises perfectly; the COUNT is read');
    console.log('    through a snapshot from before the holder committed.');
    console.log('    schedules enumerated : %d', stale.schedules);
    console.log('    worst-case recorded  : %d against a limit of %d',
                stale.worst, limit);
    if (staleViolates) {
      console.log('    CapHolds VIOLATED. The schedule that does it:');
      for (const s of stale.witness) console.log('      ' + s);
      console.log('    ^ THE LOCK IS WORKING IN EVERY STEP OF THAT TRACE.');
      console.log('      So the fix is correct BECAUSE the isolation level is');
      console.log('      read committed -- a precondition the function did not');
      console.log('      state and did not check. It does now: the SQL raises');
      console.log('      rather than returning a number it cannot stand behind.');
    } else {
      console.log('    NOT VIOLATED -- which means this enumerator has stopped');
      console.log('    modelling a stale snapshot. It is meant to fail. Read it');
      console.log('    before believing the precondition is unnecessary.');
    }
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
  // THREE CONDITIONS, NOT TWO. The third is the one added on 2026-09-14: the
  // stale-snapshot enumerator MUST violate, because it is the demonstration
  // that read-committed is load-bearing. An enumerator that quietly stopped
  // violating would leave the precondition looking proven when nothing had
  // proved it.
  return (racyViolates && lockedHolds && staleViolates) ? EXIT_CLEAN : EXIT_FINDING;
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));
module.exports = {
  enumerateRacy, enumerateLocked, enumerateLockedStaleSnapshot, main
};

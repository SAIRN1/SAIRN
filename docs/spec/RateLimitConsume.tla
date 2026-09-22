------------------------- MODULE RateLimitConsume -------------------------
(***************************************************************************)
(* The AI rate limiter's count-then-insert, stated formally. Item 78,      *)
(* second target -- the token-deduction concurrency bug.                   *)
(*                                                                         *)
(* WHY THIS ONE NEEDS A SPEC AND NOT A TEST. The defect is not in any      *)
(* single execution. Every individual request reads a count, compares it   *)
(* to a limit, and inserts -- and every one of those, ALONE, is correct.   *)
(* A test that runs the function proves exactly that and nothing about the *)
(* thing that is wrong. The fault only exists in the INTERLEAVING, and a   *)
(* property over all interleavings is what a specification is for.         *)
(*                                                                         *)
(* THE REAL INCIDENT, from api/_lib/ai-rate-limit.js's own header:         *)
(*                                                                         *)
(*   "N simultaneous requests all read the SAME count, all decide they are *)
(*    under the limit, and all insert -- 50 requests arriving at count 199 *)
(*    against a limit of 200 were ALL permitted."                          *)
(*                                                                         *)
(* AND THE PART THAT MAKES THIS LIVE RATHER THAN HISTORICAL:               *)
(* sql/sairn_ai_rate_limit_consume_fn.sql HAS NEVER BEEN RUN. Checked      *)
(* 2026-09-14 against db/schema_snapshot.json. So the RPC does not exist,  *)
(* the code falls back to the original count-then-insert, and THE RACY     *)
(* PATH IS THE ONE RUNNING TODAY. The file says so itself and reports mode *)
(* 'observe-racy' so the race is visible in the return value rather than   *)
(* being a silent property of the deployment.                              *)
(*                                                                         *)
(* NOT MODEL-CHECKED HERE. No Java and no TLC on this machine, verified    *)
(* 2026-09-14. tools/rate_limit_race_model.js enumerates EVERY INTERLEAVING*)
(* of a small number of requests instead -- which for this property is not *)
(* a sample but a proof over that bound -- and exhibits the violating      *)
(* schedule rather than asserting one exists.                              *)
(***************************************************************************)
\* Integers, NOT Naturals (fixed 2026-09-22). Line 46 defines NoRead == -1
\* and Naturals has NO UNARY MINUS, so this spec DID NOT PARSE: TLC stopped
\* at "Couldnt resolve prefix operator -." before generating a single state.
\* Found the first time it was run through a model checker.
EXTENDS Integers, FiniteSets

CONSTANTS
    Requests,   \* the concurrent callers
    Limit       \* calls permitted per window

ASSUME Limit \in Nat /\ Limit > 0

VARIABLES
    rows,       \* how many calls have been RECORDED
    seen,       \* [Requests -> Nat \cup {NoRead}]  what each request READ
    done        \* the requests that have finished

NoRead == -1
vars == <<rows, seen, done>>

TypeOK ==
    /\ rows \in Nat
    /\ seen \in [Requests -> Nat \cup {NoRead}]
    /\ done \subseteq Requests

Init ==
    /\ rows = 0
    /\ seen = [r \in Requests |-> NoRead]
    /\ done = {}

(***************************************************************************)
(* THE RACY PATH -- TWO STEPS, AND THE GAP BETWEEN THEM IS THE BUG.        *)
(* This is the live behaviour today, because the RPC migration has not     *)
(* been run.                                                               *)
(***************************************************************************)
RacyRead(r) ==
    /\ r \notin done
    /\ seen[r] = NoRead
    /\ seen' = [seen EXCEPT ![r] = rows]
    /\ UNCHANGED <<rows, done>>

RacyInsert(r) ==
    /\ r \notin done
    /\ seen[r] # NoRead
    \* The decision is made against what THIS request read, which by now may
    \* be arbitrarily out of date. Nothing re-checks it.
    /\ seen[r] < Limit
    /\ rows' = rows + 1
    /\ done' = done \cup {r}
    /\ UNCHANGED seen

RacyRefuse(r) ==
    /\ r \notin done
    /\ seen[r] # NoRead
    /\ seen[r] >= Limit
    /\ done' = done \cup {r}
    /\ UNCHANGED <<rows, seen>>

RacyNext ==
    \E r \in Requests : RacyRead(r) \/ RacyInsert(r) \/ RacyRefuse(r)

RacySpec == Init /\ [][RacyNext]_vars

(***************************************************************************)
(* THE LOCKED PATH -- ONE STEP. public.sairn_ai_rate_limit_consume() takes *)
(* a pg_advisory_xact_lock keyed on the app_id and does the count and the  *)
(* insert inside ONE transaction, so no other request can observe or act   *)
(* on the count in between.                                                *)
(***************************************************************************)
LockedConsume(r) ==
    /\ r \notin done
    /\ IF rows < Limit
         THEN /\ rows' = rows + 1
              /\ seen' = [seen EXCEPT ![r] = rows]
         ELSE /\ UNCHANGED rows
              /\ seen' = [seen EXCEPT ![r] = rows]
    /\ done' = done \cup {r}

LockedNext == \E r \in Requests : LockedConsume(r)

LockedSpec == Init /\ [][LockedNext]_vars

(***************************************************************************)
(* THE ASSUMPTION LockedConsume MAKES, NOW WRITTEN DOWN. Added 2026-09-14. *)
(*                                                                         *)
(* "no other request can observe or act on the count in between" is true   *)
(* of the INSERT because of the lock. It is true of the COUNT only because *)
(* of the ISOLATION LEVEL, and that was nowhere stated.                    *)
(*                                                                         *)
(* pg_advisory_xact_lock serialises ACQUISITION; it does not move the      *)
(* transaction's SNAPSHOT. Under read committed each statement takes a     *)
(* fresh snapshot, so the count after the lock sees the previous holder's  *)
(* committed row and collapsing the request to one step is sound. Under    *)
(* repeatable read or serializable the snapshot is taken once, before the  *)
(* wait, and a caller that waited on the lock counts against a world in    *)
(* which the holder had not yet committed.                                 *)
(*                                                                         *)
(* StaleSnapshotConsume is that, as two steps -- the snapshot and the      *)
(* locked run -- which is exactly the shape RacyConsume has. The lock      *)
(* removes the interleaving of the WRITE and changes nothing about the     *)
(* READ, so the counterexample survives:                                   *)
(*                                                                         *)
(*   StaleSnapshotSpec => []CapHolds     is FALSE                          *)
(*                                                                         *)
(* THE FUNCTION NOW REFUSES TO RUN OUTSIDE READ COMMITTED rather than      *)
(* relying on nobody changing it. A precondition that is only true because *)
(* nobody has touched a setting is not a precondition, it is a habit.      *)
(***************************************************************************)
StaleSnapshotSnap(r) ==
    /\ seen[r] = NoRead
    /\ seen' = [seen EXCEPT ![r] = rows]
    /\ UNCHANGED <<rows, done>>

StaleSnapshotRun(r) ==
    /\ seen[r] # NoRead
    /\ r \notin done
    /\ IF seen[r] < Limit
         THEN rows' = rows + 1
         ELSE UNCHANGED rows
    /\ done' = done \cup {r}
    /\ UNCHANGED seen

StaleSnapshotNext ==
    \E r \in Requests : StaleSnapshotSnap(r) \/ StaleSnapshotRun(r)

StaleSnapshotSpec == Init /\ [][StaleSnapshotNext]_vars

(***************************************************************************)
(* THE PROPERTY. It is one line, and it is the whole disagreement between  *)
(* the two specs.                                                          *)
(*                                                                         *)
(*   LockedSpec => []CapHolds     is true                                  *)
(*   RacySpec   => []CapHolds     is FALSE, and the counterexample is a    *)
(*                                schedule with as few as two requests     *)
(*                                                                         *)
(* A test cannot tell these two apart, because both satisfy it on every    *)
(* SEQUENTIAL run.                                                         *)
(***************************************************************************)
CapHolds == rows <= Limit

(***************************************************************************)
(* AND THE WEAKER PROPERTY THE RACY PATH DOES STILL HAVE, stated because   *)
(* "it is racy" is not the same as "it is unbounded" and the difference    *)
(* decides how urgent this is. No request inserts more than once, so the   *)
(* overshoot is bounded by the number of requests in flight -- not by the  *)
(* window, and not by anything the operator sets.                          *)
(***************************************************************************)
BoundedOvershoot == rows <= Limit + Cardinality(Requests)

(***************************************************************************)
(* WHY OBSERVE MODE IS NOT A MITIGATION, and this is the operational       *)
(* point the spec exists to make precise:                                  *)
(*                                                                         *)
(* In observe mode nothing is refused, so CapHolds is irrelevant and the   *)
(* race costs nothing. The moment SAIRN_AI_RATE_LIMIT_MODE=enforce is set  *)
(* while the fallback is live, the SAME schedule that was harmless becomes *)
(* a limit that LOOKS enforced and is not -- which the file's own header   *)
(* calls the worst of both worlds. The spec says exactly why: enforcement  *)
(* changes which states are reachable, not which are correct.              *)
(***************************************************************************)

=============================================================================

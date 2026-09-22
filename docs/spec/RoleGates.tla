---------------------------- MODULE RoleGates ----------------------------
(***************************************************************************)
(* SAIRN's cross-app role gates, stated formally. Item 78.                 *)
(*                                                                         *)
(* WHY THIS CLASS OF CODE. AWS's strongest real formal-methods win is      *)
(* Cedar -- an authorization engine whose core was specified and proved    *)
(* rather than reviewed -- because authorization is the rare place where   *)
(* the rules are small enough to state exactly and the cost of a wrong     *)
(* answer is unbounded. SAIRN's role gates are that shape: sixteen apps,   *)
(* a handful of roles each, and a wrong answer is somebody reading a       *)
(* controlled-substance register or an attorney trust balance.             *)
(*                                                                         *)
(* WHAT THIS SPEC IS FOR, AND WHAT IT IS NOT.                              *)
(*                                                                         *)
(*   IT IS      a statement of the properties the gates are supposed to    *)
(*              have, precise enough that a violation is a fact rather     *)
(*              than an opinion, and separated into the ones that MUST     *)
(*              hold and the ones that merely DO hold today.               *)
(*                                                                         *)
(*   IT IS NOT  a proof about the JavaScript. TLA+ specifies a model; the  *)
(*              code is not derived from it and nothing checks that the    *)
(*              model matches. tools/role_gate_invariants.js closes that   *)
(*              gap from the other end -- it reads the REAL exported role  *)
(*              sets out of api/*-auth.js and checks these same invariants *)
(*              exhaustively. Neither alone is enough; the spec says what  *)
(*              is true and the checker says the code still agrees.        *)
(*                                                                         *)
(* NOT MODEL-CHECKED HERE. No Java and no TLC on this machine, verified    *)
(* 2026-09-14 -- so this file has NOT been run through a model checker and *)
(* must not be described as verified. The invariants below were instead    *)
(* checked exhaustively against the real role sets by the companion tool,  *)
(* over a state space small enough that exhaustive IS the check: sixteen   *)
(* apps by at most six roles. That is a real result and it is a DIFFERENT  *)
(* result from TLC's; running TLC would additionally check the spec        *)
(* against ITSELF, which is the half nobody has done.                      *)
(***************************************************************************)
EXTENDS FiniteSets, Naturals

CONSTANTS
    Apps,        \* the sixteen api/*-auth.js modules
    Roles,       \* every role name appearing anywhere: owner, admin, dvm, ...
    Employees,
    \* Per-app role sets, read from the modules. A function App -> SUBSET Roles.
    Provisioning,
    Management,
    Authenticated,
    BroadRead,
    \* Added 2026-09-14 with I6. Vocabulary is ROLES_BY_APP in api/_lib/auth.js
    \* -- the one place every auth handler already keys into. StatedAuthenticated
    \* is the subset of Apps that write AUTHENTICATED_ROLES down themselves, and
    \* it exists so I6 is checked against evidence rather than against the
    \* derivation it licenses.
    Vocabulary,
    StatedAuthenticated

VARIABLES
    active,      \* [Employees -> BOOLEAN]   is the credential still live
    roleOf,      \* [Employees -> Roles]
    appOf,       \* [Employees -> Apps]      which app the credential belongs to
    session      \* [Employees -> Apps \cup {NoApp}]  which app a token was minted for

\* NoApp WAS AN UNBOUNDED CHOOSE AND TLC CANNOT EVALUATE ONE (fixed
\* 2026-09-22, the first time this spec was actually run through a model
\* checker). It read:
\*
\*     NoApp == CHOOSE x : x \notin Apps
\*
\* CHOOSE with no set to range over has nothing to enumerate, so TLC stops
\* at "attempted to evaluate an unbounded CHOOSE" while computing the
\* INITIAL STATES -- 0 states generated. The spec could not be checked at
\* all, which is exactly what "NOT MODEL-CHECKED" in the open-work row
\* meant and nobody had yet discovered was blocking rather than merely
\* undone.
\*
\* A CONSTANT with an ASSUME is the standard way to spell "some value
\* outside Apps": the model supplies it, and the ASSUME keeps the claim
\* honest instead of leaving it implied.
CONSTANT NoApp
ASSUME NoApp \notin Apps

vars == <<active, roleOf, appOf, session>>

TypeOK ==
    /\ active \in [Employees -> BOOLEAN]
    /\ roleOf \in [Employees -> Roles]
    /\ appOf  \in [Employees -> Apps]
    /\ session \in [Employees -> Apps \cup {NoApp}]

(***************************************************************************)
(* THE GATE. Every endpoint on this platform asks the same three questions *)
(* in the same order, and the ORDER IS PART OF THE PROPERTY: an app check  *)
(* that runs after a role check leaks which roles exist in another app.    *)
(***************************************************************************)
Passes(e, app, allowed) ==
    /\ session[e] = app          \* the token was minted FOR THIS APP
    /\ active[e]                 \* the credential is still live
    /\ roleOf[e] \in allowed[app]

(***************************************************************************)
(* I1  APP ISOLATION. A token minted for one app can never pass a gate in  *)
(*     another, whatever the role is called. This is the one that matters  *)
(*     most and the one a shared role vocabulary quietly erodes: `owner`   *)
(*     means something in all sixteen apps, and nothing about the STRING   *)
(*     distinguishes them.                                                 *)
(***************************************************************************)
AppIsolation ==
    \A e \in Employees, a \in Apps :
        (session[e] # a) => ~Passes(e, a, Authenticated)

(***************************************************************************)
(* I2  DEACTIVATION IS IMMEDIATE AT THE GATE. A signed token outlives the  *)
(*     credential it was minted from -- by up to twelve hours here -- so   *)
(*     the gate must consult liveness, not the token's claim about it.     *)
(***************************************************************************)
DeactivationBinds ==
    \A e \in Employees, a \in Apps :
        ~active[e] => ~Passes(e, a, Authenticated)

(***************************************************************************)
(* I3  PROVISIONING IS THE NARROWEST GATE. Whoever may create credentials  *)
(*     must already be management. The converse is NOT required and does   *)
(*     not hold: SAIRNvet's `manager` is management and cannot prescribe.  *)
(***************************************************************************)
ProvisioningIsManagement ==
    \A a \in Apps : Provisioning[a] \subseteq Management[a]

(***************************************************************************)
(* I4  MANAGEMENT CAN SIGN IN. A role that gates a management action and   *)
(*     is not in the app's authenticated set is a gate nobody can pass --  *)
(*     which reads as "locked down" and is "broken".                       *)
(***************************************************************************)
ManagementIsAuthenticated ==
    \A a \in Apps : Management[a] \subseteq Authenticated[a]

(***************************************************************************)
(* I5  NO EMPTY GATE. An empty allowed-set is not a strict gate; it is a   *)
(*     door with no key, and whether that reads as refuse-all or allow-all *)
(*     depends on how the predicate was written -- which is exactly the    *)
(*     kind of thing nobody notices until it is the wrong one.             *)
(***************************************************************************)
NoEmptyGate ==
    \A a \in Apps :
        /\ Authenticated[a] # {}
        /\ Management[a] # {}

(***************************************************************************)
(* I6  WHO MAY SIGN IN *IS* THE APP'S ROLE VOCABULARY. Added 2026-09-14.   *)
(*                                                                         *)
(*     This one is different from I3-I5 in kind, and the difference is the *)
(*     point. I3-I5 are properties the gates must have. I6 is the          *)
(*     ASSUMPTION that lets the companion checker read Authenticated[a]    *)
(*     for the fourteen apps that never write it down -- it takes them     *)
(*     from ROLES_BY_APP in api/_lib/auth.js instead.                      *)
(*                                                                         *)
(*     An assumption a tool relies on and nobody checks is how a checker   *)
(*     grows coverage by getting less true. So it is stated here as an     *)
(*     invariant and checked against the two apps that DO write            *)
(*     AUTHENTICATED_ROLES down. If it ever fails, every derived           *)
(*     Authenticated[a] is withdrawn platform-wide and those checks go     *)
(*     back to not-checkable -- a derivation whose licence has lapsed must *)
(*     stop answering rather than keep answering.                          *)
(*                                                                         *)
(*     Stated over StatedAuthenticated, the apps that declare it, because  *)
(*     asserting it over every app would be asserting the derivation       *)
(*     against itself.                                                     *)
(***************************************************************************)
AuthenticatedMatchesVocabulary ==
    \A a \in StatedAuthenticated : Authenticated[a] = Vocabulary[a]

(***************************************************************************)
(* AND ONE THAT IS DELIBERATELY *NOT* AN INVARIANT.                        *)
(*                                                                         *)
(* In SAIRNroofing today, Management \subseteq BroadRead. That makes the   *)
(* predicate `~management /\ ~broad` IDENTICAL to `~broad` at all 22 sites *)
(* that spell it out -- so the management term is redundant, today.        *)
(*                                                                         *)
(* It is stated as an OBSERVATION rather than a requirement because the    *)
(* day a management role is added that is not a broad reader, the meaning  *)
(* of all 22 changes AT ONCE, silently, and every one of them starts       *)
(* answering a different question. The point of writing it down is that    *)
(* the change becomes visible as a spec edit instead of arriving as        *)
(* behaviour.                                                              *)
(***************************************************************************)
ManagementCurrentlySubsetOfBroadRead ==
    \A a \in DOMAIN BroadRead : Management[a] \subseteq BroadRead[a]

Safety ==
    /\ TypeOK
    /\ AppIsolation
    /\ DeactivationBinds
    /\ ProvisioningIsManagement
    /\ ManagementIsAuthenticated
    /\ NoEmptyGate
    /\ AuthenticatedMatchesVocabulary

(***************************************************************************)
(* Transitions. Only the ones that can move a gate's answer.               *)
(***************************************************************************)
Init ==
    /\ active  = [e \in Employees |-> TRUE]
    /\ roleOf  \in [Employees -> Roles]
    /\ appOf   \in [Employees -> Apps]
    /\ session = [e \in Employees |-> NoApp]

SignIn(e) ==
    /\ active[e]
    /\ session' = [session EXCEPT ![e] = appOf[e]]
    /\ UNCHANGED <<active, roleOf, appOf>>

Deactivate(e) ==
    \* NOTE: the SESSION IS NOT CLEARED. That is the real system -- a signed
    \* token stays valid until it expires -- and it is why DeactivationBinds
    \* has to be checked at the gate rather than at sign-out.
    /\ active' = [active EXCEPT ![e] = FALSE]
    /\ UNCHANGED <<roleOf, appOf, session>>

ChangeRole(e, r) ==
    /\ r \in Roles
    /\ roleOf' = [roleOf EXCEPT ![e] = r]
    /\ UNCHANGED <<active, appOf, session>>

Next ==
    \/ \E e \in Employees : SignIn(e)
    \/ \E e \in Employees : Deactivate(e)
    \/ \E e \in Employees, r \in Roles : ChangeRole(e, r)

Spec == Init /\ [][Next]_vars

=============================================================================

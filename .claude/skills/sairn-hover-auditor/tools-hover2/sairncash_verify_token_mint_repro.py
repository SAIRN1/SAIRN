#!/usr/bin/env python
"""sairncash_verify_token_mint_repro.py -- this role's OWN static repro for
a bearer-ID-to-auth-token escalation found during the undirected sweep
(batch L, SAIRNcash, first-ever hover2 pass on this vertical).

GOAL: confirm, by direct source read, that api/sairncash/verify.js's
`subscriptionId` branch mints a Firebase custom auth token
(`mintFirebaseToken(customerId)` -> `firebase-admin.js`'s
`admin.auth().createCustomToken(uid)`) for whoever supplies a bare,
ALREADY-ACTIVE Stripe subscription id, with NO check that the caller is
the subscription's own owner beyond Stripe confirming the id itself is
real and active.

WHY THIS IS A FINDING AND NOT JUST THE SAME DISCLOSED RISK AS portal.js:
portal.js's own header already discloses and accepts "possession of a
subscription id is a real credential" for BILLING PORTAL access (view
invoices, update card, cancel) -- a bounded, Stripe-hosted surface.
verify.js's subscriptionId branch hands out STRICTLY MORE for the exact
same bearer-knowledge: the customer's email+name (PII) AND a minted
Firebase custom token, which the token-minting module's OWN header
(api/_lib/firebase-admin.js:66-73) states should only be produced for "a
customer this request already proved ownership of via a real trial/
license check higher up the call stack." Subscription-id knowledge is
NOT an ownership proof by that module's own stated standard -- it is
exactly the bearer-knowledge-only shape the module's comment says the
caller must NOT rely on alone. This is an internal inconsistency between
what firebase-admin.js documents as its precondition and what verify.js
actually supplies, not merely a restatement of portal.js's accepted
tradeoff.

NON-GOALS: this does not assert anything about the `sessionId` branch
(a short-lived, one-time Stripe Checkout token returned only to the
browser that just completed payment, not a reusable, persistent, leak-
prone credential the way a subscriptionId is) -- that branch is a
different, much lower-risk shape and is deliberately out of scope here.
Does not assert anything about trial-verify.js's `trialToken` path,
which is a server-generated-and-stored random token with its own
different threat model, not examined this pass.

ALTERNATIVES CONSIDERED:
  1. Attempt a live call against the real SAIRNcash deployment -- rejected,
     NO BUILDER EXECUTION / no live traffic is the standing rule for this
     role, and this would require a real Stripe subscription id this role
     does not have a legitimate way to obtain.
  2. Trace whether the FRONT END (sairncash.html) ever exposes a
     subscriptionId to anything other than its own owner -- out of scope
     for a static check of the SERVER'S OWN gate; the server-side gap
     exists regardless of how disciplined the client is, which is the
     same "the identifier the caller can edit is the vulnerability"
     principle portal.js's own comment already names.

Read-only against api/sairncash/verify.js and api/_lib/firebase-admin.js.
Writes nothing.
"""
import argparse
import os
import re
import sys

SUBSCRIPTION_BRANCH_RE = re.compile(
    r"stripe\.subscriptions\.retrieve\(subscriptionId.*?\n(.*?)\n\};",
    re.S)
OWNERSHIP_CHECK_HINTS = re.compile(
    r"session|req\.headers\.authorization|verifySessionToken|req\.cookies|"
    r"ownerEmail|matchesEmail|req\.user", re.I)


def analyze(verify_src, firebase_admin_src):
    out = {'subscription_branch_found': False, 'mints_token': False,
           'has_ownership_check': None, 'firebase_admin_states_precondition': False}
    m = SUBSCRIPTION_BRANCH_RE.search(verify_src)
    if not m:
        return out
    out['subscription_branch_found'] = True
    branch = m.group(1)
    out['mints_token'] = 'mintFirebaseToken(customerId)' in branch
    out['has_ownership_check'] = bool(OWNERSHIP_CHECK_HINTS.search(branch))
    out['firebase_admin_states_precondition'] = (
        'already proved ownership' in firebase_admin_src
        or 'real trial/license check' in firebase_admin_src)
    return out


def selftest():
    fx_vulnerable_verify = """
module.exports = async (req, res) => {
  const sub = await stripe.subscriptions.retrieve(subscriptionId, { expand: ['customer'] });
  const active = sub.status === 'active';
  const customerId = sub.customer;
  res.status(200).json({
    valid: true,
    firebaseToken: await mintFirebaseToken(customerId)
  });
};
"""
    fx_fixed_verify = """
module.exports = async (req, res) => {
  const sub = await stripe.subscriptions.retrieve(subscriptionId, { expand: ['customer'] });
  const active = sub.status === 'active';
  const session = verifySessionToken(tokenFromRequest(req));
  if (!session) { res.status(401).json({ error: 'sign in first' }); return; }
  const customerId = sub.customer;
  res.status(200).json({
    valid: true,
    firebaseToken: await mintFirebaseToken(customerId)
  });
};
"""
    fx_firebase_admin = """
// uid is always customerId... trusted by RTDB rules as exactly "the
// customer this request already proved ownership of via a real trial/
// license check higher up the call stack."
"""
    v1 = analyze(fx_vulnerable_verify, fx_firebase_admin)
    v2 = analyze(fx_fixed_verify, fx_firebase_admin)
    ok = (v1['subscription_branch_found'] and v1['mints_token'] and
          v1['has_ownership_check'] is False and
          v1['firebase_admin_states_precondition'] and
          v2['has_ownership_check'] is True)
    print('SELFTEST %s: vulnerable has_ownership_check=%r, fixed has_ownership_check=%r' %
          ('PASS' if ok else 'FAIL', v1['has_ownership_check'], v2['has_ownership_check']))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())

    verify_path = os.path.join(args.repo, 'api', 'sairncash', 'verify.js')
    fa_path = os.path.join(args.repo, 'api', '_lib', 'firebase-admin.js')
    for p in (verify_path, fa_path):
        if not os.path.isfile(p):
            print('COULD NOT RUN: %s not found' % p)
            sys.exit(2)
    verify_src = open(verify_path, encoding='utf-8').read()
    fa_src = open(fa_path, encoding='utf-8').read()
    r = analyze(verify_src, fa_src)
    print('subscriptionId branch found: %s' % r['subscription_branch_found'])
    print('mints a Firebase custom token (mintFirebaseToken(customerId)): %s' % r['mints_token'])
    print('has an ownership/session check before minting: %s' % r['has_ownership_check'])
    print('firebase-admin.js states an ownership precondition for minting: %s' %
          r['firebase_admin_states_precondition'])
    if (r['subscription_branch_found'] and r['mints_token'] and
            r['has_ownership_check'] is False and r['firebase_admin_states_precondition']):
        print('FINDING CONFIRMED: a bare, valid subscriptionId mints a Firebase auth '
              "token with no ownership check, violating firebase-admin.js's own "
              'stated minting precondition.')
        sys.exit(1)
    elif r['subscription_branch_found']:
        print('NO FINDING: either an ownership check exists, or the precondition is not stated.')
        sys.exit(0)
    else:
        print('COULD NOT RUN: subscriptionId branch pattern not found -- source shape changed.')
        sys.exit(2)


if __name__ == '__main__':
    main()

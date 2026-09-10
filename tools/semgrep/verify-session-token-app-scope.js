// Fixture for tools/semgrep/verify-session-token-app-scope.yml.
// Run: semgrep --test --config tools/semgrep tools/semgrep
//
// `ruleid:` marks a line the rule MUST flag, `ok:` a line it must NOT. The ok
// lines are the point: a rule that fires on everything is not a rule, and the
// two-vs-three argument distinction is the entire content of this one.

const { verifySessionToken, verifyPreAuthToken, tokenFromRequest } = require('../api/_lib/auth');
const APP = 'sairnexample';

function bad(req, licHash) {
  // ruleid: verify-session-token-missing-expected-app
  return verifySessionToken(tokenFromRequest(req), licHash);
}

function badNamespaced(req, licHash) {
  // ruleid: verify-session-token-missing-expected-app
  return auth.verifySessionToken(tokenFromRequest(req), licHash);
}

function good(req, licHash) {
  // ok: verify-session-token-missing-expected-app
  return verifySessionToken(tokenFromRequest(req), licHash, APP);
}

function goodNamespaced(req, licHash) {
  // ok: verify-session-token-missing-expected-app
  return auth.verifySessionToken(tokenFromRequest(req), licHash, 'sairncare');
}

function badPreAuth(body, licHash) {
  // ruleid: verify-preauth-token-missing-expected-app
  return verifyPreAuthToken(body.preauth_token, licHash);
}

function goodPreAuth(body, licHash) {
  // ok: verify-preauth-token-missing-expected-app
  return verifyPreAuthToken(body.preauth_token, licHash, APP);
}

// A three-argument call whose third argument is a variable that happens to be
// undefined at runtime is NOT what this rule detects, and saying so here stops
// the next reader assuming coverage the rule does not have.
function outOfScope(req, licHash, maybeUndefined) {
  // ok: verify-session-token-missing-expected-app
  return verifySessionToken(tokenFromRequest(req), licHash, maybeUndefined);
}

module.exports = { bad, badNamespaced, good, goodNamespaced, badPreAuth, goodPreAuth, outOfScope };

# Threat-modeling checklist: OWASP Top 10 + STRIDE, run together

A reusable reference template for the Threat modeling pass (see SKILL.md).
Both lenses apply on every pass -- OWASP for the specific vulnerability-class
checklist, STRIDE for the six broader security properties underneath those
classes. Governed absolutely by the Rules of Engagement in SKILL.md: every
item below is investigated by code-traced proof of concept, never by live
exploitation.

## OWASP Top 10 -- concrete vulnerability-class checklist

Check each explicitly against the code actually being reviewed, not from
memory of what the category usually means:

- [ ] **Broken Access Control** -- can a session/licence reach a resource
  it shouldn't (cross-app, cross-tenant, cross-role)?
- [ ] **Cryptographic Failures** -- is sensitive data (credentials, PHI,
  financial figures) stored or transmitted without appropriate protection?
- [ ] **Injection** -- SQL, command, or dynamic-query injection via
  unsanitized input reaching a query builder or shell call?
- [ ] **Insecure Design** -- is the *design itself* missing a control a
  correct implementation can't compensate for (no rate limit designed in,
  no audit trail designed in)?
- [ ] **Security Misconfiguration** -- default credentials, verbose error
  leakage, permissive CORS, an unintended debug endpoint left reachable?
- [ ] **Vulnerable and Outdated Components** -- see the dependency
  health-check tool (`dependency_health_check.py`) as the concrete
  companion to this item.
- [ ] **Identification and Authentication Failures** -- session fixation,
  weak token generation, missing re-check after deactivation?
- [ ] **Software and Data Integrity Failures** -- unsigned/unverified
  updates, deserialization of untrusted data, CI/CD pipeline trust gaps?
- [ ] **Security Logging and Monitoring Failures** -- would an attack
  attempt actually be visible in logs/alerts, or does it fail silently?
- [ ] **Server-Side Request Forgery (SSRF)** -- can user input cause the
  server to make a request to an attacker-chosen destination?

## STRIDE -- the six properties underneath the vulnerability classes

Each maps to one violated security property. Real overlap between
categories exists and is expected (STRIDE's own creators acknowledge
this) -- log a finding under every category that genuinely applies rather
than forcing a single artificial choice.

- [ ] **Spoofing** (violates Authentication) -- can an actor convincingly
  claim to be someone/something they are not?
- [ ] **Tampering** (violates Integrity) -- can data be modified
  in-flight or at-rest without detection?
- [ ] **Repudiation** (violates Non-repudiation/Accountability) -- could
  an actor deny taking an action with nothing to disprove it? **Not
  covered by OWASP Top 10 at all** -- this platform's hash-chained audit
  checkpoints and this role's own self-log are the real, working
  mitigations to check against this question specifically.
- [ ] **Information Disclosure** (violates Confidentiality) -- can data
  reach a party never meant to see it?
- [ ] **Denial of Service** (violates Availability) -- can a real actor
  degrade or block service for legitimate users?
- [ ] **Elevation of Privilege** (violates Authorization) -- can an actor
  gain capabilities beyond what they were granted?

## Running the pass

1. Pick the target (a resource, an endpoint, an app boundary).
2. Walk the OWASP list first -- concrete, checkable, fast.
3. Walk STRIDE second, paying specific attention to Repudiation.
4. For anything that looks real, build the code-traced proof of concept
   per the Rules of Engagement -- never execute live.
5. For a HIGH finding, ask the post-exploitation question: what becomes
   reachable from here if this were actually exploited.
6. Score with the reconciled severity formula (Tier x Exploitability x
   Impact, Scope stated separately) -- see SKILL.md's Severity scoring
   section.

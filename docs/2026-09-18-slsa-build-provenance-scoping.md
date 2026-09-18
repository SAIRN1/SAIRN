# SLSA build provenance — what is attestable here, and the one decision that is Michael's

**2026-09-18 (Fourth).** Michael confirmed the work; the hover auditor found the
gap (zero provenance anywhere). **The brief was "across the 4 workflows" and
three of the four have nothing to attest.** That is not a refusal, it is the
finding: this is reported before building the wrong thing.

---

## 1. What `attest-build-provenance` actually needs

It signs a **subject** — a file, by digest — and records provenance saying which
workflow, from which commit, produced it. **No artifact, no subject, no
attestation.** It is not a workflow badge.

| Workflow | Produces | Attestable |
|---|---|---|
| `codeql.yml` | a security scan, results to GitHub | **No** — a scanner emits findings, not an artifact |
| `cron-liveness.yml` | an HTTP probe and an alert | **No** — a watchdog produces no file |
| `hover-separation.yml` | a pass/fail gate decision | **No** — a gate produces no file |
| `nightly-backup.yml` | **an encrypted `.sql.age` dump, pushed to Cloudflare R2** | **YES** |

**One of four, and it is the right one.** The dump is the only artifact this
platform produces that LEAVES it: an encrypted database backup, in a
third-party bucket, that somebody will one day restore from under time
pressure. Provenance answers the question nobody can answer at that moment —
*is this the file our workflow made, from this commit, or something that
arrived in the bucket another way.*

**Done.** `nightly-backup.yml` now carries `id-token: write` and
`attestations: write` and attests the dump.

**TWO ORDERING DECISIONS, both deliberate and both in the file:**

* **Attest BEFORE the R2 upload**, on the local file. The provenance then covers
  the bytes *this job produced*, rather than whatever is in the bucket
  afterwards. Attesting the uploaded copy would prove only that something with
  that digest exists — which the bucket already tells you.
* **Attest AFTER the size floor.** Attesting a dump the job is about to reject
  would issue signed provenance for a file the workflow itself does not accept.
  A signature is not a quality judgement and should not be handed to something
  already known to be wrong.

⚠ **IT HAS NEVER RUN.** Every execution of `nightly-backup.yml` so far has
failed at the dump step, before reaching the upload. The attestation is
**written and unexercised**, and the file says so at the step.

---

## 2. THE REAL DECISION POINT: the product has no GitHub-built artifact at all

`vercel.json` line 2:

```json
"buildCommand": "mkdir -p dist && cp *.html dist/ && cp stonedesk.html dist/index.html && cp sw.js dist/sw.js"
```

**Vercel builds and deploys from the git push. No GitHub Actions workflow
touches the deployed bytes** — there is no deploy step in any of the four, and
`vercel` appears in them exactly once, in a watchdog URL.

So the thing customers actually run has **no provenance and cannot be given any
by adding a step to an existing workflow.** That is a genuine architecture
question and it is not mine to settle. Three options, with their real costs:

**A. Move the build into Actions, deploy the output to Vercel.**
Real SLSA provenance on the deployed bundle. **Cost: the zero-config deploy
goes.** Every push currently gets a preview URL and a production deploy with no
pipeline to maintain; this replaces that with a workflow that can break, a
token to hold and rotate (a new NHI-register identity with production deploy
authority), and a second place deploys can fail. For a platform whose apps are
`cp *.html dist/`, the build being attested is a file copy.

**B. Accept no provenance on the deployed app.** Attest the backup only, and
record the gap. **Cost:** nothing verifies that what Vercel served matches what
the repo held. Today the mitigation is `tools/deploy_verify_notify.py`, which
hashes the live site against HEAD after a push — a real control, and a
*detection* rather than an *attestation*: it says the bytes match now, not who
produced them.

**C. Attest a SOURCE MANIFEST rather than a build.** A workflow on push that
emits `{path: sha256}` for every deployed file at that commit and attests THAT.
No build moves, zero-config survives, and you gain a signed record of what a
commit was supposed to deploy — which is exactly what the post-deploy hash
check needs to compare against. **Cost: it is not SLSA build provenance** and
must not be described as it. It attests a manifest, not a build, and it cannot
prove Vercel used it.

**Recommendation, stated as one rather than hidden in the options: C, then
revisit A if the deployed surface ever stops being a file copy.** It closes the
verification gap the auditor is actually pointing at, at no operational cost,
and it does not trade a working deploy for a stronger word. **A is the only one
that yields real SLSA on the product, and it is a real cost for a build that
copies files.** Not built here — it is a decision, not a task.

---

## 3. What is NOT claimed

* **That the platform now has SLSA build provenance.** It has provenance on ONE
  artifact, in a workflow that has never successfully produced that artifact.
* **That attestation verifies the backup is good.** It says who made the file.
  The restore-and-coherence step is what says it is a usable backup, and that is
  a different control that has also never run.
* **That the three non-attestable workflows are somehow covered.** They are not.
  They produce no artifact, and pretending otherwise would be the fabrication
  this platform's own checks exist to catch.
* **A consumption side.** Nothing yet VERIFIES an attestation before restoring
  from a dump. Provenance nobody checks is a signature in a drawer, and the
  restore runbook does not mention it.

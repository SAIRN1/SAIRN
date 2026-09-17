"""tests/intake_link_no_credential.js must REFUSE the key going back in the URL.

Run: python tests/intake_link_no_credential_probe.py

THE LINK THE SHOP IS INVITED TO SEND TO EVERY CUSTOMER USED TO CARRY A BEARER
CREDENTIAL. It was built as

    INTAKE_FORM_URL + '?shop=' + shop + '&lic=' + slabLicKey()

and the Share button's own copy says "Hi! Before your appointment, please take 2
minutes to fill out this quick project form". slabLicKey() is sdLicenseKey() --
the SAME string sent as `Authorization: Bearer` on every /api/sd-data call.

VERIFIED LIVE against SD-AUDIT-2026 with the bearer key and NO employee session:
`slabs` returned the full inventory and is WRITABLE, `profile` returned the
shop's business record, `memory` returned its AI memories. So the link handed to
prospects carried a working credential into their SMS thread, their browser
history, and any referrer.

The repair is subtractive -- the key is simply not read -- and a subtractive fix
is the kind that gets quietly undone, because putting the read back looks like
adding a feature rather than removing a guard. The suite's own last arm says so:
"If someone later fixes the 404 by building the form, the note is what tells them
not to put the key back."

A SUITE GUARDING AN ABSENCE IS THE HARDEST KIND TO TRUST, because the thing it
asserts is that nothing is there, and that is also what a suite looking in the
wrong place reports. These mutations put each removed thing BACK:

  * the licence key returns to the URL -- the original defect, one string
    concatenation;
  * it returns via a different spelling, sdLicenseKey() rather than slabLicKey(),
    which is the same credential and would slip a check that names one function;
  * ?shop= reverts to the company DISPLAY NAME, which cannot identify a shop to
    api/stonedesk-public.js -- the link could never have submitted anything;
  * a shop with no slug gets a URL again, which is the "looked ready and was
    not" defect this panel was repaired for;
  * a FAILED read emits a link built from nothing;
  * the note recording WHY the key was removable is deleted, which is what a
    later reader would need to not put it back.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'intake_link_no_credential.js')
APP = 'stonedesk.html'

# ANCHORS INLINE, NEVER IN A CONSTANT. tools/mutation_anchor_check.py reads
# MUTATIONS with `ast` rather than importing (importing a probe RUNS it), so a
# tuple element that is a NAME resolves to nothing and is reported ANCHOR-0.
# The first draft of this file hoisted the emit line into `EMIT` and produced
# three false zeros -- the same defect already recorded as 7bb6eb2a, made again
# within the hour, and caught in seconds this time because the check exists.
# That is the whole argument for the mechanical version of a rule.

MUTATIONS = [
    ("1. THE ORIGINAL DEFECT, ONE CONCATENATION. The licence key goes back into "
     "the URL the shop is told to send to every customer -- a working bearer "
     "credential for the full slab inventory (writable), the business profile "
     "and the shop's AI memories, in an SMS thread",
     APP,
     "    lf.value = INTAKE_FORM_URL + '?shop=' + encodeURIComponent(slug);",
     "    lf.value = INTAKE_FORM_URL + '?shop=' + encodeURIComponent(slug)"
     " + '&lic=' + encodeURIComponent(slabLicKey());"),

    ("2. the same credential under a DIFFERENT NAME. slabLicKey() is "
     "sdLicenseKey(); a check that names one function and not the other reads "
     "as a guard and is a spelling test",
     APP,
     "    lf.value = INTAKE_FORM_URL + '?shop=' + encodeURIComponent(slug);",
     "    lf.value = INTAKE_FORM_URL + '?shop=' + encodeURIComponent(slug)"
     " + '&lic=' + encodeURIComponent(sdLicenseKey());"),

    ("3. ?shop= reverts to the company DISPLAY NAME. /stonedesk-catalog has "
     "used the slug since 2026-09-02, so this is one parameter meaning two "
     "things in one app -- and a display name cannot identify a shop to "
     "api/stonedesk-public.js, so the link could never submit anything",
     APP,
     "    lf.value = INTAKE_FORM_URL + '?shop=' + encodeURIComponent(slug);",
     "    lf.value = INTAKE_FORM_URL + '?shop=' + "
     "encodeURIComponent((window._sdBizProfile && window._sdBizProfile.company) "
     "|| 'StoneDesk');"),

    ("4. a shop with NO public slug gets a URL anyway. That is the defect this "
     "whole panel was repaired for -- a link that LOOKED READY and would be "
     "refused -- and it returns by deleting four lines",
     APP,
     "    if (!slug) {\n      lf.placeholder = 'Set a public address in the Public Catalog panel first"
     " — an intake link needs one.';\n      return;\n    }",
     "    if (!slug) { slug = 'shop'; }"),

    ("5. a FAILED read emits a link built from nothing instead of saying it "
     "could not check. An unusable thing presented as ready, which is the same "
     "shape as everything else this panel was doing wrong",
     APP,
     "    console.error('[intake] could not read sd_public_shop for the link:', e);\n"
     "    lf.placeholder = 'Could not check your public address — reload the page.';",
     "    lf.value = INTAKE_FORM_URL + '?shop=';"),

    ("6. the NOTE recording why the key was removable is deleted. It is the "
     "only thing telling a later reader who 'fixes' the 404 by building the "
     "form not to put the credential back -- and a subtractive fix with no "
     "surviving reason is a fix waiting to be undone",
     APP,
     "  // purpose-made public token, never this key.",
     "  //"),
]

if __name__ == '__main__':
    sys.exit(run_probe(
        SUITE, MUTATIONS,
        title='the intake share link -- the suite must refuse a bearer '
              'credential going back into a URL sent to customers'))

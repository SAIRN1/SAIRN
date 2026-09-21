"""tests/sairncare_transport_refusal.js must REFUSE, not merely agree.

Run: python tests/run_sairncare_transport_refusal_sabotage_probe.py

# REQUIREMENT: the suite guarding SAIRNcare's second transport must go RED when
#   the `&& !d.error` clause comes back, when the stamp is keyed on the body
#   instead of the status, when the server's actionable message is dropped,
#   when a refused credential read goes back to reading as an empty ledger,
#   when refused and genuinely-empty collapse to the same value, and when the
#   export's null guard -- correct and unreachable for as long as the defect
#   lived -- is removed from the other side

WHAT WAS OPEN. `alfPostRaw()` carried `if(!r.ok && !d.error)`, so its
HTTP_<status> normalisation fired only when the server sent NO error body.
deea8c55 removed that same clause from `alfRoute()` and `alfData()` and left it
here on purpose, recorded in a comment above the function: neither caller
persists, so the blast radius differed and folding it in would have made one
change do two things.

REPRODUCED against the shipped file before the fix, driving the real functions:
a 401 came back as NO_SESSION, a 403 as FORBIDDEN, a 503 as NOT_PROVISIONED,
and `upstream()`'s 502 as a body with NO CODE AT ALL -- all four into a renderer
whose `code` field is where the COMPLIANCE ENGINE's refusals go. And every one
of them set `_crRecords = []`, which renders as "No credential or training
entries recorded yet".

── WHY THE LEDGER ARMS ARE THE ONES TO KEEP ───────────────────────────────
A wrong code on a screen is read by one person once. `ALF_EXPORTS.credentials`
turns `_crRecords` into a CSV whose own preamble prints `ROWS IN THIS FILE: 0`,
and that file is what goes to an inspector. The export ALREADY refused on
`_crRecords === null`, under a comment saying never-loaded and genuinely-empty
are different facts -- correct, and dead, because nothing ever produced null on
a refusal. Arm 6 plants the removal of that guard, because a fix that depends
on a guard somebody else may delete is half a fix.

── AND ARM 5 IS WHY ARM 4 IS NOT ENOUGH ───────────────────────────────────
Setting `_crRecords = null` unconditionally would satisfy every "a refusal is
null" arm and destroy the distinction the fix exists to create. Arm 5 collapses
empty into null and the suite has to notice.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sabotage_harness import run_probe                           # noqa: E402

SUITE = os.path.join('tests', 'sairncare_transport_refusal.js')
APP = 'sairncare.html'

MUTATIONS = [
    ("1. THE `&& !d.error` CLAUSE COMES BACK -- the state of this transport "
     "until 2026-09-21, in which a transport refusal is rendered where the "
     "compliance engine's refusal codes belong",
     APP,
     "      if(!r.ok)return {ok:false,error:{code:'HTTP_'+r.status,\n"
     "        message:(d.error&&d.error.message)||'The server refused this request.'}};\n"
     "      return d;\n"
     "    }).catch(function(){return {ok:false,error:{code:'BAD_RESPONSE',message:'The server returned an unreadable response.'}};});",
     "      if(!r.ok&&!d.error)return {ok:false,error:{code:'HTTP_'+r.status,\n"
     "        message:(d.error&&d.error.message)||'The server refused this request.'}};\n"
     "      return d;\n"
     "    }).catch(function(){return {ok:false,error:{code:'BAD_RESPONSE',message:'The server returned an unreadable response.'}};});"),

    ("2. THE STAMP IS KEYED ON THE BODY INSTEAD OF THE STATUS -- it fires only "
     "when the server named no code, which is the same hole spelled the other "
     "way round and leaves the 502 the only one caught",
     APP,
     "      if(!r.ok)return {ok:false,error:{code:'HTTP_'+r.status,\n"
     "        message:(d.error&&d.error.message)||'The server refused this request.'}};\n"
     "      return d;\n"
     "    }).catch(function(){return {ok:false,error:{code:'BAD_RESPONSE',message:'The server returned an unreadable response.'}};});",
     "      if(!r.ok&&!(d.error&&d.error.code))return {ok:false,error:{code:'HTTP_'+r.status,\n"
     "        message:(d.error&&d.error.message)||'The server refused this request.'}};\n"
     "      return d;\n"
     "    }).catch(function(){return {ok:false,error:{code:'BAD_RESPONSE',message:'The server returned an unreadable response.'}};});"),

    ("3. THE SERVER'S MESSAGE IS DROPPED FOR THE CODE -- the status is right "
     "and the operator loses the sentence naming the SQL file they have to run",
     APP,
     "      if(!r.ok)return {ok:false,error:{code:'HTTP_'+r.status,\n"
     "        message:(d.error&&d.error.message)||'The server refused this request.'}};\n"
     "      return d;\n"
     "    }).catch(function(){return {ok:false,error:{code:'BAD_RESPONSE',message:'The server returned an unreadable response.'}};});",
     "      if(!r.ok)return {ok:false,error:{code:'HTTP_'+r.status,\n"
     "        message:'The server refused this request.'}};\n"
     "      return d;\n"
     "    }).catch(function(){return {ok:false,error:{code:'BAD_RESPONSE',message:'The server returned an unreadable response.'}};});"),

    ("4. A REFUSED CREDENTIAL READ IS AN EMPTY LEDGER AGAIN -- the half with a "
     "FILE at the end of it, exportable as a CSV saying ROWS IN THIS FILE: 0 "
     "about a ledger nobody was allowed to read",
     APP,
     "    var _crOk=!!(r&&Array.isArray(r.data)&&!r.error&&r.ok!==false);\n"
     "    _crRecords=_crOk?r.data:null;",
     "    var _crOk=!!(r&&Array.isArray(r.data)&&!r.error&&r.ok!==false);\n"
     "    _crRecords=_crOk?r.data:[];"),

    ("5. REFUSED AND GENUINELY EMPTY COLLAPSE TO THE SAME VALUE -- every "
     "'a refusal is null' arm passes and the distinction the fix exists to "
     "create is gone",
     APP,
     "    _crRecords=_crOk?r.data:null;",
     "    _crRecords=(_crOk&&r.data.length)?r.data:null;"),

    ("6. THE EXPORT'S NULL GUARD IS REMOVED -- the guard was correct and "
     "unreachable for as long as the defect lived, so deleting it now re-opens "
     "the same file from the other side",
     APP,
     "      if(_crRecords===null)return null;\n",
     ""),
]

sys.exit(run_probe(
    SUITE, MUTATIONS,
    title='SAIRNcare: a request the second transport could not complete must '
          'arrive as a REFUSAL -- with a code the engine does not own, the '
          "server's own message, and a credential ledger that is NOT empty",
    stage=(APP,),
))

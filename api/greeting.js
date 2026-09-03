// api/greeting.js
// ---------------------------------------------------------------------------
// The opening line an assistant shows before anyone has typed anything.
//
// WHY THIS FILE EXISTS. sairnscape.html has called
// https://sairn.vercel.app/api/greeting on every app open since the feature
// shipped, and the endpoint has never existed. Probed live 2026-09-03: 404. The
// client reads `data.greeting`, gets undefined, returns silently, and the
// static empty-state welcome shows instead -- so nobody has ever seen a
// personalised greeting and nothing ever said so. Found by a sweep for live
// apps calling API paths with no file in api/.
//
// ── IT DOES NOT CALL CLAUDE, AND THAT IS THE DESIGN ────────────────────────
// A greeting is the one string on the page that must render before the user has
// asked for anything. Routing it through an LLM would add a paid call and a
// round trip to every single app open, for a sentence nobody is reading closely
// -- and it would introduce the one thing a greeting must never do, which is
// state something about the customer's business that nobody checked. This
// composes from time of day, day of week, and the app's own vocabulary. No
// model, no cost, no latency, and nothing it says can be wrong.
//
// ── IT NEVER ECHOES CALLER INPUT, AND THAT IS A SECURITY PROPERTY ──────────
// sairnscape.html injects the result with innerHTML inside a template literal:
//     div.innerHTML = `...<p>${greeting}</p>...`
// So whatever this returns is parsed as HTML by the browser. If the greeting
// contained anything a caller supplied, that would be reflected XSS on every
// app open. `app_id` is therefore matched against a fixed table and a value
// that is not in it falls through to the neutral copy -- it is never
// interpolated, never echoed in an error, and never reaches the response.
//
// The client side is being escaped too, in the same change. Two independent
// guards for one hazard is correct here: this endpoint could be called by a
// future client that forgets, and that client could be pointed at a future
// endpoint that forgets.
//
// ── DETERMINISTIC ──────────────────────────────────────────────────────────
// Same app, same hour, same weekday -> same greeting. No Math.random(). It is
// testable, it is cacheable, and a support conversation about "what did it say
// to me" has an answer. The day-of-week index rotates the closing line so it is
// not identical every morning without being unpredictable.
// ---------------------------------------------------------------------------

// Per app: what its users actually do, in their own words. Anything not here
// gets the neutral copy -- including a missing, misspelled or hostile app_id.
const APPS = {
  sairnscape:    { noun: 'crews',        work: 'properties and crews' },
  sairngrounds:  { noun: 'crews',        work: 'grounds and course work' },
  stonedesk:     { noun: 'the shop',     work: 'slabs, quotes and jobs' },
  sairnbuild:    { noun: 'the site',     work: 'jobs, subs and draws' },
  sairnroofing:  { noun: 'crews',        work: 'claims, crews and jobs' },
  sairndental:   { noun: 'the practice', work: 'the schedule and the day sheet' },
  sairncare:     { noun: 'the facility', work: 'residents and staffing' },
  sairnsenior:   { noun: 'the agency',   work: 'visits and caregivers' },
  sairnlaw:      { noun: 'the firm',     work: 'matters and deadlines' },
  sairnlegacy:   { noun: 'the home',     work: 'cases and arrangements' },
  sairndesign:   { noun: 'the studio',   work: 'clients and projects' },
  sairnbiz:      { noun: 'the business', work: 'people, time and payroll' },
  sairncode:     { noun: 'the desk',     work: 'claims and coding' },
  sairnmechanical: { noun: 'the shop',   work: 'dispatch and technicians' }
};

// Local hour -> the part of the day. Sent by the client because the server has
// no idea what timezone anybody is in, and a greeting that says "good morning"
// at nine in the evening is worse than no greeting.
function partOfDay(hour) {
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) return null;
  if (hour < 5) return 'late';
  if (hour < 12) return 'morning';
  if (hour < 17) return 'afternoon';
  if (hour < 22) return 'evening';
  return 'late';
}

const OPENERS = {
  morning: 'Morning.',
  afternoon: 'Afternoon.',
  evening: 'Evening.',
  late: 'Working late.'
};

// Rotated by weekday so the same person does not read the identical sentence
// five days running. Deliberately generic: none of these claims anything about
// the customer's data.
const CLOSERS = [
  'What do you want to look at first?',            // Sunday
  'What is on top of the pile?',                   // Monday
  'Where do you want to start?',                   // Tuesday
  'What needs sorting?',                           // Wednesday
  'What can I help with?',                         // Thursday
  'What is left before the weekend?',              // Friday
  'What are you catching up on?'                   // Saturday
];

// Exported for the test suite. Pure: same inputs, same string, no clock, no
// randomness, no I/O.
function buildGreeting(appId, hour, day) {
  const part = partOfDay(hour);
  const app = Object.prototype.hasOwnProperty.call(APPS, String(appId)) ? APPS[String(appId)] : null;
  const closer = Number.isInteger(day) && day >= 0 && day <= 6
    ? CLOSERS[day]
    : CLOSERS[4];   // the neutral one, not a crash and not a blank

  // No recognised time of day -- the client sent something odd, or nothing.
  // Still a real greeting, just without the time reference.
  if (!part) {
    return app
      ? 'Ready when you are — ' + app.work + '. ' + closer
      : 'Ready when you are. ' + closer;
  }
  if (!app) {
    return OPENERS[part] + ' ' + closer;
  }
  if (part === 'late') {
    return OPENERS[part] + ' I can still pull up ' + app.work + '. ' + closer;
  }
  return OPENERS[part] + ' I have ' + app.work + ' ready when you are. ' + closer;
}

module.exports = async (req, res) => {
  // GET is allowed as well as POST. The only caller today POSTs, but a greeting
  // is a read with no side effects and refusing GET would be a rule with no
  // reason behind it.
  if (req.method !== 'POST' && req.method !== 'GET') {
    res.status(405).json({ error: { message: 'Method not allowed — GET or POST' } });
    return;
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  body = body || {};
  const q = req.query || {};

  const appId = body.app_id || q.app_id;
  // parseInt rather than Number: the client sends integers, but a query string
  // sends '9', and Number('') is 0 -- which would silently become midnight.
  const hourRaw = body.client_hour !== undefined ? body.client_hour : q.client_hour;
  const dayRaw = body.client_day !== undefined ? body.client_day : q.client_day;
  const hour = parseInt(hourRaw, 10);
  const day = parseInt(dayRaw, 10);

  // NO AUTHENTICATION, deliberately. The caller today is a marketing-page
  // assistant that runs before any licence is entered, so requiring one would
  // mean the greeting only ever appeared to signed-in users -- which is the
  // opposite of where a first impression matters. It is safe to leave open
  // because this endpoint reads NOTHING: no database, no licence lookup, no
  // customer data. It is a pure function of three numbers and a name from a
  // fixed table.
  res.setHeader('Cache-Control', 'public, max-age=300');
  res.status(200).json({
    greeting: buildGreeting(appId, Number.isNaN(hour) ? null : hour, Number.isNaN(day) ? null : day)
  });
};

module.exports.buildGreeting = buildGreeting;
module.exports.APPS = APPS;

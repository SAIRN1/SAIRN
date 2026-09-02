// api/stonedesk-public.test.js
// Unit tests for the pure, decidable parts of StoneDesk's public surface --
// the ones that decide what an anonymous visitor is allowed to see.
//
// These do NOT need Supabase. Everything asserted here is a pure function of
// its input, which is the point: the rules that decide what leaves the building
// should not need a database to be checkable.
//
// Run: node api/stonedesk-public.test.js

const assert = require('assert');
const { publicSlabView, isPublished, hashIp } = require('./_lib/stonedesk-public');

let passed = 0;
function t(name, fn) {
  try { fn(); passed++; console.log('  ok - ' + name); }
  catch (e) { console.error('  FAIL - ' + name); console.error('    ' + e.message); process.exitCode = 1; }
}

console.log('stonedesk public surface');

// ── PUBLICATION IS OPT-IN, AND ABSENT MEANS NO ──────────────────────────────
t('a slab with no published flag is NOT published', () => {
  assert.strictEqual(isPublished({ id: 'S1', material: 'granite' }), false);
});
t('published must be exactly true -- a truthy string does not publish a slab', () => {
  assert.strictEqual(isPublished({ published: 'yes' }), false);
  assert.strictEqual(isPublished({ published: 1 }), false);
  assert.strictEqual(isPublished({ published: true }), true);
});
t('null and undefined are not published', () => {
  assert.strictEqual(isPublished(null), false);
  assert.strictEqual(isPublished(undefined), false);
});

// ── THE PUBLIC SHAPE IS BUILT BY NAMING ITS FIELDS ──────────────────────────
// This is the test that matters most. A slab blob carries what the SHOP needs.
// If publicSlabView ever became a delete-list instead of a builder, a field
// added later would leak by default, and this asserts it cannot.
t('a slab carrying internal fields exposes ONLY the named public ones', () => {
  const v = publicSlabView({
    id: 'S1', material: 'quartzite', colorName: 'Taj Mahal', usableSqft: 52,
    thickness: '3cm', finish: 'polished', photo_base64: 'data:image/png;base64,AAA',
    // everything below is internal and must not survive
    cost: 1450, vendor: 'MSI', supplier: 'Regional Stone', status: 'reserved',
    reservedForJob: 'JOB-9', margin: 0.42, notes: 'chip on the left corner',
    blockId: 'BLK-3', internalGrade: 'level 4'
  });
  assert.deepStrictEqual(Object.keys(v).sort(),
    ['color_name', 'finish', 'id', 'material', 'photo_base64', 'thickness', 'usable_sqft']);
});
t('cost, vendor and supplier are absent from the public shape', () => {
  const v = publicSlabView({ id: 'S1', cost: 1450, vendor: 'MSI', supplier: 'Regional Stone' });
  assert.strictEqual('cost' in v, false);
  assert.strictEqual('vendor' in v, false);
  assert.strictEqual('supplier' in v, false);
});
t('a field invented after this code was written does not appear', () => {
  const v = publicSlabView({ id: 'S1', someFutureInternalField: 'secret' });
  assert.strictEqual('someFutureInternalField' in v, false);
});
t('the public shape survives a slab with nothing on it', () => {
  const v = publicSlabView({});
  assert.strictEqual(v.id, '');
  assert.strictEqual(v.usable_sqft, null);
  assert.strictEqual(v.photo_base64, '');
});
t('usable_sqft is null rather than 0 when it is unknown -- 0 sqft is a claim, absent is not', () => {
  assert.strictEqual(publicSlabView({ id: 'S1' }).usable_sqft, null);
  assert.strictEqual(publicSlabView({ id: 'S1', usableSqft: 52 }).usable_sqft, 52);
});
t('both the camelCase and snake_case field names a slab might carry are read', () => {
  assert.strictEqual(publicSlabView({ colorName: 'Taj' }).color_name, 'Taj');
  assert.strictEqual(publicSlabView({ color_name: 'Taj' }).color_name, 'Taj');
});
t('a non-string photo is dropped rather than passed through', () => {
  assert.strictEqual(publicSlabView({ photo_base64: { evil: true } }).photo_base64, '');
});

// ── IP HASHING ──────────────────────────────────────────────────────────────
t('the rate-limit key is a hash, never the address itself', () => {
  const h = hashIp('203.0.113.7');
  assert.match(h, /^[0-9a-f]{64}$/);
  assert.strictEqual(h.includes('203.0.113.7'), false);
});
t('the same address hashes the same way twice, and two addresses differ', () => {
  assert.strictEqual(hashIp('203.0.113.7'), hashIp('203.0.113.7'));
  assert.notStrictEqual(hashIp('203.0.113.7'), hashIp('203.0.113.8'));
});

// ── THE SLUG NORMALISER, as the server applies it ───────────────────────────
// Mirrors api/sd-data.js's sd_public_shop write branch exactly. Kept here
// because it decides a public URL, and a public URL that two clients disagree
// about is a support call.
function normaliseSlug(v) {
  return String(v == null ? '' : v).trim().toLowerCase()
    .replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);
}
t('a shop name becomes a usable slug', () => {
  assert.strictEqual(normaliseSlug('  Main Street Stone  '), 'main-street-stone');
});
t('punctuation collapses rather than being dropped silently', () => {
  assert.strictEqual(normaliseSlug("O'Hara & Sons, Ltd."), 'o-hara-sons-ltd');
});
t('leading and trailing separators are trimmed', () => {
  assert.strictEqual(normaliseSlug('---abc---'), 'abc');
});
t('a slug of pure punctuation becomes empty, which the server then refuses to publish', () => {
  assert.strictEqual(normaliseSlug('!!!'), '');
});
t('a slug is capped so it cannot become an unbounded URL', () => {
  assert.strictEqual(normaliseSlug('a'.repeat(200)).length, 60);
});
t('a path traversal attempt cannot survive normalisation', () => {
  assert.strictEqual(normaliseSlug('../../etc/passwd'), 'etc-passwd');
});

console.log('\n' + passed + ' passed' + (process.exitCode ? ', see failures above' : ''));

// tools/posthook.js — PostToolUse hook. After any Edit/Write to a *.html file,
// node --checks every inline <script> block and prints ONLY if one fails
// (silent + non-blocking when clean, to keep context/token cost at zero on the
// happy path). Enforces CLAUDE.md's "zero errors before any changes" rule.
const fs = require('fs'), cp = require('child_process'), os = require('os'), path = require('path');
let input = '';
try { input = fs.readFileSync(0, 'utf8'); } catch (e) {}
let fp = '';
try { fp = ((JSON.parse(input) || {}).tool_input || {}).file_path || ''; } catch (e) {}
if (!/\.html$/i.test(fp) || !fs.existsSync(fp)) process.exit(0);
try {
  const html = fs.readFileSync(fp, 'utf8');
  const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi;
  let m, i = 0, fails = [];
  const tmp = os.tmpdir();
  while ((m = re.exec(html))) {
    i++;
    const f = path.join(tmp, `hk_${process.pid}_${i}.js`);
    fs.writeFileSync(f, m[1]);
    try { cp.execSync(`node --check "${f}"`, { stdio: 'pipe' }); } catch (e) { fails.push(i); }
    fs.unlinkSync(f);
  }
  if (fails.length) console.log(`⚠ ${path.basename(fp)}: ${fails.length} inline <script> block(s) FAIL node --check -> [${fails.join(',')}]. Fix before committing.`);
} catch (e) {}
process.exit(0);

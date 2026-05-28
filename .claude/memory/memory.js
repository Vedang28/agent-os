#!/usr/bin/env node
// Project session-memory CLI. No dependencies. Place at .claude/memory/memory.js
// Usage:
//   node .claude/memory/memory.js log "<summary>"
//   node .claude/memory/memory.js decide "<title>" "<why>"
//   node .claude/memory/memory.js recent [n]
//   node .claude/memory/memory.js search "<keyword>"

const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const SESSION_LOG = path.join(DIR, 'SESSION_LOG.md');
const DECISIONS = path.join(DIR, 'DECISIONS.md');

function now() {
  return new Date().toISOString().replace('T', ' ').slice(0, 16);
}

function ensure(file, header) {
  if (!fs.existsSync(file)) fs.writeFileSync(file, header);
}

function fail(msg) {
  console.error('error:', msg);
  process.exit(1);
}

function log(summary) {
  if (!summary) return fail('log needs a summary string');
  ensure(SESSION_LOG, '# SESSION LOG\n\n> Append-only. Newest at the bottom.\n');
  fs.appendFileSync(SESSION_LOG, `\n## ${now()}\n${summary}\n`);
  console.log('logged ->', SESSION_LOG);
}

function decide(title, why) {
  if (!title) return fail('decide needs a title');
  ensure(DECISIONS, '# DECISION RECORD (ADR)\n\n> Append-only architectural decisions.\n');
  fs.appendFileSync(DECISIONS, `\n## ${now()} — ${title}\n${why || '(no rationale given)'}\n`);
  console.log('recorded ->', DECISIONS);
}

function recent(n) {
  n = parseInt(n, 10) || 5;
  if (!fs.existsSync(SESSION_LOG)) return console.log('(no session log yet)');
  const text = fs.readFileSync(SESSION_LOG, 'utf8');
  const entries = text.split(/\n## /).slice(1).map((e) => '## ' + e);
  console.log(entries.slice(-n).join('\n') || '(no entries yet)');
}

function search(kw) {
  if (!kw) return fail('search needs a keyword');
  let hits = 0;
  for (const f of [SESSION_LOG, DECISIONS]) {
    if (!fs.existsSync(f)) continue;
    fs.readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
      if (line.toLowerCase().includes(kw.toLowerCase())) {
        console.log(`${path.basename(f)}:${i + 1}: ${line.trim()}`);
        hits++;
      }
    });
  }
  if (!hits) console.log(`(no matches for "${kw}")`);
}

const [cmd, a, b] = process.argv.slice(2);
const table = {
  log: () => log(a),
  decide: () => decide(a, b),
  recent: () => recent(a),
  search: () => search(a),
};
(table[cmd] || (() => console.log('usage: log | decide | recent [n] | search <kw>')))();

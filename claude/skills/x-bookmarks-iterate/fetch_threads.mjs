#!/usr/bin/env node
/**
 * fetch_threads.mjs — fetch X conversation threads for given tweet IDs.
 *
 * Uses the same Chrome-CDP credential-discovery pattern as the bookmark
 * fetcher (see /x-bookmark-export-cdp), but targets the TweetDetail
 * GraphQL operation (which returns the full conversation: original
 * tweet + all replies in the thread).
 *
 * Usage:
 *   node fetch_threads.mjs --ids 1234,5678,9012 --out /tmp/bookmark-threads
 *   node fetch_threads.mjs --ids-file /tmp/ids.txt --out /tmp/bookmark-threads
 *
 * Writes one file per tweet ID:  <out>/<id>.json  containing the raw
 * TweetDetail GraphQL response. Existing files are skipped (idempotent).
 */

import { writeFileSync, existsSync, mkdirSync, readFileSync, cpSync, rmSync, mkdtempSync } from 'fs';
import { join } from 'path';
import { spawn } from 'child_process';
import { tmpdir } from 'os';
import WebSocket from 'ws';

const CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const CHROME_PROFILE = process.env.CHROME_PROFILE
  || `${process.env.HOME}/Library/Application Support/Google/Chrome`;
// unpredictable per-run dir in the user's private temp dir — this holds
// copied Chrome cookies, so it must not live at a fixed world-guessable path
const TEMP_DIR = mkdtempSync(join(tmpdir(), 'bookmark-threads-chrome-'));
const DEBUG_PORT = 9235;  // different port from fetch-bookmarks.mjs

const sleep = ms => new Promise(r => setTimeout(r, ms));

function parseArgs() {
  const args = { ids: [], out: join(tmpdir(), 'bookmark-threads'), force: false };
  for (let i = 2; i < process.argv.length; i++) {
    const a = process.argv[i];
    if (a === '--ids') args.ids = process.argv[++i].split(',').map(s => s.trim()).filter(Boolean);
    else if (a === '--ids-file') args.ids = readFileSync(process.argv[++i], 'utf8').split(/\s+/).filter(Boolean);
    else if (a === '--out') args.out = process.argv[++i];
    else if (a === '--force') args.force = true;
  }
  if (!args.ids.length) {
    console.error('Usage: fetch_threads.mjs --ids id1,id2,... [--out dir] [--force]');
    process.exit(2);
  }
  return args;
}

function prepareProfile() {
  if (existsSync(TEMP_DIR)) rmSync(TEMP_DIR, { recursive: true });
  mkdirSync(join(TEMP_DIR, 'Default'), { recursive: true });
  for (const f of ['Cookies', 'Cookies-journal']) {
    const src = join(CHROME_PROFILE, 'Default', f);
    if (existsSync(src)) cpSync(src, join(TEMP_DIR, 'Default', f));
  }
  const ls = join(CHROME_PROFILE, 'Local State');
  if (existsSync(ls)) cpSync(ls, join(TEMP_DIR, 'Local State'));
  writeFileSync(join(TEMP_DIR, 'First Run'), '');
}

async function launchChrome(seedUrl) {
  const proc = spawn(CHROME_PATH, [
    `--remote-debugging-port=${DEBUG_PORT}`,
    `--user-data-dir=${TEMP_DIR}`,
    '--no-first-run', '--no-default-browser-check', '--disable-extensions',
    '--window-size=800,600', seedUrl,
  ], { stdio: 'ignore', detached: true });
  proc.unref();

  for (let i = 0; i < 20; i++) {
    await sleep(1000);
    try {
      const r = await fetch(`http://localhost:${DEBUG_PORT}/json`);
      if (r.ok) return proc;
    } catch {}
  }
  throw new Error('Chrome did not start');
}

async function connectToPage() {
  const targets = await (await fetch(`http://localhost:${DEBUG_PORT}/json`)).json();
  const page = targets.find(t => t.type === 'page' && t.url.includes('x.com'));
  if (!page) throw new Error('No X page found');

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.on('open', resolve);
    ws.on('error', reject);
  });

  let msgId = 1;
  function evaluate(expression) {
    return new Promise((resolve, reject) => {
      const id = msgId++;
      const timeout = setTimeout(() => reject(new Error('Eval timeout')), 60000);
      function handler(data) {
        const msg = JSON.parse(data.toString());
        if (msg.id === id) {
          clearTimeout(timeout);
          ws.off('message', handler);
          resolve(msg.result?.result?.value);
        }
      }
      ws.on('message', handler);
      ws.send(JSON.stringify({ id, method: 'Runtime.evaluate',
        params: { expression, awaitPromise: true, returnByValue: true } }));
    });
  }

  return { ws, evaluate };
}

async function discoverTweetDetailCreds(ws, evaluate, seedTweetId) {
  let networkMsgId = 99990;
  ws.send(JSON.stringify({ id: networkMsgId++, method: 'Network.enable', params: {} }));
  await sleep(500);

  let qid = null, bearer = null, features = null, fieldToggles = null;

  ws.on('message', (data) => {
    const msg = JSON.parse(data.toString());
    if (msg.method === 'Network.requestWillBeSent') {
      const url = msg.params?.request?.url || '';
      const headers = msg.params?.request?.headers || {};
      if (url.includes('/graphql/') && url.includes('TweetDetail')) {
        const m = url.match(/\/graphql\/([^/]+)\/TweetDetail/);
        if (m) qid = m[1];
        bearer = headers['authorization'] || headers['Authorization'] || bearer;
        const f = url.match(/features=([^&]+)/);
        if (f) features = decodeURIComponent(f[1]);
        const ft = url.match(/fieldToggles=([^&]+)/);
        if (ft) fieldToggles = decodeURIComponent(ft[1]);
      }
    }
  });

  console.log(`→ Navigating to tweet ${seedTweetId} to discover TweetDetail credentials...`);
  await evaluate(`location.href = "https://x.com/i/status/${seedTweetId}"`);

  // Poll for up to 15s
  for (let i = 0; i < 30; i++) {
    if (qid && bearer) break;
    await sleep(500);
  }

  return { qid, bearer, features, fieldToggles };
}

async function fetchOneThread(evaluate, creds, csrf, tweetId) {
  const { qid, bearer, features, fieldToggles } = creds;
  const expr = `
    (async () => {
      const vars = ${JSON.stringify(JSON.stringify({
        focalTweetId: tweetId,
        with_rux_injections: false,
        rankingMode: 'Relevance',
        includePromotedContent: false,
        withCommunity: true,
        withQuickPromoteEligibilityTweetFields: true,
        withBirdwatchNotes: true,
        withVoice: true,
      }))};
      const url = '/i/api/graphql/${qid}/TweetDetail?variables=' + encodeURIComponent(vars)
        + '&features=' + encodeURIComponent(${JSON.stringify(features || '')})
        + (${JSON.stringify(fieldToggles || '')} ? '&fieldToggles=' + encodeURIComponent(${JSON.stringify(fieldToggles || '')}) : '');
      const r = await fetch(url, {
        credentials: 'include',
        headers: {
          Authorization: ${JSON.stringify(bearer)},
          'X-Csrf-Token': ${JSON.stringify(csrf)},
          'Content-Type': 'application/json',
          'x-twitter-active-user': 'yes',
          'x-twitter-auth-type': 'OAuth2Session',
          'x-twitter-client-language': 'en',
        },
      });
      const txt = await r.text();
      return JSON.stringify({ status: r.status, body: txt });
    })()
  `;
  const raw = await evaluate(expr);
  const wrapped = JSON.parse(raw);
  if (wrapped.status !== 200) {
    return { error: `HTTP ${wrapped.status}`, body: wrapped.body.slice(0, 400) };
  }
  return JSON.parse(wrapped.body);
}

async function main() {
  const args = parseArgs();
  mkdirSync(args.out, { recursive: true });

  // Filter to IDs that don't already have a saved thread
  const todo = args.ids.filter(id => args.force || !existsSync(join(args.out, `${id}.json`)));
  if (!todo.length) {
    console.log(`All ${args.ids.length} threads already cached in ${args.out}`);
    return;
  }
  console.log(`Need to fetch ${todo.length} of ${args.ids.length} threads (rest cached)`);

  prepareProfile();
  const seedUrl = `https://x.com/i/status/${todo[0]}`;
  const chromeProc = await launchChrome(seedUrl);
  await sleep(2500);

  const { ws, evaluate } = await connectToPage();

  // Wait for login if needed
  let ct0 = await evaluate('document.cookie.match(/ct0=([^;]+)/)?.[1] || "none"');
  if (ct0 === 'none') {
    console.log('⚠ Not logged in. Log in to X in the Chrome window...');
    for (let i = 0; i < 120; i++) {
      await sleep(2000);
      ct0 = await evaluate('document.cookie.match(/ct0=([^;]+)/)?.[1] || "none"');
      if (ct0 !== 'none') break;
    }
  }

  const creds = await discoverTweetDetailCreds(ws, evaluate, todo[0]);
  if (!creds.qid || !creds.bearer) {
    console.error('✗ Could not discover TweetDetail credentials');
    ws.close();
    try { process.kill(-chromeProc.pid); } catch {}
    process.exit(1);
  }
  console.log(`✓ Credentials discovered (QID: ${creds.qid})`);

  const csrf = await evaluate('document.cookie.match(/ct0=([^;]+)/)[1]');

  let ok = 0, fail = 0;
  for (const id of todo) {
    try {
      const data = await fetchOneThread(evaluate, creds, csrf, id);
      if (data.error) {
        console.error(`  ✗ ${id}: ${data.error}`);
        fail++;
      } else {
        writeFileSync(join(args.out, `${id}.json`), JSON.stringify(data));
        console.log(`  ✓ ${id}`);
        ok++;
      }
    } catch (e) {
      console.error(`  ✗ ${id}: ${e.message}`);
      fail++;
    }
    await sleep(700);
  }

  ws.close();
  try { process.kill(-chromeProc.pid); } catch {}
  rmSync(TEMP_DIR, { recursive: true, force: true });

  console.log(`Done. ${ok} fetched, ${fail} failed. Output: ${args.out}`);
}

main().catch(err => {
  console.error('Fatal:', err.message);
  try { rmSync(TEMP_DIR, { recursive: true, force: true }); } catch {}
  process.exit(1);
});

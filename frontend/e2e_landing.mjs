// Temporary E2E reproduction: landing page navigation with a leftover session.
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import WebSocket from "ws";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = process.env.BASE_URL || "http://localhost:5173";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {
  const profile = mkdtempSync(join(tmpdir(), "ff-chrome-"));
  const proc = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-first-run",
    "--remote-debugging-port=9334", `--user-data-dir=${profile}`, "about:blank",
  ], { stdio: "ignore" });
  let target = null;
  for (let i = 0; i < 60; i++) {
    await sleep(300);
    try {
      const res = await fetch("http://127.0.0.1:9334/json/list");
      target = (await res.json()).find((t) => t.type === "page");
      if (target) break;
    } catch { /* retry */ }
  }
  if (!target) throw new Error("no debug target");
  return { proc, profile, wsUrl: target.webSocketDebuggerUrl };
}

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map();
    ws.on("message", (raw) => {
      const msg = JSON.parse(raw.toString());
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error))); else resolve(msg.result);
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (this.pending.has(id)) { this.pending.delete(id); reject(new Error(`timeout ${method}`)); }
      }, 20000);
    });
  }
}

async function evaluate(cdp, expression) {
  const res = await cdp.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (res.exceptionDetails) throw new Error("eval threw: " + JSON.stringify(res.exceptionDetails));
  return res.result.value;
}

const SCENARIOS = [
  {
    name: "offline-demo-session-left-over",
    seed: `localStorage.setItem('focusflow_user', JSON.stringify({id:1,username:'Alex'}));
            localStorage.setItem('focusflow_offline_demo','1');`,
  },
  {
    name: "stale-token-session-left-over",
    seed: `localStorage.setItem('focusflow_user', JSON.stringify({id:1,username:'Alex',access_token:'deadbeefdeadbeef'}));
            localStorage.setItem('focusflow_access_token','deadbeefdeadbeef');`,
  },
  {
    name: "clean-no-session",
    seed: `localStorage.clear();`,
  },
];

async function run() {
  const { proc, profile, wsUrl } = await launch();
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.on("open", res); ws.on("error", rej); });
  const cdp = new CDP(ws);
  await cdp.send("Runtime.enable");
  await cdp.send("Page.enable");

  const results = {};

  for (const sc of SCENARIOS) {
    await cdp.send("Page.navigate", { url: `${BASE}/` });
    await sleep(1200);
    await evaluate(cdp, sc.seed);
    await cdp.send("Page.reload");
    await sleep(2500);

    const landing = await evaluate(cdp, `(() => {
      const btns = [...document.querySelectorAll('.navbar-actions button')];
      return {
        url: location.href,
        buttons: btns.map(b => ({ text: b.textContent.trim(), visible: !!(b.offsetWidth||b.offsetHeight) })),
        signupButtonPresent: !!document.querySelector('.navbar-actions .btn-primary'),
      };
    })()`);

    const afterLoginClick = await evaluate(cdp, `(async () => {
      const btn = [...document.querySelectorAll('.navbar-actions button')]
        .find(b => /log in|open workspace/i.test(b.textContent));
      if (!btn) return { clicked: false };
      btn.click();
      await new Promise(r => setTimeout(r, 2000));
      return { clicked: true, url: location.href };
    })()`);

    // Try to reach the login page directly by URL (as a user would via a bookmark)
    const directLogin = await evaluate(cdp, `(async () => {
      window.history.pushState({}, '', '/login');
      window.dispatchEvent(new PopStateEvent('popstate'));
      await new Promise(r => setTimeout(r, 1500));
      return { url: location.href, heading: document.querySelector('.form-heading')?.textContent || null };
    })()`);

    results[sc.name] = { landing, afterLoginClick, directLogin };
  }

  console.log(JSON.stringify(results, null, 2));
  ws.close(); proc.kill();
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignore */ }
}

run().catch((e) => { console.error("E2E FAILED:", e); process.exit(1); });

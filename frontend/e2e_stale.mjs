// Temporary E2E: what happens when the stored token is no longer valid?
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import WebSocket from "ws";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const BASE = process.env.BASE_URL || "http://localhost:5173";
const API = process.env.API_URL || "http://127.0.0.1:5000";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {
  const profile = mkdtempSync(join(tmpdir(), "ff-chrome-"));
  const proc = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-first-run",
    "--remote-debugging-port=9335", `--user-data-dir=${profile}`, "about:blank",
  ], { stdio: "ignore" });
  let target = null;
  for (let i = 0; i < 60; i++) {
    await sleep(300);
    try {
      const res = await fetch("http://127.0.0.1:9335/json/list");
      target = (await res.json()).find((t) => t.type === "page");
      if (target) break;
    } catch { /* retry */ }
  }
  if (!target) throw new Error("no debug target");
  return { proc, profile, wsUrl: target.webSocketDebuggerUrl };
}

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map(); this.netEvents = [];
    ws.on("message", (raw) => {
      const msg = JSON.parse(raw.toString());
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error))); else resolve(msg.result);
      } else if (msg.method === "Network.responseReceived") {
        const r = msg.params.response;
        if (r.url.includes("/api/")) this.netEvents.push(`${r.status} ${r.url.replace(/^https?:\/\/[^/]+/, "")}`);
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

async function run() {
  const { proc, profile, wsUrl } = await launch();
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.on("open", res); ws.on("error", rej); });
  const cdp = new CDP(ws);
  await cdp.send("Runtime.enable");
  await cdp.send("Page.enable");
  await cdp.send("Network.enable");

  const results = {};

  // 1. Log in for real to get a genuine token
  await cdp.send("Page.navigate", { url: `${BASE}/login` });
  await sleep(3000);
  await evaluate(cdp, `(async () => {
    document.querySelector('button.submit-btn').click();
    await new Promise(r => setTimeout(r, 2500));
  })()`);
  const token = await evaluate(cdp, `localStorage.getItem('focusflow_access_token')`);
  results.step1_login_token = token ? "obtained" : "MISSING";

  // 2. Revoke that token server-side (simulates logout revocation / DB reset)
  const revoke = await fetch(`${API}/api/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: "{}",
  });
  results.step2_revoke_status = revoke.status;

  // 3. Now the browser still holds the dead token. Go to the landing page.
  await cdp.send("Page.navigate", { url: `${BASE}/` });
  await sleep(2500);
  results.step3_landing = await evaluate(cdp, `(() => {
    const btns = [...document.querySelectorAll('.navbar-actions button')];
    return {
      url: location.href,
      buttons: btns.map(b => b.textContent.trim()),
      signupVisible: !!document.querySelector('.navbar-actions .btn-primary'),
    };
  })()`);

  // 4. Click "Log in" -> does it reach the login form?
  results.step4_clickLogin = await evaluate(cdp, `(async () => {
    const btn = [...document.querySelectorAll('.navbar-actions button')]
      .find(b => /log in|open workspace/i.test(b.textContent));
    if (!btn) return { clicked: false };
    btn.click();
    await new Promise(r => setTimeout(r, 2500));
    return {
      clicked: true,
      url: location.href,
      formVisible: !!document.querySelector('form.auth-form'),
      errorText: document.querySelector('.error-badge')?.innerText?.trim() || null,
    };
  })()`);

  // 5. Try to open the signup page by URL
  await cdp.send("Page.navigate", { url: `${BASE}/signup` });
  await sleep(2500);
  results.step5_directSignup = await evaluate(cdp, `({
    url: location.href,
    formVisible: !!document.querySelector('form.auth-form'),
    heading: document.querySelector('.form-heading')?.textContent || null,
  })`);

  results.step6_apiCalls = cdp.netEvents.slice(-14);
  results.step7_sessionStillStored = await evaluate(cdp, `({
    token: localStorage.getItem('focusflow_access_token'),
    user: localStorage.getItem('focusflow_user'),
  })`);

  console.log(JSON.stringify(results, null, 2));
  ws.close(); proc.kill();
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignore */ }
}

run().catch((e) => { console.error("E2E FAILED:", e); process.exit(1); });

// Temporary E2E reproduction of the sign-in / sign-up flow using the
// Chrome DevTools Protocol (no extra npm dependencies required).
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
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--remote-debugging-port=9333",
    `--user-data-dir=${profile}`,
    "about:blank",
  ], { stdio: "ignore" });

  let target = null;
  for (let i = 0; i < 60; i++) {
    await sleep(300);
    try {
      const res = await fetch("http://127.0.0.1:9333/json/list");
      const list = await res.json();
      target = list.find((t) => t.type === "page");
      if (target) break;
    } catch { /* not up yet */ }
  }
  if (!target) throw new Error("Chrome did not expose a debugging target");
  return { proc, profile, wsUrl: target.webSocketDebuggerUrl };
}

class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    this.events = [];
    ws.on("message", (raw) => {
      const msg = JSON.parse(raw.toString());
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else if (msg.method) {
        this.events.push(msg);
      }
    });
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`timeout: ${method}`));
        }
      }, 20000);
    });
  }
}

async function evaluate(cdp, expression) {
  const res = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (res.exceptionDetails) {
    throw new Error("eval threw: " + JSON.stringify(res.exceptionDetails));
  }
  return res.result.value;
}


async function run() {
  const { proc, profile, wsUrl } = await launch();
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.on("open", res); ws.on("error", rej); });
  const cdp = new CDP(ws);

  await cdp.send("Runtime.enable");
  await cdp.send("Log.enable");
  await cdp.send("Network.enable");
  await cdp.send("Page.enable");

  const consoleErrors = [];
  const failedRequests = [];
  const consoleLogs = [];

  ws.on("message", (raw) => {
    const msg = JSON.parse(raw.toString());
    if (msg.method === "Runtime.consoleAPICalled") {
      const text = (msg.params.args || []).map((a) => a.value ?? a.description ?? "").join(" ");
      consoleLogs.push(`[${msg.params.type}] ${text}`);
      if (msg.params.type === "error" || msg.params.type === "warning") {
        consoleErrors.push(`[${msg.params.type}] ${text}`);
      }
    }
    if (msg.method === "Log.entryAdded" && msg.params.entry.level === "error") {
      consoleErrors.push(`[log:${msg.params.entry.source}] ${msg.params.entry.text}`);
    }
    if (msg.method === "Network.loadingFailed") {
      failedRequests.push(`${msg.params.type} ${msg.params.errorText}`);
    }
    if (msg.method === "Network.responseReceived") {
      const r = msg.params.response;
      if (r.url.includes("/api/")) consoleLogs.push(`[api] ${r.status} ${r.url}`);
    }
  });

  const results = {};

  // ---------- LOGIN ----------
  await cdp.send("Page.navigate", { url: `${BASE}/login` });
  await sleep(3500);

  results.loginPageRendered = await evaluate(cdp, `(() => {
    const form = document.querySelector('form.auth-form');
    const btn = document.querySelector('button.submit-btn');
    return {
      hasForm: !!form,
      hasButton: !!btn,
      buttonText: btn ? btn.textContent.trim() : null,
      bodyText: document.body.innerText.slice(0, 300),
    };
  })()`);

  results.loginClick = await evaluate(cdp, `(async () => {
    const btn = document.querySelector('button.submit-btn');
    if (!btn) return { clicked: false, reason: 'no button' };
    btn.click();
    await new Promise(r => setTimeout(r, 2500));
    return {
      clicked: true,
      url: location.href,
      errorBadge: document.querySelector('.error-badge')?.innerText?.trim() || null,
      localStorage: Object.fromEntries(Object.entries(localStorage)),
    };
  })()`);


  // ---------- SIGNUP ----------
  await evaluate(cdp, `localStorage.clear()`);
  await cdp.send("Page.navigate", { url: `${BASE}/signup` });
  await sleep(2500);

  results.signupPageRendered = await evaluate(cdp, `(() => {
    const form = document.querySelector('form.auth-form');
    const btn = document.querySelector('button.submit-btn');
    const inputs = [...document.querySelectorAll('form.auth-form input')].map(i => ({ type: i.type, ph: i.placeholder }));
    return { hasForm: !!form, hasButton: !!btn, buttonText: btn?.textContent?.trim() || null, inputs };
  })()`);

  const uniq = `e2e${Date.now()}`;
  results.signupClick = await evaluate(cdp, `(async () => {
    const form = document.querySelector('form.auth-form');
    if (!form) return { clicked: false, reason: 'no form' };
    const inputs = [...form.querySelectorAll('input')];
    const setVal = (el, v) => {
      const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    };
    setVal(inputs[0], '${uniq}');
    setVal(inputs[1], '${uniq}@example.com');
    setVal(inputs[2], 'secret123');
    setVal(inputs[3], 'secret123');
    await new Promise(r => setTimeout(r, 300));
    const btn = form.querySelector('button.submit-btn');
    btn.click();
    await new Promise(r => setTimeout(r, 3000));
    return {
      clicked: true,
      url: location.href,
      errorBadge: document.querySelector('.error-badge')?.innerText?.trim() || null,
      localStorage: Object.fromEntries(Object.entries(localStorage)),
    };
  })()`);

  results.consoleErrors = consoleErrors;
  results.failedRequests = failedRequests;
  results.consoleLogs = consoleLogs.slice(-40);

  console.log(JSON.stringify(results, null, 2));

  ws.close();
  proc.kill();
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignore */ }
}

run().catch((err) => {
  console.error("E2E FAILED:", err);
  process.exit(1);
});

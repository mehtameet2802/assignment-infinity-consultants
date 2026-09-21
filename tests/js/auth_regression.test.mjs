import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import test from "node:test";
import { JSDOM } from "jsdom";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const staticJs = join(repoRoot, "app", "static", "js");
let importCounter = 0;

async function importStatic(moduleName, { fresh = false } = {}) {
  const base = pathToFileURL(join(staticJs, moduleName)).href;
  const href = fresh ? `${base}?t=${importCounter++}` : base;
  return import(href);
}

function setupUnlockDom() {
  const dom = new JSDOM(
    `
    <div id="view-unlock" class="hidden"></div>
    <div id="app-shell" class="hidden"></div>
  `,
    { url: "http://127.0.0.1/" }
  );
  globalThis.document = dom.window.document;
  globalThis.window = dom.window;
  globalThis.sessionStorage = dom.window.sessionStorage;
  return dom;
}

test("missing sessionStorage key shows unlock view", async () => {
  setupUnlockDom();
  const { showUnlockView, getApiKey } = await importStatic("auth.js", { fresh: true });
  assert.equal(getApiKey(), null);
  showUnlockView();
  assert.equal(document.getElementById("view-unlock").classList.contains("hidden"), false);
});

test("api client attaches X-API-Key header", async () => {
  setupUnlockDom();
  const { setApiKey } = await importStatic("auth.js", { fresh: true });
  setApiKey("st_test-header-key");
  const originalFetch = globalThis.fetch;
  let capturedHeaders = null;
  globalThis.fetch = async (_url, options) => {
    capturedHeaders = options.headers;
    return {
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ ok: true }),
    };
  };
  const { apiGet } = await importStatic("api.js", { fresh: true });
  await apiGet("/expenses");
  globalThis.fetch = originalFetch;
  assert.equal(capturedHeaders["X-API-Key"], "st_test-header-key");
});

test("401 response clears stored key and notifies lock handler", async () => {
  setupUnlockDom();
  const authMod = await import(pathToFileURL(join(staticJs, "auth.js")).href);
  const { apiGet } = await import(pathToFileURL(join(staticJs, "api.js")).href);
  authMod.setApiKey("st_old");
  let locked = false;
  authMod.onUnauthorized(() => {
    locked = true;
  });
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    text: async () =>
      JSON.stringify({
        error: "unauthorized",
        details: [{ field: null, message: "A valid API key is required" }],
      }),
  });
  await apiGet("/dashboard?month=2026-09").catch(() => {});
  assert.equal(authMod.getApiKey(), null);
  assert.equal(locked, true);
  globalThis.fetch = undefined;
});

test("rotation new key is rendered as text only in markup", () => {
  const html = readFileSync(join(repoRoot, "app", "static", "index.html"), "utf8");
  assert.match(html, /id="rotation-new-key"/);
  assert.doesNotMatch(html, /innerHTML\s*=\s*.*api_key/);
});

test("security route exists in app path map", () => {
  const appSource = readFileSync(join(staticJs, "app.js"), "utf8");
  assert.match(appSource, /security:\s*"\/settings\/security"/);
});

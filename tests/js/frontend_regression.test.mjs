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
  const href = fresh ? `${base}?test=${moduleName}-${importCounter++}` : base;
  return import(href);
}

test("escapeHtml neutralizes HTML in expense notes", async () => {
  const { escapeHtml } = await importStatic("formatters.js");
  const payload = '<img src=x onerror="alert(1)">';
  const escaped = escapeHtml(payload);
  assert.equal(escaped.includes("<"), false);
  assert.equal(escaped.includes("onerror"), true);
});

test("expenseTableRowHtml does not emit raw HTML from notes", async () => {
  const { expenseTableRowHtml } = await importStatic("expenses.js");
  const row = expenseTableRowHtml({
    date: "2025-08-01",
    category: "Other",
    payment_method: "Cash",
    note: '<script>alert("xss")</script>',
    amount: "10.00",
  });
  assert.match(row, /&lt;script&gt;alert/);
  assert.doesNotMatch(row, /<script>alert/);
});

test("initAnalytics runs before initNavigation in app bootstrap", () => {
  const appSource = readFileSync(join(staticJs, "app.js"), "utf8");
  const initAppBlock = appSource.slice(appSource.indexOf("function initApp()"));
  const analyticsIdx = initAppBlock.indexOf("initAnalytics(");
  const navigationIdx = initAppBlock.indexOf("initNavigation(");
  assert.ok(analyticsIdx > -1 && navigationIdx > -1);
  assert.ok(analyticsIdx < navigationIdx);
});

test("initAnalytics initializes month inputs for direct /analytics load", async () => {
  const dom = new JSDOM(
    `
    <input id="analytics-start-month" type="month" />
    <input id="analytics-end-month" type="month" />
    <button id="analytics-apply" type="button"></button>
    <button id="analytics-retry" type="button"></button>
  `,
    { url: "http://127.0.0.1/analytics" }
  );
  globalThis.document = dom.window.document;
  globalThis.window = dom.window;

  const { getAnalyticsRange, initAnalytics } = await importStatic("analytics.js", {
    fresh: true,
  });
  assert.deepEqual(getAnalyticsRange(), ["", ""]);
  initAnalytics("2026-04", "2026-09");
  assert.deepEqual(getAnalyticsRange(), ["2026-04", "2026-09"]);
});

test("populateComboSelectors clears stale combination UI when empty", async () => {
  const dom = new JSDOM(
    `
    <p id="analytics-combo-empty" class="hidden"></p>
    <select id="analytics-combo-category"><option>Stale</option></select>
    <select id="analytics-combo-payment"><option>Stale</option></select>
    <table><tbody id="analytics-combo-table"><tr><td>stale row</td></tr></tbody></table>
    <canvas id="analytics-combo-chart"></canvas>
  `
  );
  globalThis.document = dom.window.document;
  globalThis.window = dom.window;
  globalThis.Chart = class {
    destroy() {}
  };

  const { populateComboSelectors } = await importStatic("analytics.js", { fresh: true });
  populateComboSelectors({ category_payment_monthly: [] });

  const empty = document.getElementById("analytics-combo-empty");
  const table = document.getElementById("analytics-combo-table");
  assert.equal(empty.classList.contains("hidden"), false);
  assert.equal(table.innerHTML, "");
  assert.equal(document.getElementById("analytics-combo-category").innerHTML, "");
  assert.equal(document.getElementById("analytics-combo-payment").innerHTML, "");
});

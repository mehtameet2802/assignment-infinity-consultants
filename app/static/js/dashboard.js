import { apiGet } from "./api.js";
import { renderCategoryDonut } from "./charts.js";
import {
  formatChangeSummary,
  formatCurrency,
  formatDisplayDate,
  formatMonth,
  formatPercentage,
  shiftMonth,
} from "./formatters.js";

let selectedMonth = null;
let loading = false;

function setLoading(isLoading) {
  loading = isLoading;
  const overlay = document.getElementById("dashboard-loading");
  if (overlay) overlay.classList.toggle("hidden", !isLoading);
}

function renderTopMetric(containerId, items, emptyLabel) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!items?.length) {
    el.innerHTML = `<p class="font-metric-md text-metric-md text-on-surface">No spending</p>`;
    return;
  }
  if (items.length === 1) {
    const item = items[0];
    const name = item.category || item.payment_method;
    el.innerHTML = `
      <p class="text-3xl font-bold text-on-surface">${formatCurrency(item.amount)}</p>
      <p class="font-semibold mt-2">${name}</p>
      <p class="text-sm text-secondary">${formatPercentage(item.percentage_of_total)} of total</p>
    `;
    return;
  }
  const names = items.map((item) => item.category || item.payment_method).join(", ");
  const tieLabel = items[0].category ? "tied categories" : "tied methods";
  el.innerHTML = `
    <p class="text-3xl font-bold text-on-surface">${formatCurrency(items[0].amount)}</p>
    <p class="font-semibold mt-2">${items.length} ${tieLabel}</p>
    <p class="text-sm text-secondary" title="${names}">${names}</p>
  `;
}

function fixTopPaymentTies(containerId, items) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!items?.length) {
    el.innerHTML = `<p class="font-metric-md text-metric-md text-on-surface">No spending</p>`;
    return;
  }
  if (items.length === 1) {
    const item = items[0];
    el.innerHTML = `
      <p class="font-metric-lg text-metric-lg text-on-surface">${formatCurrency(item.amount)}</p>
      <p class="font-headline-sm text-headline-sm mt-2">${item.payment_method}</p>
      <p class="font-body-sm text-body-sm text-secondary">${formatPercentage(item.percentage_of_total)} of total</p>
    `;
    return;
  }
  const names = items.map((item) => item.payment_method).join(", ");
  el.innerHTML = `
    <p class="font-metric-lg text-metric-lg text-on-surface">${formatCurrency(items[0].amount)}</p>
    <p class="font-headline-sm text-headline-sm mt-2">${items.length} tied methods</p>
    <p class="font-body-sm text-body-sm text-secondary" title="${names}">${names}</p>
  `;
}

function renderDashboard(data) {
  document.getElementById("dashboard-month-label").textContent = formatMonth(data.month);
  document.getElementById("dashboard-total-spend").textContent = formatCurrency(data.total_spend);
  document.getElementById("dashboard-txn-count").textContent = `${data.transaction_count} expenses this month`;

  const change = formatChangeSummary(data.month_change);
  document.getElementById("dashboard-change-amount").textContent = change.amount;
  document.getElementById("dashboard-change-percent").textContent = change.percent;
  document.getElementById("dashboard-change-previous").textContent = `from ${formatCurrency(data.month_change.previous_amount)}`;

  renderTopMetric("dashboard-top-category", data.top_categories, "No spending");
  fixTopPaymentTies("dashboard-top-payment", data.top_payment_methods);

  const categoryList = document.getElementById("dashboard-category-list");
  categoryList.innerHTML = data.category_breakdown
    .map(
      (item) => `
      <div class="flex items-center justify-between py-2 border-b border-outline-variant/20">
        <span class="font-body-md">${item.category}</span>
        <div class="text-right">
          <p class="font-headline-sm">${formatCurrency(item.amount)}</p>
          <p class="font-body-sm text-secondary">${formatPercentage(item.percentage_of_total)}</p>
        </div>
      </div>`
    )
    .join("");

  const paymentList = document.getElementById("dashboard-payment-list");
  paymentList.innerHTML = data.payment_method_breakdown
    .map(
      (item) => `
      <div class="flex items-center justify-between py-2 border-b border-outline-variant/20">
        <span class="font-body-md">${item.payment_method}</span>
        <div class="text-right">
          <p class="font-headline-sm">${formatCurrency(item.amount)}</p>
          <p class="font-body-sm text-secondary">${formatPercentage(item.percentage_of_total)}</p>
        </div>
      </div>`
    )
    .join("");

  const donutWrap = document.getElementById("dashboard-donut-wrap");
  const donutEmpty = document.getElementById("dashboard-donut-empty");
  const canvas = document.getElementById("dashboard-category-chart");
  if (Number(data.total_spend) > 0) {
    donutWrap.classList.remove("hidden");
    donutEmpty.classList.add("hidden");
    renderCategoryDonut(canvas, data.category_breakdown, data.total_spend);
  } else {
    donutWrap.classList.add("hidden");
    donutEmpty.classList.remove("hidden");
  }

  const tbody = document.getElementById("dashboard-recent-body");
  if (!data.recent_expenses.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-secondary">No expenses in this month.</td></tr>`;
    return;
  }
  tbody.innerHTML = data.recent_expenses
    .map(
      (item) => `
      <tr class="border-t border-outline-variant/20">
        <td class="py-3 px-4">${formatDisplayDate(item.date)}</td>
        <td class="py-3 px-4">${item.category}</td>
        <td class="py-3 px-4">${item.payment_method}</td>
        <td class="py-3 px-4">${item.note || "—"}</td>
        <td class="py-3 px-4 text-right font-headline-sm">${formatCurrency(item.amount)}</td>
      </tr>`
    )
    .join("");
}

function showDashboardError(message) {
  document.getElementById("dashboard-error").textContent = message;
  document.getElementById("dashboard-error").classList.remove("hidden");
  document.getElementById("dashboard-retry").classList.remove("hidden");
}

function hideDashboardError() {
  document.getElementById("dashboard-error").classList.add("hidden");
}

export async function loadDashboard(month) {
  if (loading) return;
  selectedMonth = month;
  setLoading(true);
  hideDashboardError();
  try {
    const data = await apiGet(`/dashboard?month=${encodeURIComponent(month)}`);
    renderDashboard(data);
  } catch {
    showDashboardError("Couldn't load dashboard data.");
  } finally {
    setLoading(false);
  }
}

export function getSelectedDashboardMonth() {
  return selectedMonth;
}

export function initDashboard(initialMonth, onMonthChange) {
  selectedMonth = initialMonth;
  document.getElementById("dashboard-prev-month").addEventListener("click", () => {
    const next = shiftMonth(selectedMonth, -1);
    onMonthChange(next);
  });
  document.getElementById("dashboard-next-month").addEventListener("click", () => {
    const next = shiftMonth(selectedMonth, 1);
    onMonthChange(next);
  });
  document.getElementById("dashboard-retry").addEventListener("click", () => {
    loadDashboard(selectedMonth);
  });
}

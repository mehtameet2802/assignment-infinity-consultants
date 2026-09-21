import { apiGet } from "./api.js";
import { renderBarChart, renderLineChart } from "./charts.js";
import {
  formatChangeAmount,
  formatCurrency,
  formatMonth,
  formatPercentage,
  shiftMonth,
} from "./formatters.js";

let summaryData = null;

function setLoading(isLoading) {
  document.getElementById("analytics-loading").classList.toggle("hidden", !isLoading);
}

function showError(message) {
  const el = document.getElementById("analytics-error");
  el.textContent = message;
  el.classList.remove("hidden");
}

function hideError() {
  document.getElementById("analytics-error").classList.add("hidden");
}

function formatChangeCell(point) {
  if (point.change_type === "not_applicable") return { amount: "—", percent: "—" };
  if (point.change_type === "no_change") return { amount: formatCurrency(0), percent: "0%" };
  if (point.change_type === "new") return { amount: formatChangeAmount(point.change_amount), percent: "New" };
  if (point.change_type === "resumed") return { amount: formatChangeAmount(point.change_amount), percent: "Resumed" };
  return {
    amount: formatChangeAmount(point.change_amount),
    percent: formatPercentage(point.change_percentage),
  };
}

function renderOverall(data) {
  const labels = data.monthly_totals.map((item) => formatMonth(item.month));
  renderLineChart(
    "analytics-overall",
    document.getElementById("analytics-overall-chart"),
    labels,
    [
      {
        label: "Total Spend",
        data: data.monthly_totals.map((item) => Number(item.amount)),
        borderColor: "#4f46e5",
        backgroundColor: "rgba(79,70,229,0.15)",
        tension: 0.25,
        fill: true,
      },
    ]
  );

  const tbody = document.getElementById("analytics-overall-table");
  tbody.innerHTML = data.monthly_totals
    .map((point) => {
      const change = formatChangeCell(point);
      return `<tr class="border-t border-outline-variant/20">
        <td class="py-2 px-3">${formatMonth(point.month)}</td>
        <td class="py-2 px-3">${formatCurrency(point.amount)}</td>
        <td class="py-2 px-3">${change.amount}</td>
        <td class="py-2 px-3">${change.percent}</td>
      </tr>`;
    })
    .join("");
}

function topCategoriesByRange(data, limit = 5) {
  return [...data.category_monthly]
    .map((series) => ({
      category: series.category,
      total: series.months.reduce((sum, month) => sum + Number(month.amount), 0),
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, limit)
    .filter((item) => item.total > 0);
}

function renderCategorySection(data) {
  const selector = document.getElementById("analytics-category-select");
  selector.innerHTML = `<option value="">Top categories (chart)</option>`;
  data.category_monthly.forEach((series) => {
    const option = document.createElement("option");
    option.value = series.category;
    option.textContent = series.category;
    selector.appendChild(option);
  });

  const renderChart = () => {
    const selected = selector.value;
    const labels = data.monthly_totals.map((item) => formatMonth(item.month));
    if (!selected) {
      const top = topCategoriesByRange(data);
      renderBarChart(
        "analytics-category",
        document.getElementById("analytics-category-chart"),
        labels,
        top.map((item, index) => ({
          label: item.category,
          data: data.category_monthly
            .find((series) => series.category === item.category)
            .months.map((month) => Number(month.amount)),
          backgroundColor: ["#4f46e5", "#3525cd", "#006e4b", "#565e74", "#6ffbbe"][index % 5],
        }))
      );
      document.getElementById("analytics-category-table").innerHTML = "";
      return;
    }
    const series = data.category_monthly.find((item) => item.category === selected);
    renderLineChart(
      "analytics-category",
      document.getElementById("analytics-category-chart"),
      labels,
      [
        {
          label: selected,
          data: series.months.map((month) => Number(month.amount)),
          borderColor: "#4f46e5",
          tension: 0.2,
        },
      ]
    );
    document.getElementById("analytics-category-table").innerHTML = series.months
      .map((point) => {
        const change = formatChangeCell(point);
        return `<tr class="border-t border-outline-variant/20">
          <td class="py-2 px-3">${formatMonth(point.month)}</td>
          <td class="py-2 px-3">${formatCurrency(point.amount)}</td>
          <td class="py-2 px-3">${change.amount}</td>
          <td class="py-2 px-3">${change.percent}</td>
        </tr>`;
      })
      .join("");
  };

  selector.onchange = renderChart;
  renderChart();
}

function renderPaymentSection(data) {
  const labels = data.monthly_totals.map((item) => formatMonth(item.month));
  renderBarChart(
    "analytics-payment",
    document.getElementById("analytics-payment-chart"),
    labels,
    data.payment_method_monthly.map((series, index) => ({
      label: series.payment_method,
      data: series.months.map((month) => Number(month.amount)),
      backgroundColor: ["#4f46e5", "#3525cd", "#006e4b", "#565e74"][index % 4],
    }))
  );
}

function populateComboSelectors(data) {
  const categorySelect = document.getElementById("analytics-combo-category");
  const paymentSelect = document.getElementById("analytics-combo-payment");
  const combos = data.category_payment_monthly;
  const categories = [...new Set(combos.map((item) => item.category))];
  categorySelect.innerHTML = categories.map((c) => `<option value="${c}">${c}</option>`).join("");
  const updatePayments = () => {
    const category = categorySelect.value;
    const methods = combos
      .filter((item) => item.category === category)
      .map((item) => item.payment_method);
    paymentSelect.innerHTML = methods
      .map((method) => `<option value="${method}">${method}</option>`)
      .join("");
    renderComboChart(data);
  };
  categorySelect.onchange = updatePayments;
  paymentSelect.onchange = () => renderComboChart(data);
  if (categories.length) {
    updatePayments();
  }
}

function renderComboChart(data) {
  const empty = document.getElementById("analytics-combo-empty");
  if (!data.category_payment_monthly.length) {
    empty.textContent = "No category/payment combinations have spending in this period.";
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  const category = document.getElementById("analytics-combo-category").value;
  const payment = document.getElementById("analytics-combo-payment").value;
  const series = data.category_payment_monthly.find(
    (item) => item.category === category && item.payment_method === payment
  );
  if (!series) return;
  const labels = series.months.map((month) => formatMonth(month.month));
  renderLineChart(
    "analytics-combo",
    document.getElementById("analytics-combo-chart"),
    labels,
    [
      {
        label: `${category} + ${payment}`,
        data: series.months.map((month) => Number(month.amount)),
        borderColor: "#006e4b",
        tension: 0.2,
      },
    ]
  );
  document.getElementById("analytics-combo-table").innerHTML = series.months
    .map((point) => {
      const change = formatChangeCell(point);
      return `<tr class="border-t border-outline-variant/20">
        <td class="py-2 px-3">${formatMonth(point.month)}</td>
        <td class="py-2 px-3">${formatCurrency(point.amount)}</td>
        <td class="py-2 px-3">${change.amount}</td>
        <td class="py-2 px-3">${change.percent}</td>
      </tr>`;
    })
    .join("");
}

function renderInsights(data) {
  const container = document.getElementById("analytics-insights");
  if (!data.insights.length) {
    container.innerHTML =
      '<p class="text-secondary font-body-md">No notable month-over-month changes for this period.</p>';
    return;
  }
  container.innerHTML = data.insights
    .map(
      (insight) => `
      <div class="bg-surface-container-lowest rounded-xl p-4 shadow-sm border border-outline-variant/20">
        <p class="font-label-sm text-secondary uppercase">${insight.type}</p>
        <p class="font-body-md mt-1">${insight.message}</p>
      </div>`
    )
    .join("");
}

function renderAnalytics(data) {
  summaryData = data;
  renderOverall(data);
  renderCategorySection(data);
  renderPaymentSection(data);
  populateComboSelectors(data);
  renderInsights(data);
}

export async function loadAnalytics(startMonth, endMonth) {
  if (startMonth > endMonth) {
    showError("Start month must not be after end month.");
    return;
  }
  setLoading(true);
  hideError();
  try {
    const data = await apiGet(
      `/summary?start_month=${encodeURIComponent(startMonth)}&end_month=${encodeURIComponent(endMonth)}`
    );
    renderAnalytics(data);
  } catch (error) {
    showError("Couldn't load analytics.");
  } finally {
    setLoading(false);
  }
}

export function initAnalytics(defaultStart, defaultEnd) {
  const startInput = document.getElementById("analytics-start-month");
  const endInput = document.getElementById("analytics-end-month");
  startInput.value = defaultStart;
  endInput.value = defaultEnd;

  document.getElementById("analytics-apply").addEventListener("click", () => {
    loadAnalytics(startInput.value, endInput.value);
  });
  document.getElementById("analytics-retry").addEventListener("click", () => {
    loadAnalytics(startInput.value, endInput.value);
  });
}

export function getSummaryData() {
  return summaryData;
}

import { ApiError, apiGet } from "./api.js";
import { formatCurrency, formatDisplayDate } from "./formatters.js";

const state = {
  offset: 0,
  limit: 20,
  filters: {
    category: "",
    payment_method: "",
    start_date: "",
    end_date: "",
  },
};

function buildQuery() {
  const params = new URLSearchParams();
  params.set("limit", String(state.limit));
  params.set("offset", String(state.offset));
  if (state.filters.category) params.set("category", state.filters.category);
  if (state.filters.payment_method) params.set("payment_method", state.filters.payment_method);
  if (state.filters.start_date) params.set("start_date", state.filters.start_date);
  if (state.filters.end_date) params.set("end_date", state.filters.end_date);
  return `/expenses?${params.toString()}`;
}

function setLoading(isLoading) {
  document.getElementById("expenses-loading").classList.toggle("hidden", !isLoading);
}

function showError(message) {
  const el = document.getElementById("expenses-error");
  el.textContent = message;
  el.classList.remove("hidden");
  document.getElementById("expenses-retry").classList.remove("hidden");
}

function hideError() {
  document.getElementById("expenses-error").classList.add("hidden");
}

function hasActiveFilters() {
  return Object.values(state.filters).some(Boolean);
}

function renderExpenses(data) {
  const tbody = document.getElementById("expenses-table-body");
  const empty = document.getElementById("expenses-empty");
  if (!data.items.length) {
    tbody.innerHTML = "";
    empty.textContent = hasActiveFilters()
      ? "No expenses match these filters."
      : "No expenses yet. Add your first expense to start tracking.";
    empty.classList.remove("hidden");
  } else {
    empty.classList.add("hidden");
    tbody.innerHTML = data.items
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

  const start = data.total === 0 ? 0 : data.offset + 1;
  const end = Math.min(data.offset + data.limit, data.total);
  document.getElementById("expenses-page-label").textContent = `Showing ${start}–${end} of ${data.total}`;

  document.getElementById("expenses-prev").disabled = data.offset <= 0;
  document.getElementById("expenses-next").disabled = data.offset + data.limit >= data.total;
}

export async function loadExpenses() {
  setLoading(true);
  hideError();
  try {
    const data = await apiGet(buildQuery());
    renderExpenses(data);
  } catch (error) {
    if (error instanceof ApiError && error.body?.error === "invalid_date_range") {
      const detail = error.body.details?.[0]?.message || "Invalid date range.";
      showError(detail);
    } else {
      showError("Couldn't load expenses.");
    }
  } finally {
    setLoading(false);
  }
}

export function initExpenses() {
  document.getElementById("expenses-apply-filters").addEventListener("click", () => {
    state.filters.category = document.getElementById("filter-category").value;
    state.filters.payment_method = document.getElementById("filter-payment").value;
    state.filters.start_date = document.getElementById("filter-start-date").value;
    state.filters.end_date = document.getElementById("filter-end-date").value;
    state.offset = 0;
    loadExpenses();
  });

  document.getElementById("expenses-clear-filters").addEventListener("click", () => {
    document.getElementById("filter-category").value = "";
    document.getElementById("filter-payment").value = "";
    document.getElementById("filter-start-date").value = "";
    document.getElementById("filter-end-date").value = "";
    state.filters = { category: "", payment_method: "", start_date: "", end_date: "" };
    state.offset = 0;
    loadExpenses();
  });

  document.getElementById("expenses-prev").addEventListener("click", () => {
    state.offset = Math.max(0, state.offset - state.limit);
    loadExpenses();
  });
  document.getElementById("expenses-next").addEventListener("click", () => {
    state.offset += state.limit;
    loadExpenses();
  });
  document.getElementById("expenses-retry").addEventListener("click", loadExpenses);
}

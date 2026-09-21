import { ApiError, apiPost } from "./api.js";
import { getAnalyticsRange, initAnalytics, loadAnalytics } from "./analytics.js";
import {
  getSelectedDashboardMonth,
  initDashboard,
  loadDashboard,
} from "./dashboard.js";
import { initExpenses, loadExpenses } from "./expenses.js";
import {
  CATEGORIES,
  PAYMENT_METHODS,
  currentMonth,
  formatCurrency,
  monthFromDate,
  shiftMonth,
  todayIsoDate,
} from "./formatters.js";

let activeView = "dashboard";
let expenseSubmitting = false;

function showToast(amount) {
  const toast = document.getElementById("success-toast");
  document.getElementById("toast-amount").textContent = formatCurrency(amount);
  toast.classList.remove("hidden", "opacity-0", "translate-y-2");
  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.classList.add("hidden"), 300);
  }, 3500);
}

function setActiveView(view) {
  activeView = view;
  ["dashboard", "expenses", "analytics"].forEach((name) => {
    document.getElementById(`view-${name}`).classList.toggle("hidden", name !== view);
    document.querySelectorAll(`[data-nav="${name}"]`).forEach((link) => {
      link.classList.toggle("text-primary", name === view);
      link.classList.toggle("border-b-2", name === view);
      link.classList.toggle("border-primary", name === view);
    });
  });
  if (view === "dashboard") loadDashboard(getSelectedDashboardMonth() || currentMonth());
  if (view === "expenses") loadExpenses();
  if (view === "analytics") {
    const [startMonth, endMonth] = getAnalyticsRange();
    loadAnalytics(startMonth, endMonth);
  }
}

function initNavigation() {
  window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace("#", "") || "dashboard";
    setActiveView(hash);
  });
  document.querySelectorAll("[data-nav]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const target = link.getAttribute("data-nav");
      window.location.hash = target;
    });
  });
  const initial = window.location.hash.replace("#", "") || "dashboard";
  setActiveView(initial);
}

function toggleExpenseModal(open) {
  document.getElementById("expense-modal").classList.toggle("hidden", !open);
  if (open) {
    document.getElementById("expense-date").value = todayIsoDate();
    document.getElementById("expense-date").max = todayIsoDate();
    clearExpenseFormErrors();
  }
}

function clearExpenseFormErrors() {
  document.getElementById("expense-form-error").textContent = "";
  document.querySelectorAll("[data-field-error]").forEach((el) => {
    el.textContent = "";
  });
}

function showExpenseFieldErrors(details) {
  details.forEach((detail) => {
    const field = detail.field || "form";
    const target =
      field === "form"
        ? document.getElementById("expense-form-error")
        : document.querySelector(`[data-field-error="${field}"]`);
    if (target) target.textContent = detail.message;
  });
}

async function submitExpense(event) {
  event.preventDefault();
  if (expenseSubmitting) return;
  clearExpenseFormErrors();
  expenseSubmitting = true;
  document.getElementById("expense-submit").disabled = true;
  const payload = {
    amount: Number(document.getElementById("expense-amount").value),
    category: document.getElementById("expense-category").value,
    payment_method: document.getElementById("expense-payment").value,
    date: document.getElementById("expense-date").value,
    note: document.getElementById("expense-note").value || null,
  };
  try {
    const created = await apiPost("/expenses", payload);
    toggleExpenseModal(false);
    showToast(created.amount);
    if (activeView === "expenses") {
      await loadExpenses();
    }
    if (activeView === "dashboard") {
      const selected = getSelectedDashboardMonth() || currentMonth();
      if (monthFromDate(created.date) === selected) {
        await loadDashboard(selected);
      }
    }
    event.target.reset();
  } catch (error) {
    if (error instanceof ApiError && error.body?.details) {
      showExpenseFieldErrors(error.body.details);
    } else {
      document.getElementById("expense-form-error").textContent =
        "Could not save expense. Please try again.";
    }
  } finally {
    expenseSubmitting = false;
    document.getElementById("expense-submit").disabled = false;
  }
}

function populateSelects() {
  const categorySelects = [
    document.getElementById("expense-category"),
    document.getElementById("filter-category"),
  ];
  categorySelects.forEach((select) => {
    select.innerHTML =
      `<option value="">All Categories</option>` +
      CATEGORIES.map((value) => `<option value="${value}">${value}</option>`).join("");
  });
  document.getElementById("expense-category").innerHTML = CATEGORIES.map(
    (value) => `<option value="${value}">${value}</option>`
  ).join("");

  const paymentSelects = [
    document.getElementById("expense-payment"),
    document.getElementById("filter-payment"),
  ];
  paymentSelects.forEach((select) => {
    select.innerHTML =
      `<option value="">All Payment Methods</option>` +
      PAYMENT_METHODS.map((value) => `<option value="${value}">${value}</option>`).join("");
  });
  document.getElementById("expense-payment").innerHTML = PAYMENT_METHODS.map(
    (value) => `<option value="${value}">${value}</option>`
  ).join("");
}

function bindGlobalActions() {
  document.querySelectorAll("[data-open-expense-modal]").forEach((button) => {
    button.addEventListener("click", () => toggleExpenseModal(true));
  });
  document.getElementById("expense-modal-close").addEventListener("click", () => {
    toggleExpenseModal(false);
  });
  document.getElementById("expense-form").addEventListener("submit", submitExpense);
  document.getElementById("toast-close").addEventListener("click", () => {
    document.getElementById("success-toast").classList.add("hidden");
  });
}

function initApp() {
  populateSelects();
  bindGlobalActions();
  initNavigation();

  const month = currentMonth();
  initDashboard(month, (nextMonth) => {
    window.location.hash = "dashboard";
    loadDashboard(nextMonth);
  });
  initExpenses();
  const analyticsEnd = month;
  const analyticsStart = shiftMonth(month, -5);
  initAnalytics(analyticsStart, analyticsEnd);

  loadDashboard(month);
}

initApp();

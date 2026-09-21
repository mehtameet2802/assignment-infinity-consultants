import { ApiError, apiPost } from "./api.js";
import {
  onUnauthorized,
  resolveAuthBootstrap,
  showAuthMisconfiguredView,
  showUnlockView,
  unlockWithKey,
  verifyStoredKey,
} from "./auth.js";
import { getAnalyticsRange, initAnalytics, loadAnalytics } from "./analytics.js";
import { destroyAllCharts } from "./charts.js";
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
import { initSecurity, loadSecurityView } from "./security.js";

let activeView = "dashboard";
let expenseSubmitting = false;
let appInitialized = false;

const VIEW_TO_PATH = {
  dashboard: "/",
  expenses: "/expenses",
  analytics: "/analytics",
  security: "/settings/security",
};

function pathToView(path) {
  if (path === "/expenses") return "expenses";
  if (path === "/analytics") return "analytics";
  if (path === "/settings/security") return "security";
  return "dashboard";
}

function updateAddExpenseButtons(view) {
  const headerBtn = document.getElementById("header-add-expense");
  if (headerBtn) headerBtn.classList.toggle("hidden", view !== "dashboard");
}

function clearSensitiveUi() {
  destroyAllCharts();
  document.getElementById("dashboard-recent-body").innerHTML = "";
  document.getElementById("expenses-table-body").innerHTML = "";
  document.getElementById("analytics-insights").innerHTML = "";
}

function onLock() {
  clearSensitiveUi();
  showUnlockView();
}

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
  updateAddExpenseButtons(view);
  ["dashboard", "expenses", "analytics", "security"].forEach((name) => {
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
  if (view === "security") loadSecurityView();
}

function navigateTo(view, { replace = false } = {}) {
  const path = VIEW_TO_PATH[view] || "/";
  if (window.location.pathname !== path) {
    const state = { view };
    if (replace) history.replaceState(state, "", path);
    else history.pushState(state, "", path);
  }
  setActiveView(view);
}

function initNavigation() {
  window.addEventListener("popstate", () => {
    setActiveView(pathToView(window.location.pathname));
  });
  document.querySelectorAll("[data-nav]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      navigateTo(link.getAttribute("data-nav"));
    });
  });
  setActiveView(pathToView(window.location.pathname));
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
  document.getElementById("unlock-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorEl = document.getElementById("unlock-error");
    errorEl.classList.add("hidden");
    const result = await unlockWithKey(document.getElementById("unlock-api-key").value);
    if (!result.ok) {
      errorEl.textContent = result.message;
      errorEl.classList.remove("hidden");
      return;
    }
    document.getElementById("unlock-api-key").value = "";
    if (!appInitialized) {
      startAppViews();
    } else {
      setActiveView(pathToView(window.location.pathname));
    }
  });
}

function startAppViews() {
  appInitialized = true;
  const month = currentMonth();
  initDashboard(month, (nextMonth) => {
    loadDashboard(nextMonth);
  });
  initExpenses();
  const analyticsEnd = month;
  const analyticsStart = shiftMonth(month, -5);
  initAnalytics(analyticsStart, analyticsEnd);
  initSecurity();
  initNavigation();
}

async function bootstrap() {
  populateSelects();
  bindGlobalActions();
  onUnauthorized(onLock);
  window.addEventListener("spend-tracker-lock", onLock);

  const authState = await resolveAuthBootstrap();
  if (authState.mode === "misconfigured") {
    showAuthMisconfiguredView();
    return;
  }
  if (authState.mode === "open") {
    document.getElementById("view-unlock").classList.add("hidden");
    document.getElementById("app-shell").classList.remove("hidden");
    startAppViews();
    return;
  }
  const verified = await verifyStoredKey();
  if (verified) {
    startAppViews();
  } else {
    showUnlockView();
  }
}

bootstrap();

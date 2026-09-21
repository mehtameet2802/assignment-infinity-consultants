export const CATEGORIES = [
  "Food & Dining",
  "Groceries",
  "Transport",
  "Shopping",
  "Bills & Utilities",
  "Entertainment",
  "Health",
  "Travel",
  "Education",
  "Other",
];

export const PAYMENT_METHODS = [
  "Credit Card",
  "Debit Card",
  "UPI",
  "Cash",
];

const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatCurrency(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (Number.isNaN(number)) return "—";
  return currencyFormatter.format(number);
}

export function formatPercentage(value) {
  if (value === null || value === undefined) return "—";
  const number = Number(value);
  if (Number.isNaN(number)) return "—";
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toFixed(2)}%`;
}

export function formatMonth(month) {
  const [year, monthNumber] = month.split("-").map(Number);
  const date = new Date(year, monthNumber - 1, 1);
  return date.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
}

export function formatDisplayDate(isoDate) {
  const date = new Date(`${isoDate}T00:00:00`);
  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function todayIsoDate() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function currentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function shiftMonth(month, delta) {
  const [year, monthNumber] = month.split("-").map(Number);
  const date = new Date(year, monthNumber - 1 + delta, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

export function monthFromDate(isoDate) {
  return isoDate.slice(0, 7);
}

export function formatChangeAmount(value) {
  if (value === null || value === undefined) return "—";
  const number = Number(value);
  const formatted = formatCurrency(Math.abs(number));
  if (number > 0) return `+${formatted}`;
  if (number < 0) return `-${formatted.replace("₹", "₹")}`;
  return formatCurrency(0);
}

export function formatChangeSummary(change) {
  const amountText = formatChangeAmount(change.change_amount);
  switch (change.change_type) {
    case "not_applicable":
      return { amount: "—", percent: "—" };
    case "no_change":
      return { amount: formatCurrency(0), percent: "0%" };
    case "new":
      return { amount: amountText, percent: "New" };
    case "resumed":
      return { amount: amountText, percent: "Resumed" };
    case "increase":
    case "decrease":
      return {
        amount: amountText,
        percent: formatPercentage(change.change_percentage),
      };
    default:
      return { amount: amountText, percent: "—" };
  }
}

const STORAGE_KEY = "spend_tracker_api_key";

let unlocked = false;
let unauthorizedHandler = null;

export function getApiKey() {
  return sessionStorage.getItem(STORAGE_KEY);
}

export function setApiKey(value) {
  sessionStorage.setItem(STORAGE_KEY, value);
}

export function clearApiKey() {
  sessionStorage.removeItem(STORAGE_KEY);
}

export function isUnlocked() {
  return unlocked;
}

export function onUnauthorized(handler) {
  unauthorizedHandler = handler;
}

export function notifyUnauthorized() {
  unlocked = false;
  if (unauthorizedHandler) unauthorizedHandler();
}

export function showUnlockView() {
  document.getElementById("view-unlock").classList.remove("hidden");
  document.getElementById("app-shell").classList.add("hidden");
}

export function showAppShell() {
  document.getElementById("view-unlock").classList.add("hidden");
  document.getElementById("app-shell").classList.remove("hidden");
}

export async function isAuthRequired() {
  const { currentMonth } = await import("./formatters.js");
  const response = await fetch(`/dashboard?month=${currentMonth()}`, {
    headers: { Accept: "application/json" },
  });
  if (response.status === 200) {
    return false;
  }
  if (response.status === 401) {
    return true;
  }
  if (response.status === 503) {
    const body = await response.json().catch(() => ({}));
    return body?.error !== "auth_not_configured";
  }
  return true;
}

export async function verifyStoredKey() {
  const apiKey = getApiKey();
  if (!apiKey) {
    showUnlockView();
    return false;
  }
  const { apiGet } = await import("./api.js");
  try {
    await apiGet("/auth/verify");
    unlocked = true;
    showAppShell();
    return true;
  } catch {
    clearApiKey();
    unlocked = false;
    showUnlockView();
    return false;
  }
}

export async function unlockWithKey(apiKey) {
  const trimmed = apiKey.trim();
  if (!trimmed) {
    return { ok: false, message: "API key is required." };
  }
  setApiKey(trimmed);
  const { apiGet } = await import("./api.js");
  try {
    await apiGet("/auth/verify");
    unlocked = true;
    showAppShell();
    return { ok: true };
  } catch (error) {
    clearApiKey();
    unlocked = false;
    const message =
      error?.body?.error === "unauthorized"
        ? "Invalid API key. Try again."
        : "Could not verify API key.";
    return { ok: false, message };
  }
}

export function lockSession() {
  clearApiKey();
  unlocked = false;
  showUnlockView();
}

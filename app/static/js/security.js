import { apiGet, apiPost } from "./api.js";
import { formatDisplayDate } from "./formatters.js";

let rotating = false;

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "—";
}

export async function loadSecurityView({ preserveRotationResult = false } = {}) {
  if (!preserveRotationResult) {
    hideRotationResult();
  }
  try {
    const data = await apiGet("/auth/api-key");
    setText("security-key-prefix", data.prefix);
    setText("security-created-at", formatDisplayDate(data.created_at.slice(0, 10)));
    setText(
      "security-last-used",
      data.last_used_at ? formatDisplayDate(data.last_used_at.slice(0, 10)) : "Never"
    );
    document.getElementById("security-error").classList.add("hidden");
  } catch {
    document.getElementById("security-error").textContent =
      "Could not load API key metadata.";
    document.getElementById("security-error").classList.remove("hidden");
  }
}

function hideRotationResult() {
  document.getElementById("rotation-result-panel").classList.add("hidden");
  document.getElementById("rotation-new-key").textContent = "";
}

export function initSecurity() {
  document.getElementById("security-rotate-start").addEventListener("click", () => {
    document.getElementById("security-rotate-form").classList.remove("hidden");
    document.getElementById("security-admin-password").value = "";
    hideRotationResult();
  });

  document.getElementById("security-rotate-cancel").addEventListener("click", () => {
    document.getElementById("security-rotate-form").classList.add("hidden");
    document.getElementById("security-admin-password").value = "";
  });

  document.getElementById("security-rotate-submit").addEventListener("click", async () => {
    if (rotating) return;
    rotating = true;
    document.getElementById("security-rotate-error").classList.add("hidden");
    const password = document.getElementById("security-admin-password").value;
    try {
      const result = await apiPost("/auth/api-key/rotate", { password });
      const { setApiKey } = await import("./auth.js");
      setApiKey(result.api_key);
      document.getElementById("security-admin-password").value = "";
      document.getElementById("security-rotate-form").classList.add("hidden");
      document.getElementById("rotation-new-key").textContent = result.api_key;
      document.getElementById("rotation-result-panel").classList.remove("hidden");
      await loadSecurityView({ preserveRotationResult: true });
    } catch (error) {
      const message =
        error?.body?.error === "invalid_admin_password"
          ? "Administrator password is incorrect."
          : "Rotation failed. Your current key is unchanged.";
      document.getElementById("security-rotate-error").textContent = message;
      document.getElementById("security-rotate-error").classList.remove("hidden");
    } finally {
      rotating = false;
    }
  });

  document.getElementById("security-copy-key").addEventListener("click", async () => {
    const value = document.getElementById("rotation-new-key").textContent;
    if (value) await navigator.clipboard.writeText(value);
  });

  document.getElementById("security-lock").addEventListener("click", async () => {
    const { lockSession } = await import("./auth.js");
    lockSession();
    window.dispatchEvent(new Event("spend-tracker-lock"));
  });
}

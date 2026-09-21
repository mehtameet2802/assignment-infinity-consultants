import { clearApiKey, getApiKey, notifyUnauthorized } from "./auth.js";

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.error || "Request failed");
    this.status = status;
    this.body = body;
  }

  fieldMessages() {
    if (!this.body?.details) return [];
    return this.body.details;
  }
}

async function parseJson(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function buildHeaders(extra = {}) {
  const headers = { Accept: "application/json", ...extra };
  const apiKey = getApiKey();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
}

async function handleResponse(response) {
  const body = await parseJson(response);
  if (response.status === 401 && body?.error === "unauthorized") {
    clearApiKey();
    notifyUnauthorized();
  }
  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body;
}

export async function apiGet(path) {
  const response = await fetch(path, { headers: buildHeaders() });
  return handleResponse(response);
}

export async function apiPost(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: buildHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

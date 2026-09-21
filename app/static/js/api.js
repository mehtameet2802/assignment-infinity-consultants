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

export async function apiGet(path) {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
  });
  const body = await parseJson(response);
  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body;
}

export async function apiPost(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  const body = await parseJson(response);
  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body;
}

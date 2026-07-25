/**
 * Minimal fetch wrapper for the Anime Generator backend.
 *
 * Every function takes an explicit baseUrl rather than a hardcoded
 * origin, since the person running this UI may point it at localhost,
 * a Docker container, or a deployed API.
 */

const REQUEST_TIMEOUT_MS = 30_000;

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.name = "ApiError";
    this.status = status; // 0 = network/unreachable, not an HTTP status
    this.code = code;
  }
}

function stripTrailingSlash(url) {
  return url.trim().replace(/\/+$/, "");
}

async function request(baseUrl, path, init) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const url = `${stripTrailingSlash(baseUrl)}${path}`;

  let response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...init,
    });
  } catch (cause) {
    const isAbort = cause instanceof DOMException && cause.name === "AbortError";
    throw new ApiError(
      0,
      isAbort ? "Timeout" : "NetworkError",
      isAbort
        ? "The request timed out. The server may be busy — try again."
        : `Could not reach ${baseUrl}. Check the address and that the server is running.`
    );
  } finally {
    clearTimeout(timer);
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      body?.error ?? "UnknownError",
      body?.detail ?? `Request failed with status ${response.status}.`
    );
  }

  return body;
}

export const api = {
  health: (baseUrl) => request(baseUrl, "/health", { method: "GET" }),

  generate: (baseUrl, seed) =>
    request(baseUrl, "/generate", {
      method: "POST",
      body: JSON.stringify(seed === undefined || seed === null ? {} : { seed }),
    }),

  /** Resolves a backend-relative path (e.g. "/generated/abc.png") to an absolute URL. */
  resolveImageUrl: (baseUrl, relativePath) => `${stripTrailingSlash(baseUrl)}${relativePath}`,
};

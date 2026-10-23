// Central helper for building backend URLs.
//
// The app talks to the API on its own origin by default ("/api/..."):
//   - in development Vite forwards "/api" to Flask (see vite.config.js)
//   - in production the API is served from the same host as the built app
// so no hard-coded hostnames are needed anywhere in the codebase.
//
// A different origin can still be used by setting VITE_API_BASE_URL, e.g.
// VITE_API_BASE_URL=https://api.focusflow.app/api

const DEFAULT_API_BASE_URL = "/api";

/**
 * Normalise the configured API base URL.
 * Falls back to the same-origin "/api" path when nothing is configured.
 */
export function resolveApiBaseUrl(env = {}) {
  const configured = String(env?.VITE_API_BASE_URL ?? "").trim();
  if (!configured) return DEFAULT_API_BASE_URL;
  const trimmed = configured.replace(/\/+$/, "");
  return trimmed || DEFAULT_API_BASE_URL;
}

export const API_BASE_URL = resolveApiBaseUrl(
  (typeof import.meta !== "undefined" && import.meta.env) || {},
);

/**
 * Build a full API URL for a path such as "/tasks" or "/tasks/12/toggle".
 */
export function apiUrl(path = "", baseUrl = API_BASE_URL) {
  const suffix = String(path ?? "").trim();
  if (!suffix) return baseUrl;
  const normalized = suffix.startsWith("/") ? suffix : `/${suffix}`;
  return `${baseUrl}${normalized}`;
}



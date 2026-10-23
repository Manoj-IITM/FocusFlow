// Shared helpers for the authentication/session state kept in localStorage.
//
// FocusFlow supports two kinds of sessions:
//
//   1. Authenticated sessions - the backend returned an access token which is
//      sent as a "Bearer" token on every API request. The token is the single
//      source of truth for the user identity on the server.
//   2. Offline demo sessions - the backend could not be reached (or the user
//      chose to try the app without a server). The user profile is stored
//      locally *without* a token and the session is flagged as a demo session
//      so the router does not redirect the user back to the login page.
//
// Both session kinds are allowed to browse the dashboard; only authenticated
// sessions can talk to the API.

export const USER_STORAGE_KEY = "focusflow_user";
export const TOKEN_STORAGE_KEY = "focusflow_access_token";
export const OFFLINE_STORAGE_KEY = "focusflow_offline_demo";

export const OFFLINE_DEMO_FLAG = "1";

function getStore() {
  try {
    if (typeof localStorage === "undefined" || localStorage === null) return null;
    return localStorage;
  } catch {
    // Accessing localStorage can throw in hardened/private browsing modes.
    return null;
  }
}

function removeItem(store, key) {
  try {
    store.removeItem(key);
  } catch {
    /* ignore storage failures */
  }
}

function setItem(store, key, value) {
  try {
    store.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

/**
 * Read the stored user profile. Returns null when nothing valid is stored.
 */
export function readStoredUser() {
  const store = getStore();
  if (!store) return null;
  try {
    const raw = store.getItem(USER_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    return parsed;
  } catch {
    // A corrupted value should never break the app - treat it as "no session".
    return null;
  }
}

/**
 * Read the stored user profile, falling back to a demo profile when missing.
 */
export function readStoredUserOr(fallback) {
  return readStoredUser() || fallback;
}

/**
 * Read the access token, or null when the session is an offline demo.
 */
export function readAccessToken() {
  const store = getStore();
  if (!store) return null;
  try {
    const token = store.getItem(TOKEN_STORAGE_KEY);
    if (!token) return null;
    const trimmed = token.trim();
    return trimmed ? trimmed : null;
  } catch {
    return null;
  }
}

/**
 * True when the stored session is an offline demo session.
 */
export function isOfflineDemoSession() {
  const store = getStore();
  if (!store) return false;
  try {
    return store.getItem(OFFLINE_STORAGE_KEY) === OFFLINE_DEMO_FLAG;
  } catch {
    return false;
  }
}

/**
 * Build the Authorization header for an outgoing request.
 *
 * The header is captured eagerly (while the token is still in storage) so it
 * can be used for requests that must be sent *before* the session is cleared
 * - for example the logout call, which revokes the token on the server.
 *
 * @returns {object|null} the header object, or null for offline demo sessions
 */
export function buildAuthHeaders() {
  const token = readAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : null;
}

/**
 * Describe the current session.
 *
 * @returns {{user: object|null, token: string|null, offline: boolean, authenticated: boolean}}
 */
export function getSession() {
  const user = readStoredUser();
  const token = readAccessToken();
  const offline = !token && Boolean(user) && isOfflineDemoSession();
  return {
    user,
    token,
    offline,
    authenticated: Boolean(user) && (Boolean(token) || offline),
  };
}

/**
 * True when the user may browse protected routes (token or offline demo).
 */
export function isAuthenticated() {
  return getSession().authenticated;
}

/**
 * Start an authenticated session backed by a real access token.
 */
export function startAuthenticatedSession(user) {
  const store = getStore();
  if (!store || !user) return null;
  const token = user.access_token || null;
  setItem(store, USER_STORAGE_KEY, JSON.stringify(user));
  if (token) {
    setItem(store, TOKEN_STORAGE_KEY, token);
    removeItem(store, OFFLINE_STORAGE_KEY);
  }
  return getSession();
}

/**
 * Start an offline demo session: a local profile without any access token.
 */
export function startOfflineDemoSession(user) {
  const store = getStore();
  if (!store || !user) return null;
  const { access_token: _ignored, ...profile } = user || {};
  setItem(store, USER_STORAGE_KEY, JSON.stringify(profile));
  removeItem(store, TOKEN_STORAGE_KEY);
  setItem(store, OFFLINE_STORAGE_KEY, OFFLINE_DEMO_FLAG);
  return getSession();
}

/**
 * Remove every trace of the current session.
 */
export function clearSession() {
  const store = getStore();
  if (!store) return;
  removeItem(store, USER_STORAGE_KEY);
  removeItem(store, TOKEN_STORAGE_KEY);
  removeItem(store, OFFLINE_STORAGE_KEY);
}

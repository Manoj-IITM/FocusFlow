import { beforeEach, describe, expect, it } from "vitest";
import {
  OFFLINE_DEMO_FLAG,
  OFFLINE_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
  USER_STORAGE_KEY,
  clearSession,
  buildAuthHeaders,
  getSession,
  isAuthenticated,
  isOfflineDemoSession,
  readAccessToken,
  readStoredUser,
  readStoredUserOr,
  startAuthenticatedSession,
  startOfflineDemoSession,
} from "./session.js";

beforeEach(() => {
  localStorage.clear();
});

describe("readStoredUser", () => {
  it("returns null when nothing is stored", () => {
    expect(readStoredUser()).toBeNull();
  });

  it("returns the parsed user profile", () => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ id: 7, username: "alex" }));
    expect(readStoredUser()).toEqual({ id: 7, username: "alex" });
  });

  it("returns null for corrupted JSON instead of throwing", () => {
    localStorage.setItem(USER_STORAGE_KEY, "{not-json");
    expect(readStoredUser()).toBeNull();
  });

  it("returns null when the stored value is not an object", () => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify("alex"));
    expect(readStoredUser()).toBeNull();
  });
});

describe("readStoredUserOr", () => {
  it("falls back to the provided default", () => {
    expect(readStoredUserOr({ id: 1, username: "Alex" })).toEqual({ id: 1, username: "Alex" });
  });

  it("prefers the stored profile over the fallback", () => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ id: 9, username: "Sam" }));
    expect(readStoredUserOr({ id: 1, username: "Alex" })).toEqual({ id: 9, username: "Sam" });
  });
});

describe("readAccessToken", () => {
  it("returns null when no token is stored", () => {
    expect(readAccessToken()).toBeNull();
  });

  it("returns the trimmed token", () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "  abc123  ");
    expect(readAccessToken()).toBe("abc123");
  });

  it("returns null for a blank token", () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "   ");
    expect(readAccessToken()).toBeNull();
  });
});
describe("startAuthenticatedSession", () => {
  it("stores the profile and the access token", () => {
    const session = startAuthenticatedSession({ id: 3, username: "alex", access_token: "tok" });

    expect(session.token).toBe("tok");
    expect(session.authenticated).toBe(true);
    expect(session.offline).toBe(false);
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBe("tok");
    expect(JSON.parse(localStorage.getItem(USER_STORAGE_KEY))).toEqual({
      id: 3,
      username: "alex",
      access_token: "tok",
    });
  });

  it("clears a previous offline demo flag", () => {
    localStorage.setItem(OFFLINE_STORAGE_KEY, OFFLINE_DEMO_FLAG);
    startAuthenticatedSession({ id: 3, username: "alex", access_token: "tok" });

    expect(localStorage.getItem(OFFLINE_STORAGE_KEY)).toBeNull();
    expect(isOfflineDemoSession()).toBe(false);
  });
});

describe("startOfflineDemoSession", () => {
  it("stores a profile without an access token", () => {
    const session = startOfflineDemoSession({ id: 1, username: "Alex" });

    expect(session.user).toEqual({ id: 1, username: "Alex" });
    expect(session.token).toBeNull();
    expect(session.offline).toBe(true);
    expect(session.authenticated).toBe(true);
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(localStorage.getItem(OFFLINE_STORAGE_KEY)).toBe(OFFLINE_DEMO_FLAG);
  });

  it("never persists an access token, even if one is supplied", () => {
    startOfflineDemoSession({ id: 1, username: "Alex", access_token: "tok" });

    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(JSON.parse(localStorage.getItem(USER_STORAGE_KEY)).access_token).toBeUndefined();
  });

  it("removes a stale token from a previous session", () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "old-token");
    startOfflineDemoSession({ id: 1, username: "Alex" });

    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });
});

describe("buildAuthHeaders", () => {
  it("returns null when no token is stored", () => {
    expect(buildAuthHeaders()).toBeNull();
  });

  it("returns null for an offline demo session", () => {
    startOfflineDemoSession({ id: 1, username: "Alex" });

    expect(buildAuthHeaders()).toBeNull();
  });

  it("builds a Bearer header from the stored token", () => {
    localStorage.setItem(TOKEN_STORAGE_KEY, "tok");

    expect(buildAuthHeaders()).toEqual({ Authorization: "Bearer tok" });
  });

  it("still returns the token after the session is cleared (eager capture)", () => {
    // The logout flow captures the header before clearing the session so the
    // server can revoke the token.
    localStorage.setItem(TOKEN_STORAGE_KEY, "tok");
    const headers = buildAuthHeaders();
    clearSession();

    expect(headers).toEqual({ Authorization: "Bearer tok" });
    expect(buildAuthHeaders()).toBeNull();
  });
});

describe("getSession", () => {
  it("reports no session when localStorage is empty", () => {
    expect(getSession()).toEqual({
      user: null,
      token: null,
      offline: false,
      authenticated: false,
    });
  });

  it("treats a stored profile without a token or offline flag as signed out", () => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ id: 1, username: "Alex" }));

    const session = getSession();
    expect(session.authenticated).toBe(false);
    expect(session.offline).toBe(false);
    expect(isAuthenticated()).toBe(false);
  });

  it("treats a token-backed profile as authenticated", () => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ id: 1, username: "Alex" }));
    localStorage.setItem(TOKEN_STORAGE_KEY, "tok");

    const session = getSession();
    expect(session.authenticated).toBe(true);
    expect(session.offline).toBe(false);
    expect(isAuthenticated()).toBe(true);
  });

  it("treats an offline demo profile as authenticated but not token-backed", () => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ id: 1, username: "Alex" }));
    localStorage.setItem(OFFLINE_STORAGE_KEY, OFFLINE_DEMO_FLAG);

    const session = getSession();
    expect(session.authenticated).toBe(true);
    expect(session.offline).toBe(true);
    expect(session.token).toBeNull();
    expect(isAuthenticated()).toBe(true);
  });

  it("prefers the token when both a token and the offline flag exist", () => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ id: 1, username: "Alex" }));
    localStorage.setItem(TOKEN_STORAGE_KEY, "tok");
    localStorage.setItem(OFFLINE_STORAGE_KEY, OFFLINE_DEMO_FLAG);

    const session = getSession();
    expect(session.token).toBe("tok");
    expect(session.offline).toBe(false);
    expect(session.authenticated).toBe(true);
  });
});

describe("clearSession", () => {
  it("removes the profile, the token and the offline flag", () => {
    startAuthenticatedSession({ id: 1, username: "Alex", access_token: "tok" });
    clearSession();

    expect(localStorage.getItem(USER_STORAGE_KEY)).toBeNull();
    expect(localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(localStorage.getItem(OFFLINE_STORAGE_KEY)).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });

  it("also clears an offline demo session", () => {
    startOfflineDemoSession({ id: 1, username: "Alex" });
    clearSession();

    expect(localStorage.getItem(OFFLINE_STORAGE_KEY)).toBeNull();
    expect(isAuthenticated()).toBe(false);
  });
});



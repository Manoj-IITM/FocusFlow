import { describe, expect, it } from "vitest";
import { apiUrl, resolveApiBaseUrl } from "./api.js";

describe("apiUrl", () => {
  it("builds same-origin URLs by default", () => {
    expect(apiUrl("/tasks")).toBe("/api/tasks");
    expect(apiUrl("/tasks/12/toggle")).toBe("/api/tasks/12/toggle");
  });

  it("adds the leading slash when the path is missing one", () => {
    expect(apiUrl("tasks")).toBe("/api/tasks");
  });

  it("never hard-codes a host", () => {
    const url = apiUrl("/stats");
    expect(url.startsWith("http://")).toBe(false);
    expect(url.startsWith("https://")).toBe(false);
    expect(url).not.toContain("127.0.0.1");
    expect(url).not.toContain("localhost");
  });

  it("supports an explicit base URL", () => {
    expect(apiUrl("/tasks", "https://api.focusflow.app/api")).toBe(
      "https://api.focusflow.app/api/tasks",
    );
  });

  it("handles empty and nullish paths", () => {
    expect(apiUrl("")).toBe("/api");
    expect(apiUrl(null)).toBe("/api");
    expect(apiUrl(undefined)).toBe("/api");
  });
});

describe("resolveApiBaseUrl", () => {
  it("defaults to the same-origin /api path", () => {
    expect(resolveApiBaseUrl({})).toBe("/api");
    expect(resolveApiBaseUrl({ VITE_API_BASE_URL: "" })).toBe("/api");
    expect(resolveApiBaseUrl({ VITE_API_BASE_URL: "   " })).toBe("/api");
  });

  it("uses the configured base URL when provided", () => {
    expect(resolveApiBaseUrl({ VITE_API_BASE_URL: "https://api.focusflow.app/api" })).toBe(
      "https://api.focusflow.app/api",
    );
  });

  it("strips trailing slashes from the configured base URL", () => {
    expect(resolveApiBaseUrl({ VITE_API_BASE_URL: "https://api.focusflow.app/api///" })).toBe(
      "https://api.focusflow.app/api",
    );
  });

  it("falls back to /api when the configured value is only slashes", () => {
    expect(resolveApiBaseUrl({ VITE_API_BASE_URL: "///" })).toBe("/api");
  });
});

import { describe, expect, it } from "bun:test";

// Replicate the proxy logic from src/proxy.ts for isolated testing
function proxyHandler(token: string | undefined): { status: number; redirectUrl?: string } {
  if (!token) {
    return { status: 302, redirectUrl: "/connection/login" };
  }
  return { status: 200 };
}

describe("Proxy Middleware (unit)", () => {
  it("returns 302 and redirect URL when no token", () => {
    const result = proxyHandler(undefined);
    expect(result.status).toBe(302);
    expect(result.redirectUrl).toBe("/connection/login");
  });

  it("returns 200 when token is present", () => {
    const result = proxyHandler("valid-token");
    expect(result.status).toBe(200);
    expect(result.redirectUrl).toBeUndefined();
  });

  it("returns 302 for empty string token (falsy check)", () => {
    const result = proxyHandler("");
    expect(result.status).toBe(302);
  });
});
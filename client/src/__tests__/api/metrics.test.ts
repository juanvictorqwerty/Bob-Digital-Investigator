import { describe, expect, it, beforeAll, afterAll } from "bun:test";
import { proxy } from "@/proxy";
import { NextRequest, NextResponse } from "next/server";

// Mock NextResponse.redirect
const originalRedirect = NextResponse.redirect;
const originalNext = NextResponse.next;

describe("Proxy Middleware", () => {
  beforeAll(() => {
    // Mock NextResponse methods
    NextResponse.redirect = ((url: URL) => ({
      status: 302,
      headers: new Headers({ Location: url.toString() }),
      url: url.toString(),
    })) as any;

    NextResponse.next = (() => ({
      status: 200,
      headers: new Headers(),
    })) as any;
  });

  afterAll(() => {
    NextResponse.redirect = originalRedirect;
    NextResponse.next = originalNext;
  });

  it("redirects to login when no token cookie is present", () => {
    // Create a request without a token
    const request = {
      cookies: {
        get: (name: string) => undefined,
      },
      url: "http://localhost:3000/some-page",
    } as unknown as NextRequest;

    const response = proxy(request);
    expect(response.status).toBe(302);
    expect(response.url).toContain("/connection/login");
  });

  it("allows request through when token cookie is present", () => {
    const request = {
      cookies: {
        get: (name: string) => ({ value: "valid-token" }),
      },
      url: "http://localhost:3000/some-page",
    } as unknown as NextRequest;

    const response = proxy(request);
    expect(response.status).toBe(200);
  });
});
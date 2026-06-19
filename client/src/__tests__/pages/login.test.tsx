import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";

// Render AuthLayout directly instead of login page to avoid Next.js router dependency
import AuthLayout from "@/components/AuthPage/AuthLayout";

describe("Login Page (via AuthLayout)", () => {
  it("renders the welcome title from AuthLayout", () => {
    render(
      <AuthLayout title="Welcome Back !" subtitle="Connect to your account">
        <div>Login form content</div>
      </AuthLayout>
    );
    expect(screen.getByText("Welcome Back !")).toBeTruthy();
    expect(screen.getByText("Connect to your account")).toBeTruthy();
  });
});
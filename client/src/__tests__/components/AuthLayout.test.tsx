import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import AuthLayout from "@/components/AuthPage/AuthLayout";

describe("AuthLayout", () => {
  it("renders title and subtitle", () => {
    render(
      <AuthLayout title="Welcome" subtitle="Sign in to your account">
        <div>Content</div>
      </AuthLayout>
    );
    expect(screen.getByText("Welcome")).toBeTruthy();
    expect(screen.getByText("Sign in to your account")).toBeTruthy();
  });

  it("renders children", () => {
    render(
      <AuthLayout title="Test" subtitle="Subtitle">
        <button>Submit</button>
      </AuthLayout>
    );
    expect(screen.getByText("Submit")).toBeTruthy();
  });

  it("renders Terms of Service and Privacy Policy links", () => {
    render(
      <AuthLayout title="Test" subtitle="Subtitle">
        <div>Content</div>
      </AuthLayout>
    );
    expect(screen.getByText("Terms of Service")).toBeTruthy();
    expect(screen.getByText("Privacy Policy")).toBeTruthy();
  });

  it("renders 'By continuing' text", () => {
    render(
      <AuthLayout title="Test" subtitle="Subtitle">
        <div>Content</div>
      </AuthLayout>
    );
    expect(screen.getByText(/By continuing/)).toBeTruthy();
  });
});
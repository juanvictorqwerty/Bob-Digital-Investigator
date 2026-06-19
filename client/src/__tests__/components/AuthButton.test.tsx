import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import AuthButton from "@/components/AuthPage/AuthButton";

describe("AuthButton", () => {
  it("renders children text", () => {
    render(<AuthButton>Sign In</AuthButton>);
    expect(screen.getByText("Sign In")).toBeTruthy();
  });

  it("shows spinner and processing text when loading", () => {
    render(<AuthButton isLoading>Sign In</AuthButton>);
    expect(screen.getByText("Processing...")).toBeTruthy();
    expect(screen.queryByText("Sign In")).toBeNull();
  });

  it("is disabled when loading", () => {
    render(<AuthButton isLoading>Sign In</AuthButton>);
    const button = screen.getByRole("button");
    expect(button.hasAttribute("disabled")).toBe(true);
  });

  it("is disabled when disabled prop is true", () => {
    render(<AuthButton disabled>Sign In</AuthButton>);
    const button = screen.getByRole("button");
    expect(button.hasAttribute("disabled")).toBe(true);
  });

  it("renders with secondary variant", () => {
    render(<AuthButton variant="secondary">Cancel</AuthButton>);
    expect(screen.getByText("Cancel")).toBeTruthy();
  });

  it("applies additional className", () => {
    render(<AuthButton className="extra-class">Click Me</AuthButton>);
    const button = screen.getByRole("button");
    expect(button.className).toContain("extra-class");
  });

  it("passes additional html button props", () => {
    render(<AuthButton data-testid="test-btn">Click</AuthButton>);
    expect(screen.getByTestId("test-btn")).toBeTruthy();
  });
});
import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import AuthInput from "@/components/AuthPage/AuthInput";

describe("AuthInput", () => {
  it("renders input element", () => {
    render(<AuthInput />);
    const input = document.querySelector("input");
    expect(input).toBeTruthy();
  });

  it("renders label when provided", () => {
    render(<AuthInput label="Email" />);
    expect(screen.getByText("Email")).toBeTruthy();
  });

  it("does not render label when not provided", () => {
    const { container } = render(<AuthInput />);
    const labels = container.querySelectorAll("label");
    expect(labels.length).toBe(0);
  });

  it("passes placeholder prop to input", () => {
    render(<AuthInput placeholder="Enter email" />);
    const input = document.querySelector("input") as HTMLInputElement;
    expect(input?.placeholder).toBe("Enter email");
  });

  it("passes type prop to input", () => {
    render(<AuthInput type="password" />);
    const input = document.querySelector("input") as HTMLInputElement;
    expect(input?.type).toBe("password");
  });

  it("applies disabled state", () => {
    render(<AuthInput disabled />);
    const input = document.querySelector("input") as HTMLInputElement;
    expect(input?.disabled).toBe(true);
  });

  it("applies custom className", () => {
    render(<AuthInput className="custom-class" />);
    const input = document.querySelector("input") as HTMLInputElement;
    expect(input?.className).toContain("custom-class");
  });
});
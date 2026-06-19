import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import SignUp from "@/app/connection/register/page";

describe("Register Page", () => {
  it("renders the welcome title", () => {
    render(<SignUp />);
    expect(screen.getByText("Welcome !")).toBeTruthy();
  });

  it("renders the subtitle", () => {
    render(<SignUp />);
    expect(screen.getByText("Create an account")).toBeTruthy();
  });

  it("renders email input", () => {
    render(<SignUp />);
    const emailInput = document.querySelector('input[type="email"]') as HTMLInputElement;
    expect(emailInput).toBeTruthy();
  });

  it("renders two password inputs", () => {
    render(<SignUp />);
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    expect(passwordInputs.length).toBe(2);
  });

  it("renders sign up button", () => {
    render(<SignUp />);
    expect(screen.getByText("Sign Up")).toBeTruthy();
  });

  it("renders login link", () => {
    render(<SignUp />);
    expect(screen.getByText("Already have an account? Login")).toBeTruthy();
  });
});
import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import AuthDivider from "@/components/AuthPage/AuthDivider";

describe("AuthDivider", () => {
  it("renders the divider with 'or' text", () => {
    render(<AuthDivider />);
    expect(screen.getByText("or")).toBeTruthy();
  });

  it("renders without crashing", () => {
    const { container } = render(<AuthDivider />);
    expect(container.querySelector("div")).toBeTruthy();
  });
});
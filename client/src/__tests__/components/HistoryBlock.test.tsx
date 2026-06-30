import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import HistoryBlock from "@/components/HistoryBlock";

describe("HistoryBlock", () => {
  it("renders the Bob AURA header", () => {
    render(<HistoryBlock />);
    expect(screen.getByText("Bob")).toBeTruthy();
    expect(screen.getByText("AURA")).toBeTruthy();
  });

  it("renders the History heading", () => {
    render(<HistoryBlock />);
    expect(screen.getByText("History")).toBeTruthy();
  });

  it("renders without crashing when no token cookie exists", () => {
    render(<HistoryBlock />);
    // Should render the header without errors
    expect(screen.getByText("History")).toBeTruthy();
  });
});

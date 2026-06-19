import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import StatCards from "@/components/resultView/statCards";

describe("StatCards", () => {
  const mockStats = {
    total_sources: 42,
    with_publish_date: 30,
    with_image_metadata: 15,
    unique_domains: 10,
    trusted_domains: 5,
  };

  it("renders all stat labels", () => {
    render(<StatCards stats={mockStats} />);
    expect(screen.getByText("Total Sources")).toBeTruthy();
    expect(screen.getByText("With Date")).toBeTruthy();
    expect(screen.getByText("With Metadata")).toBeTruthy();
    expect(screen.getByText("Unique Domains")).toBeTruthy();
    expect(screen.getByText("Trusted Sites")).toBeTruthy();
  });

  it("displays the correct stat values", () => {
    render(<StatCards stats={mockStats} />);
    expect(screen.getByText("42")).toBeTruthy();
    expect(screen.getByText("30")).toBeTruthy();
    expect(screen.getByText("15")).toBeTruthy();
    expect(screen.getByText("10")).toBeTruthy();
    expect(screen.getByText("5")).toBeTruthy();
  });

  it("renders with all zeros", () => {
    const zeroStats = {
      total_sources: 0,
      with_publish_date: 0,
      with_image_metadata: 0,
      unique_domains: 0,
      trusted_domains: 0,
    };
    render(<StatCards stats={zeroStats} />);
    const zeros = screen.getAllByText("0");
    expect(zeros.length).toBe(5);
  });
});
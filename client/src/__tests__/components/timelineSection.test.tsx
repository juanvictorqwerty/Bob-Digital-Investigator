import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import TimelineSection from "@/components/resultView/timelineSection";

describe("TimelineSection", () => {
  const mockTimeline = [
    { date: "2024-01-01", domain: "example.com", url: "https://example.com/1" },
    { date: "2024-06-15", domain: "test.org", url: "https://test.org/2" },
    { date: "2024-12-31", domain: "demo.net", url: "https://demo.net/3" },
  ];

  it("renders nothing when timeline is empty", () => {
    const { container } = render(<TimelineSection timeline={[]} />);
    expect(container.innerHTML.trim()).toBe("");
  });

  it("renders timeline header with entry count", () => {
    render(<TimelineSection timeline={mockTimeline} />);
    expect(screen.getByText("📅 Timeline")).toBeTruthy();
    expect(screen.getByText("3 entries")).toBeTruthy();
  });

  it("renders domain names for each entry", () => {
    render(<TimelineSection timeline={mockTimeline} />);
    expect(screen.getByText("example.com")).toBeTruthy();
    expect(screen.getByText("test.org")).toBeTruthy();
    expect(screen.getByText("demo.net")).toBeTruthy();
  });

  it("renders 'View source →' links for each entry", () => {
    render(<TimelineSection timeline={mockTimeline} />);
    const links = screen.getAllByText("View source →");
    expect(links.length).toBe(3);
  });

  it("formats dates correctly", () => {
    render(<TimelineSection timeline={mockTimeline} />);
    // Each timeline entry date should appear with the year
    expect(screen.getByText(/Jan 1, 2024/i)).toBeTruthy();
  });

  it("handles timeline with a single entry", () => {
    const single = [{ date: "2024-06-01", domain: "single.com", url: "https://single.com" }];
    render(<TimelineSection timeline={single} />);
    expect(screen.getByText("1 entries")).toBeTruthy();
    expect(screen.getByText("single.com")).toBeTruthy();
  });
});
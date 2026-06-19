import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import ResearchView from "@/components/resultView/ResearchView";

const fullReport = {
  summary: "This is the research summary.",
  key_findings: ["Finding one", "Finding two", "Finding three"],
  sources: [
    { title: "Source 1", url: "https://source1.com", snippet: "Snippet 1", domain: "example.com" },
    { title: "Source 2", url: "https://source2.com", snippet: "Snippet 2", domain: "test.org" },
  ],
  images: [
    { thumbnail_url: "https://img.com/1.jpg", source_url: "https://src.com/1", title: "Image 1" },
  ],
  videos: [
    {
      url: "https://video.com/1",
      thumbnail_url: "https://thumb.com/1.jpg",
      title: "Video 1",
      source: "YouTube",
      duration: "5:30",
    },
  ],
};

describe("ResearchView", () => {
  it('renders "What Actually Happened" for fake verdict', () => {
    render(<ResearchView report={fullReport} verdict="fake" />);
    expect(screen.getByText("What Actually Happened")).toBeTruthy();
  });

  it('renders "What Actually Happened" for suspicious verdict', () => {
    render(<ResearchView report={fullReport} verdict="suspicious" />);
    expect(screen.getByText("What Actually Happened")).toBeTruthy();
  });

  it('renders "Further Investigation" for unconfirmed verdict', () => {
    render(<ResearchView report={fullReport} verdict="unconfirmed" />);
    expect(screen.getByText("Further Investigation")).toBeTruthy();
  });

  it('renders "Additional Evidence" for real verdict', () => {
    render(<ResearchView report={fullReport} verdict="real" />);
    expect(screen.getByText("Additional Evidence")).toBeTruthy();
  });

  it("renders summary text", () => {
    render(<ResearchView report={fullReport} verdict="real" />);
    expect(screen.getByText("This is the research summary.")).toBeTruthy();
  });

  it("renders key findings", () => {
    render(<ResearchView report={fullReport} verdict="real" />);
    expect(screen.getByText("Finding one")).toBeTruthy();
    expect(screen.getByText("Finding two")).toBeTruthy();
    expect(screen.getByText("Finding three")).toBeTruthy();
  });

  it("renders sources", () => {
    render(<ResearchView report={fullReport} verdict="real" />);
    expect(screen.getByText("Source 1")).toBeTruthy();
    expect(screen.getByText("Source 2")).toBeTruthy();
  });

  it("renders source count", () => {
    render(<ResearchView report={fullReport} verdict="real" />);
    expect(screen.getByText("Sources (2)")).toBeTruthy();
  });

  it("renders images", () => {
    render(<ResearchView report={fullReport} verdict="real" />);
    expect(screen.getByText("Related Images (1)")).toBeTruthy();
  });

  it("renders videos", () => {
    render(<ResearchView report={fullReport} verdict="real" />);
    expect(screen.getByText("Related Videos (1)")).toBeTruthy();
  });

  it('renders "Key Findings" section header', () => {
    render(<ResearchView report={fullReport} verdict="real" />);
    expect(screen.getByText("Key Findings")).toBeTruthy();
  });

  it("renders without summary when empty", () => {
    const reportNoSummary = {
      ...fullReport,
      summary: "",
    };
    render(<ResearchView report={reportNoSummary} verdict="real" />);
    // Summary section shouldn't render, but key findings should
    expect(screen.getByText("Key Findings")).toBeTruthy();
  });

  it("renders empty state when key_findings is empty", () => {
    const reportEmptyFindings = {
      ...fullReport,
      key_findings: [],
    };
    render(<ResearchView report={reportEmptyFindings} verdict="real" />);
    expect(screen.queryByText("Key Findings")).toBeNull();
  });

  it("renders empty state when sources is empty", () => {
    const reportNoSources = {
      ...fullReport,
      sources: [],
    };
    render(<ResearchView report={reportNoSources} verdict="real" />);
    expect(screen.queryByText("Sources (0)")).toBeNull();
  });

  it("renders AI attribution footer", () => {
    render(<ResearchView report={fullReport} verdict="real" />);
    expect(screen.getByText(/Research compiled by AI/)).toBeTruthy();
  });
});
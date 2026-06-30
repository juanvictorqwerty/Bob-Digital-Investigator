import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";
import RobotResponse from "@/components/resultView/robot_response";

const baseRobot = {
  id: "123",
  verdict: "real" as const,
  confidence: 0.95,
  short_summary: "This image is authentic",
  explanation: "Verified through multiple sources",
  key_evidence: ["Evidence 1", "Evidence 2"],
  research_queries: ["query 1"],
  llm_used: true,
};

describe("RobotResponse", () => {
  it("renders nothing when robot is null", () => {
    const { container } = render(<RobotResponse robot={null} />);
    expect(container.innerHTML.trim()).toBe("");
  });

  it("renders verdict label with icon for 'real'", () => {
    render(<RobotResponse robot={baseRobot} />);
    expect(screen.getByText("Real News")).toBeTruthy();
  });

  it("renders verdict 'Fake News'", () => {
    render(<RobotResponse robot={{ ...baseRobot, verdict: "fake", confidence: 0.85 }} />);
    expect(screen.getByText("Fake News")).toBeTruthy();
  });

  it("renders verdict 'Suspicious'", () => {
    render(<RobotResponse robot={{ ...baseRobot, verdict: "suspicious", confidence: 0.6 }} />);
    expect(screen.getByText("Suspicious")).toBeTruthy();
  });

  it("renders verdict 'Unconfirmed'", () => {
    render(<RobotResponse robot={{ ...baseRobot, verdict: "unconfirmed", confidence: 0.4 }} />);
    expect(screen.getByText("Unconfirmed")).toBeTruthy();
  });

  it("renders short summary", () => {
    render(<RobotResponse robot={baseRobot} />);
    expect(screen.getByText("This image is authentic")).toBeTruthy();
  });

  it("renders explanation when short_summary is empty", () => {
    render(
      <RobotResponse
        robot={{
          ...baseRobot,
          short_summary: "",
          explanation: "Fallback explanation",
        }}
      />
    );
    expect(screen.getByText("Fallback explanation")).toBeTruthy();
  });

  it("renders key evidence items", () => {
    render(<RobotResponse robot={baseRobot} />);
    expect(screen.getByText("Evidence 1")).toBeTruthy();
    expect(screen.getByText("Evidence 2")).toBeTruthy();
  });

  it("renders 'Rules-based' badge when llm_used is false", () => {
    render(<RobotResponse robot={{ ...baseRobot, llm_used: false }} />);
    expect(screen.getByText("Rules-based")).toBeTruthy();
  });

  it("does not render 'Rules-based' badge when llm_used is true", () => {
    render(<RobotResponse robot={baseRobot} />);
    expect(screen.queryByText("Rules-based")).toBeNull();
  });

  it("renders 'View research report →' button when onViewMore is provided", () => {
    render(<RobotResponse robot={baseRobot} onViewMore={() => {}} />);
    expect(screen.getByText("View research report →")).toBeTruthy();
  });

  it("renders '← Back to results' button when showResearch is true", () => {
    render(
      <RobotResponse
        robot={baseRobot}
        showResearch={true}
        onBackToResults={() => {}}
      />
    );
    expect(screen.getByText("← Back to results")).toBeTruthy();
  });

  it("renders compact variant", () => {
    render(<RobotResponse robot={baseRobot} compact={true} />);
    expect(screen.getByText("Real News")).toBeTruthy();
    expect(screen.getByText("95% confidence")).toBeTruthy();
  });

  it("renders AI attribution footer", () => {
    render(<RobotResponse robot={baseRobot} />);
    expect(screen.getByText(/Analysis powered by AI/)).toBeTruthy();
  });
});
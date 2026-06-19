import { describe, expect, it } from "bun:test";
import { render, screen } from "@testing-library/react";

// Test LoadingScreen directly instead of full page to avoid Next.js router dependency
import LoadingScreen from "@/components/resultView/loadingScreen";

describe("ReverseSearchResult Page (via LoadingScreen)", () => {
  it("LoadingScreen renders when no results are available", () => {
    render(
      <LoadingScreen
        finished={true}
        progress="Done"
        progressStep="complete"
        sseLog={[]}
      />
    );
    expect(screen.getByText("Analysis Complete!")).toBeTruthy();
  });
});
import { describe, expect, it } from "bun:test";

// Replicate the getStage logic from loadingScreen.tsx for isolated testing
function getStage(step: string): string {
  const s = step?.toLowerCase() || "";
  if (s === "queued" || s === "queuing") return "queued";
  if (s.includes("upload")) return "uploading";
  if (s.includes("search") || s.includes("crawl") || s.includes("fetch") || s.includes("process"))
    return "processing";
  if (s.includes("analyz") || s.includes("llm") || s.includes("robot") || s.includes("ai"))
    return "analyzing";
  if (s.includes("compil") || s.includes("render") || s.includes("build") || s.includes("final"))
    return "compiling";
  if (s.includes("done") || s.includes("complete") || s.includes("finish")) return "complete";
  if (s.includes("error") || s.includes("fail")) return "error";
  if (step) return "processing";
  return "uploading";
}

describe("loadingScreen - getStage", () => {
  it('returns "uploading" for empty or undefined step', () => {
    expect(getStage("")).toBe("uploading");
    expect(getStage(undefined as any)).toBe("uploading");
  });

  it('returns "queued" for queued/queuing', () => {
    expect(getStage("queued")).toBe("queued");
    expect(getStage("Queuing")).toBe("queued");
  });

  it('returns "uploading" for step containing "upload"', () => {
    expect(getStage("uploading image")).toBe("uploading");
  });

  it('returns "processing" for search/crawl/fetch/process keywords', () => {
    expect(getStage("searching")).toBe("processing");
    expect(getStage("crawling")).toBe("processing");
    expect(getStage("fetching data")).toBe("processing");
    expect(getStage("processing")).toBe("processing");
  });

  it('returns "analyzing" for analyz/llm/robot/ai keywords', () => {
    expect(getStage("analyzing")).toBe("analyzing");
    expect(getStage("llm")).toBe("analyzing");
    expect(getStage("robot")).toBe("analyzing");
    expect(getStage("ai classification")).toBe("analyzing");
  });

  it('returns "compiling" for compil/render/build/final keywords', () => {
    expect(getStage("compiling")).toBe("compiling");
    expect(getStage("rendering")).toBe("compiling");
    expect(getStage("building")).toBe("compiling");
    expect(getStage("finalizing")).toBe("compiling");
  });

  it('returns "complete" for done/complete/finish keywords', () => {
    expect(getStage("done")).toBe("complete");
    expect(getStage("complete")).toBe("complete");
    expect(getStage("finished")).toBe("complete");
  });

  it('returns "error" for error keyword', () => {
    expect(getStage("error")).toBe("error");
    expect(getStage("error_msg")).toBe("error");
  });

  it('returns "processing" for unknown non-empty step', () => {
    expect(getStage("random step")).toBe("processing");
  });
});
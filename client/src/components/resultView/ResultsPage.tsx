"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import HistoryBlock from "@/components/HistoryBlock";
import RobotResponse from "@/components/resultView/robot_response";
import TimelineSection from "@/components/resultView/timelineSection";
import ResultCard from "@/components/resultView/resultCard";
import StatCards from "@/components/resultView/statCards";
import ImageGallery from "@/components/resultView/imageGallery";
import LoadingScreen from "@/components/resultView/loadingScreen";
import ResearchView from "@/components/resultView/ResearchView";

interface SearchResult {
  page_url: string;
  image_url: string;
  title: string;
  domain: string;
  thumbnail: string;
  publish_date: string | null;
  engine: string;
  image_metadata: any;
  extracted_text: string;
  score?: number;
  crawl_data?: any;
}

interface TimelineEntry {
  date: string;
  domain: string;
  url: string;
}

interface Statistics {
  total_sources: number;
  with_publish_date: number;
  with_image_metadata: number;
  unique_domains: number;
  trusted_domains: number;
}

interface ResearchSource {
  title: string;
  url: string;
  snippet: string;
  domain: string;
}

interface ResearchImage {
  thumbnail_url: string;
  source_url: string;
  title: string;
}

interface ResearchVideo {
  url: string;
  thumbnail_url: string;
  title: string;
  source: string;
  duration?: string;
}

interface ResearchReport {
  summary: string;
  key_findings: string[];
  sources: ResearchSource[];
  images: ResearchImage[];
  videos: ResearchVideo[];
}

interface RobotAnalysisData {
  id?: string;
  verdict: "real" | "fake" | "suspicious" | "unconfirmed";
  confidence: number;
  short_summary: string;
  explanation: string;
  key_evidence: string[];
  research_queries?: string[];
  research_report?: ResearchReport;
  llm_used: boolean;
}

interface Results {
  normalized_results: SearchResult[];
  top_candidates: SearchResult[];
  timeline: TimelineEntry[];
  statistics: Statistics;
  uploaded_image?: string;
  robot_analysis?: RobotAnalysisData;
  query?: string;
}

type ViewMode = "original" | "research-loading" | "research-results";

interface ResultsPageProps {
  results: Results;
  cachedImage?: string;
  onNewSearch: () => void;
  // Called when the user picks a history item from the sidebar
  onSelectHistoryResult?: (results: any, alias: string, imageUrl: string) => void;
  onAliasUpdate?: (id: string, newAlias: string) => void;
}

export default function ResultsPage({
  results: initialResults,
  cachedImage,
  onNewSearch,
  onSelectHistoryResult,
  onAliasUpdate,
}: ResultsPageProps) {
  const [results, setResults] = useState<Results>(initialResults);
  const [viewMode, setViewMode] = useState<ViewMode>("original");
  const [researchSseLog, setResearchSseLog] = useState<
    Array<{ event: string; data: any; timestamp: string }>
  >([]);
  const [researchProgress, setResearchProgress] = useState("");
  const [researchProgressStep, setResearchProgressStep] = useState("");

  // Sync internal state when the prop changes (e.g. user selects a different history item)
  useEffect(() => {
    setResults(initialResults);
    setViewMode("original");
    setResearchSseLog([]);
    setResearchProgress("");
    setResearchProgressStep("");
  }, [initialResults]);

  // ref for the right-hand column so we can measure its left offset for the fixed footer
  const rightColRef = useRef<HTMLDivElement>(null);

  const items: SearchResult[] = results.normalized_results ?? [];
  const stats = results.statistics ?? {
    total_sources: 0,
    with_publish_date: 0,
    with_image_metadata: 0,
    unique_domains: 0,
    trusted_domains: 0,
  };
  const timeline = results.timeline ?? [];
  const robot = results.robot_analysis ?? null;

  // Sort: dated items first (oldest → newest), then undated
  const sorted = [...items].sort((a, b) => {
    if (a.publish_date && b.publish_date)
      return (
        new Date(a.publish_date).getTime() - new Date(b.publish_date).getTime()
      );
    if (a.publish_date) return -1;
    if (b.publish_date) return 1;
    return (b.score || 0) - (a.score || 0);
  });

  const oldestDatedIndex = sorted.findIndex((r) => r.publish_date);
  const withImages = items.filter((r) => r.thumbnail);

  // ── Research SSE polling ──────────────────────────────────────────────────
  const pollResearchProgress = useCallback(
    async (taskId: string, token: string): Promise<any> => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/discover/progress/${taskId}/`,
        {
          headers: {
            Authorization: `Token ${token}`,
            Accept: "text/event-stream",
          },
        }
      );

      if (!response.ok)
        throw new Error(`SSE connection failed: ${response.status}`);

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      return new Promise((resolve, reject) => {
        const read = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, { stream: true });
              const parts = buffer.split("\n\n");
              buffer = parts.pop() ?? "";

              for (const block of parts) {
                const eventMatch = block.match(/^event: (.+)$/m);
                const dataMatch = block.match(/^data: (.+)$/m);
                if (!dataMatch) continue;

                const event = eventMatch?.[1]?.trim() ?? "message";
                const data = JSON.parse(dataMatch[1]);

                setResearchSseLog((prev) => [
                  ...prev,
                  { event, data, timestamp: new Date().toISOString() },
                ]);

                if (event === "progress") {
                  setResearchProgress(data.message);
                  setResearchProgressStep(data.step);
                } else if (event === "queued") {
                  setResearchProgress(data.message);
                  setResearchProgressStep("queued");
                } else if (event === "done") {
                  reader.cancel();
                  resolve(data);
                  return;
                } else if (event === "error") {
                  reader.cancel();
                  reject(new Error(data.error));
                  return;
                }
              }
            }
          } catch (err) {
            reject(err);
          }
        };
        read();
      });
    },
    []
  );

  // ── View-more / research trigger ─────────────────────────────────────────
  const handleViewMore = useCallback(async () => {
    if (!robot) return;

    if (robot.research_report?.summary) {
      setViewMode("research-results");
      return;
    }

    if (!robot.id) {
      console.error("No analysis_id available");
      return;
    }

    setViewMode("research-loading");
    setResearchSseLog([]);
    setResearchProgress("Starting research...");
    setResearchProgressStep("loading");

    const token = Cookies.get("token");
    if (!token) {
      setViewMode("original");
      return;
    }

    try {
      const checkResponse = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/discover/generate/`,
        {
          method: "POST",
          headers: {
            Authorization: `Token ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ analysis_id: robot.id }),
        }
      );

      if (!checkResponse.ok) {
        // Try to get the response body as text first (may be HTML or JSON)
        let responseBody = "";
        try {
          responseBody = await checkResponse.text();
        } catch {
          responseBody = "(unable to read response body)";
        }
        console.error("Discover/generate request failed:", {
          status: checkResponse.status,
          statusText: checkResponse.statusText,
          body: responseBody.substring(0, 500),
          headers: Object.fromEntries(checkResponse.headers.entries()),
        });
        throw new Error(
          `Request failed: ${checkResponse.status} - ${responseBody.substring(0, 200)}`
        );
      }

      const checkData = await checkResponse.json();

      if (checkData.status === "already_exists") {
        const updatedResults = { ...results };
        if (updatedResults.robot_analysis) {
          updatedResults.robot_analysis.research_report =
            checkData.research_report;
          updatedResults.robot_analysis.research_queries =
            checkData.research_queries;
        }
        setResults(updatedResults);
        setViewMode("research-results");
        return;
      }

      const result = await pollResearchProgress(checkData.task_id, token);

      const updatedResults = { ...results };
      if (updatedResults.robot_analysis) {
        updatedResults.robot_analysis.research_report = result.research_report;
        updatedResults.robot_analysis.research_queries = result.research_queries;
      }
      setResults(updatedResults);
      setViewMode("research-results");
    } catch (error) {
      console.error("Research generation failed:", error);
      setViewMode("original");
    }
  }, [robot, results, pollResearchProgress]);

  const handleBackToResults = useCallback(() => {
    setViewMode("original");
  }, []);

  // ── When a history item is selected from the sidebar ─────────────────────
  // Reset view so we show the new result's original data, not stale research
  const handleHistorySelect = useCallback(
    (newResults: any, alias: string, imageUrl: string) => {
      setResults(newResults);
      setViewMode("original");
      setResearchSseLog([]);
      setResearchProgress("");
      setResearchProgressStep("");
      // Bubble up to parent (page.tsx) so cachedImage etc. can also update
      onSelectHistoryResult?.(newResults, alias, imageUrl);
    },
    [onSelectHistoryResult]
  );

  // ── Layout ────────────────────────────────────────────────────────────────
  // The key insight: header and footer must live INSIDE the right column,
  // not at viewport level, so they don't bleed over the sidebar.
  return (
    <div className="h-screen bg-linear-to-br from-gray-50 to-gray-100 flex overflow-hidden">
      {/* ── Left Sidebar (full height, fixed width) ── */}
      <aside className="bg-blue-50 w-[260px] shrink-0 border-r-2 border-gray-400 flex flex-col h-full overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4">
          <HistoryBlock
            onSelectResult={handleHistorySelect}
            onAliasUpdate={onAliasUpdate}
          />
        </div>
      </aside>

      {/* ── Right Column: header + scrollable body + footer, all scoped ── */}
      <div ref={rightColRef} className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">

        {/* ── Sticky Header (scoped to right column) ── */}
        <header className="shrink-0 bg-white/95 backdrop-blur-sm border-b border-gray-200 shadow-sm z-30">
          <div className="flex items-center justify-between px-6 py-3">
            <div className="flex items-center gap-4">
              {cachedImage && (
                <div className="relative">
                  <div className="w-12 h-12 rounded-xl overflow-hidden bg-gray-100 ring-2 ring-blue-500 ring-offset-2">
                    <img
                      src={cachedImage}
                      alt="Uploaded"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-green-500 rounded-full border-2 border-white" />
                </div>
              )}
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  {viewMode === "research-results"
                    ? "Research Report"
                    : "Reverse Image Search"}
                </h1>
                <p className="text-xs text-gray-500">
                  {viewMode === "research-results"
                    ? "Additional research based on the analysis verdict"
                    : `Found ${stats.total_sources} results across Google · Sorted by relevance`}
                </p>
              </div>
            </div>
            <button
              onClick={onNewSearch}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm"
            >
              New Search
            </button>
          </div>
        </header>

        {/* ── Scrollable Main Body ── */}
        <main className="flex-1 overflow-y-auto min-h-0">
          {/* Bottom padding clears the robot footer (~220px is safe) */}
          <div className="max-w-5xl mx-auto px-6 pt-6 pb-56">

            {viewMode === "original" && (
              <>
                <StatCards stats={stats} />
                <TimelineSection timeline={timeline} />
                <ResultCard sorted={sorted} oldestDatedIndex={oldestDatedIndex} />
                <ImageGallery withImages={withImages} />
              </>
            )}

            {viewMode === "research-loading" && (
              <div className="py-12">
                <LoadingScreen
                  sseLog={researchSseLog.map((e) => ({
                    ...e,
                    timestamp: new Date(e.timestamp),
                  }))}
                  progress={researchProgress}
                  progressStep={researchProgressStep}
                  finished={false}
                />
              </div>
            )}

            {viewMode === "research-results" && robot?.research_report && (
              <ResearchView
                report={robot.research_report}
                verdict={robot.verdict}
              />
            )}
          </div>
        </main>

        {/* ── Robot Response Footer (scoped to right column) ── */}
        {/*
          Always render when robot data exists — covers both live results
          and history items that carry robot_analysis.
          Using `sticky bottom-0` keeps it at the base of the flex column
          rather than viewport-fixed, so it stays within the right panel.
        */}
        {robot ? (
          <footer className="shrink-0 bg-white/95 backdrop-blur-sm border-t-2 border-gray-200 shadow-[0_-4px_20px_rgba(0,0,0,0.08)] z-30">
            <RobotResponse
              robot={robot}
              compact={false}
              onViewMore={handleViewMore}
              onBackToResults={handleBackToResults}
              showResearch={viewMode === "research-results"}
            />
          </footer>
        ) : (
          /* Placeholder footer so layout doesn't jump when robot is absent */
          <footer className="shrink-0 h-4 bg-transparent" />
        )}
      </div>
    </div>
  );
}
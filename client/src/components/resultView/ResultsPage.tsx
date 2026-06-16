"use client";

import { useState, useCallback } from "react";
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
}

export default function ResultsPage({ results: initialResults, cachedImage, onNewSearch }: ResultsPageProps) {
  const [results, setResults] = useState<Results>(initialResults);
  const [viewMode, setViewMode] = useState<ViewMode>("original");
  const [researchSseLog, setResearchSseLog] = useState<Array<{event: string; data: any; timestamp: string}>>([]);
  const [researchProgress, setResearchProgress] = useState("");
  const [researchProgressStep, setResearchProgressStep] = useState("");

  const items: SearchResult[] = results.normalized_results ?? [];
  const stats = results.statistics ?? { total_sources: 0, with_publish_date: 0, with_image_metadata: 0, unique_domains: 0, trusted_domains: 0 };
  const timeline = results.timeline ?? [];
  const robot = results.robot_analysis ?? null;

  // Sort: dated items first (oldest → newest), then undated
  const sorted = [...items].sort((a, b) => {
    if (a.publish_date && b.publish_date)
      return new Date(a.publish_date).getTime() - new Date(b.publish_date).getTime();
    if (a.publish_date) return -1;
    if (b.publish_date) return 1;
    return (b.score || 0) - (a.score || 0);
  });

  const oldestDatedIndex = sorted.findIndex((r) => r.publish_date);
  const withImages = items.filter((r) => r.thumbnail);

  // Poll research progress via SSE
  const pollResearchProgress = useCallback(async (taskId: string, token: string): Promise<any> => {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/discover/progress/${taskId}/`,
      {
        headers: {
          "Authorization": `Token ${token}`,
          "Accept": "text/event-stream",
        },
      }
    );

    if (!response.ok) {
      throw new Error(`SSE connection failed: ${response.status}`);
    }

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

              setResearchSseLog((prev) => [...prev, { event, data, timestamp: new Date().toISOString() }]);

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
  }, []);

  // Handle "View more" click
  const handleViewMore = useCallback(async () => {
    if (!robot) return;

    // If research already exists, just show it
    if (robot.research_report && robot.research_report.summary) {
      setViewMode("research-results");
      return;
    }

    // If no analysis_id, can't trigger research
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
            "Authorization": `Token ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ analysis_id: robot.id }),
        }
      );

      if (!checkResponse.ok) {
        throw new Error(`Request failed: ${checkResponse.status}`);
      }

      const checkData = await checkResponse.json();

      if (checkData.status === "already_exists") {
        // Research already exists, update results and show
        const updatedResults = { ...results };
        if (updatedResults.robot_analysis) {
          updatedResults.robot_analysis.research_report = checkData.research_report;
          updatedResults.robot_analysis.research_queries = checkData.research_queries;
        }
        setResults(updatedResults);
        setViewMode("research-results");
        return;
      }

      // Poll for progress
      const taskId = checkData.task_id;
      const result = await pollResearchProgress(taskId, token);

      // Update results with research data
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

  // Handle "Back to results" click
  const handleBackToResults = useCallback(() => {
    setViewMode("original");
  }, []);

  return (
    <main className="h-screen bg-linear-to-br from-gray-50 to-gray-100 flex flex-col">
      {/* ── Fixed Header Bar ── */}
      <header className="sticky top-0 z-30 shrink-0 bg-white/95 backdrop-blur-sm border-b border-gray-200 shadow-sm">
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
                <div className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-green-500 rounded-full border-2 border-white"></div>
              </div>
            )}
            <div>
              <h1 className="text-xl font-bold text-gray-900 bg-linear-to-r from-gray-900 to-gray-600 bg-clip-text">
                {viewMode === "research-results" ? "Research Report" : "Reverse Image Search"}
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

      {/* ── Scrollable Content Area with Sidebar ── */}
      <div className="flex-1 flex min-h-0 overflow-hidden relative z-20">
        {/* Left Sidebar */}
        <div className="bg-blue-50 w-[260px] shrink-0 border-r-2 border-gray-400 flex flex-col h-full">
          <div className="flex-1 overflow-y-auto p-4">
            <HistoryBlock />
          </div>
        </div>

        {/* Main Results (scrolls behind footer) */}
        <div className="flex-1 overflow-y-auto pb-64 relative">
          <div className="max-w-5xl mx-auto px-6 pt-6">
            {/* ── Original View ── */}
            {viewMode === "original" && (
              <>
                <StatCards stats={stats} />
                <TimelineSection timeline={timeline} />
                <ResultCard sorted={sorted} oldestDatedIndex={oldestDatedIndex} />
                <ImageGallery withImages={withImages} />
              </>
            )}

            {/* ── Research Loading View ── */}
            {viewMode === "research-loading" && (
              <div className="py-12">
                <LoadingScreen
                  sseLog={researchSseLog.map(e => ({ ...e, timestamp: new Date(e.timestamp) }))}
                  progress={researchProgress}
                  progressStep={researchProgressStep}
                  finished={false}
                />
              </div>
            )}

            {/* ── Research Results View ── */}
            {viewMode === "research-results" && robot?.research_report && (
              <ResearchView
                report={robot.research_report}
                verdict={robot.verdict}
              />
            )}
          </div>

          {/* ── Spacer so last content clears the fixed footer ── */}
          <div className="h-8" />
        </div>
      </div>

      {/* ── Fixed AI Response Footer (overlays bottom of scrollable content) ── */}
      {robot && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-sm border-t-2 border-gray-200 shadow-[0_-4px_20px_rgba(0,0,0,0.08)]">
          <RobotResponse
            robot={robot}
            compact={false}
            onViewMore={handleViewMore}
            onBackToResults={handleBackToResults}
            showResearch={viewMode === "research-results"}
          />
        </div>
      )}
    </main>
  );
}
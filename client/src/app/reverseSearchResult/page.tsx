"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ResultsPage from "@/components/resultView/ResultsPage";
import LoadingScreen from "@/components/resultView/loadingScreen";

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

interface Results {
  normalized_results: SearchResult[];
  top_candidates: SearchResult[];
  timeline: TimelineEntry[];
  statistics: Statistics;
  uploaded_image?: string;
  robot_analysis?: RobotAnalysisData;
}

export default function ReverseSearchResult() {
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(true);
  const [cachedImage, setCachedImage] = useState<string | null>(null);
  const [sseLog, setSseLog] = useState<Array<{event: string; data: any; timestamp: string}>>([]);
  const [progress, setProgress] = useState("");
  const [progressStep, setProgressStep] = useState("");
  const router = useRouter();

  useEffect(() => {
    const storedResults = sessionStorage.getItem("searchResults");
    if (storedResults) {
      const parsedResults = JSON.parse(storedResults);
      setResults(parsedResults);
      
      if (parsedResults.uploaded_image) {
        setCachedImage(parsedResults.uploaded_image);
      }

      if (parsedResults.robot_analysis || parsedResults.timeline?.length > 0) {
        setLoading(false);
        return;
      }
    }
    
    const storedSseLog = sessionStorage.getItem("sseLog");
    if (storedSseLog) {
      try {
        const parsed = JSON.parse(storedSseLog);
        setSseLog(parsed);
        if (parsed.length > 0) {
          const last = parsed[parsed.length - 1];
          if (last.data?.message) setProgress(last.data.message);
          if (last.data?.step) setProgressStep(last.data.step);
          if (last.event === "done") {
            setLoading(false);
            return;
          }
        }
      } catch (e) {
        // ignore
      }
    }
    
    setTimeout(() => {
      setLoading(false);
    }, 2000);
  }, []);

  if (loading) {
    return (
      <LoadingScreen
        sseLog={sseLog.map(e => ({ ...e, timestamp: new Date(e.timestamp) }))}
        progress={progress}
        progressStep={progressStep}
        finished={!!(results?.robot_analysis || results?.timeline?.length)}
      />
    );
  }

  if (!results) {
    return (
      <main className="min-h-screen bg-linear-to-br from-gray-50 to-gray-100 flex flex-col items-center justify-center px-4">
        <div className="text-center">
          <div className="text-6xl mb-6">🔍</div>
          <h1 className="text-2xl font-semibold text-gray-800 mb-3">No results found</h1>
          <p className="text-gray-500 mb-8">Try uploading a different image or check back later</p>
          <button
            onClick={() => router.push("/")}
            className="rounded-xl bg-linear-to-r from-blue-600 to-blue-700 px-6 py-3 text-sm font-medium text-white hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg hover:shadow-xl"
          >
            Back to home
          </button>
        </div>
      </main>
    );
  }

  return (
    <ResultsPage
      results={results}
      cachedImage={cachedImage ?? undefined}
      onNewSearch={() => router.push("/")}
    />
  );
}
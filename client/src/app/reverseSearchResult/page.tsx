"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import HistoryBlock from "@/components/HistoryBlock";
import RobotResponse from "@/components/resultView/robot_response";
import TimelineSection from "@/components/resultView/timelineSection";
import ResultCard from "@/components/resultView/resultCard";
import StatCards from "@/components/resultView/statCards";
import ImageGallery from "@/components/resultView/imageGallery";
import LoadingScreen from "@/components/resultView/loadingScreen";

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

interface RobotAnalysisData {
  verdict: "real" | "fake" | "suspicious" | "unconfirmed";
  confidence: number;
  short_summary: string;
  explanation: string;
  key_evidence: string[];
  llm_used: boolean;
}

interface Results {
  normalized_results: SearchResult[];
  top_candidates: SearchResult[];
  timeline: TimelineEntry[];
  statistics: Statistics;
  uploaded_image?: string; // Base64 of uploaded image
  robot_analysis?: RobotAnalysisData;
}

function domainIcon(domain: string): string {
  const d = domain.toLowerCase();
  if (d.includes("github")) return "🐙";
  if (d.includes("youtube")) return "▶️";
  if (d.includes("linkedin")) return "💼";
  if (d.includes("facebook")) return "📘";
  if (d.includes("instagram")) return "📸";
  if (d.includes("pinterest")) return "📌";
  if (d.includes("medium")) return "✍️";
  return "🌐";
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "No date";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function ReverseSearchResult() {
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(true);
  const [cachedImage, setCachedImage] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const storedResults = sessionStorage.getItem("searchResults");
    if (storedResults) {
      const parsedResults = JSON.parse(storedResults);
      setResults(parsedResults);
      
      // Load cached image if available
      if (parsedResults.uploaded_image) {
        setCachedImage(parsedResults.uploaded_image);
      }
    }
    
    // Simulate minimum loading time for better UX
    setTimeout(() => {
      setLoading(false);
    }, 1500);
  }, []);

  if (loading) {
    return <LoadingScreen />;
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
    return (b.score || 0) - (a.score || 0); // Sort by score if no dates
  });

  const oldestDatedIndex = sorted.findIndex((r) => r.publish_date);

  // Images: keep original ordering to find "oldest" by array position
  const withImages = items.filter((r) => r.thumbnail);

  // Stats from new format
  const crawledCount = items.filter((r) => r.crawl_data && r.crawl_data.crawl_status === "success").length;

  return (
    <main className="h-screen bg-linear-to-br from-gray-50 to-gray-100 grid grid-cols-4">

      <div className="bg-blue-50 col-span-1 p-4 border-r-2 border-gray-400">
                  <HistoryBlock/>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8 col-span-3 overflow-y-auto">
        
        {/* Header with uploaded image preview */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              {/* Cached Image Display */}
              {cachedImage && (
                <div className="relative">
                  <div className="w-16 h-16 rounded-xl overflow-hidden bg-gray-100 ring-2 ring-blue-500 ring-offset-2">
                    <img
                      src={cachedImage}
                      alt="Uploaded"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="absolute -top-2 -right-2 w-5 h-5 bg-green-500 rounded-full border-2 border-white"></div>
                </div>
              )}
              <div>
                <h1 className="text-2xl font-bold text-gray-900 bg-linear-to-r from-gray-900 to-gray-600 bg-clip-text">
                  Reverse Image Search
                </h1>
                <p className="text-sm text-gray-500 mt-1">
                  Found {stats.total_sources} results across Google · Sorted by relevance
                </p>
              </div>
            </div>
            <button
              onClick={() => router.push("/")}
              className="rounded-xl border border-gray-200 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm"
            >
              New Search
            </button>
          </div>
        </div>

        {/* Stats Cards - Modern Design */}
        <StatCards stats={stats} />

        {/* Timeline Section */}
        <TimelineSection timeline={timeline} />

        {/* Results list - Modern Cards */}
        <ResultCard sorted={sorted} oldestDatedIndex={oldestDatedIndex} />
        
        {/* Image Gallery Section - Modern Grid */}
        <ImageGallery withImages={withImages} />

        <RobotResponse robot={robot} />
      </div>
    </main>
  );
}
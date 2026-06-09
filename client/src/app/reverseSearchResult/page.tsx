"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import HistoryBlock from "@/components/HistoryBlock";

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
  uploaded_image?: string; // Base64 of uploaded image
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

// Beautiful Loading Screen Component
function LoadingScreen() {
  return (
    <div className="fixed inset-0 bg-linear-to-br from-gray-50 via-white to-gray-50 z-50 flex items-center justify-center">
      <div className="relative">
        {/* Animated rings */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-32 h-32 border-4 border-blue-200 rounded-full animate-ping opacity-75"></div>
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-24 h-24 border-4 border-blue-300 rounded-full animate-pulse"></div>
        </div>
        
        {/* Main spinner */}
        <div className="relative flex flex-col items-center gap-6">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          
          {/* Animated dots */}
          <div className="flex gap-2 mt-4">
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
          </div>
          
          <p className="text-gray-600 font-medium mt-4 animate-pulse">
            Analyzing image...
          </p>
          <p className="text-sm text-gray-400">
            Searching across the web for matches
          </p>
        </div>
      </div>
    </div>
  );
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
    <main className="min-h-screen bg-linear-to-br from-gray-50 to-gray-100">

      <div className="bg-blue-50 col-span-1 p-4 border-r-2 border-gray-400">
                  <HistoryBlock/>
      </div>
       

      <div className="max-w-6xl mx-auto px-4 py-8">
        
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
                  Found {stats.total_sources} results across Google & Yandex · Sorted by relevance
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
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          {[
            { label: "Total Sources", value: stats.total_sources, icon: "🔍", color: "from-blue-500 to-blue-600" },
            { label: "With Date", value: stats.with_publish_date, icon: "�", color: "from-purple-500 to-purple-600" },
            { label: "With Metadata", value: stats.with_image_metadata, icon: "�", color: "from-green-500 to-green-600" },
            { label: "Unique Domains", value: stats.unique_domains, icon: "🌐", color: "from-orange-500 to-orange-600" },
            { label: "Trusted Sites", value: stats.trusted_domains, icon: "✅", color: "from-teal-500 to-teal-600" },
          ].map((s) => (
            <div key={s.label} className="group relative overflow-hidden bg-white rounded-2xl shadow-sm hover:shadow-md transition-all duration-300">
              <div className={`absolute top-0 right-0 w-32 h-32 bg-linear-to-br ${s.color} opacity-5 rounded-full transform translate-x-16 -translate-y-16 group-hover:scale-150 transition-transform duration-500`}></div>
              <div className="relative p-5">
                <div className="text-3xl mb-2">{s.icon}</div>
                <p className="text-2xl font-bold text-gray-900">{s.value}</p>
                <p className="text-xs text-gray-500 mt-1">{s.label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Timeline Section */}
        {timeline.length > 0 && (
          <div className="mb-12">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                📅 Timeline
                <span className="text-xs font-normal text-gray-500 bg-white px-2 py-0.5 rounded-full">
                  {timeline.length} entries
                </span>
              </h2>
            </div>
            
            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-linear-to-b from-blue-500 to-purple-500"></div>
                
                <div className="space-y-4">
                  {timeline.map((entry, i) => (
                    <div key={i} className="relative flex items-start gap-4 pl-10">
                      {/* Timeline dot */}
                      <div className={`absolute left-2 w-5 h-5 rounded-full border-4 border-white ${
                        i === 0 ? 'bg-blue-500' : i === timeline.length - 1 ? 'bg-purple-500' : 'bg-gray-300'
                      }`}></div>
                      
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-800">{formatDate(entry.date)}</p>
                        <p className="text-xs text-gray-500">{entry.domain}</p>
                        <a
                          href={entry.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-700 mt-1 inline-block"
                        >
                          View source →
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Results list - Modern Cards */}
        <div className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900">Top Candidates</h2>
            <span className="text-xs text-gray-500 bg-white px-3 py-1 rounded-full shadow-sm">
              Sorted by relevance
            </span>
          </div>
          
          <div className="grid gap-3">
            {sorted.slice(0, 20).map((r, i) => (
              <div
                key={r.page_url}
                className="group bg-white rounded-xl hover:rounded-2xl border border-gray-100 hover:border-gray-200 transition-all duration-300 p-4 flex items-start gap-4 shadow-sm hover:shadow-md"
              >
                {/* Icon */}
                <div className="w-10 h-10 rounded-xl bg-linear-to-br from-gray-50 to-gray-100 border border-gray-100 flex items-center justify-center text-lg shrink-0 group-hover:scale-110 transition-transform">
                  {domainIcon(r.domain)}
                </div>

                {/* Body */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-xs text-gray-500 font-mono">{r.domain}</p>
                    {r.engine && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-500 capitalize">
                        {r.engine}
                      </span>
                    )}
                    {r.score !== undefined && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 font-medium">
                        Score: {r.score}
                      </span>
                    )}
                  </div>
                  <a
                    href={r.page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-gray-800 hover:text-blue-600 transition-colors line-clamp-2"
                  >
                    {r.title}
                  </a>

                  <div className="flex flex-wrap items-center gap-2 mt-3">
                    {/* Date badge */}
                    <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-600">
                      📅 {formatDate(r.publish_date)}
                    </span>

                    {/* Crawl status */}
                    {r.crawl_data ? (
                      r.crawl_data.crawl_status === "success" ? (
                        <span className="text-xs px-2.5 py-1 rounded-full bg-green-50 text-green-700 border border-green-100">
                          ✓ crawled
                        </span>
                      ) : (
                        <span className="text-xs px-2.5 py-1 rounded-full bg-red-50 text-red-600 border border-red-100">
                          ✗ {r.crawl_data.crawl_error ?? "failed"}
                        </span>
                      )
                    ) : (
                      <span className="text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-500">
                        ○ not crawled
                      </span>
                    )}

                    {/* Oldest badge */}
                    {i === oldestDatedIndex && (
                      <span className="text-xs px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-medium">
                        🏆 oldest dated
                      </span>
                    )}
                  </div>
                </div>
                
                {/* External link icon */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Image Gallery Section - Modern Grid */}
        {withImages.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                🖼️ Image Gallery
                <span className="text-xs font-normal text-gray-500 bg-white px-2 py-0.5 rounded-full">
                  {withImages.length} images
                </span>
              </h2>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {withImages.map((r, i) => (
                <div
                  key={r.page_url}
                  className={`group relative bg-white rounded-xl overflow-hidden border transition-all duration-300 hover:shadow-lg hover:-translate-y-1 ${
                    i === 0
                      ? "border-amber-300 ring-2 ring-amber-200"
                      : "border-gray-100 hover:border-gray-200"
                  }`}
                >
                  <div className="relative aspect-video bg-gray-100 overflow-hidden">
                    <img
                      src={r.thumbnail}
                      alt={r.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    {i === 0 && (
                      <div className="absolute top-2 left-2 bg-amber-500 text-white text-xs px-2 py-1 rounded-full font-medium shadow-lg">
                        Oldest
                      </div>
                    )}
                  </div>
                  <div className="p-3">
                    <p className="text-xs font-medium text-gray-800 line-clamp-2">{r.title}</p>
                    <p className="text-xs text-gray-400 mt-1 truncate">{r.domain}</p>
                  </div>
                  
                  {/* Hover overlay with link */}
                  <a
                    href={r.page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all duration-300 flex items-center justify-center"
                  >
                    <span className="opacity-0 group-hover:opacity-100 bg-white text-gray-800 text-xs px-2 py-1 rounded-full shadow-lg transform translate-y-2 group-hover:translate-y-0 transition-all">
                      View source →
                    </span>
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
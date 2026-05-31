"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface SearchResult {
  title: string;
  url: string;
  domain: string;
  thumbnail?: string;
  published_date: string | null;
  is_crawled: boolean;
  crawl_status?: string;
  crawl_error?: string;
  crawled_at?: string;
  raw_snippet?: string;
  file_size_bytes?: number | null;
  dimensions?: { width: number; height: number } | null;
}

interface Results {
  results: SearchResult[];
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
  const router = useRouter();

  useEffect(() => {
    const storedResults = sessionStorage.getItem("searchResults");
    if (storedResults) {
      setResults(JSON.parse(storedResults));
    }
    setLoading(false);
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-500">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Loading results…</span>
        </div>
      </main>
    );
  }

  if (!results) {
    return (
      <main className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
        <h1 className="text-xl font-medium text-gray-800 mb-4">No results found</h1>
        <button
          onClick={() => router.push("/")}
          className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          Back to home
        </button>
      </main>
    );
  }

  const items: SearchResult[] = results.results ?? [];

  // Sort: dated items first (oldest → newest), then undated
  const sorted = [...items].sort((a, b) => {
    if (a.published_date && b.published_date)
      return new Date(a.published_date).getTime() - new Date(b.published_date).getTime();
    if (a.published_date) return -1;
    if (b.published_date) return 1;
    return 0;
  });

  const oldestDatedIndex = sorted.findIndex((r) => r.published_date);

  // Images: keep original ordering to find "oldest" by array position
  const withImages = items.filter((r) => r.thumbnail);

  // Stats
  const crawledCount = items.filter((r) => r.is_crawled).length;
  const datedCount = items.filter((r) => r.published_date).length;

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-10">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-medium text-gray-900">Reverse search results</h1>
            <p className="text-sm text-gray-400 mt-1">Sorted oldest first · {items.length} results</p>
          </div>
          <button
            onClick={() => router.push("/")}
            className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            New search
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-3 mb-8">
          {[
            { label: "Total", value: items.length },
            { label: "Crawled", value: crawledCount },
            { label: "With date", value: datedCount },
            { label: "With images", value: withImages.length },
          ].map((s) => (
            <div key={s.label} className="bg-white rounded-xl border border-gray-100 p-4">
              <p className="text-xs text-gray-400 mb-1">{s.label}</p>
              <p className="text-2xl font-medium text-gray-900">{s.value}</p>
            </div>
          ))}
        </div>

        {/* Results list */}
        <div className="flex flex-col gap-2 mb-10">
          {sorted.map((r, i) => (
            <div
              key={r.url}
              className="bg-white rounded-xl border border-gray-100 hover:border-gray-200 transition-colors p-4 flex items-start gap-3"
            >
              {/* Icon */}
              <div className="w-9 h-9 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center text-base flex-shrink-0">
                {domainIcon(r.domain)}
              </div>

              {/* Body */}
              <div className="min-w-0 flex-1">
                <p className="text-xs text-gray-400 mb-0.5 truncate">{r.domain}</p>
                <a
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-gray-800 hover:text-blue-600 transition-colors block truncate"
                >
                  {r.title}
                </a>

                <div className="flex flex-wrap items-center gap-2 mt-2">
                  {/* Date badge */}
                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-500">
                    📅 {formatDate(r.published_date)}
                  </span>

                  {/* Crawl status */}
                  {r.is_crawled ? (
                    r.crawl_status === "success" ? (
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-green-50 text-green-700">
                        crawled
                      </span>
                    ) : (
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-red-50 text-red-600">
                        {r.crawl_error ?? "failed"}
                      </span>
                    )
                  ) : (
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-gray-100 text-gray-500">
                      not crawled
                    </span>
                  )}

                  {/* Oldest badge */}
                  {i === oldestDatedIndex && (
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 font-medium">
                      oldest dated
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Image section */}
        {withImages.length > 0 && (
          <>
            <hr className="border-gray-100 mb-6" />
            <h2 className="text-sm font-medium text-gray-500 mb-4 flex items-center gap-2">
              🖼️ Results with images
            </h2>
            <div className="grid grid-cols-3 gap-3">
              {withImages.map((r, i) => (
                <div
                  key={r.url}
                  className={`bg-white rounded-xl overflow-hidden border transition-colors ${
                    i === 0
                      ? "border-amber-300 ring-1 ring-amber-200"
                      : "border-gray-100 hover:border-gray-200"
                  }`}
                >
                  <img
                    src={r.thumbnail}
                    alt={r.title}
                    className="w-full h-24 object-cover bg-gray-100"
                  />
                  <div className="p-2.5">
                    <p className="text-xs font-medium text-gray-800 truncate">{r.title}</p>
                    <p className="text-xs text-gray-400 mt-0.5 truncate">
                      {r.domain}
                      {i === 0 && (
                        <span className="ml-1 text-amber-600 font-medium">· oldest image</span>
                      )}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
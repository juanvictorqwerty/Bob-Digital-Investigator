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

export default function ResultCard({ sorted, oldestDatedIndex }: { sorted: SearchResult[], oldestDatedIndex: number }) {
  return (
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
        );
    }
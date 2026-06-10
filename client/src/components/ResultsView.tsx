"use client";

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

interface ResultsData {
  normalized_results?: SearchResult[];
  top_candidates?: SearchResult[];
  timeline?: TimelineEntry[];
  statistics?: Statistics;
  uploaded_image?: string;
  query?: string;
  robot_analysis?: RobotAnalysisData;
}

interface ResultsViewProps {
  results: ResultsData;
  alias: string;
  imageUrl: string;
  onBack: () => void;
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

const VERDICT_CONFIG: Record<string, { icon: string; label: string; bg: string; border: string; text: string }> = {
  real:        { icon: "🛡️", label: "Real News",     bg: "bg-green-50",   border: "border-green-300",  text: "text-green-800" },
  fake:        { icon: "🚨", label: "Fake News",     bg: "bg-red-50",     border: "border-red-300",    text: "text-red-800" },
  suspicious:  { icon: "⚠️", label: "Suspicious",    bg: "bg-amber-50",   border: "border-amber-300",  text: "text-amber-800" },
  unconfirmed: { icon: "❓", label: "Unconfirmed",   bg: "bg-gray-50",    border: "border-gray-300",   text: "text-gray-700" },
};

export default function ResultsView({ results, alias, imageUrl, onBack }: ResultsViewProps) {
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
  const userClaim = results.query ?? "";

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

  // Confidence color
  function confidenceColor(score: number): string {
    if (score >= 0.8) return "bg-green-500";
    if (score >= 0.6) return "bg-emerald-500";
    if (score >= 0.4) return "bg-amber-500";
    return "bg-red-500";
  }

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-8">
      {/* Input Evidence Cards */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        {/* Uploaded Image */}
        {imageUrl && (
          <div className="flex-1 rounded-xl border border-purple-200 bg-purple-50 p-4 shadow-sm">
            <div className="flex items-start gap-3">
              <span className="text-xl shrink-0 mt-0.5">🖼️</span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-purple-700 uppercase tracking-wider mb-2">Input Image</p>
                <img
                  src={imageUrl}
                  alt="Uploaded search image"
                  className="w-full max-h-40 object-contain rounded-lg border border-purple-200 bg-white"
                />
              </div>
            </div>
          </div>
        )}

        {/* User's Claim / Query Text */}
        {userClaim && (
          <div className="flex-1 rounded-xl border border-blue-200 bg-blue-50 p-4 shadow-sm">
            <div className="flex items-start gap-3">
              <span className="text-xl shrink-0 mt-0.5">📝</span>
              <div>
                <p className="text-xs font-semibold text-blue-700 uppercase tracking-wider mb-1">Claim being investigated</p>
                <p className="text-sm text-blue-900 italic leading-relaxed">"{userClaim}"</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Robot Verdict Banner */}
      {robot && (() => {
        const cfg = VERDICT_CONFIG[robot.verdict] ?? VERDICT_CONFIG.unconfirmed;
        return (
          <div className={`mb-8 rounded-2xl border-2 ${cfg.border} ${cfg.bg} p-6 shadow-sm transition-all hover:shadow-md`}>
            <div className="flex items-start gap-4">
              <div className="text-4xl shrink-0">{cfg.icon}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 flex-wrap mb-2">
                  <span className={`text-lg font-bold ${cfg.text}`}>{cfg.label}</span>
                  <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${cfg.bg} ${cfg.text} border ${cfg.border}`}>
                    <span className={`w-2 h-2 rounded-full ${confidenceColor(robot.confidence)}`}></span>
                    {Math.round(robot.confidence * 100)}% confidence
                  </span>
                  {!robot.llm_used && (
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-200 text-gray-600 font-medium">
                      Rules-based
                    </span>
                  )}
                </div>
                {robot.short_summary && (
                  <p className={`text-sm font-medium ${cfg.text} mb-2`}>{robot.short_summary}</p>
                )}
                <p className="text-sm text-gray-600 leading-relaxed">{robot.explanation}</p>
                {robot.key_evidence && robot.key_evidence.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Key Evidence</p>
                    <ul className="space-y-1">
                      {robot.key_evidence.map((ev, i) => (
                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                          <span className="text-gray-400 mt-0.5 shrink-0">•</span>
                          <span>{ev}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })()}

      {/* Stats summary line */}
      <p className="text-sm text-gray-500 mb-6">
        Found {stats.total_sources} results across Google & Yandex · Sorted by relevance
      </p>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        {[
          { label: "Total Sources", value: stats.total_sources, icon: "🔍", color: "from-blue-500 to-blue-600" },
          { label: "With Date", value: stats.with_publish_date, icon: "📅", color: "from-purple-500 to-purple-600" },
          { label: "With Metadata", value: stats.with_image_metadata, icon: "📋", color: "from-green-500 to-green-600" },
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
              <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-linear-to-b from-blue-500 to-purple-500"></div>
              <div className="space-y-4">
                {timeline.map((entry, i) => (
                  <div key={i} className="relative flex items-start gap-4 pl-10">
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

      {/* Results list */}
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
              <div className="w-10 h-10 rounded-xl bg-linear-to-br from-gray-50 to-gray-100 border border-gray-100 flex items-center justify-center text-lg shrink-0 group-hover:scale-110 transition-transform">
                {domainIcon(r.domain)}
              </div>

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
                  <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-gray-100 text-gray-600">
                    📅 {formatDate(r.publish_date)}
                  </span>

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

                  {i === oldestDatedIndex && (
                    <span className="text-xs px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-medium">
                      🏆 oldest dated
                    </span>
                  )}
                </div>
              </div>

              <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Image Gallery */}
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
  );
}
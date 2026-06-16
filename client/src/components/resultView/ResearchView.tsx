"use client";

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

interface ResearchViewProps {
  report: ResearchReport;
  verdict: string;
}

function domainIcon(domain: string): string {
  const d = domain.toLowerCase();
  if (d.includes("youtube")) return "▶️";
  if (d.includes("facebook")) return "📘";
  if (d.includes("twitter") || d.includes("x.com")) return "🐦";
  if (d.includes("wikipedia")) return "📚";
  if (d.includes("reuters")) return "📰";
  if (d.includes("bbc")) return "📺";
  return "🌐";
}

export default function ResearchView({ report, verdict }: ResearchViewProps) {
  const isFalse = verdict === "fake" || verdict === "suspicious";
  const isUnconfirmed = verdict === "unconfirmed";

  const sectionTitle = isFalse
    ? "What Actually Happened"
    : isUnconfirmed
    ? "Further Investigation"
    : "Additional Evidence";

  const sectionIcon = isFalse ? "🔍" : isUnconfirmed ? "❓" : "✅";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-lg">{sectionIcon}</span>
        <h2 className="text-lg font-semibold text-gray-900">{sectionTitle}</h2>
      </div>

      {/* Summary */}
      {report.summary && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
            {report.summary}
          </p>
        </div>
      )}

      {/* Key Findings */}
      {report.key_findings && report.key_findings.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Key Findings
          </h3>
          <ul className="space-y-2">
            {report.key_findings.map((finding: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-blue-500 mt-0.5 shrink-0">•</span>
                <span>{finding}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Sources */}
      {report.sources && report.sources.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Sources ({report.sources.length})
          </h3>
          <div className="space-y-3">
            {report.sources.map((source: ResearchSource, i: number) => (
              <div
                key={i}
                className="bg-white rounded-xl border border-gray-100 p-4 hover:border-gray-200 hover:shadow-sm transition-all"
              >
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center text-base shrink-0">
                    {domainIcon(source.domain)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-400 font-mono mb-0.5">{source.domain}</p>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-gray-800 hover:text-blue-600 transition-colors line-clamp-2"
                    >
                      {source.title}
                    </a>
                    {source.snippet && (
                      <p className="text-xs text-gray-500 mt-1.5 line-clamp-2 leading-relaxed">
                        {source.snippet}
                      </p>
                    )}
                  </div>
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Images */}
      {report.images && report.images.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Related Images ({report.images.length})
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {report.images.map((img: ResearchImage, i: number) => (
              <a
                key={i}
                href={img.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="group relative aspect-square rounded-xl overflow-hidden bg-gray-100 border border-gray-100 hover:border-blue-300 hover:shadow-md transition-all"
              >
                {img.thumbnail_url ? (
                  <img
                    src={img.thumbnail_url}
                    alt={img.title || "Related image"}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400 text-2xl">
                    🖼️
                  </div>
                )}
                <div className="absolute inset-0 bg-linear-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="absolute bottom-0 left-0 right-0 p-2">
                    <p className="text-xs text-white line-clamp-2">{img.title}</p>
                  </div>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Videos */}
      {report.videos && report.videos.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Related Videos ({report.videos.length})
          </h3>
          <div className="space-y-3">
            {report.videos.map((video: ResearchVideo, i: number) => (
              <a
                key={i}
                href={video.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-4 bg-white rounded-xl border border-gray-100 p-3 hover:border-gray-200 hover:shadow-sm transition-all"
              >
                {/* Thumbnail */}
                <div className="relative w-40 aspect-video rounded-lg overflow-hidden bg-gray-100 shrink-0">
                  {video.thumbnail_url ? (
                    <img
                      src={video.thumbnail_url}
                      alt={video.title || "Video"}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400 text-2xl">
                      ▶️
                    </div>
                  )}
                  {video.duration && (
                    <span className="absolute bottom-1 right-1 text-[10px] bg-black/75 text-white px-1.5 py-0.5 rounded font-medium">
                      {video.duration}
                    </span>
                  )}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-10 h-10 rounded-full bg-black/50 flex items-center justify-center">
                      <svg className="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </div>
                  </div>
                </div>
                {/* Info */}
                <div className="flex-1 min-w-0 pt-1">
                  <p className="text-sm font-medium text-gray-800 line-clamp-2">{video.title}</p>
                  {video.source && (
                    <p className="text-xs text-gray-400 mt-1">{video.source}</p>
                  )}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Attribution */}
      <div className="text-center pt-4">
        <p className="text-xs text-gray-400">
          Research compiled by AI from web search results · Verify critical information through official sources.
        </p>
      </div>
    </div>
  );
}
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

interface RobotResponseProps {
  robot: RobotAnalysisData | null;
  compact?: boolean;
  onViewMore?: () => void;
  onBackToResults?: () => void;
  showResearch?: boolean;
}

export default function RobotResponse({ robot, compact = false, onViewMore, onBackToResults, showResearch = false }: RobotResponseProps) {
  return (
    <>
      {robot && (() => {
        const VERDICT_STYLES: Record<string, { icon: string; label: string; bg: string; border: string; text: string; badge: string }> = {
          real:        { icon: "🛡️", label: "Real News",     bg: "bg-green-50",   border: "border-green-300",  text: "text-green-800",  badge: "from-green-500 to-emerald-600" },
          fake:        { icon: "🚨", label: "Fake News",     bg: "bg-red-50",     border: "border-red-300",    text: "text-red-800",    badge: "from-red-500 to-rose-600" },
          suspicious:  { icon: "⚠️", label: "Suspicious",    bg: "bg-amber-50",   border: "border-amber-300",  text: "text-amber-800",  badge: "from-amber-500 to-orange-600" },
          unconfirmed: { icon: "❓", label: "Unconfirmed",   bg: "bg-gray-50",    border: "border-gray-300",   text: "text-gray-700",   badge: "from-gray-500 to-slate-600" },
        };
        const cfg = VERDICT_STYLES[robot.verdict] ?? VERDICT_STYLES.unconfirmed;
        const confidencePct = Math.round(robot.confidence * 100);

        if (compact) {
          return (
            <div className="flex items-start gap-4 px-6 py-3 max-w-full overflow-hidden">
              <div className="text-3xl shrink-0">{cfg.icon}</div>
              <div className="flex-1 min-w-0 flex flex-wrap items-center gap-x-4 gap-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-base font-bold ${cfg.text}`}>{cfg.label}</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cfg.bg} ${cfg.text} border ${cfg.border}`}>
                    {confidencePct}% confidence
                  </span>
                </div>
                {robot.short_summary && (
                  <p className={`text-sm ${cfg.text} truncate max-w-[400px]`}>{robot.short_summary}</p>
                )}
                {!robot.short_summary && robot.explanation && (
                  <p className="text-xs text-gray-500 truncate max-w-[500px]">{robot.explanation}</p>
                )}
              </div>
            </div>
          );
        }

        return (
          <div className="mb-6 pt-6 border-t-2 border-gray-200">
            {/* Section heading */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-base">BOB</span>
              <h2 className="text-base font-semibold text-gray-900">AI Analysis Conclusion</h2>
              {!robot.llm_used && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-200 text-gray-600 font-medium">
                  Rules-based
                </span>
              )}
            </div>

            {/* Verdict card */}
            <div className={`rounded-xl border-2 ${cfg.border} ${cfg.bg} p-4 shadow-sm transition-all hover:shadow-md`}>
              <div className="flex items-start gap-3">
                <div className="text-3xl shrink-0">{cfg.icon}</div>
                <div className="flex-1 min-w-0">
                  {/* Verdict badge + confidence */}
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className={`text-base font-bold ${cfg.text}`}>{cfg.label}</span>
                    <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full ${cfg.bg} ${cfg.text} border ${cfg.border}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        robot.confidence >= 0.8 ? "bg-green-500" :
                        robot.confidence >= 0.6 ? "bg-emerald-500" :
                        robot.confidence >= 0.4 ? "bg-amber-500" :
                        "bg-red-500"
                      }`}></span>
                    </span>
                  </div>

                  {/* Short summary */}
                  {robot.short_summary && (
                    <p className={`text-sm font-medium ${cfg.text} mb-1.5`}>{robot.short_summary}</p>
                  )}

                  {/* Explanation */}
                  <p className="text-sm text-gray-600 leading-relaxed">{robot.explanation}</p>

                  {/* Key evidence */}
                  {robot.key_evidence && robot.key_evidence.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-gray-200">
                      <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Key Evidence</p>
                      <ul className="space-y-1">
                        {robot.key_evidence.map((ev: string, i: number) => (
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

            {/* Action buttons */}
            <div className="mt-3 flex items-center gap-4">
              {showResearch && onBackToResults ? (
                <button
                  className="text-sm font-medium text-gray-600 hover:text-gray-900 hover:underline flex items-center gap-1"
                  onClick={onBackToResults}
                >
                  ← Back to results
                </button>
              ) : onViewMore ? (
                <button
                  className="text-sm font-medium text-blue-600 hover:underline"
                  onClick={onViewMore}
                >
                  View research report →
                </button>
              ) : null}
            </div>

            {/* AI attribution footer */}
            <div className="mt-3 text-center">
              <p className="text-[10px] text-gray-400">
                Analysis powered by AI · Results may contain errors. Verify critical information through official sources.
              </p>
            </div>
          </div>
        );
      })()}
    </>
  );
}
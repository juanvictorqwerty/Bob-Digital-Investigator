interface RobotAnalysisData {
  verdict: "real" | "fake" | "suspicious" | "unconfirmed";
  confidence: number;
  short_summary: string;
  explanation: string;
  key_evidence: string[];
  llm_used: boolean;
}

export default function RobotResponse({ robot }: { robot: RobotAnalysisData | null }) {
  return (
    <>

    {/* Robot AI Analysis Footer — always shown at bottom when available */}
            {robot && (() => {
            const VERDICT_STYLES: Record<string, { icon: string; label: string; bg: string; border: string; text: string; badge: string }> = {
                real:        { icon: "🛡️", label: "Real News",     bg: "bg-green-50",   border: "border-green-300",  text: "text-green-800",  badge: "from-green-500 to-emerald-600" },
                fake:        { icon: "🚨", label: "Fake News",     bg: "bg-red-50",     border: "border-red-300",    text: "text-red-800",    badge: "from-red-500 to-rose-600" },
                suspicious:  { icon: "⚠️", label: "Suspicious",    bg: "bg-amber-50",   border: "border-amber-300",  text: "text-amber-800",  badge: "from-amber-500 to-orange-600" },
                unconfirmed: { icon: "❓", label: "Unconfirmed",   bg: "bg-gray-50",    border: "border-gray-300",   text: "text-gray-700",   badge: "from-gray-500 to-slate-600" },
            };
            const cfg = VERDICT_STYLES[robot.verdict] ?? VERDICT_STYLES.unconfirmed;
            const confidencePct = Math.round(robot.confidence * 100);
            
            return (
                <div className="mb-8 pt-8 border-t-2 border-gray-200">
                {/* Section heading */}
                <div className="flex items-center gap-2 mb-4">
                    <span className="text-lg">🤖</span>
                    <h2 className="text-lg font-semibold text-gray-900">AI Analysis Conclusion</h2>
                    {!robot.llm_used && (
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-200 text-gray-600 font-medium">
                        Rules-based
                    </span>
                    )}
                </div>

                {/* Verdict card */}
                <div className={`rounded-2xl border-2 ${cfg.border} ${cfg.bg} p-6 shadow-sm transition-all hover:shadow-md`}>
                    <div className="flex items-start gap-4">
                    <div className="text-4xl shrink-0">{cfg.icon}</div>
                    <div className="flex-1 min-w-0">
                        {/* Verdict badge + confidence */}
                        <div className="flex items-center gap-3 flex-wrap mb-3">
                        <span className={`text-lg font-bold ${cfg.text}`}>{cfg.label}</span>
                        <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${cfg.bg} ${cfg.text} border ${cfg.border}`}>
                            <span className={`w-2 h-2 rounded-full ${
                            robot.confidence >= 0.8 ? "bg-green-500" :
                            robot.confidence >= 0.6 ? "bg-emerald-500" :
                            robot.confidence >= 0.4 ? "bg-amber-500" :
                            "bg-red-500"
                            }`}></span>
                            {confidencePct}% confidence
                        </span>
                        </div>
                        
                        {/* Short summary */}
                        {robot.short_summary && (
                        <p className={`text-sm font-medium ${cfg.text} mb-2`}>{robot.short_summary}</p>
                        )}
                        
                        {/* Explanation */}
                        <p className="text-sm text-gray-600 leading-relaxed">{robot.explanation}</p>
                        
                        {/* Key evidence */}
                        {robot.key_evidence && robot.key_evidence.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-gray-200">
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Key Evidence</p>
                            <ul className="space-y-1.5">
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

                {/* AI attribution footer */}
                <div className="mt-4 text-center">
                    <p className="text-xs text-gray-400">
                    Analysis powered by AI · Results may contain errors. Verify critical information through official sources.
                    </p>
                </div>
                </div>
            );
            })()}

        </>
  );
}
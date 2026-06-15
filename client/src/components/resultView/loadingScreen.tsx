"use client";

import { useEffect, useState } from "react";

interface SSEEvent {
  event: string;
  data: any;
  timestamp: Date;
}

interface LoadingScreenProps {
  sseLog?: SSEEvent[];
  progress?: string;
  progressStep?: string;
  finished?: boolean;
}

// Stage definitions
const STAGES: Record<string, { icon: string; label: string; color: string; bgColor: string }> = {
  uploading: {
    icon: "📤",
    label: "Uploading Image",
    color: "from-blue-500 to-blue-600",
    bgColor: "bg-blue-50",
  },
  queued: {
    icon: "⏳",
    label: "Queued for Processing",
    color: "from-amber-500 to-orange-500",
    bgColor: "bg-amber-50",
  },
  processing: {
    icon: "🔍",
    label: "Searching the Web",
    color: "from-purple-500 to-purple-600",
    bgColor: "bg-purple-50",
  },
  analyzing: {
    icon: "🤖",
    label: "Analyzing Results",
    color: "from-emerald-500 to-teal-500",
    bgColor: "bg-emerald-50",
  },
  compiling: {
    icon: "📊",
    label: "Compiling Report",
    color: "from-indigo-500 to-indigo-600",
    bgColor: "bg-indigo-50",
  },
  complete: {
    icon: "🎉",
    label: "Complete!",
    color: "from-green-500 to-green-600",
    bgColor: "bg-green-50",
  },
  error: {
    icon: "💥",
    label: "Error",
    color: "from-red-500 to-rose-500",
    bgColor: "bg-red-50",
  },
};

function getStage(step: string): string {
  const s = step?.toLowerCase() || "";
  if (s === "queued" || s === "queuing") return "queued";
  if (s.includes("upload")) return "uploading";
  if (s.includes("search") || s.includes("crawl") || s.includes("fetch") || s.includes("process")) return "processing";
  if (s.includes("analyz") || s.includes("llm") || s.includes("robot") || s.includes("ai")) return "analyzing";
  if (s.includes("compil") || s.includes("render") || s.includes("build") || s.includes("final")) return "compiling";
  if (s.includes("done") || s.includes("complete") || s.includes("finish")) return "complete";
  if (s.includes("error") || s.includes("fail")) return "error";
  if (step) return "processing";
  return "uploading";
}

export default function LoadingScreen({ sseLog = [], progress = "", progressStep = "", finished = false }: LoadingScreenProps) {
  const [currentStage, setCurrentStage] = useState<string>("uploading");
  const [progressMessage, setProgressMessage] = useState<string>("Starting analysis...");
  const [visibleLogCount, setVisibleLogCount] = useState<number>(0);
  const [showTerminal, setShowTerminal] = useState(false);

  // Update stage based on progressStep or SSE events
  useEffect(() => {
    if (progressStep) {
      setCurrentStage(getStage(progressStep));
    }
    if (progress) {
      setProgressMessage(progress);
    }
  }, [progressStep, progress]);

  // Auto-advance stages when no SSE data is coming (simulation)
  useEffect(() => {
    if (sseLog.length > 0) return; // Real data incoming, don't simulate

    const stageTimers = [
      { stage: "uploading", duration: 800 },
      { stage: "queued", duration: 1200 },
      { stage: "processing", duration: 2500 },
      { stage: "analyzing", duration: 2000 },
      { stage: "compiling", duration: 1500 },
    ];

    const runStages = async () => {
      for (const s of stageTimers) {
        if (finished) return;
        await new Promise((r) => setTimeout(r, s.duration));
        if (finished) return;
        setCurrentStage(s.stage);
        setProgressMessage(`Stage: ${STAGES[s.stage]?.label || s.stage}`);
      }
    };

    runStages();
  }, [sseLog.length, finished]);

  // Animate log lines appearing
  useEffect(() => {
    if (sseLog.length > visibleLogCount) {
      const timer = setTimeout(() => {
        setVisibleLogCount((prev) => prev + 1);
      }, 250);
      return () => clearTimeout(timer);
    }
  }, [sseLog, visibleLogCount]);

  // Show terminal once we have SSE data
  useEffect(() => {
    if (sseLog.length > 0) {
      setShowTerminal(true);
    }
  }, [sseLog]);

  // Auto-scroll log
  useEffect(() => {
    if (showTerminal) {
      const el = document.getElementById("log-end");
      el?.scrollIntoView({ behavior: "smooth" });
    }
  }, [visibleLogCount, showTerminal]);

  const stage = STAGES[currentStage] ?? STAGES.uploading;
  const isComplete = finished || currentStage === "complete";
  const isError = currentStage === "error";

  return (
    <div className="fixed inset-0 bg-linear-to-br from-gray-50 via-white to-gray-100 z-50 flex items-center justify-center">
      <div className="w-full max-w-lg mx-auto px-6">
        {/* Main animation card */}
        <div
          className={`relative overflow-hidden rounded-3xl border-2 p-10 transition-all duration-700 ${
            isComplete
              ? "border-green-300 bg-green-50/50"
              : isError
              ? "border-red-300 bg-red-50/50"
              : "border-gray-200 bg-white"
          } shadow-2xl`}
        >
          {/* Animated background glow */}
          {!isComplete && !isError && (
            <div
              className={`absolute inset-0 bg-linear-to-br ${stage.color} opacity-[0.04] animate-pulse rounded-3xl`}
            />
          )}

          {/* Success celebration rings */}
          {isComplete && (
            <>
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-64 h-64 rounded-full border-4 border-green-300 animate-ping opacity-30" />
              </div>
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-40 h-40 rounded-full border-4 border-green-400 animate-ping opacity-20" style={{ animationDelay: "0.3s" }} />
              </div>
            </>
          )}

          {/* Error shake */}
          {isError && (
            <div className="absolute inset-0 bg-red-500/5 animate-shake rounded-3xl" />
          )}

          <div className="relative z-10 flex flex-col items-center gap-5">
            {/* Animated icon */}
            <div className="relative">
              <div
                className={`text-7xl transition-all duration-500 ${
                  isComplete
                    ? "animate-bounce"
                    : isError
                    ? "animate-shake"
                    : "animate-float"
                }`}
              >
                {isComplete ? "🎉" : isError ? "💥" : stage.icon}
              </div>

              {/* Scanning line effect for processing stages */}
              {currentStage === "processing" && (
                <div className="absolute inset-x-0 h-0.5 bg-purple-500/40 animate-scan-line rounded-full" />
              )}
            </div>

            {/* Stage label with gradient text */}
            <h3
              className={`text-2xl font-bold bg-linear-to-r ${stage.color} bg-clip-text text-transparent`}
            >
              {isComplete ? "Analysis Complete!" : isError ? "Something went wrong" : stage.label}
            </h3>

            {/* Progress message */}
            <p className="text-sm text-gray-500 text-center max-w-sm leading-relaxed">
              {progressMessage || "Processing your request..."}
            </p>

            {/* Animated progress bar */}
            {!isComplete && !isError && (
              <div className="w-full max-w-xs mt-2">
                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full bg-linear-to-r ${stage.color} rounded-full animate-progress`}
                    style={{
                      width: "100%",
                      animation: "progress-indeterminate 1.5s ease-in-out infinite",
                    }}
                  />
                </div>
              </div>
            )}

            {/* Stage indicator dots */}
            <div className="flex items-center gap-3 mt-2">
              {Object.entries(STAGES).map(([key, s]) => {
                if (key === "error") return null;
                const stages = Object.keys(STAGES).filter((k) => k !== "error");
                const idx = stages.indexOf(key);
                const currentIdx = stages.indexOf(currentStage);
                const isPast = idx < currentIdx;
                const isCurrent = idx === currentIdx;

                return (
                  <div key={key} className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-500 ${
                        isPast
                          ? "bg-green-500 text-white scale-90 shadow-md"
                          : isCurrent
                          ? `bg-linear-to-br ${s.color} text-white scale-110 shadow-lg shadow-current/20`
                          : "bg-gray-100 text-gray-400 scale-90"
                      }`}
                    >
                      {isPast ? "✓" : isCurrent ? (
                        <span className="animate-spin text-base">⟳</span>
                      ) : (
                        idx + 1
                      )}
                    </div>
                    {idx < stages.length - 1 && (
                      <div
                        className={`w-10 h-0.5 rounded transition-all duration-500 ${
                          isPast ? "bg-green-400" : isCurrent ? "bg-gray-300 animate-pulse" : "bg-gray-200"
                        }`}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Real-time backend terminal log */}
        {showTerminal && (
          <div className="mt-6 rounded-2xl border border-gray-200 bg-gray-950 overflow-hidden shadow-2xl animate-slide-up">
            {/* Terminal header */}
            <div className="flex items-center gap-2 px-5 py-3 bg-gray-900 border-b border-gray-800">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
              </div>
              <span className="text-xs text-gray-500 font-mono ml-2">backend ~ sse-stream</span>
              <span className="text-xs text-gray-600 ml-auto">
                <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse mr-1.5" />
                {sseLog.length} events
              </span>
            </div>

            {/* Terminal output */}
            <div className="p-5 max-h-72 overflow-y-auto font-mono text-xs leading-relaxed space-y-1.5">
              {sseLog.slice(0, visibleLogCount).map((entry, i) => {
                const isErr = entry.event === "error";
                const isDone = entry.event === "done";
                const isProgress = entry.event === "progress" || entry.event === "message";
                const time = entry.timestamp.toLocaleTimeString();

                let colorClass = "text-gray-500";
                if (isErr) colorClass = "text-red-400";
                else if (isDone) colorClass = "text-green-400";
                else if (isProgress) colorClass = "text-blue-300";
                else if (entry.event === "queued") colorClass = "text-amber-300";

                return (
                  <div key={i} className={`flex items-start gap-3 ${colorClass} animate-slide-up`}>
                    <span className="shrink-0 text-[10px] text-gray-600 w-16">[{time}]</span>
                    <span className="shrink-0 w-4 text-center">
                      {isErr ? "✗" : isDone ? "✓" : ">"}
                    </span>
                    <span className="break-all flex-1">
                      {entry.event !== "message" && (
                        <span className="text-[10px] uppercase tracking-wider opacity-60 mr-1.5">
                          [{entry.event}]
                        </span>
                      )}
                      {typeof entry.data === "object"
                        ? JSON.stringify(entry.data, null, 1)
                        : String(entry.data)}
                    </span>
                  </div>
                );
              })}
              <div id="log-end" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
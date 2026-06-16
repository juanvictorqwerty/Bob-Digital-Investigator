"use client";

import { useEffect, useState, useRef } from "react";

interface SSEEvent {
  event: string;
  data: any;
  timestamp: Date;
}

interface ProcessingAnimationProps {
  progress: string;
  progressStep: string;
  sseLog: SSEEvent[];
  isActive: boolean;
  fileName?: string;
  fileType?: string;
}

// Stage definitions with icons, colors, and display labels
const STAGES: Record<string, { icon: string; label: string; color: string; bgColor: string; ringColor: string }> = {
  uploading: {
    icon: "📤",
    label: "Uploading",
    color: "from-blue-500 to-blue-600",
    bgColor: "bg-blue-50",
    ringColor: "border-blue-300",
  },
  queued: {
    icon: "⏳",
    label: "In Queue",
    color: "from-amber-500 to-orange-500",
    bgColor: "bg-amber-50",
    ringColor: "border-amber-300",
  },
  processing: {
    icon: "🔍",
    label: "Searching Web",
    color: "from-purple-500 to-purple-600",
    bgColor: "bg-purple-50",
    ringColor: "border-purple-300",
  },
  analyzing: {
    icon: "🤖",
    label: "Analyzing",
    color: "from-emerald-500 to-teal-500",
    bgColor: "bg-emerald-50",
    ringColor: "border-emerald-300",
  },
  complete: {
    icon: "✅",
    label: "Complete",
    color: "from-green-500 to-green-600",
    bgColor: "bg-green-50",
    ringColor: "border-green-300",
  },
  error: {
    icon: "❌",
    label: "Error",
    color: "from-red-500 to-rose-500",
    bgColor: "bg-red-50",
    ringColor: "border-red-300",
  },
};

function getStage(step: string): string {
  const s = step?.toLowerCase() || "";
  if (s === "queued" || s === "queuing") return "queued";
  if (s.includes("upload")) return "uploading";
  if (s.includes("search") || s.includes("crawl") || s.includes("fetch") || s.includes("process")) return "processing";
  if (s.includes("analyz") || s.includes("llm") || s.includes("robot") || s.includes("ai")) return "analyzing";
  if (s.includes("done") || s.includes("complete") || s.includes("finish")) return "complete";
  if (s.includes("error") || s.includes("fail")) return "error";
  // If we have progress but no specific stage, assume processing
  if (step) return "processing";
  return "uploading";
}

export default function ProcessingAnimation({
  progress,
  progressStep,
  sseLog,
  isActive,
  fileName,
  fileType,
}: ProcessingAnimationProps) {
  const currentStage = getStage(progressStep);
  const stage = STAGES[currentStage] ?? STAGES.uploading;
  const logEndRef = useRef<HTMLDivElement>(null);
  const [visibleLogLines, setVisibleLogLines] = useState<number>(0);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [sseLog]);

  // Animate log lines appearing one by one
  useEffect(() => {
    if (sseLog.length > visibleLogLines) {
      const timer = setTimeout(() => {
        setVisibleLogLines((prev) => prev + 1);
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [sseLog, visibleLogLines]);

  // Reset visible count when log changes drastically
  useEffect(() => {
    setVisibleLogLines(sseLog.length);
  }, [sseLog.length]);

  const isError = currentStage === "error";
  const isComplete = currentStage === "complete";

  return (
    <div className="w-full space-y-6">
      {/* Main animation card */}
      <div
        className={`relative overflow-hidden rounded-2xl border-2 ${stage.ringColor} ${stage.bgColor} p-8 transition-all duration-500`}
      >
        {/* Animated background gradient */}
        {!isError && !isComplete && (
          <div
            className={`absolute inset-0 bg-linear-to-br ${stage.color} opacity-[0.03] animate-pulse`}
          />
        )}

        {/* Success animation overlay */}
        {isComplete && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-48 h-48 rounded-full bg-green-400/10 animate-ping" />
          </div>
        )}

        <div className="relative z-10 flex flex-col items-center gap-4">
          {/* Animated icon */}
          <div className="relative">
            <div
              className={`text-6xl transition-all duration-500 ${
                isComplete
                  ? "animate-bounce"
                  : isError
                  ? "animate-shake"
                  : "animate-float"
              }`}
            >
              {isComplete ? "🎉" : isError ? "💥" : stage.icon}
            </div>
            {!isComplete && !isError && (
              <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-12 h-1 bg-current opacity-20 rounded-full animate-pulse" />
            )}
          </div>

          {/* Stage label */}
          <h3 className={`text-xl font-bold bg-linear-to-r ${stage.color} bg-clip-text text-transparent`}>
            {stage.label}
          </h3>

          {/* Progress message */}
          <p className="text-sm text-gray-600 text-center max-w-md">{progress}</p>

          {/* Progress steps visualization */}
          <div className="flex items-center gap-2 mt-2">
            {Object.entries(STAGES).map(([key, s]) => {
              if (key === "error") return null;
              const stages = Object.keys(STAGES).filter((k) => k !== "error");
              const idx = stages.indexOf(key);
              const currentIdx = stages.indexOf(currentStage);
              const isPast = idx < currentIdx;
              const isCurrent = idx === currentIdx;

              return (
                <div key={key} className="flex items-center gap-2">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-500 ${
                      isPast
                        ? "bg-green-500 text-white scale-90"
                        : isCurrent
                        ? `bg-linear-to-br ${s.color} text-white scale-110 shadow-lg`
                        : "bg-gray-200 text-gray-400 scale-90"
                    }`}
                  >
                    {isPast ? "✓" : isCurrent ? s.icon.charAt(0) : idx + 1}
                  </div>
                  {idx < stages.length - 1 && (
                    <div
                      className={`w-8 h-0.5 rounded transition-all duration-500 ${
                        isPast ? "bg-green-400" : isCurrent ? "bg-gray-300 animate-pulse" : "bg-gray-200"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* File info */}
          {fileName && (
            <div className="mt-2 text-xs text-gray-400 flex items-center gap-1">
              <span>📄</span>
              <span className="truncate max-w-[200px]">{fileName}</span>
              {fileType && <span>· {fileType.toUpperCase()}</span>}
            </div>
          )}
        </div>
      </div>

      {/* Real-time backend response log */}
      {sseLog.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-gray-900 overflow-hidden shadow-lg">
          {/* Terminal header */}
          <div className="flex items-center gap-2 px-4 py-2 bg-gray-800 border-b border-gray-700">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div className="w-3 h-3 rounded-full bg-yellow-500" />
              <div className="w-3 h-3 rounded-full bg-green-500" />
            </div>
            <span className="text-xs text-gray-400 font-mono ml-2">backend-response.log</span>
            <span className="text-xs text-gray-600 ml-auto">
              {sseLog.length} events
            </span>
          </div>

          {/* Log content */}
          <div className="p-4 max-h-64 overflow-y-auto font-mono text-xs space-y-1">
            {sseLog.slice(0, visibleLogLines).map((entry, i) => {
              const isErr = entry.event === "error";
              const isDone = entry.event === "done";
              const isProgress = entry.event === "progress";
              const time = entry.timestamp.toLocaleTimeString();

              return (
                <div
                  key={i}
                  className={`flex items-start gap-2 py-0.5 ${
                    isErr
                      ? "text-red-400"
                      : isDone
                      ? "text-green-400"
                      : isProgress
                      ? "text-blue-300"
                      : "text-gray-400"
                  }`}
                >
                  <span className="shrink-0 text-gray-600">[{time}]</span>
                  <span className="shrink-0 text-gray-500">{isErr ? "✗" : isDone ? "✓" : "→"}</span>
                  <span className="break-all">
                    {typeof entry.data === "object"
                      ? JSON.stringify(entry.data, null, 1)
                      : String(entry.data)}
                  </span>
                </div>
              );
            })}
            <div ref={logEndRef} />
          </div>
        </div>
      )}
    </div>
  );
}
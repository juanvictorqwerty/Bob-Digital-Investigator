"use client";

import { BackGroundColor } from "@/colors/Colors";
import UploadCard from "@/components/UploadCard";
import { useState, useCallback } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";
import HistoryBlock from "@/components/HistoryBlock";
import ResultsView from "@/components/ResultsView";

export default function Home() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [query, setQuery] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState<string>("");
  const [progressStep, setProgressStep] = useState<string>("");
  const [historyResults, setHistoryResults] = useState<any>(null);
  const [historyAlias, setHistoryAlias] = useState<string>("");
  const [historyImageUrl, setHistoryImageUrl] = useState<string>("");
  const [sseLog, setSseLog] = useState<Array<{event: string; data: any; timestamp: string}>>([]);
  const [showProcessingAnimation, setShowProcessingAnimation] = useState(false);
  const [historyViewMode, setHistoryViewMode] = useState<"original" | "research-loading" | "research-results">("original");
  const [researchSseLog, setResearchSseLog] = useState<Array<{event: string; data: any; timestamp: Date}>>([]);
  const [researchProgress, setResearchProgress] = useState("");
  const [researchProgressStep, setResearchProgressStep] = useState("");

  const handleMediaSelect = (file: File | null) => {
    setSelectedFile(file);
  };

  const handleQueryChange = (q: string) => {
    setQuery(q);
  };

  const handleSelectResult = (results: any, alias: string, imageUrl: string) => {
    setHistoryResults(results);
    setHistoryAlias(alias);
    setHistoryImageUrl(imageUrl);
    setHistoryViewMode("original");
  };

  // Poll research progress via SSE (for history view)
  const pollResearchProgress = useCallback(async (taskId: string, token: string): Promise<any> => {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/discover/progress/${taskId}/`,
      {
        headers: {
          "Authorization": `Token ${token}`,
          "Accept": "text/event-stream",
        },
      }
    );

    if (!response.ok) {
      throw new Error(`SSE connection failed: ${response.status}`);
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    return new Promise((resolve, reject) => {
      const read = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split("\n\n");
            buffer = parts.pop() ?? "";

            for (const block of parts) {
              const eventMatch = block.match(/^event: (.+)$/m);
              const dataMatch = block.match(/^data: (.+)$/m);
              if (!dataMatch) continue;

              const event = eventMatch?.[1]?.trim() ?? "message";
              const data = JSON.parse(dataMatch[1]);

              setResearchSseLog((prev) => [...prev, { event, data, timestamp: new Date() }]);

              if (event === "progress") {
                setResearchProgress(data.message);
                setResearchProgressStep(data.step);
              } else if (event === "queued") {
                setResearchProgress(data.message);
                setResearchProgressStep("queued");
              } else if (event === "done") {
                reader.cancel();
                resolve(data);
                return;
              } else if (event === "error") {
                reader.cancel();
                reject(new Error(data.error));
                return;
              }
            }
          }
        } catch (err) {
          reject(err);
        }
      };

      read();
    });
  }, []);

  // Handle "View more" click for history view
  const handleHistoryViewMore = useCallback(async () => {
    const robot = historyResults?.robot_analysis;
    if (!robot) return;

    // If research already exists, just show it
    if (robot.research_report && robot.research_report.summary) {
      setHistoryViewMode("research-results");
      return;
    }

    // If no analysis_id, can't trigger research
    if (!robot.id) {
      console.error("No analysis_id available for history");
      return;
    }

    setHistoryViewMode("research-loading");
    setResearchSseLog([]);
    setResearchProgress("Starting research...");
    setResearchProgressStep("loading");

    const token = Cookies.get("token");
    if (!token) {
      setHistoryViewMode("original");
      return;
    }

    try {
      const checkResponse = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/discover/generate/`,
        {
          method: "POST",
          headers: {
            "Authorization": `Token ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ analysis_id: robot.id }),
        }
      );

      if (!checkResponse.ok) {
        throw new Error(`Request failed: ${checkResponse.status}`);
      }

      const checkData = await checkResponse.json();

      if (checkData.status === "already_exists") {
        const updatedResults = { ...historyResults };
        if (updatedResults.robot_analysis) {
          updatedResults.robot_analysis.research_report = checkData.research_report;
          updatedResults.robot_analysis.research_queries = checkData.research_queries;
        }
        setHistoryResults(updatedResults);
        setHistoryViewMode("research-results");
        return;
      }

      const taskId = checkData.task_id;
      const result = await pollResearchProgress(taskId, token);

      const updatedResults = { ...historyResults };
      if (updatedResults.robot_analysis) {
        updatedResults.robot_analysis.research_report = result.research_report;
        updatedResults.robot_analysis.research_queries = result.research_queries;
      }
      setHistoryResults(updatedResults);
      setHistoryViewMode("research-results");

    } catch (error) {
      console.error("Research generation failed:", error);
      setHistoryViewMode("original");
    }
  }, [historyResults, pollResearchProgress]);

  // Handle "Back to results" for history view
  const handleHistoryBackToResults = useCallback(() => {
    setHistoryViewMode("original");
  }, []);

  const addSseLog = (event: string, data: any) => {
    const entry = { event, data, timestamp: new Date().toISOString() };
    setSseLog((prev) => {
      const updated = [...prev, entry];
      // Keep sessionStorage in sync for the result page
      sessionStorage.setItem("sseLog", JSON.stringify(updated));
      return updated;
    });
  };

  const pollProgress = async (taskId: string, token: string): Promise<any> => {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/reverse-search/progress/${taskId}/`,
      {
        headers: {
          "Authorization": `Token ${token}`,
          "Accept": "text/event-stream",
        },
      }
    );

    if (!response.ok) {
      throw new Error(`SSE connection failed: ${response.status}`);
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    return new Promise((resolve, reject) => {
      const read = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split("\n\n");
            buffer = parts.pop() ?? "";

            for (const block of parts) {
              const eventMatch = block.match(/^event: (.+)$/m);
              const dataMatch = block.match(/^data: (.+)$/m);
              if (!dataMatch) continue;

              const event = eventMatch?.[1]?.trim() ?? "message";
              const data = JSON.parse(dataMatch[1]);

              // Log every SSE event for real-time display on results page
              addSseLog(event, data);

              if (event === "progress") {
                setProgress(data.message);
                setProgressStep(data.step);
              } else if (event === "queued") {
                setProgress(data.message);
                setProgressStep("queued");
              } else if (event === "done") {
                reader.cancel();
                resolve(data);
                return;
              } else if (event === "error") {
                reader.cancel();
                reject(new Error(data.error));
                return;
              }
            }
          }
        } catch (err) {
          reject(err);
        }
      };

      read();
    });
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setProgress("Uploading image...");

    try {
      const base64Image = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(selectedFile);
      });

      const formData = new FormData();
      formData.append("image", selectedFile);
      if (query.trim()) {
        formData.append("query", query.trim());
      }
      const token = Cookies.get("token");

      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/reverse-search/`, {
        method: "POST",
        body: formData,
        headers: {
          "Authorization": `Token ${token}`,
        },
      });

      if (!response.ok) {
        alert("Error uploading image");
        setIsUploading(false);
        setProgress("");
        return;
      }

      const data = await response.json();

      if (data.task_id) {
        setProgress("Queued for processing...");
        setProgressStep("queued");

        try {
          const results = await pollProgress(data.task_id, token || "");

          const resultsWithImage = { ...results, uploaded_image: base64Image, query: query.trim() };

          sessionStorage.setItem("searchResults", JSON.stringify(resultsWithImage));
          router.push("/reverseSearchResult");
        } catch (error) {
          console.error(error);
          alert("An error occurred during processing");
        }
      } else {
        const resultsWithImage = { ...data, uploaded_image: base64Image, query: query.trim() };
        sessionStorage.setItem("searchResults", JSON.stringify(resultsWithImage));
        router.push("/reverseSearchResult");
      }
    } catch (error) {
      console.error(error);
      alert("An error occurred during upload");
    } finally {
      setIsUploading(false);
      setProgress("");
      setProgressStep("");
    }
  };

  return (
    <>
      <main className={`${BackGroundColor} grid grid-cols-4 h-screen`}>

        <div className="bg-blue-50 col-span-1 p-4 border-r-2 border-gray-400">
            <HistoryBlock
              onSelectResult={handleSelectResult}
              onAliasUpdate={(id, newAlias) => {
                if (historyAlias && id) {
                  setHistoryAlias(newAlias);
                }
              }}
            />
        </div>
 
        <div className="h-full flex flex-col justify-center items-center col-span-3 overflow-auto">
          {historyResults ? (
            <>
              {/* Ribbon bar with image and alias */}
              <div className="sticky top-0 z-10 bg-white/95 backdrop-blur-sm border-b border-gray-200 shadow-sm px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {historyImageUrl && (
                    <div className="w-10 h-10 rounded-lg overflow-hidden bg-gray-100 ring-2 ring-blue-500 ring-offset-1 shrink-0">
                      <img
                        src={historyImageUrl}
                        alt="Uploaded"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}
                  <div>
                    <h2 className="text-base font-semibold text-gray-900">{historyAlias || "Reverse Image Search"}</h2>
                    <p className="text-xs text-gray-500">Viewing search results</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setHistoryResults(null);
                    setHistoryAlias("");
                    setHistoryImageUrl("");
                  }}
                  className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all shadow-sm"
                >
                  New Search
                </button>
              </div>
                  <div className="flex-1 overflow-auto px-4">
                    <ResultsView
                      results={historyResults}
                      alias={historyAlias}
                      imageUrl={historyImageUrl}
                      onBack={() => {
                        setHistoryResults(null);
                        setHistoryAlias("");
                        setHistoryImageUrl("");
                      }}
                      viewMode={historyViewMode}
                      onViewMore={handleHistoryViewMore}
                      onBackToResults={handleHistoryBackToResults}
                    />
                  </div>
            </>
          ) : (
            <>
              <div className="w-full max-w-md mx-auto">
                <UploadCard onFileSelect={handleMediaSelect} onQueryChange={handleQueryChange} />
              </div>

              {selectedFile && (
                <div className="mt-6 w-full max-w-md mx-auto">
                  <button
                    onClick={handleSubmit}
                    className="w-full rounded-xl bg-linear-to-r from-blue-600 to-blue-700 px-6 py-3 font-medium text-white hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={isUploading}
                  >
                    {isUploading ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        {progress || "Investigating..."}
                      </span>
                    ) : (
                      "Investigate File"
                    )}
                  </button>

                  {progress && (
                    <div className="mt-3 text-center">
                      <p className="text-sm text-gray-600">{progress}</p>
                      {progressStep && (
                        <p className="text-xs text-gray-400 mt-1 capitalize">{progressStep}</p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </>
  );
}
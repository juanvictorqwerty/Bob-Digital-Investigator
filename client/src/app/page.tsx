"use client";

import { BackGroundColor } from "@/colors/Colors";
import UploadCard from "@/components/UploadCard";
import { useState } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState<string>("");
  const [progressStep, setProgressStep] = useState<string>("");

  const handleMediaSelect = (file: File | null) => {
    setSelectedFile(file);
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

          const resultsWithImage = { ...results, uploaded_image: base64Image };

          sessionStorage.setItem("searchResults", JSON.stringify(resultsWithImage));
          router.push("/reverseSearchResult");
        } catch (error) {
          console.error(error);
          alert("An error occurred during processing");
        }
      } else {
        const resultsWithImage = { ...data, uploaded_image: base64Image };
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
      <main className={BackGroundColor}>
        <div className="min-h-screen flex flex-col items-center justify-center px-4">
          <div className="w-full max-w-md mx-auto">
            <UploadCard onFileSelect={handleMediaSelect} />
          </div>

          {selectedFile && (
            <div className="mt-6 w-full max-w-md mx-auto">
              <button
                onClick={handleSubmit}
                className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-3 font-medium text-white hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
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
        </div>
      </main>
    </>
  );
}
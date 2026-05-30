"use client";

import { BackGroundColor } from "@/colors/Colors";
import UploadCard from "@/components/UploadCard";
import { useState } from "react";

export default function Home() {
  // 1. Create a state to hold the selected file in the parent component
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // 2. Define a proper callback function that accepts the file parameter
  const handleMediaSelect = (file: File | null) => {
    setSelectedFile(file);
    console.log("Selected file captured in parent:", file);
  };

  return (
    <>
      <main className={BackGroundColor}>
        {/* Perfect centering container */}
        <div className="min-h-screen flex flex-col items-center justify-center px-4">
          {/* Upload Card - perfectly centered */}
          <div className="w-full max-w-md mx-auto">
            <UploadCard onFileSelect={handleMediaSelect} />
          </div>

          {/* Submit button - centered below the card */}
          {selectedFile && (
            <div className="mt-6 w-full max-w-md mx-auto">
              <button 
                onClick={() => console.log("Ready to send to Django:", selectedFile)}
                className="w-full rounded-xl bg-blue-600 px-6 py-2 font-medium text-white hover:bg-blue-700 transition-colors"
              >
                Investigate File
              </button>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
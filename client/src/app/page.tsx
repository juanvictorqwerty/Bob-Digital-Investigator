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

  const handleMediaSelect = (file: File | null) => {
    setSelectedFile(file);
    console.log("Selected file captured in parent:", file);
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;

    setIsUploading(true);

    try {
      // Convert image to base64 for caching
      const base64Image = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(selectedFile);
      });

      // Create formdata to upload the file
      const formData = new FormData();
      formData.append("image", selectedFile);
      const token = Cookies.get("token");

      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/reverse-search/`, {
        method: "POST",
        body: formData,
        headers: {
          "Authorization": `Token ${token}`
        },
      });

      if (!response.ok) {
        alert("Error uploading image");
        setIsUploading(false);
        return;
      }
      
      const data = await response.json();
      
      // Add the uploaded image base64 to the results for caching
      const resultsWithImage = {
        ...data,
        uploaded_image: base64Image
      };
      
      console.log(data);
      setIsUploading(false);
      
      // Store results with cached image in sessionStorage and navigate to results page
      sessionStorage.setItem('searchResults', JSON.stringify(resultsWithImage));
      router.push('/reverseSearchResult');
    } catch (error) {
      console.error(error);
      setIsUploading(false);
      alert("An error occurred during upload");
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
                    Investigating...
                  </span>
                ) : (
                  "Investigate File"
                )}
              </button>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
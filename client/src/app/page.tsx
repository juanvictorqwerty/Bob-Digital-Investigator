"use client";

import { BackGroundColor } from "@/colors/Colors";
import UploadCard from "@/components/UploadCard";
import { useState } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  // 1. Create a state to hold the selected file in the parent component
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading,setIsUploading]=useState(false)

  // 2. Define a proper callback function that accepts the file parameter
  const handleMediaSelect =(file: File | null) => {
    setSelectedFile(file);
    console.log("Selected file captured in parent:", file);
  };

  const handleSubmit= async()=>{

    if(!selectedFile) return;

    setIsUploading(true);

    try{
      //Create formdata to upload the file
      const formData=new FormData();
      formData.append("image",selectedFile); //the name expected by Django backend
      const token=Cookies.get("token");


      const response= await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/reverse-search/`,{
        method:"POST",
        body:formData,
        headers:{
          "Authorization": `Token ${token}`
        },
      });

      if (!response.ok){
        alert("error")
        }
        const data= await response.json()
        console.log(data)
        setIsUploading(false)
        
        // Store results in sessionStorage and navigate to results page
        sessionStorage.setItem('searchResults', JSON.stringify(data));
        router.push('/reverseSearchResult');
      }
    catch(error){
      console.error(error)
    }

  }

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
                onClick={handleSubmit}
                className="w-full rounded-xl bg-blue-600 px-6 py-2 font-medium text-white hover:bg-blue-700 transition-colors"
                disabled={isUploading}
              >
                {isUploading ? "Uploading..." : "Investigate File"}
              </button>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
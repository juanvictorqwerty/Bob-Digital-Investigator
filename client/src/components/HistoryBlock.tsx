import { BackGroundColor } from "@/colors/Colors"

export default function HistoryBlock(){
    return (
        <main className={`${BackGroundColor} w-full h-screen p-2 hover:bg-gray-100`}>
            <h1 className="mx-auto bg-blue-300 text-center p-2 font-bold rounded drop-shadow-blue-400 ">
                Bob Digital Investigator
            </h1>
        </main>
    )
}
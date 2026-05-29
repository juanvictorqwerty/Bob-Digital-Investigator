"use client";



export default function AuthDivider() {

    return (
        <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
                <div className={`w-full border-t border-gray-300/30`} />
            </div>
            <div className="relative flex justify-center text-sm">
                <span className={`px-2 bg-gray-50 text-gray-500`}>
                    or
                </span>
            </div>
        </div>
    );
}
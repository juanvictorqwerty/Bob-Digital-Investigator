"use client";


import { ButtonHTMLAttributes, ReactNode } from "react";

interface AuthButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary";
    isLoading?: boolean;
    children: ReactNode;
}

export default function AuthButton({
    variant = "primary",
    isLoading = false,
    children,
    className = "",
    ...props
}: AuthButtonProps) {

    const baseClasses = "w-full py-3 px-4 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
        primary: `bg-linear-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white hover:shadow-lg hover:shadow-blue-500/20`,
        secondary: `border border-gray-300/50 text-gray-900 hover:border-gray-400/50 hover:bg-gray-100/30`,
    };

    return (
        <button
            {...props}
            disabled={isLoading || props.disabled}
            className={`${baseClasses} ${variants[variant]} ${className}`}
        >
            {isLoading ? (
                <>
                    <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    {variant === "primary" ? "Processing..." : "Loading..."}
                </>
            ) : (
                children
            )}
        </button>
    );
}
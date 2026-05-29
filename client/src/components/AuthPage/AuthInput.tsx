"use client";


import { InputHTMLAttributes } from "react";

interface AuthInputProps extends InputHTMLAttributes<HTMLInputElement> {
    label?: string;
}

export default function AuthInput({ label, className = "", ...props }: AuthInputProps) {

    return (
        <div className="relative group">
            {label && (
                <label className={`block text-sm font-medium mb-2 transition-colors duration-300 text-gray-700`}>
                    {label}
                </label>
            )}
            <input
                {...props}
                className={`
                    w-full px-4 py-3 rounded-lg
                    focus:outline-none focus:ring-2 transition-all duration-200
                    disabled:opacity-50
                    bg-gray-100/50 border border-gray-300/50 text-gray-900 placeholder-gray-500 focus:ring-blue-400/50 focus:border-blue-400/50
                    ${className}
                `}
            />
            <div
                className={`
                    absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100
                    transition-opacity duration-300 pointer-events-none
                    bg-linear-to-r from-blue-400/10 to-purple-400/10
                `}
            />
        </div>
    );
}
"use client";


import { ReactNode } from "react";

interface AuthLayoutProps {
    children: ReactNode;
    title: string;
    subtitle: string;
}

export default function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {

    return (
        <div
            className={`
                min-h-screen transition-colors duration-300
                bg-linear-to-br from-white via-gray-50 to-gray-100
                flex items-center justify-center p-4 relative overflow-hidden
            `}
        >
            {/* Animated background orbs */}
            <div className={`absolute -top-40 -right-40 w-80 h-80 rounded-full blur-3xl animate-pulse bg-blue-400/5`} />
            <div className={`absolute -bottom-40 -left-40 w-80 h-80 rounded-full blur-3xl animate-pulse delay-1000 bg-indigo-400/5`} />
            <div className={`absolute top-1/2 left-1/2 w-96 h-96 rounded-full blur-3xl bg-purple-400/5`} />

            <div className="relative z-10 w-full max-w-md">
                <div
                    className={`
                        backdrop-blur-xl rounded-2xl shadow-2xl p-8 md:p-10
                        transition-all duration-300
                        bg-white/50 border border-gray-200/50
                    `}
                >
                    {/* Header without Theme Toggle */}
                    <div className="mb-8">
                        <h1 className={`text-4xl font-light tracking-tight mb-2 text-gray-900`}>
                            {title}
                        </h1>
                        <p className={`text-sm font-light text-gray-600`}>
                            {subtitle}
                        </p>
                    </div>

                    {children}
                </div>

                {/* Footer */}
                <p className={`text-center text-xs mt-8 text-gray-500`}>
                    By continuing, you agree to our{" "}
                    <a href="#" className={`transition-colors text-gray-700 hover:text-gray-900`}>
                        Terms of Service
                    </a>
                    {" "}and{" "}
                    <a href="#" className={`transition-colors text-gray-700 hover:text-gray-900`}>
                        Privacy Policy
                    </a>
                </p>
            </div>
        </div>
    );
}
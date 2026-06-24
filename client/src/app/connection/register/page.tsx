"use client"
import AuthLayout from "@/components/AuthPage/AuthLayout";
import { ButtonColor, ButtonTextColor, ButtonColorHover } from "@/colors/Colors";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function SignUp() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");
    const router = useRouter();

    const handleSignUp = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (password !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        setIsLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/signup/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email: email,
                    password: password,
                }),
            });

            if (response.status === 201) {
                router.push("/connection/login");
            } else {
                const data = await response.json();
                setError(data.email?.[0] || data.password?.[0] || "Registration failed. Please try again.");
            }
        } catch {
            setError("An error occurred. Please try again later.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <AuthLayout title="Welcome !" subtitle="Create an account">
            <form onSubmit={handleSignUp}>
                <div className="mb-4">
                    <label htmlFor="email" className="block text-sm font-light text-gray-700">Email</label>
                    <input
                        type="email"
                        id="email"
                        onChange={e => setEmail(e.target.value)}
                        value={email}
                        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <div className="mb-4">
                    <label htmlFor="password" className="block text-sm font-light text-gray-700">Password</label>
                    <input
                        type="password"
                        id="password"
                        onChange={e => setPassword(e.target.value)}
                        value={password}
                        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <div className="mb-4">
                    <label htmlFor="confirmPassword" className="block text-sm font-light text-gray-700">Confirm Password</label>
                    <input
                        type="password"
                        id="confirmPassword"
                        onChange={e => setConfirmPassword(e.target.value)}
                        value={confirmPassword}
                        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                {error && (
                    <p className="mb-4 text-sm text-red-600">{error}</p>
                )}
                <button
                    type="submit"
                    disabled={isLoading}
                    className={`${ButtonColor} hover:${ButtonColorHover} ${ButtonTextColor} rounded-md w-full mx-auto h-[50px] disabled:opacity-50`}
                >
                    {isLoading ? "Creating account..." : "Sign Up"}
                </button>
            </form>
            <div className="mt-4 text-center">
                <Link href="/connection/login" className="text-blue-600 hover:underline">
                    Already have an account? Login
                </Link>
            </div>
        </AuthLayout>
    )
}
"use client"
import AuthLayout from "@/components/AuthPage/AuthLayout";
import { ButtonColor, ButtonTextColor, ButtonColorHover } from "@/colors/Colors";
import { useState } from "react";
import Cookies from "js-cookie";
import { useRouter } from "next/navigation";

export default function Login() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false)
    const router = useRouter();

    const handleLogin = async (e: React.SubmitEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/login/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email: email,
                    password: password,
                }),
            });

            if (response.status === 200) {
                // 2. Extract the JSON body data from the response stream
                const data = await response.json();

                // 3. Set cookies using the extracted data strings
                Cookies.set("token", data.token, {
                    expires: 60,
                    secure: true,
                    sameSite: "strict",
                });
                Cookies.set("email", data.email, {
                    expires: 60,
                    secure: true,
                    sameSite: "strict",
                });

                // 4. Redirect the user AFTER cookies are successfully set
                router.push("/");
            } else {
                alert("Wrong password or email");
            }
        } catch (error) {
            console.error("Network error during authentication:", error);
            alert("An error occurred. Please try again later.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <AuthLayout title="Welcome Back !" subtitle="Connect to your account" >
            <form onSubmit={handleLogin}>
                <div className="mb-4">
                    <label htmlFor="email" className="block text-sm font-light text-gray-700">
                        Email
                    </label>
                    <input
                        type="email"
                        id="email"
                        onChange={e => setEmail(e.target.value)}
                        value={email}
                        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <div className="mb-4">
                    <label htmlFor="password" className="block text-sm font-light text-gray-700">
                        Password
                    </label>
                    <input
                        type="password"
                        id="password"
                        onChange={e => setPassword(e.target.value)}
                        value={password}
                        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <button
                    type="submit"
                    className={`w-full px-4 py-2 ${ButtonColor} hover: ${ButtonColorHover} ${ButtonTextColor} rounded-md h-[50px] `}
                    onSubmit={handleLogin}
                    disabled={isLoading}
                >
                    {isLoading ? "Logging in..." : "Login"}
                </button>
            </form>
        </AuthLayout>
    )
}
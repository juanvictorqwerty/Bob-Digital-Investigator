import AuthLayout from "@/components/AuthPage/AuthLayout";
import { ButtonColor, ButtonTextColor, ButtonColorHover } from "@/colors/Colors";
import Link from "next/link";

export default function SignUp() {
    return (
        <AuthLayout title="Welcome !" subtitle="Create an account">
            <form>
                <div className="mb-4">
                    <label htmlFor="email" className="block text-sm font-light text-gray-700">Email</label>
                    <input type="email" id="email" className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div className="mb-4">
                    <label htmlFor="email" className="block text-sm font-light text-gray-700">Password</label>
                    <input type="password" id="password" className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div className="mb-4">
                    <label htmlFor="password" className="block text-sm font-light text-gray-700">Confirm Password</label>
                    <input type="password" id="password" className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <button type="submit" className={`${ButtonColor} hover: ${ButtonColorHover} ${ButtonTextColor} rounded-md w-full mx-auto h-[50px] `}>Sign Up</button>
            </form>
            <div className="mt-4 text-center">
                <Link href="/connection/login" className="text-blue-600 hover:underline">
                    Already have an account? Login
                </Link>
            </div>
        </AuthLayout>
    )
}
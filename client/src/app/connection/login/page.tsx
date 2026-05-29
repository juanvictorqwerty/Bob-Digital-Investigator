import AuthLayout from "@/components/AuthPage/AuthLayout";
import { ButtonColor, ButtonTextColor, ButtonColorHover } from "@/colors/Colors";

export default function Login() {

    return (
        <AuthLayout title="Welcome Back !" subtitle="Connect to your account" >
            <form>
                <div className="mb-4">
                    <label htmlFor="email" className="block text-sm font-light text-gray-700">
                        Email
                    </label>
                    <input
                        type="email"
                        id="email"
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
                        className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <button
                    type="submit"
                    className={`w-full px-4 py-2 ${ButtonColor} hover: ${ButtonColorHover} ${ButtonTextColor} rounded-md h-[50px] `}
                >
                    Login
                </button>
            </form>
        </AuthLayout>
    )
}
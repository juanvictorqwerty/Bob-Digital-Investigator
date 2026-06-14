export default function LoadingScreen() {
  return (
    <div className="fixed inset-0 bg-linear-to-br from-gray-50 via-white to-gray-50 z-50 flex items-center justify-center">
      <div className="relative">
        {/* Animated rings */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-32 h-32 border-4 border-blue-200 rounded-full animate-ping opacity-75"></div>
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-24 h-24 border-4 border-blue-300 rounded-full animate-pulse"></div>
        </div>
        
        {/* Main spinner */}
        <div className="relative flex flex-col items-center gap-6">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          
          {/* Animated dots */}
          <div className="flex gap-2 mt-4">
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
          </div>
          
          <p className="text-gray-600 font-medium mt-4 animate-pulse">
            Analyzing image...
          </p>
          <p className="text-sm text-gray-400">
            Searching across the web for matches
          </p>
        </div>
      </div>
    </div>
  );
}
export default function ImageGallery({ withImages }: { withImages: SearchResult[] }) {
    return (
            <>
    {withImages.length > 0 && (
            <div>
                <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    🖼️ Image Gallery
                    <span className="text-xs font-normal text-gray-500 bg-white px-2 py-0.5 rounded-full">
                    {withImages.length} images
                    </span>
                </h2>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {withImages.map((r, i) => (
                    <div
                    key={r.page_url}
                    className={`group relative bg-white rounded-xl overflow-hidden border transition-all duration-300 hover:shadow-lg hover:-translate-y-1 ${
                        i === 0
                        ? "border-amber-300 ring-2 ring-amber-200"
                        : "border-gray-100 hover:border-gray-200"
                    }`}
                    >
                    <div className="relative aspect-video bg-gray-100 overflow-hidden">
                        <img
                        src={r.thumbnail}
                        alt={r.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                        {i === 0 && (
                        <div className="absolute top-2 left-2 bg-amber-500 text-white text-xs px-2 py-1 rounded-full font-medium shadow-lg">
                            Oldest
                        </div>
                        )}
                    </div>
                    <div className="p-3">
                        <p className="text-xs font-medium text-gray-800 line-clamp-2">{r.title}</p>
                        <p className="text-xs text-gray-400 mt-1 truncate">{r.domain}</p>
                    </div>
                    
                    {/* Hover overlay with link */}
                    <a
                        href={r.page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all duration-300 flex items-center justify-center"
                    >
                        <span className="opacity-0 group-hover:opacity-100 bg-white text-gray-800 text-xs px-2 py-1 rounded-full shadow-lg transform translate-y-2 group-hover:translate-y-0 transition-all">
                        View source →
                        </span>
                    </a>
                    </div>
                ))}
                </div>
            </div>
            )}
        </>
    );
}
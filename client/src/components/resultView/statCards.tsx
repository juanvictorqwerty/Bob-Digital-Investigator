interface Statistics {
  total_sources: number;
  with_publish_date: number;
  with_image_metadata: number;
  unique_domains: number;
  trusted_domains: number;
}

export default function StatCards({ stats }: { stats: Statistics }) {
    return (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                    {[
                        { label: "Total Sources", value: stats.total_sources, icon: "🔍", color: "from-blue-500 to-blue-600" },
                        { label: "With Date", value: stats.with_publish_date, icon: "�", color: "from-purple-500 to-purple-600" },
                        { label: "With Metadata", value: stats.with_image_metadata, icon: "�", color: "from-green-500 to-green-600" },
                        { label: "Unique Domains", value: stats.unique_domains, icon: "🌐", color: "from-orange-500 to-orange-600" },
                        { label: "Trusted Sites", value: stats.trusted_domains, icon: "✅", color: "from-teal-500 to-teal-600" },
                    ].map((s) => (
                        <div key={s.label} className="group relative overflow-hidden bg-white rounded-2xl shadow-sm hover:shadow-md transition-all duration-300">
                        <div className={`absolute top-0 right-0 w-32 h-32 bg-linear-to-br ${s.color} opacity-5 rounded-full transform translate-x-16 -translate-y-16 group-hover:scale-150 transition-transform duration-500`}></div>
                        <div className="relative p-5">
                            <div className="text-3xl mb-2">{s.icon}</div>
                            <p className="text-2xl font-bold text-gray-900">{s.value}</p>
                            <p className="text-xs text-gray-500 mt-1">{s.label}</p>
                        </div>
                        </div>
                    ))}
            </div>
    );
}
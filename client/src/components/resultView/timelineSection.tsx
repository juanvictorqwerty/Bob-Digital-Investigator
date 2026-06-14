interface TimelineEntry {
  date: string;
  domain: string;
  url: string;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "No date";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function TimelineSection({ timeline }: { timeline: TimelineEntry[] }) {
  return (
    <>
      {timeline.length > 0 && (
        <div className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              📅 Timeline
              <span className="text-xs font-normal text-gray-500 bg-white px-2 py-0.5 rounded-full">
                {timeline.length} entries
              </span>
            </h2>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 p-6">
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-linear-to-b from-blue-500 to-purple-500"></div>

              <div className="space-y-4">
                {timeline.map((entry, i) => (
                  <div key={i} className="relative flex items-start gap-4 pl-10">
                    {/* Timeline dot */}
                    <div className={`absolute left-2 w-5 h-5 rounded-full border-4 border-white ${
                      i === 0 ? 'bg-blue-500' : i === timeline.length - 1 ? 'bg-purple-500' : 'bg-gray-300'
                    }`}></div>

                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800">{formatDate(entry.date)}</p>
                      <p className="text-xs text-gray-500">{entry.domain}</p>
                      <a
                        href={entry.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 hover:text-blue-700 mt-1 inline-block"
                      >
                        View source →
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
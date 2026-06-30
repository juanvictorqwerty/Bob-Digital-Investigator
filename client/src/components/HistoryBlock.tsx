"use client";

import { useEffect, useState, useCallback } from "react";
import Cookies from "js-cookie";
import { BackGroundColor } from "@/colors/Colors";

interface HistoryItem {
  id: string;
  alias: string;
  query: string;
  image_url: string | null;
  image_thumbnail: string | null;
  created_at: string;
}

interface HistoryBlockProps {
  onSelectResult?: (results: any, alias: string, imageUrl: string) => void;
  onAliasUpdate?: (id: string, newAlias: string) => void;
}

export default function HistoryBlock({ onSelectResult, onAliasUpdate }: HistoryBlockProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const fetchHistory = useCallback(async () => {
    const token = Cookies.get("token");
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/history/`,
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (err) {
      console.error("Failed to fetch history:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleAliasSave = async (id: string) => {
    const token = Cookies.get("token");
    if (!token) return;

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/history/${id}/alias/`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Token ${token}`,
          },
          body: JSON.stringify({ alias: editValue }),
        }
      );
      if (res.ok) {
        setHistory((prev) =>
          prev.map((item) =>
            item.id === id ? { ...item, alias: editValue } : item
          )
        );
        onAliasUpdate?.(id, editValue);
      }
    } catch (err) {
      console.error("Failed to update alias:", err);
    }
    setEditingId(null);
  };

  const handleItemClick = async (item: HistoryItem) => {
    if (!onSelectResult) return;

    const token = Cookies.get("token");
    if (!token) return;

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/history/${item.id}/`,
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );
      if (res.ok) {
        const data = await res.json();
        onSelectResult(data.results, data.alias, data.image_url || "");
      }
    } catch (err) {
      console.error("Failed to fetch detail:", err);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className={`${BackGroundColor} h-full flex flex-col p-2`}>
      
      <h1 className="relative mx-auto mb-3 w-fit shrink-0">
        {/* Main badge */}
        <span
          className="relative inline-flex items-center gap-2 px-4 py-1.5 rounded-xl font-bold tracking-wider uppercase text-white text-xs"
          style={{
            background: "linear-gradient(135deg, #0f0c29, #302b63, #24243e)",
            border: "1px solid rgba(255,255,255,0.15)",
            boxShadow: "0 0 0 1px rgba(99,102,241,0.3), 0 4px 12px rgba(99,102,241,0.25)",
          }}
        >
          <span className="text-base">🔍</span>
          <span>
            <span
              style={{
                background: "linear-gradient(90deg, #a78bfa, #ec4899, #38bdf8)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              Bob
            </span>
            <span className="text-white/80 mx-0.5">·</span>
            <span className="text-white/80">AURA</span>
          </span>
        </span>
      </h1>

      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-1 shrink-0">
        History
      </h2>

      <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1">
        {loading && (
          <p className="text-xs text-gray-400 text-center py-4">Loading...</p>
        )}

        {!loading && history.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">No searches yet</p>
        )}

        {history.map((item) => (
          <div
            key={item.id}
            className="bg-white rounded-lg border border-gray-200 p-2 cursor-pointer hover:shadow-md transition-shadow group"
            onClick={() => handleItemClick(item)}
          >
            <div className="flex items-center gap-2">
              {/* Thumbnail */}
              <div className="w-10 h-10 rounded-md overflow-hidden bg-gray-100 shrink-0">
                {item.image_thumbnail ? (
                  <img
                    src={item.image_thumbnail}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
                    🖼
                  </div>
                )}
              </div>

              {/* Alias and date */}
              <div className="flex-1 min-w-0">
                {editingId === item.id ? (
                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      className="text-sm font-medium text-gray-800 border border-blue-300 rounded px-2 py-1 w-full outline-none focus:ring-2 focus:ring-blue-400"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleAliasSave(item.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                    />
                    <button
                      onClick={() => handleAliasSave(item.id)}
                      className="px-3 py-1.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-sm"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-2 py-1.5 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <div
                    className="text-xs font-medium text-gray-800 truncate"
                    onDoubleClick={(e) => {
                      e.stopPropagation();
                      setEditingId(item.id);
                      setEditValue(item.alias);
                    }}
                    title="Double-click to edit"
                  >
                    {item.alias}
                  </div>
                )}
                <p className="text-xs text-gray-400 truncate mt-0.5">
                  {formatDate(item.created_at)}
                </p>
              </div>

              {/* Edit button */}
              {editingId !== item.id && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingId(item.id);
                    setEditValue(item.alias);
                  }}
                  className="opacity-0 group-hover:opacity-100 text-xs text-gray-400 hover:text-blue-600 transition-all shrink-0"
                  title="Edit alias"
                >
                  ✏️
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

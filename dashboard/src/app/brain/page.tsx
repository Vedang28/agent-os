"use client";

import { useEffect, useState } from "react";
import NoteViewer from "@/components/NoteViewer";
import SearchBar from "@/components/SearchBar";
import { getBrainNotes, searchBrain } from "@/lib/api";
import type { NoteInfo } from "@/lib/types";

export default function BrainPage() {
  const [notes, setNotes] = useState<NoteInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [searchResults, setSearchResults] = useState<NoteInfo[] | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNote, setSelectedNote] = useState<NoteInfo | null>(null);

  useEffect(() => {
    getBrainNotes()
      .then((res) => {
        setNotes(res.notes);
        setTotal(res.total);
      })
      .catch(() => {});
  }, []);

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    try {
      const res = await searchBrain(query);
      setSearchResults(res.results);
    } catch {
      setSearchResults([]);
    }
  };

  const clearSearch = () => {
    setSearchResults(null);
    setSearchQuery("");
  };

  const displayNotes = searchResults ?? notes;

  return (
    <div className="h-full flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Brain Browser</h1>

      <SearchBar onSearch={handleSearch} />

      {searchQuery && (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <span>Results for &ldquo;{searchQuery}&rdquo;</span>
          <button onClick={clearSearch} className="text-blue-400 hover:underline">
            Clear
          </button>
        </div>
      )}

      <div className="flex-1 grid grid-cols-3 gap-6 min-h-0">
        <div className="col-span-1 overflow-auto space-y-1">
          <div className="text-sm text-gray-500 mb-2">{total} notes total</div>
          {displayNotes.map((note) => (
            <button
              key={note.title}
              onClick={() => setSelectedNote(note)}
              className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                selectedNote?.title === note.title
                  ? "bg-blue-900 text-white"
                  : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              <div className="truncate">{note.title}</div>
              {note.tags.length > 0 && (
                <div className="text-xs text-gray-600 truncate">
                  {note.tags.join(", ")}
                </div>
              )}
            </button>
          ))}
        </div>

        <div className="col-span-2">
          {selectedNote ? (
            <NoteViewer note={selectedNote} />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-600">
              Select a note to view
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

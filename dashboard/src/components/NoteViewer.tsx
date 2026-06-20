import type { NoteInfo } from "@/lib/types";

export default function NoteViewer({ note }: { note: NoteInfo }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h3 className="text-white font-semibold text-lg">{note.title}</h3>
      {note.tags.length > 0 && (
        <div className="flex gap-1 mt-2">
          {note.tags.map((tag) => (
            <span
              key={tag}
              className="bg-gray-700 text-gray-300 px-2 py-0.5 rounded text-xs"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
      <div className="mt-3 text-gray-300 text-sm whitespace-pre-wrap font-mono">
        {note.content}
      </div>
      {note.created_at && (
        <div className="mt-3 text-gray-500 text-xs">
          {new Date(note.created_at).toLocaleString()}
        </div>
      )}
    </div>
  );
}

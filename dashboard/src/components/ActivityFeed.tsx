"use client";

import { useEffect, useRef, useState } from "react";
import type { AgentEvent } from "@/lib/types";
import { AgentWebSocket } from "@/lib/ws";

const MAX_EVENTS = 100;

const TYPE_COLORS: Record<string, string> = {
  department_active: "bg-blue-600",
  task_complete: "bg-green-600",
  approval_request: "bg-yellow-600",
  kill_switch: "bg-red-600",
  tick_start: "bg-purple-600",
  tick_complete: "bg-purple-500",
  voice_request: "bg-cyan-600",
  voice_ack: "bg-cyan-500",
  voice_result: "bg-cyan-400",
  request_submitted: "bg-indigo-600",
};

export default function ActivityFeed() {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const wsRef = useRef<AgentWebSocket | null>(null);

  useEffect(() => {
    const ws = new AgentWebSocket();
    wsRef.current = ws;

    ws.onEvent((event) => {
      setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
    });

    ws.connect();
    return () => ws.disconnect();
  }, []);

  return (
    <div className="bg-gray-900 rounded-lg p-4 h-full overflow-auto">
      <h2 className="text-lg font-semibold text-white mb-3">Activity Feed</h2>
      {events.length === 0 ? (
        <p className="text-gray-500 text-sm">No events yet. Waiting for activity...</p>
      ) : (
        <ul className="space-y-2">
          {events.map((event, i) => (
            <li key={`${event.timestamp}-${i}`} className="flex items-start gap-2 text-sm">
              <span
                className={`${TYPE_COLORS[event.type] || "bg-gray-600"} text-white px-2 py-0.5 rounded text-xs font-mono shrink-0`}
              >
                {event.type}
              </span>
              <span className="text-gray-300 truncate">
                {Object.entries(event.data)
                  .map(([k, v]) => `${k}=${v}`)
                  .join(" ")}
              </span>
              <span className="text-gray-600 text-xs ml-auto shrink-0">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

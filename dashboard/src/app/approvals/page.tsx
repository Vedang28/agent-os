"use client";

import { useEffect, useRef, useState } from "react";
import ApprovalCard from "@/components/ApprovalCard";
import { AgentWebSocket } from "@/lib/ws";
import type { AgentEvent } from "@/lib/types";

export default function ApprovalsPage() {
  const [pending, setPending] = useState<AgentEvent[]>([]);
  const wsRef = useRef<AgentWebSocket | null>(null);

  useEffect(() => {
    const ws = new AgentWebSocket();
    wsRef.current = ws;

    ws.onEvent((event) => {
      if (event.type === "approval_request" && !event.data.approved) {
        setPending((prev) => [event, ...prev]);
      }
    });

    ws.connect();
    return () => ws.disconnect();
  }, []);

  const handleResolved = (index: number) => {
    setPending((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="h-full flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Approval Queue</h1>

      {pending.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          No pending approvals. Listening for new requests...
        </div>
      ) : (
        <div className="space-y-3">
          {pending.map((event, i) => (
            <ApprovalCard
              key={`${event.timestamp}-${i}`}
              event={event}
              onResolved={() => handleResolved(i)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

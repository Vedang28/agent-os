"use client";

import { approveAction } from "@/lib/api";
import type { AgentEvent } from "@/lib/types";

export default function ApprovalCard({
  event,
  onResolved,
}: {
  event: AgentEvent;
  onResolved: () => void;
}) {
  const action = (event.data.action as string) || "Unknown action";
  const taskId = (event.data.task_id as string) || "";

  const handleAction = async (approved: boolean) => {
    if (!taskId) return;
    try {
      await approveAction(taskId, approved);
      onResolved();
    } catch {
      // handle error
    }
  };

  return (
    <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-4">
      <div className="text-yellow-300 font-semibold text-sm">{action}</div>
      {event.data.details != null && (
        <div className="text-gray-400 text-xs mt-1 font-mono">
          {JSON.stringify(event.data.details) as string}
        </div>
      )}
      <div className="text-gray-500 text-xs mt-1">
        {new Date(event.timestamp).toLocaleString()}
      </div>
      <div className="flex gap-2 mt-3">
        <button
          onClick={() => handleAction(true)}
          className="bg-green-700 text-white px-3 py-1 rounded text-sm hover:bg-green-600"
        >
          Approve
        </button>
        <button
          onClick={() => handleAction(false)}
          className="bg-red-700 text-white px-3 py-1 rounded text-sm hover:bg-red-600"
        >
          Reject
        </button>
      </div>
    </div>
  );
}

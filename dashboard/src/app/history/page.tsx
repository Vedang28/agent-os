"use client";

import { useEffect, useState } from "react";
import { getHistory } from "@/lib/api";
import type { HistoryItem } from "@/lib/types";

export default function HistoryPage() {
  const [tasks, setTasks] = useState<HistoryItem[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    getHistory(filter || undefined)
      .then((res) => setTasks(res.tasks))
      .catch(() => {});
  }, [filter]);

  return (
    <div className="h-full flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Task History</h1>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1 text-sm text-gray-300"
        >
          <option value="">All departments</option>
          <option value="engineering">Engineering</option>
          <option value="intelligence">Intelligence</option>
        </select>
      </div>

      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-800">
              <th className="py-2 px-3">Task ID</th>
              <th className="py-2 px-3">Department</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3">Revisions</th>
              <th className="py-2 px-3">Tokens</th>
              <th className="py-2 px-3">Time</th>
              <th className="py-2 px-3">Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => (
              <tr key={task.task_id} className="border-b border-gray-900 hover:bg-gray-900/50">
                <td className="py-2 px-3 font-mono text-xs text-gray-400">
                  {task.task_id.slice(0, 8)}
                </td>
                <td className="py-2 px-3">{task.department}</td>
                <td className="py-2 px-3">
                  <span
                    className={`px-2 py-0.5 rounded text-xs ${
                      task.success
                        ? "bg-green-900 text-green-300"
                        : "bg-red-900 text-red-300"
                    }`}
                  >
                    {task.success ? "success" : "failed"}
                  </span>
                </td>
                <td className="py-2 px-3">{task.revisions}</td>
                <td className="py-2 px-3">{task.tokens_used.toLocaleString()}</td>
                <td className="py-2 px-3">{task.wall_clock_seconds.toFixed(1)}s</td>
                <td className="py-2 px-3 text-gray-500 text-xs">
                  {task.timestamp ? new Date(task.timestamp).toLocaleString() : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {tasks.length === 0 && (
          <p className="text-gray-500 text-center py-8">No tasks found</p>
        )}
      </div>
    </div>
  );
}

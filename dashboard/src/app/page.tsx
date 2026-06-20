"use client";

import { useEffect, useState } from "react";
import ActivityFeed from "@/components/ActivityFeed";
import AgentCard from "@/components/AgentCard";
import { getAgents, getStatus, submitRequest } from "@/lib/api";
import type { AgentInfo, StatusInfo } from "@/lib/types";

export default function DashboardPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [status, setStatus] = useState<StatusInfo | null>(null);
  const [request, setRequest] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getAgents().then(setAgents).catch(() => {});
    getStatus().then(setStatus).catch(() => {});

    const interval = setInterval(() => {
      getStatus().then(setStatus).catch(() => {});
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!request.trim() || submitting) return;
    setSubmitting(true);
    try {
      await submitRequest(request.trim());
      setRequest("");
    } catch {
      // handle error
    }
    setSubmitting(false);
  };

  return (
    <div className="h-full flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        {status && (
          <div className="flex gap-4 text-sm text-gray-400">
            <span>
              Daemon:{" "}
              <span className={status.daemon === "running" ? "text-green-400" : "text-red-400"}>
                {status.daemon}
              </span>
            </span>
            <span>Ticks: {status.tick_count}</span>
            <span>Agents: {status.agents_registered}</span>
            <span>Tools: {status.tools_registered}</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder="Submit a request to the company..."
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          disabled={submitting}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Sending..." : "Send"}
        </button>
      </form>

      <div className="flex-1 grid grid-cols-3 gap-6 min-h-0">
        <div className="col-span-2">
          <ActivityFeed />
        </div>
        <div className="space-y-4 overflow-auto">
          <h2 className="text-lg font-semibold">Agents</h2>
          {agents.length === 0 ? (
            <p className="text-gray-500 text-sm">No agents registered</p>
          ) : (
            <div className="grid gap-2">
              {agents.map((agent) => (
                <AgentCard key={agent.name} agent={agent} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

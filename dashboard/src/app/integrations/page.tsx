"use client";

import { useEffect, useState } from "react";
import {
  connectIntegration,
  disconnectIntegration,
  getIntegrations,
  getIntegrationTools,
} from "@/lib/api";
import type { IntegrationInfo, IntegrationToolInfo } from "@/lib/types";

const PERMISSION_COLORS: Record<string, string> = {
  read: "bg-green-900 text-green-300",
  write: "bg-blue-900 text-blue-300",
  shell: "bg-yellow-900 text-yellow-300",
  destructive: "bg-red-900 text-red-300",
};

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<IntegrationInfo[]>([]);
  const [tools, setTools] = useState<IntegrationToolInfo[]>([]);
  const [loading, setLoading] = useState("");

  const load = () => {
    getIntegrations()
      .then((res) => setIntegrations(res.integrations))
      .catch(() => {});
    getIntegrationTools()
      .then(setTools)
      .catch(() => {});
  };

  useEffect(load, []);

  const handleConnect = async (appName: string) => {
    setLoading(appName);
    try {
      const result = await connectIntegration(appName);
      if (result.auth_url) {
        window.open(result.auth_url, "_blank");
      }
      load();
    } catch {
      // handle error
    }
    setLoading("");
  };

  const handleDisconnect = async (appName: string) => {
    setLoading(appName);
    try {
      await disconnectIntegration(appName);
      load();
    } catch {
      // handle error
    }
    setLoading("");
  };

  return (
    <div className="h-full flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Integrations</h1>

      <div className="grid grid-cols-2 gap-4">
        {integrations.map((int) => (
          <div
            key={`${int.type}-${int.name}`}
            className="bg-gray-900 border border-gray-800 rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="text-white font-semibold capitalize">
                  {int.name}
                </span>
                <span className="text-gray-500 text-xs ml-2">{int.type}</span>
              </div>
              <span
                className={`text-xs px-2 py-0.5 rounded ${
                  int.connected
                    ? "bg-green-900 text-green-300"
                    : "bg-gray-800 text-gray-500"
                }`}
              >
                {int.connected ? "Connected" : "Not connected"}
              </span>
            </div>
            <div className="text-gray-400 text-sm mb-3">
              {int.tools_count} tools available
            </div>
            {int.type === "composio" && (
              <button
                onClick={() =>
                  int.connected
                    ? handleDisconnect(int.name)
                    : handleConnect(int.name)
                }
                disabled={loading === int.name}
                className={`text-sm px-3 py-1 rounded ${
                  int.connected
                    ? "bg-red-900 text-red-300 hover:bg-red-800"
                    : "bg-blue-700 text-white hover:bg-blue-600"
                } disabled:opacity-50`}
              >
                {loading === int.name
                  ? "..."
                  : int.connected
                  ? "Disconnect"
                  : "Connect"}
              </button>
            )}
          </div>
        ))}
        {integrations.length === 0 && (
          <p className="text-gray-500 col-span-2">
            No integrations configured. Set COMPOSIO_API_KEY to enable.
          </p>
        )}
      </div>

      <h2 className="text-lg font-semibold mt-4">Integration Tools</h2>
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-800">
              <th className="py-2 px-3">Tool Name</th>
              <th className="py-2 px-3">Integration</th>
              <th className="py-2 px-3">Permission</th>
            </tr>
          </thead>
          <tbody>
            {tools.map((tool) => (
              <tr
                key={tool.name}
                className="border-b border-gray-900 hover:bg-gray-900/50"
              >
                <td className="py-2 px-3 font-mono text-xs text-gray-300">
                  {tool.name}
                </td>
                <td className="py-2 px-3 capitalize">{tool.integration}</td>
                <td className="py-2 px-3">
                  <span
                    className={`px-2 py-0.5 rounded text-xs ${
                      PERMISSION_COLORS[tool.permission] || "bg-gray-800 text-gray-400"
                    }`}
                  >
                    {tool.permission}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {tools.length === 0 && (
          <p className="text-gray-500 text-center py-4">
            No integration tools registered
          </p>
        )}
      </div>
    </div>
  );
}

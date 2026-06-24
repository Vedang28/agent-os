"use client";

import { useEffect, useState } from "react";
import { getCosts } from "@/lib/api";
import type { CostSummary } from "@/lib/types";

export default function CostsPage() {
  const [costs, setCosts] = useState<CostSummary | null>(null);

  useEffect(() => {
    getCosts()
      .then(setCosts)
      .catch(() => {});
  }, []);

  if (!costs) {
    return <p className="text-gray-500">Loading costs...</p>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Cost Dashboard</h1>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded p-4">
          <div className="text-sm text-gray-400">Total Cost</div>
          <div className="text-2xl font-bold">${costs.total_cost_usd.toFixed(4)}</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded p-4">
          <div className="text-sm text-gray-400">Total Tokens</div>
          <div className="text-2xl font-bold">{costs.total_tokens.toLocaleString()}</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded p-4">
          <div className="text-sm text-gray-400">Burn Rate</div>
          <div className="text-2xl font-bold">${costs.burn_rate_per_hour.toFixed(4)}/hr</div>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded p-4">
        <h2 className="text-lg font-bold mb-3">Cost by Department</h2>
        {Object.keys(costs.by_department).length === 0 ? (
          <p className="text-gray-500">No department costs recorded yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2">Department</th>
                <th className="text-right py-2">Cost (USD)</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(costs.by_department)
                .sort(([, a], [, b]) => b - a)
                .map(([dept, cost]) => (
                  <tr key={dept} className="border-b border-gray-800/50">
                    <td className="py-2">{dept}</td>
                    <td className="text-right py-2">${cost.toFixed(4)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded p-4">
        <h2 className="text-lg font-bold mb-3">Cost by Model</h2>
        {Object.keys(costs.by_model).length === 0 ? (
          <p className="text-gray-500">No model costs recorded yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="text-left py-2">Model</th>
                <th className="text-right py-2">Cost (USD)</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(costs.by_model)
                .sort(([, a], [, b]) => b - a)
                .map(([model, cost]) => (
                  <tr key={model} className="border-b border-gray-800/50">
                    <td className="py-2">{model}</td>
                    <td className="text-right py-2">${cost.toFixed(4)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

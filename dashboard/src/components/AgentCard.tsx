import type { AgentInfo } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  idle: "bg-green-900 text-green-300 border-green-700",
  active: "bg-yellow-900 text-yellow-300 border-yellow-700",
  error: "bg-red-900 text-red-300 border-red-700",
};

export default function AgentCard({ agent }: { agent: AgentInfo }) {
  const style = STATUS_STYLES[agent.status] || STATUS_STYLES.idle;

  return (
    <div className={`rounded-lg border p-3 ${style}`}>
      <div className="font-mono text-sm font-semibold">{agent.name}</div>
      {agent.department && (
        <div className="text-xs opacity-75 mt-1">{agent.department}</div>
      )}
      <div className="text-xs mt-2 uppercase tracking-wide">{agent.status}</div>
    </div>
  );
}

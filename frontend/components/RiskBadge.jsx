const STYLES = {
  High: "bg-red-50 text-red-700 ring-red-600/20",
  Medium: "bg-amber-50 text-amber-700 ring-amber-600/20",
  Low: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
};

export default function RiskBadge({ tier }) {
  const cls = STYLES[tier] || "bg-slate-100 text-slate-600 ring-slate-500/20";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${cls}`}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{
          background:
            tier === "High" ? "#ef4444" : tier === "Medium" ? "#f59e0b" : "#10b981",
        }}
      />
      {tier}
    </span>
  );
}

export default function KPICard({ label, value, sub, trend, accent = "slate", icon }) {
  const accentBar = {
    red: "bg-red-500",
    amber: "bg-amber-500",
    emerald: "bg-emerald-500",
    brand: "bg-brand-600",
    slate: "bg-slate-400",
  }[accent];

  const trendUp = trend > 0;
  const trendDown = trend < 0;

  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <span className={`absolute left-0 top-0 h-full w-1 ${accentBar}`} />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
            {value}
          </p>
        </div>
        {icon && (
          <div className="rounded-lg bg-slate-50 p-2 text-slate-400">{icon}</div>
        )}
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs">
        {trend !== undefined && trend !== null && (
          <span
            className={`inline-flex items-center gap-0.5 font-medium ${
              trendUp ? "text-red-600" : trendDown ? "text-emerald-600" : "text-slate-500"
            }`}
          >
            {trendUp ? "▲" : trendDown ? "▼" : "—"} {Math.abs(trend)}
          </span>
        )}
        {sub && <span className="text-slate-400">{sub}</span>}
      </div>
    </div>
  );
}

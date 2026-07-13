"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const RISK_COLORS = { High: "#ef4444", Medium: "#f59e0b", Low: "#10b981" };

export function RiskDonut({ high, medium, low }) {
  const data = [
    { name: "High", value: high },
    { name: "Medium", value: medium },
    { name: "Low", value: low },
  ];
  const total = high + medium + low || 1;
  return (
    <div className="relative h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={70}
            outerRadius={100}
            paddingAngle={2}
            stroke="none"
          >
            {data.map((d) => (
              <Cell key={d.name} fill={RISK_COLORS[d.name]} />
            ))}
          </Pie>
          <Tooltip formatter={(v, n) => [`${v} customers`, n]} />
          <Legend verticalAlign="bottom" height={24} iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center pb-8">
        <span className="text-3xl font-semibold text-slate-900">{total.toLocaleString()}</span>
        <span className="text-xs text-slate-500">customers</span>
      </div>
    </div>
  );
}

export function TrendChart({ data }) {
  const rows = (data || []).map((d) => ({
    date: d.date.slice(5),
    avg: Math.round(d.avg_probability * 1000) / 10,
    high: d.high,
  }));
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={rows} margin={{ top: 10, right: 10, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="avgFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94a3b8" minTickGap={24} />
          <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" unit="%" />
          <Tooltip
            formatter={(v) => [`${v}%`, "Avg churn probability"]}
            labelFormatter={(l) => `Date: ${l}`}
          />
          <Area
            type="monotone"
            dataKey="avg"
            stroke="#2563eb"
            strokeWidth={2}
            fill="url(#avgFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ScoreHistoryChart({ data }) {
  const rows = (data || []).map((d) => ({
    date: new Date(d.scored_date).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    }),
    prob: Math.round(d.churn_probability * 1000) / 10,
  }));
  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={rows} margin={{ top: 10, right: 10, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="histFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94a3b8" minTickGap={20} />
          <YAxis tick={{ fontSize: 11 }} stroke="#94a3b8" unit="%" domain={[0, 100]} />
          <Tooltip formatter={(v) => [`${v}%`, "Churn probability"]} />
          <Area type="monotone" dataKey="prob" stroke="#ef4444" strokeWidth={2} fill="url(#histFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FeatureImportanceChart({ data }) {
  const rows = (data || []).slice(0, 12).map((d) => ({
    label: d.label,
    importance: Math.round(d.importance * 1000) / 10,
  }));
  return (
    <div style={{ height: Math.max(240, rows.length * 34) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
        >
          <XAxis type="number" tick={{ fontSize: 11 }} stroke="#94a3b8" unit="%" />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fontSize: 12 }}
            stroke="#94a3b8"
            width={130}
          />
          <Tooltip formatter={(v) => [`${v}%`, "Importance"]} />
          <Bar dataKey="importance" fill="#2563eb" radius={[0, 4, 4, 0]} barSize={16} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

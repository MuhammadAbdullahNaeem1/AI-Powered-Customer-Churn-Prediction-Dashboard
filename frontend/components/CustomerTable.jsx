"use client";

import { useRouter } from "next/navigation";
import RiskBadge from "./RiskBadge";
import { fmtDate } from "@/lib/api";

function ScoreBar({ value }) {
  const pct = Math.round((value || 0) * 100);
  const color = pct >= 60 ? "#ef4444" : pct >= 30 ? "#f59e0b" : "#10b981";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="tabular-nums text-sm font-medium text-slate-700">{pct}%</span>
    </div>
  );
}

const COLUMNS = [
  { key: "name", label: "Customer", sortable: true },
  { key: "tenure", label: "Tenure", sortable: true },
  { key: "contract", label: "Contract", sortable: false },
  { key: "monthly_charges", label: "Monthly", sortable: true },
  { key: "churn_probability", label: "Churn score", sortable: true },
  { key: "risk_tier", label: "Risk", sortable: true },
  { key: "last_scored", label: "Last scored", sortable: true },
];

export default function CustomerTable({ items, sort, order, onSort }) {
  const router = useRouter();

  const arrow = (key) =>
    sort === key ? (order === "desc" ? " ▼" : " ▲") : "";

  return (
    <div className="overflow-x-auto scroll-thin">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            {COLUMNS.map((c) => (
              <th
                key={c.key}
                className={`px-4 py-3 ${c.sortable ? "cursor-pointer select-none hover:text-slate-800" : ""}`}
                onClick={() => c.sortable && onSort && onSort(c.key)}
              >
                {c.label}
                {c.sortable && arrow(c.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((c) => (
            <tr
              key={c.id}
              onClick={() => router.push(`/customers/${c.id}`)}
              className="cursor-pointer transition hover:bg-slate-50"
            >
              <td className="px-4 py-3">
                <div className="font-medium text-slate-900">{c.name}</div>
                <div className="text-xs text-slate-400">{c.id}</div>
              </td>
              <td className="px-4 py-3 text-slate-600">{c.tenure} mo</td>
              <td className="px-4 py-3 text-slate-600">{c.contract}</td>
              <td className="px-4 py-3 tabular-nums text-slate-600">
                ${c.monthly_charges?.toFixed(2)}
              </td>
              <td className="px-4 py-3">
                <ScoreBar value={c.churn_probability} />
              </td>
              <td className="px-4 py-3">
                <RiskBadge tier={c.risk_tier} />
              </td>
              <td className="px-4 py-3 text-slate-500">{fmtDate(c.last_scored)}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={COLUMNS.length} className="px-4 py-10 text-center text-slate-400">
                No customers match your filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

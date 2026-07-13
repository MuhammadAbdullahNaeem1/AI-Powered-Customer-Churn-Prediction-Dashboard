"use client";

import Link from "next/link";
import RiskBadge from "./RiskBadge";
import { fmtDate } from "@/lib/api";

const STATUS_STYLES = {
  pending: "bg-slate-100 text-slate-700",
  actioned: "bg-emerald-100 text-emerald-700",
  dismissed: "bg-slate-100 text-slate-400 line-through",
};

export default function InterventionFeed({ items, onUpdate, compact = false }) {
  if (!items || items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">
        No interventions to show.
      </div>
    );
  }

  return (
    <ul className="divide-y divide-slate-100">
      {items.map((it) => (
        <li key={it.id} className="flex gap-3 py-3">
          <div
            className="mt-1 h-2 w-2 flex-shrink-0 rounded-full"
            style={{
              background:
                it.risk_tier === "High"
                  ? "#ef4444"
                  : it.risk_tier === "Medium"
                  ? "#f59e0b"
                  : "#10b981",
            }}
          />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href={`/customers/${it.customer_id}`}
                className="font-medium text-slate-900 hover:text-brand-700"
              >
                {it.customer_name || it.customer_id}
              </Link>
              <RiskBadge tier={it.risk_tier} />
              <span
                className={`rounded px-1.5 py-0.5 text-[11px] font-medium capitalize ${
                  STATUS_STYLES[it.status] || "bg-slate-100 text-slate-600"
                }`}
              >
                {it.status}
              </span>
              <span className="ml-auto text-xs text-slate-400">
                {fmtDate(it.triggered_date)}
              </span>
            </div>
            <p className="mt-0.5 text-sm font-medium text-slate-600">
              {it.intervention_type}
            </p>
            {!compact && (
              <p className="mt-0.5 text-sm text-slate-500">{it.recommendation}</p>
            )}
            {onUpdate && it.status === "pending" && (
              <div className="mt-2 flex gap-2">
                <button
                  onClick={() => onUpdate(it.id, "actioned")}
                  className="rounded-md bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-700"
                >
                  Mark actioned
                </button>
                <button
                  onClick={() => onUpdate(it.id, "dismissed")}
                  className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

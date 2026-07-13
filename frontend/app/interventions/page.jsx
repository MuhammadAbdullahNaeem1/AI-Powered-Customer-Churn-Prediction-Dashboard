"use client";

import { useCallback, useEffect, useState } from "react";
import { api, fmtNum } from "@/lib/api";
import InterventionFeed from "@/components/InterventionFeed";

const STATUSES = ["All", "pending", "actioned", "dismissed"];

export default function InterventionsPage() {
  const [items, setItems] = useState(null);
  const [status, setStatus] = useState("All");
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setItems(await api.interventions({ status, limit: 300 }));
    } catch (e) {
      setError(e.message);
    }
  }, [status]);

  useEffect(() => {
    load();
  }, [load]);

  async function onUpdate(id, newStatus) {
    await api.updateIntervention(id, newStatus);
    await load();
  }

  const counts = (items || []).reduce((acc, i) => {
    acc[i.status] = (acc[i.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Interventions</h1>
        <p className="text-sm text-slate-500">
          Retention actions triggered by the scoring pipeline
        </p>
      </div>

      <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize transition ${
              status === s ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>
      ) : !items ? (
        <div className="flex h-40 items-center justify-center text-slate-400">Loading…</div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-2 text-xs text-slate-400">
            Showing {fmtNum(items.length)} interventions
            {status === "All" &&
              ` · ${counts.pending || 0} pending, ${counts.actioned || 0} actioned, ${
                counts.dismissed || 0
              } dismissed`}
          </div>
          <InterventionFeed items={items} onUpdate={onUpdate} />
        </div>
      )}
    </div>
  );
}

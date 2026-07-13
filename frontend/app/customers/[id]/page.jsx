"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, fmtPct, fmtDate } from "@/lib/api";
import RiskBadge from "@/components/RiskBadge";
import { ScoreHistoryChart } from "@/components/ChurnChart";
import InterventionFeed from "@/components/InterventionFeed";

export default function CustomerDetailPage() {
  const { id } = useParams();
  const [c, setC] = useState(null);
  const [error, setError] = useState(null);
  const [triggering, setTriggering] = useState(false);

  async function load() {
    try {
      setC(await api.customer(id));
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  async function triggerIntervention() {
    setTriggering(true);
    try {
      await api.createIntervention(id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setTriggering(false);
    }
  }

  async function updateIntervention(iid, status) {
    await api.updateIntervention(iid, status);
    await load();
  }

  if (error)
    return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>;
  if (!c) return <div className="flex h-40 items-center justify-center text-slate-400">Loading…</div>;

  const pct = Math.round((c.churn_probability || 0) * 100);
  const ringColor = pct >= 60 ? "#ef4444" : pct >= 30 ? "#f59e0b" : "#10b981";

  const profile = [
    ["Tenure", `${c.tenure} months`],
    ["Contract", c.contract],
    ["Monthly charges", `$${c.monthly_charges?.toFixed(2)}`],
    ["Total charges", `$${c.total_charges?.toFixed(2)}`],
    ["Internet", c.internet_service],
    ["Payment method", c.payment_method],
    ["Tech support", c.tech_support],
    ["Online security", c.online_security],
    ["Paperless billing", c.paperless_billing],
    ["Senior citizen", c.senior_citizen ? "Yes" : "No"],
    ["Partner", c.partner],
    ["Dependents", c.dependents],
  ];

  return (
    <div className="space-y-6">
      <Link href="/customers" className="text-sm text-slate-500 hover:text-slate-800">
        ← Back to customers
      </Link>

      {/* Header */}
      <div className="flex flex-col gap-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-5">
          <div
            className="relative flex h-24 w-24 items-center justify-center rounded-full"
            style={{
              background: `conic-gradient(${ringColor} ${pct * 3.6}deg, #e2e8f0 0deg)`,
            }}
          >
            <div className="flex h-[76px] w-[76px] flex-col items-center justify-center rounded-full bg-white">
              <span className="text-2xl font-bold text-slate-900">{pct}%</span>
              <span className="text-[10px] uppercase tracking-wide text-slate-400">churn</span>
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">{c.name}</h1>
            <p className="text-sm text-slate-400">{c.id}</p>
            <div className="mt-2 flex items-center gap-2">
              <RiskBadge tier={c.risk_tier} />
              <span className="text-xs text-slate-400">
                Last scored {fmtDate(c.last_scored)}
              </span>
            </div>
          </div>
        </div>
        <button
          onClick={triggerIntervention}
          disabled={triggering}
          className="inline-flex items-center gap-2 self-start rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-60 sm:self-center"
        >
          {triggering ? "Creating…" : "Trigger intervention"}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Churn drivers */}
        <Card title="What's driving this risk" className="lg:col-span-2">
          <p className="mb-3 text-xs text-slate-400">
            Per-customer feature contributions (SHAP). Red pushes churn up, green pulls it down.
          </p>
          <ul className="space-y-2">
            {c.feature_contributions.map((f) => {
              const up = f.impact > 0;
              const mag = Math.min(100, Math.abs(f.impact) * 45);
              return (
                <li key={f.feature} className="flex items-center gap-3">
                  <span className="w-40 flex-shrink-0 text-sm text-slate-600">{f.label}</span>
                  <div className="flex flex-1 items-center">
                    <div className="flex w-1/2 justify-end">
                      {!up && (
                        <div className="h-3 rounded-l bg-emerald-400" style={{ width: `${mag}%` }} />
                      )}
                    </div>
                    <div className="h-4 w-px bg-slate-300" />
                    <div className="flex w-1/2 justify-start">
                      {up && (
                        <div className="h-3 rounded-r bg-red-400" style={{ width: `${mag}%` }} />
                      )}
                    </div>
                  </div>
                  <span
                    className={`w-14 text-right text-xs font-medium tabular-nums ${
                      up ? "text-red-600" : "text-emerald-600"
                    }`}
                  >
                    {up ? "+" : ""}
                    {f.impact.toFixed(2)}
                  </span>
                </li>
              );
            })}
          </ul>
        </Card>

        {/* Current recommendation */}
        <Card title="Recommended action" className="lg:col-span-1">
          {c.current_recommendation ? (
            <div className="space-y-2">
              <p className="font-medium text-slate-900">
                {c.current_recommendation.intervention_type}
              </p>
              <p className="text-sm text-slate-600">
                {c.current_recommendation.recommendation}
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              Low risk — monitor only, no action needed.
            </p>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card title="Churn score history" className="lg:col-span-2">
          <ScoreHistoryChart data={c.score_history} />
        </Card>
        <Card title="Customer profile" className="lg:col-span-1">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            {profile.map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs text-slate-400">{k}</dt>
                <dd className="font-medium text-slate-700">{v || "—"}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>

      <Card title="Intervention history">
        <InterventionFeed items={c.interventions} onUpdate={updateIntervention} />
      </Card>
    </div>
  );
}

function Card({ title, children, className = "" }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      <h2 className="mb-4 text-sm font-semibold text-slate-800">{title}</h2>
      {children}
    </section>
  );
}

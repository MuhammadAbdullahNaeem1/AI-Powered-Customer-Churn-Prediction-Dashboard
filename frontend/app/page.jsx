"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, fmtPct, fmtNum, fmtDate } from "@/lib/api";
import KPICard from "@/components/KPICard";
import { RiskDonut, TrendChart } from "@/components/ChurnChart";
import CustomerTable from "@/components/CustomerTable";
import InterventionFeed from "@/components/InterventionFeed";

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [trend, setTrend] = useState([]);
  const [topCustomers, setTopCustomers] = useState([]);
  const [interventions, setInterventions] = useState([]);
  const [error, setError] = useState(null);
  const [scoring, setScoring] = useState(false);

  async function load() {
    try {
      const [s, t, c, i] = await Promise.all([
        api.dashboardSummary(),
        api.dashboardTrend(30),
        api.customers({ page_size: 10, sort: "churn_probability", order: "desc" }),
        api.interventions({ limit: 8 }),
      ]);
      setSummary(s);
      setTrend(t);
      setTopCustomers(c.items);
      setInterventions(i);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function runScoring() {
    setScoring(true);
    try {
      await api.runScoring();
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setScoring(false);
    }
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        Failed to load dashboard: {error}
        <p className="mt-1 text-sm text-red-500">
          Is the backend running on {api.base}?
        </p>
      </div>
    );
  }

  if (!summary) return <LoadingScreen />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">
            Last scored {fmtDate(summary.last_scored)} · model {summary.model_version || "—"}
          </p>
        </div>
        <button
          onClick={runScoring}
          disabled={scoring}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-60"
        >
          {scoring ? "Scoring…" : "Run scoring now"}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KPICard
          label="Total customers"
          value={fmtNum(summary.total_customers)}
          accent="brand"
          sub="in portfolio"
        />
        <KPICard
          label="High risk"
          value={fmtNum(summary.high_risk)}
          accent="red"
          trend={summary.high_risk_trend}
          sub="vs last week"
        />
        <KPICard
          label="Medium risk"
          value={fmtNum(summary.medium_risk)}
          accent="amber"
          sub="watch closely"
        />
        <KPICard
          label="Avg churn probability"
          value={fmtPct(summary.avg_churn_probability, 1)}
          accent="slate"
          trend={
            summary.avg_prob_trend !== null && summary.avg_prob_trend !== undefined
              ? Math.round(summary.avg_prob_trend * 1000) / 10
              : undefined
          }
          sub="pts vs last week"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card title="Risk distribution" className="lg:col-span-1">
          <RiskDonut
            high={summary.high_risk}
            medium={summary.medium_risk}
            low={summary.low_risk}
          />
        </Card>
        <Card title="Avg churn probability — last 30 days" className="lg:col-span-2">
          <TrendChart data={trend} />
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card
          title="Top 10 highest-risk customers"
          className="lg:col-span-2"
          action={
            <Link href="/customers" className="text-sm font-medium text-brand-700 hover:underline">
              View all →
            </Link>
          }
        >
          <CustomerTable items={topCustomers} sort="churn_probability" order="desc" />
        </Card>
        <Card
          title="Recent interventions"
          className="lg:col-span-1"
          action={
            <Link href="/interventions" className="text-sm font-medium text-brand-700 hover:underline">
              All →
            </Link>
          }
        >
          <InterventionFeed items={interventions} compact />
        </Card>
      </div>
    </div>
  );
}

function Card({ title, action, children, className = "" }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function LoadingScreen() {
  return (
    <div className="flex h-64 items-center justify-center text-slate-400">
      <div className="animate-pulse text-sm">Loading dashboard…</div>
    </div>
  );
}

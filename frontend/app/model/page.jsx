"use client";

import { useEffect, useState } from "react";
import { api, fmtPct, fmtDate, fmtNum } from "@/lib/api";
import { FeatureImportanceChart } from "@/components/ChurnChart";

export default function ModelPage() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [toast, setToast] = useState(null);

  async function load() {
    try {
      setMetrics(await api.modelMetrics());
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function retrain() {
    setConfirmOpen(false);
    setRetraining(true);
    setToast(null);
    try {
      const res = await api.retrain();
      await load();
      setToast(
        `Retrained ${res.training.version} — ROC-AUC ${res.training.metrics.roc_auc}. Re-scored ${res.scoring.total_scored} customers.`
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setRetraining(false);
    }
  }

  if (error)
    return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>;
  if (!metrics) return <div className="flex h-40 items-center justify-center text-slate-400">Loading…</div>;

  const cards = [
    { label: "ROC-AUC", value: metrics.roc_auc?.toFixed(3), hint: "Ranking quality", accent: "brand" },
    { label: "F1 score", value: metrics.f1?.toFixed(3), hint: "Balance of P/R", accent: "emerald" },
    { label: "Precision", value: fmtPct(metrics.precision, 1), hint: "Of flagged, % correct", accent: "amber" },
    { label: "Recall", value: fmtPct(metrics.recall, 1), hint: "Of churners, % caught", accent: "red" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Model performance</h1>
          <p className="text-sm text-slate-500">
            Version {metrics.model_version || "—"} · trained {fmtDate(metrics.training_date)}
            {metrics.accuracy ? ` · accuracy ${fmtPct(metrics.accuracy, 1)}` : ""}
          </p>
        </div>
        <button
          onClick={() => setConfirmOpen(true)}
          disabled={retraining}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-60"
        >
          {retraining ? "Retraining…" : "Retrain model"}
        </button>
      </div>

      {toast && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
          {toast}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">{c.label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">{c.value ?? "—"}</p>
            <p className="mt-1 text-xs text-slate-400">{c.hint}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
          <h2 className="mb-4 text-sm font-semibold text-slate-800">
            Feature importance (global)
          </h2>
          <FeatureImportanceChart data={metrics.feature_importances} />
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-1">
          <h2 className="mb-4 text-sm font-semibold text-slate-800">Training details</h2>
          <dl className="space-y-3 text-sm">
            <Row k="Model version" v={metrics.model_version} />
            <Row k="Trained on" v={fmtDate(metrics.training_date)} />
            <Row k="Train samples" v={fmtNum(metrics.n_train)} />
            <Row k="Test samples" v={fmtNum(metrics.n_test)} />
            <Row k="Algorithm" v="XGBoost (gradient boosting)" />
            <Row k="Accuracy" v={fmtPct(metrics.accuracy, 1)} />
          </dl>
        </section>
      </div>

      {confirmOpen && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900">Retrain the model?</h3>
            <p className="mt-2 text-sm text-slate-600">
              This retrains the XGBoost classifier on the full dataset and re-scores every
              customer. It may take a few seconds and will replace the current model version.
            </p>
            <div className="mt-5 flex justify-end gap-3">
              <button
                onClick={() => setConfirmOpen(false)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={retrain}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              >
                Yes, retrain
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ k, v }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-slate-400">{k}</dt>
      <dd className="font-medium text-slate-700">{v || "—"}</dd>
    </div>
  );
}

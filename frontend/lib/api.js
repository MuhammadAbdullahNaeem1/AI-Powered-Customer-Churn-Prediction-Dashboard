const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8020";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  base: API_BASE,
  dashboardSummary: () => request("/api/dashboard/summary"),
  dashboardTrend: (days = 30) => request(`/api/dashboard/trend?days=${days}`),
  customers: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== "" && v !== null)
    ).toString();
    return request(`/api/customers?${qs}`);
  },
  customer: (id) => request(`/api/customers/${encodeURIComponent(id)}`),
  interventions: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== "" && v !== null)
    ).toString();
    return request(`/api/interventions?${qs}`);
  },
  updateIntervention: (id, status) =>
    request(`/api/interventions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  createIntervention: (customerId) =>
    request(`/api/customers/${encodeURIComponent(customerId)}/interventions`, {
      method: "POST",
    }),
  modelMetrics: () => request("/api/model/metrics"),
  retrain: () => request("/api/model/retrain", { method: "POST" }),
  runScoring: () => request("/api/scoring/run", { method: "POST" }),
};

export function fmtPct(x, digits = 0) {
  if (x === null || x === undefined) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

export function fmtNum(x) {
  if (x === null || x === undefined) return "—";
  return x.toLocaleString();
}

export function fmtDate(x) {
  if (!x) return "—";
  return new Date(x).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function tierColor(tier) {
  return { High: "#ef4444", Medium: "#f59e0b", Low: "#10b981" }[tier] || "#64748b";
}

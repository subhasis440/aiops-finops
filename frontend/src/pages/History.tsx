import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";

type HistoryItem = {
  id: string;
  cloud_provider: string;
  scope: string;
  resources_scanned: number;
  issues_found: number;
  estimated_savings: string;
  status: string;
  created_at: string;
};

type HistoryResponse = {
  analyses: HistoryItem[];
};

function statusClass(status: string): string {
  if (status === "complete") {
    return "bg-emerald-300/20 text-emerald-100";
  }
  if (status === "failed") {
    return "bg-red-300/20 text-red-100";
  }
  return "bg-amber-300/20 text-amber-100";
}

export default function History() {
  const navigate = useNavigate();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get<HistoryResponse>("/api/history");
        if (mounted) {
          setItems(response.data.analyses ?? []);
        }
      } catch (err: unknown) {
        if (mounted) {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          setError(detail ?? "Unable to load analysis history.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchHistory();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="page-shell">
      <section className="glass rounded-3xl p-6 shadow-card animate-floatin">
        <div className="flex items-center justify-between gap-3">
          <h1 className="section-title">Analysis History</h1>
          <button className="btn btn-brand" onClick={() => navigate("/dashboard")}>New Analysis</button>
        </div>

        {loading ? <p className="mt-4 text-sm text-slate-300">Loading history...</p> : null}
        {error ? <p className="mt-4 text-sm text-red-200">{error}</p> : null}

        {!loading && !error && items.length === 0 ? (
          <p className="mt-4 text-sm text-slate-300">No analysis records yet.</p>
        ) : null}

        {!loading && !error && items.length > 0 ? (
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-y-2 text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-300">
                  <th className="px-3 py-2">Provider</th>
                  <th className="px-3 py-2">Scope</th>
                  <th className="px-3 py-2">Issues</th>
                  <th className="px-3 py-2">Savings</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="glass-strong">
                    <td className="rounded-l-xl px-3 py-3 font-semibold text-slate-100">{item.cloud_provider}</td>
                    <td className="px-3 py-3 text-slate-100">{item.scope}</td>
                    <td className="px-3 py-3 text-slate-100">{item.issues_found}</td>
                    <td className="px-3 py-3 text-slate-100">{item.estimated_savings || "$0/month"}</td>
                    <td className="px-3 py-3">
                      <span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(item.status)}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-slate-300">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="rounded-r-xl px-3 py-3 text-right">
                      <button className="btn btn-muted" onClick={() => navigate(`/report/${item.id}`)}>
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}

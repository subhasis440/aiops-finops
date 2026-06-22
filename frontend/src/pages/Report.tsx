import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../api";

type AnalysisIssue = {
  resource_name: string;
  issue_type: string;
  severity: "high" | "medium" | "low" | string;
  explanation: string;
  fix_command: string;
};

type AnalysisResult = {
  summary: string;
  issues: AnalysisIssue[];
  estimated_savings: string;
};

type AnalysisResponse = {
  id: string;
  cloud_provider: string;
  scope: string;
  resources_scanned: number;
  issues_found: number;
  estimated_savings: string;
  analysis_result: AnalysisResult | null;
  status: string;
  error_message?: string;
  created_at: string;
};

function severityClass(severity: string): string {
  const normalized = severity.toLowerCase();
  if (normalized === "high") {
    return "bg-red-400/20 text-red-200 border-red-300/50";
  }
  if (normalized === "medium") {
    return "bg-amber-300/20 text-amber-100 border-amber-200/40";
  }
  return "bg-emerald-300/20 text-emerald-100 border-emerald-200/40";
}

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const fetchAnalysis = async () => {
      if (!id) {
        setError("Missing analysis id.");
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const response = await api.get<AnalysisResponse>(`/api/analyses/${id}`);
        if (mounted) {
          setAnalysis(response.data);
        }
      } catch (err: unknown) {
        if (mounted) {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          setError(detail ?? "Unable to load analysis report.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchAnalysis();
    return () => {
      mounted = false;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="page-shell">
        <div className="glass rounded-3xl p-6">Loading analysis report...</div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="page-shell">
        <div className="glass rounded-3xl p-6 text-red-200">{error ?? "Analysis not found."}</div>
      </div>
    );
  }

  const result = analysis.analysis_result;
  const issues = result?.issues ?? [];

  return (
    <div className="page-shell space-y-5">
      <section className="glass rounded-3xl p-6 shadow-card animate-floatin">
        <h1 className="section-title">Analysis Report</h1>
        <p className="subtle mt-2 text-sm">
          Provider: <span className="font-semibold text-slate-100">{analysis.cloud_provider}</span> | Scope: {" "}
          <span className="font-semibold text-slate-100">{analysis.scope}</span>
        </p>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <div className="glass-strong rounded-2xl p-4">
            <p className="text-xs uppercase tracking-wide text-slate-300">Resources Scanned</p>
            <p className="mt-1 text-3xl font-bold text-white">{analysis.resources_scanned}</p>
          </div>
          <div className="glass-strong rounded-2xl p-4">
            <p className="text-xs uppercase tracking-wide text-slate-300">Issues Found</p>
            <p className="mt-1 text-3xl font-bold text-white">{analysis.issues_found}</p>
          </div>
          <div className="glass-strong rounded-2xl p-4">
            <p className="text-xs uppercase tracking-wide text-slate-300">Estimated Savings</p>
            <p className="mt-1 text-3xl font-bold text-white">
              {analysis.estimated_savings || result?.estimated_savings || "$0/month"}
            </p>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-white/10 bg-slate-950/35 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-300">Summary</p>
          <p className="mt-2 text-sm text-slate-100">
            {result?.summary ?? "Analysis summary is not available yet."}
          </p>
          {analysis.status === "failed" ? (
            <p className="mt-3 text-sm text-red-200">Failure reason: {analysis.error_message}</p>
          ) : null}
        </div>

        <div className="mt-5 flex gap-3">
          <button className="btn btn-muted" onClick={() => navigate("/history")}>Back to History</button>
          <button className="btn btn-brand" onClick={() => navigate("/dashboard")}>Run Another Analysis</button>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="section-title">Detected Issues</h2>
        {issues.length === 0 ? (
          <div className="glass rounded-2xl p-5 text-sm text-slate-200">
            No issues found in this analysis run.
          </div>
        ) : null}

        {issues.map((issue, index) => (
          <article key={`${issue.resource_name}-${index}`} className="glass rounded-2xl p-5 shadow-card animate-floatin">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-display text-xl font-semibold text-white">{issue.resource_name}</h3>
                <p className="mt-1 text-sm text-slate-300">Type: {issue.issue_type}</p>
              </div>
              <span
                className={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wide ${severityClass(issue.severity)}`}
              >
                {issue.severity}
              </span>
            </div>

            <p className="mt-4 text-sm text-slate-100">{issue.explanation}</p>

            <div className="mt-4 rounded-xl border border-white/15 bg-slate-950/60 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-300">Fix Command</p>
              <pre className="mt-2 overflow-x-auto text-sm text-emerald-200">{issue.fix_command}</pre>
              <button
                className="btn btn-muted mt-3"
                onClick={async () => {
                  await navigator.clipboard.writeText(issue.fix_command);
                }}
              >
                Copy Command
              </button>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}

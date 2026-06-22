import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import ProgressTracker from "../components/ProgressTracker";
import { api } from "../api";

type ScopeItem = {
  id: string;
  name: string;
  location?: string;
};

type ScopesResponse = {
  provider: string;
  scopes: ScopeItem[];
};

type AnalyzeResponse = {
  analysis_id: string;
  status: string;
};

export default function Dashboard() {
  const { token } = useAuth();
  const navigate = useNavigate();

  const [provider, setProvider] = useState("azure");
  const [scopes, setScopes] = useState<ScopeItem[]>([]);
  const [scope, setScope] = useState("");
  const [loadingScopes, setLoadingScopes] = useState(false);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const loadScopes = async () => {
      setError(null);
      setLoadingScopes(true);
      try {
        const response = await api.get<ScopesResponse>("/api/scopes", {
          params: { provider },
        });
        if (!mounted) {
          return;
        }
        const fetchedScopes = response.data.scopes ?? [];
        setScopes(fetchedScopes);
        setScope(fetchedScopes[0]?.name ?? "");
      } catch (err: unknown) {
        if (!mounted) {
          return;
        }
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setError(detail ?? "Failed to fetch cloud scopes.");
        setScopes([]);
      } finally {
        if (mounted) {
          setLoadingScopes(false);
        }
      }
    };

    loadScopes();
    return () => {
      mounted = false;
    };
  }, [provider]);

  const runAnalysis = async () => {
    if (!scope) {
      setError("Select a scope first.");
      return;
    }

    setError(null);
    setRunningAnalysis(true);
    try {
      const response = await api.post<AnalyzeResponse>("/api/analyze", {
        provider,
        scope,
      });
      setAnalysisId(response.data.analysis_id);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Analysis could not be started.");
      setRunningAnalysis(false);
    }
  };

  return (
    <div className="page-shell">
      <section className="glass rounded-3xl p-6 shadow-card animate-floatin">
        <h1 className="font-display text-3xl font-bold text-white">Cloud FinOps Dashboard</h1>
        <p className="subtle mt-2 max-w-2xl text-sm">
          Select a provider and scope, then run AI analysis to detect over-provisioning, idle
          resources, and cost misconfigurations.
        </p>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-semibold">Cloud Provider</label>
            <select
              className="select-field"
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value);
                setAnalysisId(null);
                setRunningAnalysis(false);
              }}
            >
              <option value="azure">Azure</option>
              <option value="aws">AWS</option>
              <option value="gcp">GCP</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-semibold">Scope</label>
            <select
              className="select-field"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              disabled={loadingScopes || scopes.length === 0}
            >
              {scopes.length === 0 ? <option value="">No scopes found</option> : null}
              {scopes.map((item) => (
                <option key={item.id || item.name} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
            <p className="subtle mt-1 text-xs">
              {loadingScopes ? "Loading scopes..." : `${scopes.length} scopes available`}
            </p>
          </div>
        </div>

        {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button className="btn btn-brand" onClick={runAnalysis} disabled={runningAnalysis || !scope}>
            {runningAnalysis ? "Analysis Running..." : "Run Analysis"}
          </button>
          <button className="btn btn-muted" onClick={() => navigate("/history")}>
            View History
          </button>
        </div>
      </section>

      {analysisId && token ? (
        <ProgressTracker
          analysisId={analysisId}
          token={token}
          onComplete={(finishedId) => {
            navigate(`/report/${finishedId}`);
          }}
        />
      ) : null}
    </div>
  );
}

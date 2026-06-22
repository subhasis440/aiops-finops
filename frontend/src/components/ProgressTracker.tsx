import { useEffect, useMemo, useState } from "react";

import { getWsBaseUrl } from "../api";

type ProgressEvent = {
  status: string;
  message: string;
};

type ProgressTrackerProps = {
  analysisId: string;
  token: string;
  onComplete: (analysisId: string) => void;
};

function statusColor(status: string): string {
  if (status === "failed") {
    return "bg-red-400";
  }
  if (status === "complete") {
    return "bg-emerald-300";
  }
  return "bg-amber-300";
}

export default function ProgressTracker({
  analysisId,
  token,
  onComplete,
}: ProgressTrackerProps) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [socketState, setSocketState] = useState("connecting");

  const wsUrl = useMemo(() => {
    const base = getWsBaseUrl();
    return `${base}/ws/progress/${analysisId}?token=${encodeURIComponent(token)}`;
  }, [analysisId, token]);

  useEffect(() => {
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setSocketState("connected");
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as ProgressEvent;
        setEvents((prev) => {
          if (prev.some((item) => item.status === payload.status && item.message === payload.message)) {
            return prev;
          }
          return [...prev, payload];
        });

        if (payload.status === "complete") {
          setSocketState("completed");
          window.setTimeout(() => onComplete(analysisId), 800);
        }

        if (payload.status === "failed") {
          setSocketState("failed");
        }
      } catch {
        setEvents((prev) => [...prev, { status: "unknown", message: event.data }]);
      }
    };

    socket.onerror = () => {
      setSocketState("error");
    };

    socket.onclose = () => {
      setSocketState((prev) => (prev === "completed" ? prev : "closed"));
    };

    return () => {
      socket.close();
    };
  }, [analysisId, onComplete, wsUrl]);

  return (
    <div className="glass-strong mt-6 rounded-2xl p-5 shadow-card animate-floatin">
      <h3 className="section-title">Live Analysis Progress</h3>
      <p className="subtle mt-1 text-sm">Connection: {socketState}</p>

      <ol className="mt-4 space-y-3">
        {events.length === 0 ? (
          <li className="subtle text-sm">Waiting for progress updates...</li>
        ) : null}

        {events.map((event, index) => {
          const isLast = index === events.length - 1;
          return (
            <li
              key={`${event.status}-${index}`}
              className={`flex items-start gap-3 rounded-xl border border-white/10 bg-slate-950/35 p-3 ${
                isLast ? "animate-floatin" : ""
              }`}
            >
              <span
                className={`mt-1 inline-block h-2.5 w-2.5 rounded-full ${statusColor(event.status)} ${
                  isLast && event.status !== "complete" && event.status !== "failed" ? "animate-pulse" : ""
                }`}
              />
              <div>
                <p className="text-sm font-semibold text-slate-100">{event.message}</p>
                <p className="text-xs uppercase tracking-wide text-slate-400">{event.status}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

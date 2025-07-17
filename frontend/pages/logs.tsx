import React, { useEffect, useState } from "react";

interface LogEntry {
  timestamp: string;
  action: string;
  user?: string;
}

export default function LogsPage() {
  // connect to the backend websocket and stream logs in real time
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const url = `${window.location.protocol.replace("http", "ws")}//${window.location.host}/ws/logs`;
    const ws = new WebSocket(url);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as LogEntry;
        setEntries((prev) => [...prev.slice(-99), data]);
      } catch {
        // ignore parse errors
      }
    };
    ws.onerror = () => setError("Connection lost");
    return () => ws.close();
  }, []);

  return (
    <div className="p-4 space-y-2">
      <h1 className="text-xl font-bold">Live Logs</h1>
      {error && <p className="text-red-600">{error}</p>}
      <ul className="text-sm space-y-1">
        {entries.map((e, i) => (
          <li key={i}>
            {e.timestamp} {e.user ? `(${e.user})` : ""} - {e.action}
          </li>
        ))}
      </ul>
    </div>
  );
}

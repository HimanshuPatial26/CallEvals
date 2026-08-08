import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { listCalls } from "./api/client";
import UploadPanel from "./components/UploadPanel";
import CallList from "./components/CallList";
import CallDetail from "./components/CallDetail";

function App() {
  const [calls, setCalls] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await listCalls();
      setCalls(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const hasProcessing = calls.some((c) => c.status === "processing");
    const interval = setInterval(refresh, hasProcessing ? 3000 : 8000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, calls.length]);

  function handleUploaded(record) {
    setCalls((prev) => [record, ...prev]);
    setSelectedId(record.id);
  }

  function handleFeedbackChange(newFeedback) {
    setCalls((prev) => prev.map((c) => (c.id === selectedId ? { ...c, feedback: newFeedback } : c)));
  }

  const selectedCall = calls.find((c) => c.id === selectedId);

  return (
    <div className="app">
      <header className="app-header">
        <h1>CallEvals</h1>
        <p className="subtitle">Sales call review — Phase 0</p>
      </header>

      {error && <p className="error">{error}</p>}

      <div className="app-body">
        <aside className="sidebar">
          <UploadPanel onUploaded={handleUploaded} />
          <CallList calls={calls} selectedId={selectedId} onSelect={setSelectedId} />
        </aside>

        <main className="main">
          {selectedCall ? (
            <CallDetail call={selectedCall} onFeedbackChange={handleFeedbackChange} />
          ) : (
            <p className="hint">Select a call to review it.</p>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;

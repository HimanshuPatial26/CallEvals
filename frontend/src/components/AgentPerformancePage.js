import { useCallback, useEffect, useState } from "react";
import { listAgents, getAgentPerformance } from "../api/client";
import AgentOverviewPanel from "./AgentOverviewPanel";
import AgentScoreBreakdownPanel from "./AgentScoreBreakdownPanel";
import AgentBehaviorPanel from "./AgentBehaviorPanel";
import AgentFunnelPanel from "./AgentFunnelPanel";
import AgentPipelineInsightsPanel from "./AgentPipelineInsightsPanel";
import AgentSentimentIntentPanel from "./AgentSentimentIntentPanel";
import AgentQualityTrendPanel from "./AgentQualityTrendPanel";
import AgentCoachingPanel from "./AgentCoachingPanel";

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 29);
  const iso = (d) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end) };
}

export default function AgentPerformancePage({ initialAgentId }) {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [range, setRange] = useState(defaultRange);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listAgents()
      .then((data) => {
        setAgents(data);
        if (data.length > 0 && !selectedAgent) {
          const preset = initialAgentId && data.some((a) => a.id === initialAgentId) ? initialAgentId : data[0].id;
          setSelectedAgent(preset);
        }
      })
      .catch((err) => setError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadReport = useCallback(async () => {
    if (!selectedAgent) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getAgentPerformance(selectedAgent, range.start, range.end);
      setReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedAgent, range]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  return (
    <div className="agent-performance-page">
      <div className="agent-performance-controls panel">
        <label className="outcome-field">
          Agent
          <select value={selectedAgent} onChange={(e) => setSelectedAgent(e.target.value)}>
            {agents.length === 0 && <option value="">No agents yet</option>}
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
                {a.team_name ? ` — ${a.team_name}` : ""} ({a.calls_analyzed})
              </option>
            ))}
          </select>
        </label>
        <label className="outcome-field">
          From
          <input type="date" value={range.start} onChange={(e) => setRange((r) => ({ ...r, start: e.target.value }))} />
        </label>
        <label className="outcome-field">
          To
          <input type="date" value={range.end} onChange={(e) => setRange((r) => ({ ...r, end: e.target.value }))} />
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="hint loading-state">Loading…</p>}

      {!loading && agents.length === 0 && (
        <p className="hint">No calls uploaded yet — upload a call with an agent name to see performance data here.</p>
      )}

      {!loading && report && (
        <>
          <AgentOverviewPanel report={report} />
          <AgentScoreBreakdownPanel breakdown={report.score_breakdown} />
          <AgentBehaviorPanel talkTime={report.talk_time} discoveryAvgScore={report.discovery_avg_score} objections={report.objections} />
          <AgentFunnelPanel closing={report.closing} conversion={report.conversion} matrix={report.quality_outcome_matrix} />
          <AgentPipelineInsightsPanel
            callsToClose={report.calls_to_close}
            lostReasons={report.lost_reasons}
            sourceBreakdown={report.source_breakdown}
          />
          <AgentSentimentIntentPanel sentiment={report.sentiment} conversion={report.conversion} />
          <AgentQualityTrendPanel
            distribution={report.quality_distribution}
            consistency={report.consistency_score}
            trend={report.trend}
          />
          <AgentCoachingPanel
            strengths={report.strengths}
            weaknesses={report.weaknesses}
            recommendations={report.coaching_recommendations}
            benchmark={report.team_benchmark}
          />
          {report.notes.length > 0 && (
            <section className="panel">
              <h3>Notes</h3>
              <ul className="insights-list">
                {report.notes.map((note, i) => (
                  <li key={i}>
                    <span className="insights-label">{note}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}

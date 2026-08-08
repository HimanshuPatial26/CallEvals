import { useCallback, useEffect, useState } from "react";
import { getOrgPerformance, getTeamPerformance } from "../api/client";
import AgentOverviewPanel from "./AgentOverviewPanel";
import AgentScoreBreakdownPanel from "./AgentScoreBreakdownPanel";
import AgentBehaviorPanel from "./AgentBehaviorPanel";
import AgentFunnelPanel from "./AgentFunnelPanel";
import AgentPipelineInsightsPanel from "./AgentPipelineInsightsPanel";
import AgentSentimentIntentPanel from "./AgentSentimentIntentPanel";
import AgentQualityTrendPanel from "./AgentQualityTrendPanel";
import AgentCoachingPanel from "./AgentCoachingPanel";
import LeaderboardPanel from "./LeaderboardPanel";

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 29);
  const iso = (d) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end) };
}

// The TEAM and ORGANIZATION levels of the CALL -> AGENT -> TEAM ->
// ORGANIZATION hierarchy, in one tab: it opens on the org rollup, and
// clicking a row in the team leaderboard drills into that team (same
// panels, filtered population) without leaving the tab. Clicking a row in
// a team's agent leaderboard hands off to the Agent Performance tab via
// onDrillToAgent, completing the drill all the way down to CALL/AGENT.
export default function OrganizationPage({ onDrillToAgent }) {
  const [range, setRange] = useState(defaultRange);
  const [teamId, setTeamId] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    // The org and team reports have different shapes (agent_leaderboard vs.
    // team_leaderboard, org_benchmark vs. nothing) -- clear the stale report
    // now so a level switch never renders one shape's data through the
    // other's panels while the new fetch is in flight.
    setReport(null);
    try {
      const data = teamId ? await getTeamPerformance(teamId, range.start, range.end) : await getOrgPerformance(range.start, range.end);
      setReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [teamId, range]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  // Setting loading here, synchronously in the same event as the teamId
  // change, matters: without it React renders once with the *new* teamId
  // but the *old*, differently-shaped report (loadReport's own setReport(null)
  // only lands a render later, via the effect) -- LeaderboardPanel would get
  // handed the wrong report's fields and crash on that first render.
  function selectTeam(id) {
    setLoading(true);
    setTeamId(id);
  }

  const isTeamLevel = teamId != null;
  const title = report
    ? isTeamLevel
      ? `${report.team_name} — ${report.period_start} to ${report.period_end}`
      : `Organization — ${report.period_start} to ${report.period_end}`
    : "";

  return (
    <div className="agent-performance-page">
      <div className="agent-performance-controls panel">
        {isTeamLevel && (
          <button type="button" className="link-button" onClick={() => selectTeam(null)}>
            ← All teams
          </button>
        )}
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

      {!loading && report && (
        <>
          <AgentOverviewPanel report={report} title={title} />
          <AgentScoreBreakdownPanel breakdown={report.score_breakdown} title={isTeamLevel ? "Team score" : "Organization score"} />
          <AgentBehaviorPanel talkTime={report.talk_time} discoveryAvgScore={report.discovery_avg_score} objections={report.objections} />
          <AgentFunnelPanel closing={report.closing} conversion={report.conversion} matrix={report.quality_outcome_matrix} />
          <AgentPipelineInsightsPanel
            callsToClose={report.calls_to_close}
            lostReasons={report.lost_reasons}
            sourceBreakdown={report.source_breakdown}
          />
          <AgentSentimentIntentPanel sentiment={report.sentiment} conversion={report.conversion} />
          <AgentQualityTrendPanel distribution={report.quality_distribution} consistency={report.consistency_score} trend={report.trend} />
          <AgentCoachingPanel
            strengths={report.strengths}
            weaknesses={report.weaknesses}
            recommendations={report.coaching_recommendations}
            benchmark={isTeamLevel ? report.org_benchmark : null}
            benchmarkTitle="Org average"
          />
          <LeaderboardPanel
            title={isTeamLevel ? "Agent leaderboard" : "Team leaderboard"}
            rows={isTeamLevel ? report.agent_leaderboard : report.team_leaderboard}
            onSelect={isTeamLevel ? onDrillToAgent : selectTeam}
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

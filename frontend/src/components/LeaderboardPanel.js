// Reused for both "teams within the org" and "agents within a team" rollups
// (schemas.LeaderboardRow is the same shape either way). Clicking a row
// drills one level down the CALL -> AGENT -> TEAM -> ORGANIZATION hierarchy.
export default function LeaderboardPanel({ title, rows, onSelect }) {
  return (
    <section className="panel">
      <h3>{title}</h3>
      {rows.length === 0 ? (
        <p className="hint">No data for this period.</p>
      ) : (
        <table className="trend-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Overall score</th>
              <th>Conversion</th>
              <th>Calls analyzed</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.id}
                className={onSelect ? "leaderboard-row-clickable" : ""}
                onClick={onSelect ? () => onSelect(row.id) : undefined}
              >
                <td>{row.name}</td>
                <td>{row.overall_score != null ? Math.round(row.overall_score) : "—"}</td>
                <td>{row.conversion_rate_pct != null ? `${row.conversion_rate_pct.toFixed(0)}%` : "—"}</td>
                <td>{row.calls_analyzed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

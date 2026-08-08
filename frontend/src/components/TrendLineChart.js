const W = 760;
const H = 190;

function seriesPoints(trend, key) {
  const pts = [];
  trend.forEach((p, i) => {
    const v = p[key];
    if (v == null) return;
    const x = trend.length > 1 ? (i / (trend.length - 1)) * W : W / 2;
    const y = H - (Math.max(0, Math.min(100, v)) / 100) * (H - 24) - 12;
    pts.push([x, y]);
  });
  return pts;
}

function polyPoints(pts) {
  return pts.map(([x, y]) => `${x},${y}`).join(" ");
}

// Dual-line chart for a PerformanceMetrics.trend series (real weekly
// avg_score + conversion_rate_pct, both already 0-100 scales -- no fake
// "sentiment trajectory," this plots what the API actually returns).
// Gaps (null weeks) are skipped, not interpolated through zero.
export default function TrendLineChart({ trend }) {
  if (!trend || trend.length === 0) {
    return <p className="hint">No calls in this period.</p>;
  }
  const scorePts = seriesPoints(trend, "avg_score");
  const convPts = seriesPoints(trend, "conversion_rate_pct");
  const grid = [0, 1, 2, 3, 4].map((i) => (
    <line key={i} x1={0} x2={W} y1={(H / 4) * i} y2={(H / 4) * i} stroke="rgba(240,146,62,.13)" strokeWidth="1" />
  ));
  const scoreLine = polyPoints(scorePts);
  const fillPoly = scorePts.length > 0 ? `${scorePts[0][0]},${H} ${scoreLine} ${scorePts[scorePts.length - 1][0]},${H}` : "";

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: 210 }}>
      <defs>
        <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(255,176,102,.42)" />
          <stop offset="100%" stopColor="rgba(255,176,102,0)" />
        </linearGradient>
      </defs>
      {grid}
      {scorePts.length > 0 && <polygon points={fillPoly} fill="url(#trend-fill)" />}
      {convPts.length > 1 && (
        <polyline points={polyPoints(convPts)} fill="none" stroke="#7fa39d" strokeWidth="1.6" strokeDasharray="4 4" opacity="0.85" />
      )}
      {scorePts.length > 1 && <polyline points={scoreLine} fill="none" stroke="#f0923e" strokeWidth="2.4" strokeLinejoin="round" />}
      {scorePts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="2.6" fill="#0d1a1c" stroke="#f0923e" strokeWidth="1.4" />
      ))}
    </svg>
  );
}

// Small inline trend line for a KPI tile. Real data only -- callers pass
// whatever numeric series they actually have (e.g. weekly avg_score); no
// synthetic/randomized data generation like the design reference used.
export default function Sparkline({ points, tint = "#ffb066", width = 140, height = 26 }) {
  if (!points || points.length < 2) {
    return <div style={{ height }} />;
  }
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  const d = points
    .map((p, i) => `${(i / (points.length - 1)) * width},${height - ((p - min) / range) * (height - 4) - 2}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ width: "100%", height, overflow: "visible" }}>
      <polyline points={d} fill="none" stroke={tint} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" opacity="0.9" />
    </svg>
  );
}

// Design system 05 · Icons: 24px grid, 2px stroke, rounded caps, one amber
// accent per glyph. Paths copied verbatim from "CallEvals Design System.dc.html".
// Only the icons this app actually uses so far are included -- add more from
// the doc's icon set as new UI needs them, not speculatively.

export function PlayIcon(props) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M10 8.5l6 3.5-6 3.5z" fill="#F0913C" stroke="none" />
    </svg>
  );
}

export function RetryIcon(props) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M19.5 12a7.5 7.5 0 1 1-2.4-5.5" />
      <path d="M19.5 4v4h-4" stroke="#F0913C" />
    </svg>
  );
}

export function ProcessingIcon(props) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" strokeLinecap="round" style={{ animation: "spin 1.6s linear infinite" }} {...props}>
      <circle cx="12" cy="12" r="8.5" stroke="#33302B" strokeWidth="2" />
      <path d="M12 3.5a8.5 8.5 0 0 1 8.5 8.5" stroke="#F0913C" strokeWidth="2" />
    </svg>
  );
}

export function ReadyCheckIcon(props) {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M5 12.5l4.5 4.5L19 6.5" />
    </svg>
  );
}

export function FailedCrossIcon(props) {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

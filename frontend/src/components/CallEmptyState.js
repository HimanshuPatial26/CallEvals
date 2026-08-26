// The right-hand panel before a call is selected. Design system 06 ·
// Components > "EMPTY & LOADING": a dashed card with a radial accent glow
// and the brand mark's 4 bars, animating -- purely decorative, no data of
// its own. Replaces the earlier Strands-based ambient backdrop.
const WAVEFORM_BARS = ["#6B5B49", "#F0913C", "#FFB169", "#A0713C"];
const WAVEFORM_DELAYS = ["-0.7s", "-0.4s", "-0.15s", "0s"];

export default function CallEmptyState() {
  return (
    <div className="call-empty-state">
      <div className="call-empty-content">
        <span className="call-empty-waveform" aria-hidden="true">
          {WAVEFORM_BARS.map((color, i) => (
            <span key={i} style={{ background: color, animationDelay: WAVEFORM_DELAYS[i] }} />
          ))}
        </span>
        <p className="call-empty-title">Select a call to review it.</p>
        <p className="call-empty-sub">Score, transcript, objections, and coaching will appear here.</p>
      </div>
    </div>
  );
}

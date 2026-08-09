import Strands from "./Strands";
import usePrefersReducedMotion from "../hooks/usePrefersReducedMotion";

// The right-hand panel before a call is selected. Fills the same visual
// weight CallDetail will occupy once there's something to show, with the
// ambient Strands background as a placeholder moment rather than a blank
// page -- purely decorative, no data of its own.
export default function CallEmptyState() {
  const reducedMotion = usePrefersReducedMotion();

  return (
    <div className="call-empty-state">
      {!reducedMotion && (
        <div className="call-empty-backdrop" aria-hidden="true">
          <Strands
            colors={["#f0923e", "#2dd4bf", "#d9752c"]}
            count={5}
            speed={0.28}
            amplitude={3.2}
            waviness={0.7}
            thickness={0.6}
            glow={2.1}
            taper={1.4}
            spread={1.6}
            intensity={0.4}
            saturation={1.05}
            opacity={0.4}
            scale={1.3}
          />
        </div>
      )}
      <div className="call-empty-content">
        <p className="call-empty-title">Select a call to review it.</p>
        <p className="call-empty-sub">Score breakdown, transcript, objections, and coaching will appear here.</p>
      </div>
    </div>
  );
}

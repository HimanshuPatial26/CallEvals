// PRD section 5 deliberately cut the composite call score — "gets gamed, reads as
// surveillance." The Rubric screen exposes a toggle for it (matching the mockup's
// own Phase-3 preview framing), but no scoring pipeline exists behind it, so this
// renders an honest "not built yet" state rather than a fabricated number even
// when the toggle is on.
export default function ScoreCard() {
  return (
    <div className="ce-card">
      <div className="ce-card-header">
        <span className="ce-card-title">Call score</span>
        <span className="ce-card-tag">PHASE 3</span>
      </div>
      <div className="ce-unavailable">
        Composite scoring is a Phase 3 idea, not a built pipeline — the PRD deliberately cut a single-number
        score at MVP. Turning this on doesn't compute one; behavior flags are the real signal today.
      </div>
    </div>
  );
}

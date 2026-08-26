import { useEffect, useState } from "react";
import { updateSettings } from "../api/client";

const WEIGHT_DEFS = [
  ["discovery", "Discovery questions", "Questions asked before the first pitch or price."],
  ["objection", "Objection handling", "Responded with a question or a concrete alternative, not a concession."],
  ["listening", "Listening / talk ratio", "Rep share of speaking time, penalised above 70%."],
  ["nextstep", "Next step committed", "A specific action with a date, stated by the rep."],
  ["compliance", "Compliance disclosure", "Recording disclosure present in the opening."],
];

const FLAG_DEFS = [
  ["monologue", "Monologue", "Any single rep turn over 45 seconds.", "> 45s"],
  ["no_discovery_question", "No discovery question", "Call ends with fewer than two rep questions.", "< 2 questions"],
  ["no_dated_next_step", "No dated next step", "Nothing extracted as a commitment with a date.", "F3 empty"],
  ["missing_disclosure", "Missing disclosure", "No recording disclosure in the first 30 seconds.", "first 0:30"],
  ["discount_offered_first", "Discount offered first", "Price mention before any question is asked.", "pre-question"],
];

export default function RubricScreen({ settings, onSettingsChange }) {
  const [draft, setDraft] = useState(settings);
  const [newTag, setNewTag] = useState("");
  const [saveState, setSaveState] = useState("idle");

  useEffect(() => setDraft(settings), [settings]);

  if (!draft) {
    return (
      <div className="ce-rubric-layout">
        <span className="hint">Loading…</span>
      </div>
    );
  }

  async function persist(next) {
    setDraft(next);
    setSaveState("saving");
    try {
      const saved = await updateSettings(next);
      onSettingsChange(saved);
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  }

  const weightTotal = Object.values(draft.weights).reduce((a, b) => a + b, 0);

  return (
    <div className="ce-rubric-layout">
      <div className="ce-rubric-main">
        <div className="ce-card">
          <div className="ce-card-header">
            <span className="ce-card-title">Criterion weights</span>
            <span className="ce-shape-value" style={{ marginLeft: "auto", color: weightTotal === 100 ? "var(--ce-success)" : "var(--ce-accent)" }}>
              {weightTotal}/100
            </span>
          </div>
          <div className="ce-weight-rows">
            {WEIGHT_DEFS.map(([key, label, note]) => (
              <div key={key} className="ce-weight-row">
                <div className="ce-crit-label-row">
                  <span style={{ fontSize: 13, color: "var(--ce-text)" }}>{label}</span>
                  <span className="ce-shape-value">{draft.weights[key]}</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={40}
                  step={5}
                  value={draft.weights[key]}
                  className="ce-slider"
                  onChange={(e) => persist({ ...draft, weights: { ...draft.weights, [key]: Number(e.target.value) } })}
                />
                <span className="hint">{note}</span>
              </div>
            ))}
            <span className="ce-card-footnote" style={{ color: weightTotal === 100 ? "var(--ce-success)" : "var(--ce-accent)" }}>
              {weightTotal === 100
                ? "Weights balance. These aren't wired to a scoring pipeline yet — composite scoring stays off regardless (see below)."
                : `Weights must total 100 to be internally consistent. Currently ${weightTotal}.`}
            </span>
          </div>
        </div>

        <div className="ce-card">
          <div className="ce-card-header">
            <span className="ce-card-title">Behaviour flags</span>
            <span className="ce-card-tag">WHAT MANAGERS COACH ON</span>
          </div>
          <div>
            {FLAG_DEFS.map(([key, label, note, rule]) => {
              const on = draft.flags[key];
              return (
                <div key={key} className="ce-flag-row">
                  <div className="ce-flag-info">
                    <span className={`ce-flag-name${on ? "" : " off"}`}>{label}</span>
                    <span className="ce-flag-note">{note}</span>
                  </div>
                  <span className="ce-flag-rule">{rule}</span>
                  <button
                    type="button"
                    className={`ce-toggle${on ? " on" : ""}`}
                    onClick={() => persist({ ...draft, flags: { ...draft.flags, [key]: !on } })}
                  >
                    <span className="ce-toggle-knob" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="ce-rubric-side">
        <div className="ce-card">
          <div className="ce-card-header">
            <span className="ce-card-title">Objection taxonomy</span>
            <span className="ce-card-tag">F4</span>
          </div>
          <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="ce-tag-row">
              {draft.objection_tags.map((tag, i) => {
                const core = i < 3;
                return (
                  <span key={tag} className={`ce-tag-pill${core ? " core" : ""}`}>
                    {tag}
                    {core ? (
                      <span className="hint" style={{ fontSize: 9 }}>core</span>
                    ) : (
                      <button type="button" className="ce-tag-remove" onClick={() => persist({ ...draft, objection_tags: draft.objection_tags.filter((_, j) => j !== i) })}>✕</button>
                    )}
                  </span>
                );
              })}
            </div>
            <div className="ce-tag-input-row">
              <input className="ce-text-input" value={newTag} onChange={(e) => setNewTag(e.target.value)} placeholder="Add a per-org tag" />
              <button
                type="button"
                className="ce-btn"
                onClick={() => {
                  const v = newTag.trim();
                  if (v) {
                    persist({ ...draft, objection_tags: [...draft.objection_tags, v] });
                    setNewTag("");
                  }
                }}
              >
                Add
              </button>
            </div>
            <span className="hint">
              Three core categories ship locked to the extraction pipeline (server/app/schemas.py) — narrow scope is what
              keeps precision high. Custom tags here are labels only until the extractor supports them.
            </span>
          </div>
        </div>

        <div className="ce-card">
          <div className="ce-card-header"><span className="ce-card-title">Confidence thresholds</span></div>
          <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="ce-weight-row">
              <div className="ce-crit-label-row">
                <span style={{ fontSize: 13, color: "var(--ce-text)" }}>Surface an extraction</span>
                <span className="ce-shape-value">≥ {draft.surface_threshold}%</span>
              </div>
              <input type="range" min={50} max={99} className="ce-slider" value={draft.surface_threshold} onChange={(e) => persist({ ...draft, surface_threshold: Number(e.target.value) })} />
              <span className="hint">Below this, an item is stored but not shown. Recall drops, trust holds.</span>
            </div>
            <div className="ce-weight-row">
              <div className="ce-crit-label-row">
                <span style={{ fontSize: 13, color: "var(--ce-text)" }}>Auto-flag without review</span>
                <span className="ce-shape-value">≥ {draft.autoflag_threshold}%</span>
              </div>
              <input type="range" min={50} max={99} className="ce-slider" value={draft.autoflag_threshold} onChange={(e) => persist({ ...draft, autoflag_threshold: Number(e.target.value) })} />
              <span className="hint">Above this, an item's confidence displays green instead of amber.</span>
            </div>
          </div>
        </div>

        <div className="ce-card">
          <div className="ce-card-header"><span className="ce-card-title">Digest & visibility</span></div>
          <div className="ce-card-body" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <span className="ce-shape-caps">MANAGER DIGEST</span>
              <div className="ce-digest-options">
                {["Daily", "Weekly", "Off"].map((opt) => (
                  <button key={opt} type="button" className={`ce-digest-opt${draft.digest === opt ? " active" : ""}`} onClick={() => persist({ ...draft, digest: opt })}>
                    {opt}
                  </button>
                ))}
              </div>
              <span className="hint">Not wired to email/notification delivery yet — this stores the preference.</span>
            </div>

            <div className="ce-setting-row">
              <div className="ce-setting-info">
                <span className="ce-setting-title">Rep-private mode</span>
                <span className="ce-setting-desc">Reps see their own analysis for 30 days before any manager view. Rollups mask names and hide ranking.</span>
              </div>
              <button type="button" className={`ce-toggle${draft.rep_private_mode ? " on" : ""}`} onClick={() => persist({ ...draft, rep_private_mode: !draft.rep_private_mode })}>
                <span className="ce-toggle-knob" />
              </button>
            </div>

            <div className="ce-setting-row">
              <div className="ce-setting-info">
                <span className="ce-setting-title">Composite score</span>
                <span className="ce-setting-desc">
                  PRD's original position: off, behavior flags only. No scoring pipeline exists behind this toggle —
                  turning it on shows a "not built" state, not a fabricated number.
                </span>
              </div>
              <button type="button" className={`ce-toggle${draft.composite_score_enabled ? " on" : ""}`} onClick={() => persist({ ...draft, composite_score_enabled: !draft.composite_score_enabled })}>
                <span className="ce-toggle-knob" />
              </button>
            </div>
          </div>
        </div>
        {saveState === "error" && <span className="error">Couldn't save — check the backend connection.</span>}
      </div>
    </div>
  );
}

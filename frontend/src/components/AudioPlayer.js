import { useEffect, useRef, useState } from "react";
import { audioUrl } from "../api/client";
import { PlayGlyph } from "../icons";
import { fmtTime } from "../utils/format";

const BAR_COUNT = 84;

// Real peak amplitudes decoded from the actual audio file — not a placeholder
// pattern. Falls back to a flat bar row if decoding fails (unsupported codec,
// audio not reachable yet) rather than fabricating a shape.
async function decodePeaks(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error("audio fetch failed");
  const buffer = await response.arrayBuffer();
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  const ctx = new AudioCtx();
  try {
    const audioBuffer = await ctx.decodeAudioData(buffer);
    const channel = audioBuffer.getChannelData(0);
    const blockSize = Math.max(1, Math.floor(channel.length / BAR_COUNT));
    const peaks = [];
    for (let i = 0; i < BAR_COUNT; i++) {
      let max = 0;
      const start = i * blockSize;
      for (let j = start; j < start + blockSize && j < channel.length; j++) {
        max = Math.max(max, Math.abs(channel[j]));
      }
      peaks.push(max);
    }
    return peaks;
  } finally {
    ctx.close();
  }
}

export default function AudioPlayer({ callId, duration, markers, onTimeChange, seekToRef }) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [t, setT] = useState(0);
  const [audioError, setAudioError] = useState(false);
  const [peaks, setPeaks] = useState(null);

  useEffect(() => {
    setT(0);
    setPlaying(false);
    setAudioError(false);
    setPeaks(null);
    let cancelled = false;
    decodePeaks(audioUrl(callId))
      .then((p) => {
        if (!cancelled) setPeaks(p);
      })
      .catch(() => {
        if (!cancelled) setPeaks(new Array(BAR_COUNT).fill(0.15));
      });
    return () => {
      cancelled = true;
    };
  }, [callId]);

  useEffect(() => {
    if (seekToRef) {
      seekToRef.current = (time) => {
        if (audioRef.current) audioRef.current.currentTime = time;
        setT(time);
        onTimeChange?.(time);
      };
    }
  }, [seekToRef, onTimeChange]);

  function togglePlay() {
    const el = audioRef.current;
    if (!el) return;
    if (playing) {
      el.pause();
    } else {
      el.play().catch(() => setAudioError(true));
    }
  }

  function handleSeek(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    const time = ratio * duration;
    if (audioRef.current) audioRef.current.currentTime = time;
    setT(time);
    onTimeChange?.(time);
  }

  const bars = peaks || new Array(BAR_COUNT).fill(0.15);

  return (
    <div className="ce-player">
      <audio
        ref={audioRef}
        src={audioUrl(callId)}
        preload="metadata"
        onTimeUpdate={(e) => {
          setT(e.currentTarget.currentTime);
          onTimeChange?.(e.currentTarget.currentTime);
        }}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onError={() => setAudioError(true)}
      />
      <div className="ce-player-row">
        <button type="button" className="ce-player-btn" onClick={togglePlay} disabled={audioError} aria-label={playing ? "Pause" : "Play"}>
          <PlayGlyph playing={playing} />
        </button>
        <div className="ce-player-track">
          <div className="ce-waveform" onClick={handleSeek}>
            {bars.map((amp, i) => {
              const played = (i / bars.length) * duration <= t;
              const heightPct = Math.max(8, amp * 100);
              return <span key={i} className={`ce-waveform-bar${played ? " played" : ""}`} style={{ height: `${heightPct.toFixed(0)}%` }} />;
            })}
            {markers.map((m, i) => (
              <span key={i} className="ce-waveform-marker" style={{ left: `${((m.ts / duration) * 100).toFixed(1)}%`, background: m.color }} />
            ))}
            <span className="ce-playhead" style={{ left: `${duration ? ((t / duration) * 100).toFixed(1) : 0}%` }} />
          </div>
          <div className="ce-player-meta">
            <span className="ce-player-time">
              {fmtTime(t)} / {fmtTime(duration)}
            </span>
            <div className="ce-legend">
              <span className="ce-legend-item">
                <span className="ce-legend-swatch" style={{ background: "var(--ce-accent)" }} />
                objection marker
              </span>
              <span className="ce-legend-item">
                <span className="ce-legend-swatch" style={{ background: "var(--ce-success)" }} />
                commitment
              </span>
            </div>
          </div>
          {audioError && <span className="hint">Audio couldn't be loaded for this call.</span>}
        </div>
      </div>
    </div>
  );
}

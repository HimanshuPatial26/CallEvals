// Icon set from the CallEvals design system — 24px grid, 2px stroke, rounded
// caps, one amber accent path per glyph (see design system 05 · Icons).

function Svg({ size = 18, children, className, style }) {
  return (
    <svg
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

export function IconPlay(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M10 8.5l6 3.5-6 3.5z" fill="var(--ce-accent)" stroke="none" />
    </Svg>
  );
}

export function IconUpload(props) {
  return (
    <Svg {...props}>
      <path d="M4 15v3.5c0 .8.7 1.5 1.5 1.5h13c.8 0 1.5-.7 1.5-1.5V15" />
      <path d="M12 15V4" stroke="var(--ce-accent)" />
      <path d="M8 8l4-4 4 4" stroke="var(--ce-accent)" />
    </Svg>
  );
}

export function IconDownload(props) {
  return (
    <Svg {...props}>
      <path d="M4 15v3.5c0 .8.7 1.5 1.5 1.5h13c.8 0 1.5-.7 1.5-1.5V15" />
      <path d="M12 4v11" stroke="var(--ce-accent)" />
      <path d="M8 11l4 4 4-4" stroke="var(--ce-accent)" />
    </Svg>
  );
}

export function IconRetry(props) {
  return (
    <Svg {...props}>
      <path d="M19.5 12a7.5 7.5 0 1 1-2.4-5.5" />
      <path d="M19.5 4v4h-4" stroke="var(--ce-accent)" />
    </Svg>
  );
}

export function IconReady(props) {
  return (
    <Svg {...props} style={{ ...(props.style || {}), color: "var(--ce-success)" }}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.5 12.5l2.5 2.5 5-5.5" />
    </Svg>
  );
}

export function IconFailed(props) {
  return (
    <Svg {...props} style={{ ...(props.style || {}), color: "var(--ce-danger)" }}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M9.2 9.2l5.6 5.6M14.8 9.2l-5.6 5.6" />
    </Svg>
  );
}

export function IconProcessing({ size = 18, className }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      strokeLinecap="round"
      style={{ animation: "ceSpin 1.6s linear infinite" }}
    >
      <circle cx="12" cy="12" r="8.5" stroke="var(--ce-border-control)" strokeWidth="2" />
      <path d="M12 3.5a8.5 8.5 0 0 1 8.5 8.5" stroke="var(--ce-accent)" strokeWidth="2" />
    </svg>
  );
}

export function IconObjection(props) {
  return (
    <Svg {...props}>
      <path d="M20 12.5c0 3.6-3.6 6.5-8 6.5-.9 0-1.8-.1-2.6-.3L5 20.5l1-3.4C4.7 15.9 4 14.3 4 12.5 4 8.9 7.6 6 12 6s8 2.9 8 6.5z" />
      <path d="M12 9.5v3.2" stroke="var(--ce-accent)" />
      <path d="M12 15.4h.01" stroke="var(--ce-accent)" />
    </Svg>
  );
}

export function StatusIcon({ status, size = 18 }) {
  if (status === "done") return <IconReady size={size} />;
  if (status === "failed") return <IconFailed size={size} />;
  return <IconProcessing size={size} />;
}

// Waveform mark — 7 bars, 4px wide, 4px gap, 3px radius, descending from the
// peak (45/88/62/34%). Animating bars is reserved for processing states.
export function LogoMark({ size = 24, animated = false }) {
  const bars = [
    { h: 45, delay: -0.7 },
    { h: 88, delay: -0.4 },
    { h: 62, delay: -0.15 },
    { h: 34, delay: 0 },
  ];
  const colors = ["#A0713C", "#F0913C", "#FFB169", "#A0713C"];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: size >= 24 ? 3 : 2,
        height: size,
      }}
    >
      {bars.map((b, i) => (
        <span
          key={i}
          style={{
            width: size >= 24 ? 3 : 2.5,
            height: `${b.h}%`,
            borderRadius: 2,
            background: colors[i],
            transformOrigin: "center",
            animation: animated ? `ceBar 1.15s ease-in-out infinite` : undefined,
            animationDelay: animated ? `${b.delay}s` : undefined,
          }}
        />
      ))}
    </span>
  );
}

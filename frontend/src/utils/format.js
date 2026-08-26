export function fmtTime(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

export function fmtPct(value) {
  if (value == null) return "—";
  return `${Math.round(value)}%`;
}

export function fmtRelative(isoString) {
  if (!isoString) return "—";
  const then = new Date(isoString).getTime();
  const now = Date.now();
  const diffMs = now - then;
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function fmtDateShort(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short" });
}

export function firstName(fullName) {
  if (!fullName) return "";
  return fullName.split(" ")[0];
}

export function initials(fullName) {
  if (!fullName) return "";
  return fullName
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

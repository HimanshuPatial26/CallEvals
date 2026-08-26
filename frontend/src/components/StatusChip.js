const STATUS_MAP = {
  done: { label: "Ready", cls: "ce-chip-success" },
  failed: { label: "Failed", cls: "ce-chip-danger" },
  processing: { label: "Processing", cls: "ce-chip-accent" },
};

export default function StatusChip({ status }) {
  const info = STATUS_MAP[status] || { label: "Queued", cls: "ce-chip-muted" };
  return <span className={`ce-chip ${info.cls}`}>{info.label}</span>;
}

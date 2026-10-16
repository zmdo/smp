export function StatusPill({ value, label }: { value: string; label: string }) {
  return <span className={`pill ${value}`}>{label}</span>;
}

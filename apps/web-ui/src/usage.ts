export function percentOf(used: number | null, total: number | null): number | null {
  if (used === null || total === null || total <= 0) return null;
  return Math.max(0, Math.min(100, Math.round((used / total) * 100)));
}

export function formatBytes(value: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  const digits = size >= 10 || index === 0 ? 0 : 1;
  return `${size.toFixed(digits)} ${units[index]}`;
}

export function byteCaption(used: number | null, total: number | null): string {
  if (used === null || total === null) return "";
  return `${formatBytes(used)} / ${formatBytes(total)}`;
}

export function usageLevel(percent: number): "ok" | "warn" | "hot" {
  if (percent <= 80) return "ok";
  if (percent < 90) return "warn";
  return "hot";
}

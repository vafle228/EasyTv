export function formatSize(bytes: number | null): string {
  if (bytes == null) return "";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} КБ`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(bytes < 10 * 1024 ** 2 ? 1 : 0)} МБ`;
  return `${(bytes / 1024 ** 3).toFixed(1)} ГБ`;
}

export function formatTime(seconds: number | null): string {
  if (seconds == null) return "–:––";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const mm = h ? String(m).padStart(2, "0") : String(m);
  return `${h ? `${h}:` : ""}${mm}:${String(s).padStart(2, "0")}`;
}

export function tvSubtitle(manufacturer: string | null, model: string | null, ip: string): string {
  return [model ?? manufacturer, ip].filter(Boolean).join(", ");
}

const naira = new Intl.NumberFormat("en-NG", { maximumFractionDigits: 2, minimumFractionDigits: 0 });

/** "15200.50" -> "₦15,200.5", "-2500.00" -> "-₦2,500" */
export function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  const formatted = naira.format(Math.abs(n));
  return `${n < 0 ? "-" : ""}₦${formatted}`;
}

/** "5.00" -> "5", "0.50" -> "0.5" */
export function qty(value: string | number): string {
  return String(Number(value));
}

export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-NG", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function timeAgo(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

/** plural(1, "item") -> "1 item", plural(3, "item") -> "3 items" */
export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

export const AGE_GROUPS = ["child", "teen", "adult", "elderly"] as const;

export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

import type { ErrandStatus } from "@/lib/types";
import { Badge } from "./ui";

const LABELS: Record<ErrandStatus, { label: string; tone: "yellow" | "orange" | "green" }> = {
  assigned: { label: "Not started", tone: "yellow" },
  in_progress: { label: "Shopping", tone: "orange" },
  completed: { label: "Done", tone: "green" },
};

export function ErrandStatusBadge({ status }: { status: ErrandStatus }) {
  const { label, tone } = LABELS[status];
  return <Badge tone={tone}>{label}</Badge>;
}

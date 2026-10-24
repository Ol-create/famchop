"use client";

import Link from "next/link";
import { dateTime, money } from "@/lib/format";
import { useErrands, useMe } from "@/lib/queries";
import type { Errand } from "@/lib/types";
import { Card, EmptyState, PageHeader, PageLoading } from "@/components/ui";
import { ErrandStatusBadge } from "@/components/ErrandStatusBadge";

function ErrandRow({ e, mine }: { e: Errand; mine: boolean }) {
  const pct = e.item_count ? Math.round((e.bought_count / e.item_count) * 100) : 0;
  return (
    <Link href={`/errands/${e.id}`} className="block">
      <Card className={`transition-shadow hover:shadow-md ${mine && e.status !== "completed" ? "border-2 border-accent" : ""}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-heading font-semibold">
              {mine ? "Your shopping" : `${e.assigned_to.name}'s shopping`}
              {e.market ? ` at ${e.market}` : ""}
            </p>
            <p className="text-sm text-muted">
              {money(e.released_amount)} released by {e.assigned_by?.name ?? "an admin"} · {dateTime(e.created_at)}
            </p>
          </div>
          <ErrandStatusBadge status={e.status} />
        </div>
        <div className="mt-3 flex items-center gap-3 text-sm">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-cocoa/10">
            <div className="h-full rounded-full bg-secondary" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-muted">
            {e.bought_count}/{e.item_count} items
          </span>
        </div>
        {e.status === "completed" && e.change !== null && (
          <p className="mt-2 text-sm">
            Spent {money(e.actual_spent)} ·{" "}
            {Number(e.change) >= 0 ? (
              <span className="text-secondary">{money(e.change)} returned</span>
            ) : (
              <span className="text-danger">{money(-Number(e.change))} reimbursed</span>
            )}
          </p>
        )}
      </Card>
    </Link>
  );
}

export default function ErrandsPage() {
  const me = useMe().data!;
  const errands = useErrands();
  if (errands.isLoading) return <PageLoading />;

  const all = errands.data ?? [];
  const mine = all.filter((e) => e.assigned_to.id === me.id);
  const others = all.filter((e) => e.assigned_to.id !== me.id);

  return (
    <div className="space-y-6">
      <PageHeader title="Shopping" subtitle="Market trips for your family's approved meal plans." />

      {all.length === 0 && (
        <EmptyState title="No shopping errands yet">
          {me.role === "admin" ? (
            <>
              Approve a{" "}
              <Link href="/plan" className="font-medium text-primary hover:underline">
                meal plan
              </Link>
              , then send someone to market.
            </>
          ) : (
            "When an admin sends you to market, your list will appear here."
          )}
        </EmptyState>
      )}

      {mine.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Assigned to you</h2>
          {mine.map((e) => <ErrandRow key={e.id} e={e} mine />)}
        </section>
      )}

      {others.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Family errands</h2>
          {others.map((e) => <ErrandRow key={e.id} e={e} mine={false} />)}
        </section>
      )}
    </div>
  );
}

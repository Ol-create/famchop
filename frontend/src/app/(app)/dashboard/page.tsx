"use client";

import Link from "next/link";
import { useErrands, useFamily, useLatestPlan, useMe, useMyErrands, usePrices } from "@/lib/queries";
import { money, plural, timeAgo } from "@/lib/format";
import { Badge, BudgetBar, Card, CardTitle, PageLoading } from "@/components/ui";
import { InviteCode } from "@/components/InviteCode";
import { ErrandStatusBadge } from "@/components/ErrandStatusBadge";

export default function Dashboard() {
  const me = useMe().data!;
  const family = useFamily();
  const plan = useLatestPlan();
  const myErrands = useMyErrands();
  const errands = useErrands();
  const prices = usePrices();

  if (family.isLoading) return <PageLoading />;
  const f = family.data;
  if (!f) return null;

  const isAdmin = me.role === "admin";
  const openMine = myErrands.data?.filter((e) => e.status !== "completed") ?? [];
  const unpriced = prices.data?.filter((p) => p.price === null).length ?? 0;
  const recentErrands = (errands.data ?? []).slice(0, 3);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-muted">Hello {me.name.split(" ")[0]} 👋</p>
        <h1 className="text-2xl font-bold sm:text-3xl">{f.name}</h1>
      </div>

      {openMine.map((e) => (
        <Link key={e.id} href={`/errands/${e.id}`} className="block">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border-2 border-accent bg-accent/10 p-4 hover:bg-accent/20">
            <div>
              <p className="font-heading font-semibold">🛒 You have shopping to do{e.market ? ` at ${e.market}` : ""}</p>
              <p className="text-sm text-muted">
                {e.bought_count} of {e.item_count} items bought · {money(e.released_amount)} released by {e.assigned_by?.name}
              </p>
            </div>
            <span className="font-medium text-primary">Open list →</span>
          </div>
        </Link>
      ))}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardTitle action={<Link href="/wallet" className="text-sm font-medium text-primary">View →</Link>}>
            Family wallet
          </CardTitle>
          <p className="text-3xl font-bold text-secondary">{money(f.wallet_balance)}</p>
          <p className="mt-1 text-xs text-muted">Simulated money for planning and errands</p>
        </Card>

        <Card>
          <CardTitle>Invite your family</CardTitle>
          <InviteCode code={f.invite_code} familyName={f.name} />
          <p className="mt-3 text-sm text-muted">
            {f.members.length} {f.members.length === 1 ? "member" : "members"}:{" "}
            {f.members.map((m) => m.name).join(", ")}
          </p>
        </Card>
      </div>

      <Card>
        <CardTitle action={<Link href="/plan" className="text-sm font-medium text-primary">{plan.data ? "Open plan →" : ""}</Link>}>
          This week&apos;s meal plan
        </CardTitle>
        {plan.isLoading ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : plan.data ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <Badge tone={plan.data.status === "approved" ? "green" : "yellow"}>{plan.data.status}</Badge>
              <span className="text-muted">created {timeAgo(plan.data.created_at)}</span>
            </div>
            <BudgetBar spent={plan.data.total_cost} budget={plan.data.budget} />
            {plan.data.menu[0] && (
              <p className="text-sm">
                <span className="text-muted">{plan.data.menu[0].day}: </span>
                {plan.data.menu[0].breakfast} · {plan.data.menu[0].lunch} · {plan.data.menu[0].dinner}
              </p>
            )}
          </div>
        ) : (
          <div className="text-sm text-muted">
            <p>No plan yet.</p>
            {isAdmin ? (
              <p className="mt-1">
                {unpriced > 0 && (
                  <>
                    First{" "}
                    <Link href="/prices" className="font-medium text-primary hover:underline">
                      fill in your market prices
                    </Link>{" "}
                    ({plural(unpriced, "item")} without a price), then{" "}
                  </>
                )}
                <Link href="/plan" className="font-medium text-primary hover:underline">
                  {unpriced > 0 ? "plan your week" : "Plan your week"}
                </Link>
                .
              </p>
            ) : (
              <p className="mt-1">An admin will create this week&apos;s plan.</p>
            )}
          </div>
        )}
      </Card>

      {recentErrands.length > 0 && (
        <Card>
          <CardTitle action={<Link href="/errands" className="text-sm font-medium text-primary">All →</Link>}>
            Shopping errands
          </CardTitle>
          <ul className="divide-y divide-cocoa/10">
            {recentErrands.map((e) => (
              <li key={e.id}>
                <Link href={`/errands/${e.id}`} className="flex items-center justify-between gap-3 py-3 hover:text-primary">
                  <span>
                    <span className="font-medium">{e.assigned_to.name}</span>
                    <span className="text-sm text-muted">
                      {" "}
                      · {e.bought_count}/{e.item_count} items · {money(e.released_amount)}
                    </span>
                  </span>
                  <ErrandStatusBadge status={e.status} />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

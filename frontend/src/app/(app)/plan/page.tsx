"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { money, plural, qty, timeAgo } from "@/lib/format";
import { keys, useErrands, useFamily, useLatestPlan, useMe, usePrices } from "@/lib/queries";
import type { NutritionAnalysis, Plan } from "@/lib/types";
import { Badge, Button, BudgetBar, Card, CardTitle, EmptyState, Field, Input, PageHeader, PageLoading, Textarea } from "@/components/ui";
import { AiProgress } from "@/components/AiProgress";
import { AssignErrandModal } from "@/components/AssignErrandModal";
import { ErrandStatusBadge } from "@/components/ErrandStatusBadge";

const PLAN_MESSAGES = [
  "Reading your market prices…",
  "Checking who's eating this week…",
  "Picking familiar Nigerian meals…",
  "Balancing protein for the kids…",
  "Building the shopping list…",
  "Keeping it inside your budget…",
  "Double-checking quantities…",
  "Almost there…",
];

export default function PlanPage() {
  const me = useMe().data!;
  const isAdmin = me.role === "admin";
  const plan = useLatestPlan();
  const family = useFamily();
  const prices = usePrices();
  const errands = useErrands();
  const queryClient = useQueryClient();
  const [assignOpen, setAssignOpen] = useState(false);

  const current = plan.data;
  const isDraft = current?.status === "draft";
  const errand = current ? errands.data?.find((e) => e.plan_id === current.id) : undefined;
  const unpricedPrices = prices.data?.filter((p) => p.price === null).length ?? 0;

  const onPlan = (p: Plan) => {
    queryClient.setQueryData(keys.latestPlan, p);
  };

  const generate = useMutation({
    mutationFn: (body: object) =>
      isDraft && current
        ? api<Plan>(`/plans/${current.id}/regenerate`, { method: "POST", json: body })
        : api<Plan>("/plans", { method: "POST", json: body }),
    onSuccess: (p) => {
      onPlan(p);
      toast.success(p.over_budget ? "Plan ready, but it's over budget. See the suggested swaps." : "Your week is planned!");
    },
    onError: (e) => toast.error(e.message),
  });

  const approve = useMutation({
    mutationFn: (id: number) => api<Plan>(`/plans/${id}/approve`, { method: "POST" }),
    onSuccess: (p) => {
      onPlan(p);
      toast.success("Plan approved. Now send someone to market.");
    },
    onError: (e) => toast.error(e.message),
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    generate.mutate({
      budget: String(form.get("budget")),
      notes: String(form.get("notes") ?? ""),
      pantry: String(form.get("pantry") ?? ""),
    });
  }

  if (plan.isLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Meal plan"
        subtitle={current ? `Created ${timeAgo(current.created_at)}` : "Plan a week of meals your family will eat, within budget."}
        action={current && <Badge tone={current.status === "approved" ? "green" : "yellow"}>{current.status}</Badge>}
      />

      {isAdmin && (!current || isDraft || current.status === "approved") && (
        <Card>
          <CardTitle>{isDraft ? "Change and regenerate" : current ? "Plan next week" : "Plan your week"}</CardTitle>
          {unpricedPrices > 0 && (
            <p className="mb-4 rounded-lg bg-accent/10 p-3 text-sm text-[#9a6400]">
              {plural(unpricedPrices, "item")} on your{" "}
              <Link href="/prices" className="font-medium underline">
                price list
              </Link>{" "}
              {unpricedPrices === 1 ? "has" : "have"} no price yet. Items without a price won&apos;t count towards the total.
            </p>
          )}
          <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2" key={current?.id ?? "new"}>
            <Field label="Weekly budget (₦)" hint={family.data ? `Wallet balance: ${money(family.data.wallet_balance)}` : undefined}>
              <Input
                name="budget"
                type="number"
                inputMode="decimal"
                min="1"
                step="0.01"
                required
                defaultValue={current ? Number(current.budget) : ""}
                placeholder="45000"
              />
            </Field>
            <Field label="Preferences (optional)" hint="Each member's dislikes are already included.">
              <Input name="notes" maxLength={500} defaultValue={isDraft ? current?.notes ?? "" : ""} placeholder="e.g. no pork, more fish" />
            </Field>
            <div className="sm:col-span-2">
              <Field label="Already in the kitchen (optional)" hint="These won't be bought again.">
                <Textarea name="pantry" maxLength={500} defaultValue={isDraft ? current?.pantry ?? "" : ""} placeholder="e.g. half bag of rice, palm oil, onions" />
              </Field>
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" size="lg" loading={generate.isPending}>
                {isDraft ? "Regenerate plan" : "Plan my week"}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {generate.isPending && <AiProgress messages={PLAN_MESSAGES} expected="30–60 seconds" />}

      <NutritionCard />

      {!current && !generate.isPending && (
        <EmptyState title="No meal plan yet">{isAdmin ? "Set a budget above and let FamChop plan the week." : "An admin will create this week's plan."}</EmptyState>
      )}

      {current && !generate.isPending && (
        <>
          <Card>
            <CardTitle>Budget</CardTitle>
            <BudgetBar spent={current.total_cost} budget={current.budget} label="planned of" />
            {current.unpriced_items.length > 0 && (
              <p className="mt-3 text-sm text-muted">
                Not counted (no price yet): {current.unpriced_items.join(", ")}
              </p>
            )}
            {current.swaps.length > 0 && (
              <div className="mt-4 rounded-xl bg-danger/5 p-4">
                <p className="font-heading font-semibold text-danger">Cheaper swaps to get within budget</p>
                <ul className="mt-2 space-y-1 text-sm">
                  {current.swaps.map((s, i) => (
                    <li key={i}>
                      <span className="font-medium">{s.from_item}</span> → <span className="font-medium text-secondary">{s.to_item}</span>
                      <span className="text-muted"> · {s.reason}</span>
                    </li>
                  ))}
                </ul>
                {isDraft && isAdmin && <p className="mt-2 text-xs text-muted">Add a swap to Preferences above and regenerate, or raise the budget.</p>}
              </div>
            )}

            {isAdmin && (
              <div className="mt-5 flex flex-wrap gap-2">
                {isDraft && (
                  <Button variant="secondary" onClick={() => approve.mutate(current.id)} loading={approve.isPending}>
                    Approve plan
                  </Button>
                )}
                {current.status === "approved" && !errand && (
                  <Button variant="secondary" onClick={() => setAssignOpen(true)}>
                    Send someone to market
                  </Button>
                )}
              </div>
            )}
            {errand && (
              <Link
                href={`/errands/${errand.id}`}
                className="mt-5 flex items-center justify-between gap-3 rounded-xl border border-cocoa/10 p-3 hover:bg-cream"
              >
                <span className="text-sm">
                  <span className="font-medium">{errand.assigned_to.name}</span> is shopping for this plan · {errand.bought_count}/{errand.item_count} bought
                </span>
                <ErrandStatusBadge status={errand.status} />
              </Link>
            )}
          </Card>

          <MenuCard plan={current} />

          <div className="grid gap-6 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <GroceryCard plan={current} />
            </div>
            <div className="lg:col-span-2">
              <NutritionScoreCard plan={current} />
            </div>
          </div>

          <p className="text-center text-xs text-muted">{current.disclaimer}</p>
          <AssignErrandModal plan={current} open={assignOpen} onClose={() => setAssignOpen(false)} />
        </>
      )}
    </div>
  );
}

function MenuCard({ plan }: { plan: Plan }) {
  return (
    <Card>
      <CardTitle>7-day menu</CardTitle>
      {/* Table on wide screens */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-sm">
          <thead className="text-left text-muted">
            <tr>
              <th className="py-2 pr-3 font-medium">Day</th>
              <th className="py-2 pr-3 font-medium">Breakfast</th>
              <th className="py-2 pr-3 font-medium">Lunch</th>
              <th className="py-2 font-medium">Dinner</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-cocoa/10">
            {plan.menu.map((d) => (
              <tr key={d.day} className="align-top">
                <td className="py-2.5 pr-3 font-semibold text-primary">{d.day}</td>
                <td className="py-2.5 pr-3">{d.breakfast}</td>
                <td className="py-2.5 pr-3">{d.lunch}</td>
                <td className="py-2.5">{d.dinner}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* Cards on phones */}
      <ul className="space-y-3 md:hidden">
        {plan.menu.map((d) => (
          <li key={d.day} className="rounded-xl bg-cream p-3 text-sm">
            <p className="mb-1 font-semibold text-primary">{d.day}</p>
            <p><span className="text-muted">Breakfast:</span> {d.breakfast}</p>
            <p><span className="text-muted">Lunch:</span> {d.lunch}</p>
            <p><span className="text-muted">Dinner:</span> {d.dinner}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function GroceryCard({ plan }: { plan: Plan }) {
  return (
    <Card>
      <CardTitle>Shopping list</CardTitle>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-muted">
            <tr>
              <th className="py-2 pr-2 font-medium">Item</th>
              <th className="py-2 pr-2 text-right font-medium">Qty</th>
              <th className="py-2 pr-2 text-right font-medium">Price</th>
              <th className="py-2 text-right font-medium">Subtotal</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-cocoa/10">
            {plan.items.map((i) => (
              <tr key={i.id}>
                <td className="py-2 pr-2">{i.item}</td>
                <td className="whitespace-nowrap py-2 pr-2 text-right">
                  {qty(i.quantity)} {i.unit}
                </td>
                <td className="whitespace-nowrap py-2 pr-2 text-right text-muted">{i.unit_price ? money(i.unit_price) : "no price"}</td>
                <td className="whitespace-nowrap py-2 text-right font-medium">{i.unit_price ? money(i.subtotal) : "—"}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-cocoa/15">
              <td colSpan={3} className="py-2 font-semibold">Total</td>
              <td className={`py-2 text-right font-bold ${plan.over_budget ? "text-danger" : "text-secondary"}`}>{money(plan.total_cost)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted">Costs are calculated from your own price list, not by the AI.</p>
    </Card>
  );
}

function NutritionScoreCard({ plan }: { plan: Plan }) {
  if (!plan.nutrition) return null;
  const { score, note, tips } = plan.nutrition;
  const bars: [string, number][] = [
    ["Protein", score.protein],
    ["Carbs", score.carbs],
    ["Vegetables", score.vegetables],
    ["Fruit", score.fruit],
  ];
  return (
    <Card>
      <CardTitle>Nutrition balance</CardTitle>
      <div className="space-y-2.5">
        {bars.map(([label, value]) => (
          <div key={label} className="flex items-center gap-3 text-sm">
            <span className="w-20 shrink-0">{label}</span>
            <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-cocoa/10">
              <div
                className={`h-full rounded-full ${value >= 7 ? "bg-secondary" : value >= 4 ? "bg-accent" : "bg-danger"}`}
                style={{ width: `${value * 10}%` }}
              />
            </div>
            <span className="w-8 text-right font-medium">{value}/10</span>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm">{note}</p>
      {tips.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
          {tips.map((t, i) => <li key={i}>{t}</li>)}
        </ul>
      )}
    </Card>
  );
}

function NutritionCard() {
  const analyze = useMutation({
    mutationFn: () => api<NutritionAnalysis>("/nutrition/analyze", { method: "POST" }),
    onError: (e) => toast.error(e.message),
  });

  return (
    <Card>
      <CardTitle
        action={
          <Button variant="outline" size="sm" onClick={() => analyze.mutate()} loading={analyze.isPending}>
            {analyze.data ? "Analyze again" : "Analyze our needs"}
          </Button>
        }
      >
        Family nutrition needs
      </CardTitle>
      {analyze.isPending ? (
        <AiProgress messages={["Looking at everyone's ages…", "Thinking about growing kids…", "Picking affordable foods…"]} expected="10–20 seconds" />
      ) : analyze.data ? (
        <div className="space-y-4 text-sm">
          <ul className="space-y-1.5">
            {analyze.data.priorities.map((p, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-secondary">●</span>
                {p}
              </li>
            ))}
          </ul>
          {analyze.data.focus_foods.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {analyze.data.focus_foods.map((f) => <Badge key={f} tone="green">{f}</Badge>)}
            </div>
          )}
          {analyze.data.tips.length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-muted">
              {analyze.data.tips.map((t, i) => <li key={i}>{t}</li>)}
            </ul>
          )}
          <p className="text-xs text-muted">{analyze.data.disclaimer}</p>
        </div>
      ) : (
        <p className="text-sm text-muted">See what your household needs most this week, based on everyone&apos;s age and what they avoid.</p>
      )}
    </Card>
  );
}

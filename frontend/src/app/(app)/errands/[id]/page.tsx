"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { dateTime, money, qty } from "@/lib/format";
import { keys, useErrand, useMe } from "@/lib/queries";
import type { Errand, ErrandItem } from "@/lib/types";
import { Button, Card, CardTitle, ErrorNote, Modal, PageLoading } from "@/components/ui";
import { ErrandStatusBadge } from "@/components/ErrandStatusBadge";

export default function ErrandPage() {
  const id = Number(useParams<{ id: string }>().id);
  const me = useMe().data!;
  const errand = useErrand(id);
  const queryClient = useQueryClient();
  const [confirmOpen, setConfirmOpen] = useState(false);

  const refreshRelated = () => {
    queryClient.invalidateQueries({ queryKey: keys.errands });
    queryClient.invalidateQueries({ queryKey: keys.wallet });
    queryClient.invalidateQueries({ queryKey: keys.family });
    queryClient.invalidateQueries({ queryKey: keys.prices });
  };

  const updateItem = useMutation({
    mutationFn: ({ itemId, body }: { itemId: number; body: object }) =>
      api<Errand>(`/errands/${id}/items/${itemId}`, { method: "PATCH", json: body }),
    onSuccess: (e) => queryClient.setQueryData(keys.errand(id), e),
    onError: (e) => toast.error(e.message),
  });

  const complete = useMutation({
    mutationFn: () => api<Errand>(`/errands/${id}/complete`, { method: "POST" }),
    onSuccess: (e) => {
      queryClient.setQueryData(keys.errand(id), e);
      refreshRelated();
      setConfirmOpen(false);
      toast.success("Shopping complete! The wallet has been updated.");
    },
    onError: (e) => toast.error(e.message),
  });

  if (errand.isLoading) return <PageLoading />;
  if (errand.error || !errand.data) return <ErrorNote error={errand.error} />;
  const e = errand.data;

  const isShopper = e.assigned_to.id === me.id;
  const isAdmin = me.role === "admin";
  const done = e.status === "completed";
  const canEdit = isShopper && !done;
  const change = Number(e.released_amount) - Number(e.spent_so_far);
  // Bought items with no planned price need an actual price before the errand can be finished
  const needsPrice = e.items.filter((i) => i.bought && i.unit_price === null && i.actual_price === null).map((i) => i.item);

  return (
    <div className="space-y-6 pb-24">
      <div>
        <Link href="/errands" className="text-sm text-muted hover:text-primary">
          ← All shopping
        </Link>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold sm:text-3xl">
            {isShopper ? "Your shopping list" : `${e.assigned_to.name}'s shopping`}
          </h1>
          <ErrandStatusBadge status={e.status} />
        </div>
        <p className="mt-1 text-muted">
          {e.market ? `${e.market} · ` : ""}
          {money(e.released_amount)} from {e.assigned_by?.name ?? "the wallet"} · {dateTime(e.created_at)}
        </p>
      </div>

      {done ? <ResultCard e={e} /> : <ProgressCard e={e} />}

      <Card className="p-0 sm:p-0">
        <div className="border-b border-cocoa/10 px-5 py-4">
          <h2 className="text-lg font-semibold">Items</h2>
          {canEdit && <p className="text-sm text-muted">Tick items as you buy them. If you paid a different amount, type what you paid.</p>}
        </div>
        <ul className="divide-y divide-cocoa/10">
          {e.items.map((item) => (
            <ItemRow
              key={item.id}
              item={item}
              editable={canEdit}
              done={done}
              saving={updateItem.isPending && updateItem.variables?.itemId === item.id}
              onChange={(body) => updateItem.mutate({ itemId: item.id, body })}
            />
          ))}
        </ul>
      </Card>

      {!done && (isShopper || isAdmin) && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-cocoa/10 bg-surface/95 backdrop-blur">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
            <span className="text-sm">
              Spent <span className="font-semibold">{money(e.spent_so_far)}</span> of {money(e.released_amount)}
              <span className={change >= 0 ? "text-secondary" : "text-danger"}>
                {" "}
                · {change >= 0 ? `${money(change)} change` : `${money(-change)} over`}
              </span>
            </span>
            <Button variant="secondary" onClick={() => setConfirmOpen(true)}>
              {isShopper ? "Finish shopping" : `Complete for ${e.assigned_to.name}`}
            </Button>
          </div>
        </div>
      )}

      <Modal open={confirmOpen} onClose={() => setConfirmOpen(false)} title="Finish shopping?">
        <div className="space-y-2 text-sm">
          <p>
            {e.bought_count} of {e.item_count} items bought.
            {e.bought_count < e.item_count && " Items not ticked count as not bought."}
          </p>
          <dl className="space-y-1 rounded-xl bg-cream p-3">
            <div className="flex justify-between"><dt>Money released</dt><dd>{money(e.released_amount)}</dd></div>
            <div className="flex justify-between"><dt>Spent</dt><dd>{money(e.spent_so_far)}</dd></div>
            <div className={`flex justify-between font-semibold ${change >= 0 ? "text-secondary" : "text-danger"}`}>
              <dt>{change >= 0 ? "Change back to wallet" : "Wallet reimburses"}</dt>
              <dd>{money(Math.abs(change))}</dd>
            </div>
          </dl>
          {needsPrice.length > 0 ? (
            <p className="rounded-lg bg-danger/5 p-3 text-danger">
              Enter what {isShopper ? "you" : e.assigned_to.name} paid for {needsPrice.join(", ")} first. {needsPrice.length === 1 ? "It has" : "They have"} no planned price.
            </p>
          ) : (
            <p className="text-muted">Prices you entered will update the family price list.</p>
          )}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirmOpen(false)}>Keep shopping</Button>
          <Button variant="secondary" onClick={() => complete.mutate()} loading={complete.isPending} disabled={needsPrice.length > 0}>
            Yes, finish
          </Button>
        </div>
      </Modal>
    </div>
  );
}

function ProgressCard({ e }: { e: Errand }) {
  const pct = e.item_count ? Math.round((e.bought_count / e.item_count) * 100) : 0;
  return (
    <Card>
      <div className="flex items-center justify-between text-sm">
        <span>
          <span className="text-lg font-semibold">{e.bought_count}</span> of {e.item_count} items bought
        </span>
        <span className="text-muted">Planned {money(e.planned_total)}</span>
      </div>
      <div className="mt-2 h-3 overflow-hidden rounded-full bg-cocoa/10">
        <div className="h-full rounded-full bg-secondary transition-all" style={{ width: `${pct}%` }} />
      </div>
    </Card>
  );
}

function ResultCard({ e }: { e: Errand }) {
  const change = Number(e.change);
  return (
    <Card className="border-2 border-secondary/30">
      <CardTitle>Shopping done ✅</CardTitle>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="rounded-xl bg-cream p-3">
          <p className="text-xs text-muted">Released</p>
          <p className="font-semibold">{money(e.released_amount)}</p>
        </div>
        <div className="rounded-xl bg-cream p-3">
          <p className="text-xs text-muted">Spent</p>
          <p className="font-semibold">{money(e.actual_spent)}</p>
        </div>
        <div className={`rounded-xl p-3 ${change >= 0 ? "bg-secondary/10 text-secondary" : "bg-danger/10 text-danger"}`}>
          <p className="text-xs">{change >= 0 ? "Change returned" : "Reimbursed"}</p>
          <p className="font-semibold">{money(Math.abs(change))}</p>
        </div>
      </div>
      <p className="mt-3 text-sm text-muted">
        Finished {e.completed_at ? dateTime(e.completed_at) : ""}. The wallet and the family price list have been updated.
      </p>
    </Card>
  );
}

function ItemRow({
  item,
  editable,
  done,
  saving,
  onChange,
}: {
  item: ErrandItem;
  editable: boolean;
  done: boolean;
  saving: boolean;
  onChange: (body: object) => void;
}) {
  const current = item.actual_price === null ? "" : String(Number(item.actual_price));
  const [price, setPrice] = useState(current);
  useEffect(() => setPrice(current), [current]);

  const planned = Number(item.planned_cost);
  const paid = item.actual_price !== null ? Number(item.actual_price) : null;
  const diff = paid !== null && item.unit_price !== null ? paid - planned : null;

  function savePrice() {
    const trimmed = price.trim();
    if (trimmed === current) return;
    if (trimmed !== "" && (Number.isNaN(Number(trimmed)) || Number(trimmed) < 0)) {
      toast.error("Enter a valid amount");
      setPrice(current);
      return;
    }
    onChange({ actual_price: trimmed === "" ? null : trimmed });
  }

  return (
    <li className={`flex flex-wrap items-center gap-3 px-5 py-3 ${item.bought ? "bg-secondary/5" : ""}`}>
      <input
        type="checkbox"
        checked={item.bought}
        disabled={!editable || saving}
        onChange={(e) => onChange({ bought: e.target.checked })}
        className="h-6 w-6 shrink-0 cursor-pointer rounded accent-secondary disabled:cursor-default"
        aria-label={`Bought ${item.item}`}
      />
      <div className="min-w-[8rem] flex-1">
        <p className={`font-medium ${item.bought && done ? "" : item.bought ? "text-secondary" : ""}`}>{item.item}</p>
        <p className="text-sm text-muted">
          {qty(item.quantity)} {item.unit} · planned {item.unit_price !== null ? money(planned) : "no price"}
        </p>
      </div>
      {editable ? (
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted">Paid ₦</span>
          <input
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            onBlur={savePrice}
            onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
            type="number"
            inputMode="decimal"
            min="0"
            step="0.01"
            placeholder={item.unit_price !== null ? String(planned) : "required"}
            className={`w-28 rounded-lg border px-2 py-1.5 text-right text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 ${
              item.bought && item.unit_price === null && paid === null ? "border-danger" : "border-cocoa/15"
            }`}
            aria-label={`Amount paid for ${item.item}`}
          />
        </label>
      ) : (
        item.bought && (
          <span className="text-sm">
            {paid !== null ? money(paid) : money(planned)}
            {diff !== null && diff !== 0 && (
              <span className={diff > 0 ? "text-danger" : "text-secondary"}>
                {" "}
                ({diff > 0 ? "+" : "-"}
                {money(Math.abs(diff))})
              </span>
            )}
          </span>
        )
      )}
    </li>
  );
}

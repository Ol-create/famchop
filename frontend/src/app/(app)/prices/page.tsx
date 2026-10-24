"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { money, timeAgo } from "@/lib/format";
import { keys, useMe, usePrices } from "@/lib/queries";
import type { Price } from "@/lib/types";
import { Badge, Button, Card, Input, PageHeader, PageLoading } from "@/components/ui";

interface Row {
  key: string;
  item: string;
  unit: string;
  price: string; // "" = not priced yet
  updated_at?: string;
}

let nextKey = 0;
const toRows = (prices: Price[]): Row[] =>
  prices.map((p) => ({
    key: `p${p.id}`,
    item: p.item,
    unit: p.unit,
    price: p.price === null ? "" : String(Number(p.price)),
    updated_at: p.updated_at,
  }));

const snapshot = (rows: Row[]) => JSON.stringify(rows.map(({ item, unit, price }) => [item.trim(), unit.trim(), price.trim()]));

function problems(rows: Row[]): string | null {
  const seen = new Set<string>();
  for (const r of rows) {
    if (!r.item.trim() || !r.unit.trim()) return "Every row needs an item and a unit.";
    if (r.price.trim() && (Number.isNaN(Number(r.price)) || Number(r.price) < 0)) return `Check the price for ${r.item}.`;
    const k = `${r.item.trim().toLowerCase()}|${r.unit.trim().toLowerCase()}`;
    if (seen.has(k)) return `${r.item} (${r.unit}) is listed twice.`;
    seen.add(k);
  }
  return null;
}

export default function PricesPage() {
  const me = useMe().data!;
  const prices = usePrices();
  const queryClient = useQueryClient();
  const isAdmin = me.role === "admin";

  const [rows, setRows] = useState<Row[]>([]);
  const [saved, setSaved] = useState("[]");

  useEffect(() => {
    if (prices.data) {
      const r = toRows(prices.data);
      setRows(r);
      setSaved(snapshot(r));
    }
  }, [prices.data]);

  const dirty = snapshot(rows) !== saved;
  const error = useMemo(() => problems(rows), [rows]);
  const unpriced = rows.filter((r) => !r.price.trim()).length;

  // Warn before leaving with unsaved edits
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const save = useMutation({
    mutationFn: () =>
      api<Price[]>("/prices", {
        method: "PUT",
        json: {
          items: rows.map((r) => ({ item: r.item, unit: r.unit, price: r.price.trim() === "" ? null : r.price.trim() })),
        },
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(keys.prices, data);
      toast.success("Prices saved");
    },
    onError: (e) => toast.error(e.message),
  });

  const update = (key: string, field: "item" | "unit" | "price", value: string) =>
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, [field]: value } : r)));

  if (prices.isLoading) return <PageLoading />;

  return (
    <div className="space-y-6 pb-20">
      <PageHeader
        title="Market prices"
        subtitle="What you actually pay at your market. The meal plan uses these for every cost."
        action={unpriced > 0 ? <Badge tone="yellow">{unpriced} without a price</Badge> : <Badge tone="green">All priced</Badge>}
      />

      <Card className="p-0 sm:p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-cocoa/10 text-left text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Item</th>
                <th className="px-2 py-3 font-medium">Unit</th>
                <th className="px-2 py-3 font-medium">Price (₦)</th>
                {isAdmin && <th className="w-10 px-2 py-3" aria-label="Remove" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-cocoa/5">
              {rows.map((r) =>
                isAdmin ? (
                  <tr key={r.key}>
                    <td className="px-4 py-2">
                      <Input value={r.item} onChange={(e) => update(r.key, "item", e.target.value)} aria-label="Item" maxLength={120} className="min-w-[9rem]" />
                    </td>
                    <td className="px-2 py-2">
                      <Input value={r.unit} onChange={(e) => update(r.key, "unit", e.target.value)} aria-label="Unit" maxLength={40} className="w-24" />
                    </td>
                    <td className="px-2 py-2">
                      <Input
                        value={r.price}
                        onChange={(e) => update(r.key, "price", e.target.value)}
                        aria-label={`Price for ${r.item || "item"}`}
                        type="number"
                        inputMode="decimal"
                        min="0"
                        step="0.01"
                        placeholder="Enter price"
                        className={`w-32 ${r.price.trim() ? "" : "border-accent bg-accent/5"}`}
                      />
                    </td>
                    <td className="px-2 py-2">
                      <button
                        onClick={() => setRows((rs) => rs.filter((x) => x.key !== r.key))}
                        className="rounded-lg p-2 text-muted hover:bg-danger/10 hover:text-danger"
                        aria-label={`Remove ${r.item}`}
                      >
                        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ) : (
                  <tr key={r.key}>
                    <td className="px-4 py-3 font-medium">{r.item}</td>
                    <td className="px-2 py-3 text-muted">per {r.unit}</td>
                    <td className="px-2 py-3">
                      {r.price ? money(r.price) : <span className="text-muted">not set</span>}
                      {r.updated_at && r.price && <span className="ml-2 text-xs text-muted">{timeAgo(r.updated_at)}</span>}
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
        {isAdmin && (
          <div className="border-t border-cocoa/10 p-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRows((rs) => [...rs, { key: `new${nextKey++}`, item: "", unit: "", price: "" }])}
            >
              + Add item
            </Button>
          </div>
        )}
      </Card>

      {!isAdmin && <p className="text-sm text-muted">Only admins can edit prices. Prices also update automatically from what shoppers pay.</p>}

      {isAdmin && dirty && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-cocoa/10 bg-surface/95 backdrop-blur">
          <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
            <span className={`text-sm ${error ? "text-danger" : "text-muted"}`}>{error ?? "You have unsaved changes"}</span>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => prices.data && setRows(toRows(prices.data))}>
                Discard
              </Button>
              <Button onClick={() => save.mutate()} loading={save.isPending} disabled={!!error}>
                Save prices
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

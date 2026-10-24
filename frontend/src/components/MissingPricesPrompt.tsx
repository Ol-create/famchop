"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { toast } from "sonner";
import { api, getToken } from "@/lib/api";
import { plural } from "@/lib/format";
import { keys, usePrices } from "@/lib/queries";
import type { Price } from "@/lib/types";
import { Button, Modal } from "./ui";

const keyOf = (item: string, unit: string) => `${item.trim().toLowerCase()}|${unit.trim().toLowerCase()}`;

/**
 * Lists the family's foods that have no price (plus any `extraItems` not on the list yet, e.g. from a plan)
 * and saves whatever the user fills in. Only admins can save prices.
 */
export function PricesModal({
  open,
  onClose,
  title = "Add your market prices",
  intro,
  extraItems = [],
  onSaved,
  secondaryAction,
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  intro?: ReactNode;
  extraItems?: { item: string; unit: string }[];
  onSaved?: (prices: Price[]) => void;
  secondaryAction?: { label: string; onClick: () => void };
}) {
  const prices = usePrices();
  const queryClient = useQueryClient();
  const [values, setValues] = useState<Record<string, string>>({});

  const listed = new Set((prices.data ?? []).map((p) => keyOf(p.item, p.unit)));
  const rows = [
    ...(prices.data ?? []).filter((p) => p.price === null).map((p) => ({ item: p.item, unit: p.unit, isNew: false })),
    ...extraItems.filter((x) => !listed.has(keyOf(x.item, x.unit))).map((x) => ({ ...x, isNew: true })),
  ];

  const valueFor = (item: string, unit: string) => values[keyOf(item, unit)]?.trim() ?? "";
  const filled = rows.filter((r) => valueFor(r.item, r.unit)).length;
  const invalid = rows.some((r) => {
    const v = valueFor(r.item, r.unit);
    return v !== "" && (Number.isNaN(Number(v)) || Number(v) < 0);
  });

  const save = useMutation({
    mutationFn: () =>
      api<Price[]>("/prices", {
        method: "PUT",
        json: {
          items: [
            ...(prices.data ?? []).map((p) => ({ item: p.item, unit: p.unit, price: valueFor(p.item, p.unit) || p.price })),
            // New foods are only added once the user gives them a price
            ...rows.filter((r) => r.isNew && valueFor(r.item, r.unit)).map((r) => ({ item: r.item, unit: r.unit, price: valueFor(r.item, r.unit) })),
          ],
        },
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(keys.prices, data);
      queryClient.invalidateQueries({ queryKey: keys.latestPlan }); // open plans are repriced on save
      setValues({});
      if (onSaved) onSaved(data);
      else {
        const left = data.filter((p) => p.price === null).length;
        toast.success(left ? `Prices saved. ${plural(left, "food")} still without a price.` : "All prices saved. You're ready to plan!");
        onClose();
      }
    },
    onError: (e) => toast.error(e.message),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (filled > 0 && !invalid) save.mutate();
  }

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="text-sm text-muted">
        {intro ?? (
          <>
            {plural(rows.length, "food")} {rows.length === 1 ? "has" : "have"} no price yet. FamChop uses your prices to keep
            meal plans within budget, so foods without one are left out of the total.
          </>
        )}
      </p>
      <form onSubmit={onSubmit} className="mt-4">
        {rows.length > 0 ? (
          <ul className="max-h-[45vh] divide-y divide-cocoa/10 overflow-y-auto rounded-xl border border-cocoa/10">
            {rows.map((r) => {
              const k = keyOf(r.item, r.unit);
              return (
                <li key={k} className="flex items-center justify-between gap-3 px-3 py-2">
                  <label htmlFor={`price-${k}`} className="text-sm">
                    <span className="font-medium">{r.item}</span>
                    <span className="text-muted"> per {r.unit}</span>
                    {r.isNew && <span className="ml-1.5 rounded bg-accent/15 px-1 text-xs text-[#9a6400]">new</span>}
                  </label>
                  <div className="flex items-center gap-1 text-sm">
                    <span className="text-muted">₦</span>
                    <input
                      id={`price-${k}`}
                      value={values[k] ?? ""}
                      onChange={(e) => setValues((v) => ({ ...v, [k]: e.target.value }))}
                      type="number"
                      inputMode="decimal"
                      min="0"
                      step="0.01"
                      placeholder="0"
                      aria-label={`Price of ${r.item} per ${r.unit}`}
                      className="w-28 rounded-lg border border-cocoa/15 px-2 py-1.5 text-right focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="rounded-xl bg-secondary/10 p-3 text-sm text-secondary">Every food has a price.</p>
        )}
        <p className="mt-2 text-xs text-muted">Fill in what you know. You can leave the rest for later.</p>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <Link href="/prices" onClick={onClose} className="text-sm font-medium text-primary hover:underline">
            Open full price list
          </Link>
          <div className="flex flex-wrap gap-2">
            {secondaryAction ? (
              <Button type="button" variant="ghost" onClick={secondaryAction.onClick}>
                {secondaryAction.label}
              </Button>
            ) : (
              <Button type="button" variant="ghost" onClick={onClose}>
                Later
              </Button>
            )}
            <Button type="submit" loading={save.isPending} disabled={filled === 0 || invalid}>
              {filled > 0 ? `Save ${plural(filled, "price")}` : "Save prices"}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}

// Holds the token of the login that already saw the prompt, so it shows once per sign-in
const SEEN_KEY = "famchop_price_prompt_seen";

function seenThisLogin(): boolean {
  try {
    return sessionStorage.getItem(SEEN_KEY) === getToken();
  } catch {
    return false;
  }
}

function markSeen() {
  try {
    const token = getToken();
    if (token) sessionStorage.setItem(SEEN_KEY, token);
  } catch {
    // Storage blocked: the prompt may show again on reload, which is harmless
  }
}

/** After an admin signs in, ask them to fill in any foods that have no price yet. */
export function MissingPricesPrompt() {
  const pathname = usePathname();
  const prices = usePrices();
  const [open, setOpen] = useState(false);
  const missing = prices.data?.filter((p) => p.price === null).length ?? 0;

  useEffect(() => {
    // The prices and plan pages handle missing prices themselves
    if (missing > 0 && pathname !== "/prices" && pathname !== "/plan" && !seenThisLogin()) {
      setOpen(true);
      markSeen();
    }
  }, [missing, pathname]);

  return <PricesModal open={open} onClose={() => setOpen(false)} />;
}

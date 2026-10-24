"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { api, getToken } from "@/lib/api";
import { plural } from "@/lib/format";
import { keys, usePrices } from "@/lib/queries";
import type { Price } from "@/lib/types";
import { Button, Modal } from "./ui";

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
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<Record<number, string>>({});

  const missing = prices.data?.filter((p) => p.price === null) ?? [];

  useEffect(() => {
    // The prices page is where they'd fill them in anyway
    if (missing.length > 0 && pathname !== "/prices" && !seenThisLogin()) {
      setOpen(true);
      markSeen();
    }
  }, [missing.length, pathname]);

  const save = useMutation({
    mutationFn: (all: Price[]) =>
      api<Price[]>("/prices", {
        method: "PUT",
        json: {
          items: all.map((p) => ({
            item: p.item,
            unit: p.unit,
            price: values[p.id]?.trim() ? values[p.id].trim() : p.price,
          })),
        },
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(keys.prices, data);
      const left = data.filter((p) => p.price === null).length;
      toast.success(left ? `Prices saved. ${plural(left, "item")} still without a price.` : "All prices saved. You're ready to plan!");
      setOpen(false);
      setValues({});
    },
    onError: (e) => toast.error(e.message),
  });

  const filled = missing.filter((p) => values[p.id]?.trim()).length;
  const invalid = missing.some((p) => {
    const v = values[p.id]?.trim();
    return v ? Number.isNaN(Number(v)) || Number(v) < 0 : false;
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (prices.data && filled > 0 && !invalid) save.mutate(prices.data);
  }

  return (
    <Modal open={open} onClose={() => setOpen(false)} title="Add your market prices">
      <p className="text-sm text-muted">
        {plural(missing.length, "food")} on your list {missing.length === 1 ? "has" : "have"} no price yet. FamChop uses
        your prices to keep meal plans within budget, so items without one are left out of the total.
      </p>
      <form onSubmit={onSubmit} className="mt-4">
        <ul className="max-h-[45vh] divide-y divide-cocoa/10 overflow-y-auto rounded-xl border border-cocoa/10">
          {missing.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-3 px-3 py-2">
              <label htmlFor={`price-${p.id}`} className="text-sm">
                <span className="font-medium">{p.item}</span>
                <span className="text-muted"> per {p.unit}</span>
              </label>
              <div className="flex items-center gap-1 text-sm">
                <span className="text-muted">₦</span>
                <input
                  id={`price-${p.id}`}
                  value={values[p.id] ?? ""}
                  onChange={(e) => setValues((v) => ({ ...v, [p.id]: e.target.value }))}
                  type="number"
                  inputMode="decimal"
                  min="0"
                  step="0.01"
                  placeholder="0"
                  className="w-28 rounded-lg border border-cocoa/15 px-2 py-1.5 text-right focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-muted">Fill in what you know. You can leave the rest for later.</p>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
          <Link href="/prices" onClick={() => setOpen(false)} className="text-sm font-medium text-primary hover:underline">
            Open full price list
          </Link>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
              Later
            </Button>
            <Button type="submit" loading={save.isPending} disabled={filled === 0 || invalid}>
              {filled > 0 ? `Save ${plural(filled, "price")}` : "Save prices"}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}

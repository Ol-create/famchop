"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, type FormEvent } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { dateTime, money } from "@/lib/format";
import { keys, useMe, useWallet } from "@/lib/queries";
import type { TransactionType, Wallet } from "@/lib/types";
import { Button, Card, CardTitle, EmptyState, Field, Input, PageHeader, PageLoading } from "@/components/ui";

const TX: Record<TransactionType, { label: string; sign: "+" | "-" }> = {
  fund: { label: "Added to wallet", sign: "+" },
  release: { label: "Released for shopping", sign: "-" },
  refund: { label: "Change returned", sign: "+" },
  spend: { label: "Overspend reimbursed", sign: "-" },
};

export default function WalletPage() {
  const me = useMe().data!;
  const wallet = useWallet();
  const queryClient = useQueryClient();
  const formRef = useRef<HTMLFormElement>(null);

  const fund = useMutation({
    mutationFn: (body: { amount: string; note: string }) => api<Wallet>("/wallet/fund", { method: "POST", json: body }),
    onSuccess: (w) => {
      queryClient.setQueryData(keys.wallet, w);
      queryClient.invalidateQueries({ queryKey: keys.family });
      toast.success(`Wallet funded. New balance ${money(w.balance)}`);
      formRef.current?.reset();
    },
    onError: (e) => toast.error(e.message),
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    fund.mutate({ amount: String(form.get("amount")), note: String(form.get("note") ?? "") });
  }

  if (wallet.isLoading || !wallet.data) return <PageLoading />;
  const isAdmin = me.role === "admin";

  return (
    <div className="space-y-6">
      <PageHeader title="Family wallet" subtitle="Money set aside for food. Simulated for now: no real payments are made." />

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <p className="text-sm text-muted">Balance</p>
          <p className="mt-1 text-4xl font-bold text-secondary">{money(wallet.data.balance)}</p>
        </Card>

        {isAdmin ? (
          <Card>
            <CardTitle>Add money</CardTitle>
            <form ref={formRef} onSubmit={onSubmit} className="space-y-3">
              <Field label="Amount (₦)">
                <Input name="amount" type="number" inputMode="decimal" min="1" max="10000000" step="0.01" required placeholder="40000" />
              </Field>
              <Field label="Note (optional)">
                <Input name="note" maxLength={255} placeholder="e.g. Salary week" />
              </Field>
              <Button type="submit" variant="secondary" loading={fund.isPending}>
                Add to wallet
              </Button>
            </form>
          </Card>
        ) : (
          <Card>
            <p className="text-sm text-muted">Only family admins can add money. When you&apos;re sent to market, the cash released to you shows below.</p>
          </Card>
        )}
      </div>

      <Card>
        <CardTitle>History</CardTitle>
        {wallet.data.transactions.length === 0 ? (
          <EmptyState title="No transactions yet">{isAdmin ? "Add money to get started." : null}</EmptyState>
        ) : (
          <ul className="divide-y divide-cocoa/10">
            {wallet.data.transactions.map((t) => {
              const meta = TX[t.type];
              return (
                <li key={t.id} className="flex items-start justify-between gap-4 py-3">
                  <div>
                    <p className="font-medium">{t.note || meta.label}</p>
                    <p className="text-sm text-muted">
                      {meta.label}
                      {t.user_name ? ` · ${t.user_name}` : ""} · {dateTime(t.created_at)}
                      {t.errand_id && (
                        <>
                          {" · "}
                          <Link href={`/errands/${t.errand_id}`} className="text-primary hover:underline">
                            errand
                          </Link>
                        </>
                      )}
                    </p>
                  </div>
                  <span className={`whitespace-nowrap font-semibold ${meta.sign === "+" ? "text-secondary" : "text-danger"}`}>
                    {meta.sign}
                    {money(t.amount)}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}

"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import { keys, useFamily } from "@/lib/queries";
import type { Errand, Plan } from "@/lib/types";
import { Button, Field, Input, Modal, Select } from "./ui";

export function AssignErrandModal({ plan, open, onClose }: { plan: Plan; open: boolean; onClose: () => void }) {
  const family = useFamily().data;
  const queryClient = useQueryClient();
  const router = useRouter();
  const balance = Number(family?.wallet_balance ?? 0);
  const total = Number(plan.total_cost);

  const assign = useMutation({
    mutationFn: (body: object) => api<Errand>("/errands", { method: "POST", json: body }),
    onSuccess: (e) => {
      toast.success(`${e.assigned_to.name} has the shopping list and ${money(e.released_amount)}`);
      queryClient.invalidateQueries({ queryKey: keys.errands });
      queryClient.invalidateQueries({ queryKey: keys.wallet });
      queryClient.invalidateQueries({ queryKey: keys.family });
      onClose();
      router.push(`/errands/${e.id}`);
    },
    onError: (e) => toast.error(e.message),
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    assign.mutate({
      plan_id: plan.id,
      assigned_to: Number(form.get("assigned_to")),
      released_amount: String(form.get("released_amount")),
      market: String(form.get("market") ?? ""),
    });
  }

  return (
    <Modal open={open} onClose={onClose} title="Send someone to market">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Who's going?">
          <Select name="assigned_to" required defaultValue="">
            <option value="" disabled>
              Choose a family member
            </option>
            {family?.members.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.role})
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Market (optional)">
          <Input name="market" placeholder="e.g. Oja Oba" maxLength={120} />
        </Field>
        <Field label="Money to release (₦)" hint={`Plan total ${money(total)} · wallet has ${money(balance)}`}>
          <Input
            name="released_amount"
            type="number"
            inputMode="decimal"
            min="1"
            step="0.01"
            max={balance || undefined}
            required
            defaultValue={Math.ceil(total) || ""}
          />
        </Field>
        {balance < total && (
          <p className="rounded-lg bg-accent/10 p-3 text-sm text-[#9a6400]">
            The wallet has less than the plan total. Add money on the Wallet page or release a smaller amount.
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="secondary" loading={assign.isPending}>
            Release money &amp; assign
          </Button>
        </div>
      </form>
    </Modal>
  );
}

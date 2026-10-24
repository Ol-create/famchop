"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { AGE_GROUPS, capitalize } from "@/lib/format";
import { keys, useFamily, useMe } from "@/lib/queries";
import type { Member, Role, User } from "@/lib/types";
import { Badge, Button, Card, CardTitle, Field, Input, PageHeader, PageLoading, Select, Textarea } from "@/components/ui";
import { InviteCode } from "@/components/InviteCode";

export default function FamilyPage() {
  const me = useMe().data!;
  const family = useFamily();
  const queryClient = useQueryClient();

  const setRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: Role }) =>
      api<Member>(`/family/members/${id}`, { method: "PATCH", json: { role } }),
    onSuccess: (m) => {
      toast.success(`${m.name} is now ${m.role === "admin" ? "an admin" : "a member"}`);
      queryClient.invalidateQueries({ queryKey: keys.family });
      queryClient.invalidateQueries({ queryKey: keys.me });
    },
    onError: (e) => toast.error(e.message),
  });

  if (family.isLoading || !family.data) return <PageLoading />;
  const f = family.data;
  const isAdmin = me.role === "admin";
  const adminCount = f.members.filter((m) => m.role === "admin").length;

  return (
    <div className="space-y-6">
      <PageHeader title={f.name} subtitle={`${f.members.length} people share this family's plans, prices and wallet.`} />

      <Card>
        <CardTitle>Invite code</CardTitle>
        <InviteCode code={f.invite_code} familyName={f.name} />
        <p className="mt-2 text-sm text-muted">New members sign up with &ldquo;Join with code&rdquo; and appear here.</p>
      </Card>

      <Card>
        <CardTitle>Members</CardTitle>
        <ul className="divide-y divide-cocoa/10">
          {f.members.map((m) => (
            <li key={m.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div>
                <p className="font-medium">
                  {m.name} {m.id === me.id && <span className="text-sm text-muted">(you)</span>}
                </p>
                <p className="text-sm text-muted">
                  {capitalize(m.age_group)}
                  {m.dislikes ? ` · avoids ${m.dislikes}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={m.role === "admin" ? "orange" : "grey"}>{m.role}</Badge>
                {isAdmin && m.role === "member" && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={adminCount >= 2}
                    title={adminCount >= 2 ? "A family can have at most 2 admins" : undefined}
                    loading={setRole.isPending && setRole.variables?.id === m.id}
                    onClick={() => setRole.mutate({ id: m.id, role: "admin" })}
                  >
                    Make admin
                  </Button>
                )}
                {isAdmin && m.role === "admin" && adminCount > 1 && (
                  <Button
                    size="sm"
                    variant="ghost"
                    loading={setRole.isPending && setRole.variables?.id === m.id}
                    onClick={() => setRole.mutate({ id: m.id, role: "member" })}
                  >
                    {m.id === me.id ? "Step down" : "Remove admin"}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
        {isAdmin && <p className="mt-2 text-xs text-muted">Up to 2 admins can fund the wallet, plan meals and send people to market.</p>}
      </Card>

      <ProfileForm me={me} />
    </div>
  );
}

function ProfileForm({ me }: { me: User }) {
  const queryClient = useQueryClient();
  const [dirty, setDirty] = useState(false);
  const save = useMutation({
    mutationFn: (body: object) => api<User>("/me/profile", { method: "PATCH", json: body }),
    onSuccess: () => {
      toast.success("Profile saved");
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: keys.me });
      queryClient.invalidateQueries({ queryKey: keys.family });
    },
    onError: (e) => toast.error(e.message),
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    save.mutate({ name: form.get("name"), age_group: form.get("age_group"), dislikes: form.get("dislikes") });
  }

  return (
    <Card>
      <CardTitle>Your profile</CardTitle>
      <form onSubmit={onSubmit} onChange={() => setDirty(true)} className="grid gap-4 sm:grid-cols-2">
        <Field label="Name">
          <Input name="name" defaultValue={me.name} required maxLength={120} />
        </Field>
        <Field label="Age group">
          <Select name="age_group" defaultValue={me.age_group}>
            {AGE_GROUPS.map((g) => (
              <option key={g} value={g}>
                {capitalize(g)}
              </option>
            ))}
          </Select>
        </Field>
        <div className="sm:col-span-2">
          <Field label="Foods you don't eat" hint="The meal planner avoids these, e.g. “beans, okra” or “no pork”.">
            <Textarea name="dislikes" defaultValue={me.dislikes ?? ""} maxLength={500} />
          </Field>
        </div>
        <div className="sm:col-span-2">
          <Button type="submit" loading={save.isPending} disabled={!dirty}>
            Save profile
          </Button>
        </div>
      </form>
    </Card>
  );
}

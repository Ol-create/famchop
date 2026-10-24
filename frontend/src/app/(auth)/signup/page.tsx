"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, setToken } from "@/lib/api";
import { AGE_GROUPS, capitalize } from "@/lib/format";
import type { AuthResponse } from "@/lib/types";
import { Button, ErrorNote, Field, Input, Select } from "@/components/ui";

function SignupForm() {
  const router = useRouter();
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"create" | "join">(params.get("join") ? "join" : "create");
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setLoading(true);
    setError(null);
    try {
      const res = await api<AuthResponse>("/auth/signup", {
        method: "POST",
        json: {
          name: form.get("name"),
          email: form.get("email"),
          password: form.get("password"),
          age_group: form.get("age_group"),
          ...(mode === "create" ? { family_name: form.get("family_name") } : { invite_code: form.get("invite_code") }),
        },
      });
      setToken(res.access_token);
      queryClient.clear();
      toast.success(mode === "create" ? "Family created! Share your invite code with the family." : "You've joined the family!");
      router.replace("/dashboard");
    } catch (err) {
      setError(err);
      setLoading(false);
    }
  }

  return (
    <>
      <h1 className="text-2xl font-bold">{mode === "create" ? "Create your family" : "Join your family"}</h1>
      <p className="mt-1 text-sm text-muted">
        {mode === "create" ? "You'll be the admin and get a code to invite everyone else." : "Ask a family admin for the invite code."}
      </p>

      <div className="mt-5 grid grid-cols-2 gap-1 rounded-lg bg-cream p-1" role="tablist">
        {(["create", "join"] as const).map((m) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={mode === m}
            onClick={() => setMode(m)}
            className={`rounded-md py-2 text-sm font-medium transition-colors ${
              mode === m ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-cocoa"
            }`}
          >
            {m === "create" ? "Create family" : "Join with code"}
          </button>
        ))}
      </div>

      <form onSubmit={onSubmit} className="mt-5 space-y-4">
        {mode === "create" ? (
          <Field label="Family name">
            <Input name="family_name" placeholder="e.g. Adeyemi Family" required maxLength={120} />
          </Field>
        ) : (
          <Field label="Invite code">
            <Input name="invite_code" placeholder="e.g. ADE-4821" required maxLength={12} className="font-mono uppercase" />
          </Field>
        )}
        <Field label="Your name">
          <Input name="name" autoComplete="name" required maxLength={120} />
        </Field>
        <Field label="Age group" hint="Helps plan the right portions and nutrition.">
          <Select name="age_group" defaultValue="adult">
            {AGE_GROUPS.map((g) => (
              <option key={g} value={g}>
                {capitalize(g)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Email">
          <Input name="email" type="email" autoComplete="email" required />
        </Field>
        <Field label="Password" hint="At least 6 characters.">
          <Input name="password" type="password" autoComplete="new-password" required minLength={6} />
        </Field>
        {error ? <ErrorNote error={error} /> : null}
        <Button type="submit" loading={loading} className="w-full" size="lg">
          {mode === "create" ? "Create family" : "Join family"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </>
  );
}

export default function SignupPage() {
  return (
    <Suspense>
      <SignupForm />
    </Suspense>
  );
}

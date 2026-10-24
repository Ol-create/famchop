"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type Health = { status: string; database: string };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Health>("/health")
      .then(setHealth)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center gap-6 px-4 text-center">
      <h1 className="text-5xl font-bold text-primary">FamChop</h1>
      <p className="text-muted">Plan your family&apos;s meals, shop smart, stay on budget.</p>

      <div className="w-full rounded-xl bg-surface p-4 text-left text-sm shadow-sm">
        <p className="mb-2 font-heading font-semibold">Setup check</p>
        {error && <p className="text-danger">API unreachable: {error}</p>}
        {!error && !health && <p className="text-muted">Checking API…</p>}
        {health && (
          <ul className="space-y-1">
            <li>
              API: <span className="font-medium text-secondary">{health.status}</span>
            </li>
            <li>
              Database:{" "}
              <span
                className={`font-medium ${health.database === "ok" ? "text-secondary" : "text-danger"}`}
              >
                {health.database}
              </span>
            </li>
          </ul>
        )}
      </div>

      <div className="flex gap-2">
        <span className="rounded-full bg-primary px-3 py-1 text-xs text-white">Primary</span>
        <span className="rounded-full bg-secondary px-3 py-1 text-xs text-white">Secondary</span>
        <span className="rounded-full bg-accent px-3 py-1 text-xs text-cocoa">Accent</span>
        <span className="rounded-full bg-danger px-3 py-1 text-xs text-white">Danger</span>
      </div>
    </main>
  );
}

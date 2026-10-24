"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getToken } from "@/lib/api";
import { Logo } from "@/components/ui";

const FEATURES = [
  { title: "Your market, your prices", body: "Type what you actually pay. Every naira in the plan comes from your own price list." },
  { title: "A week of meals that fits", body: "Gemma 4 plans 7 days of familiar Nigerian meals, balanced for kids and adults, inside your budget." },
  { title: "Send anyone to market", body: "Release money from the family wallet, assign the list, and see the change come back." },
];

export default function Landing() {
  const router = useRouter();
  useEffect(() => {
    if (getToken()) router.replace("/dashboard");
  }, [router]);

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-4">
      <header className="flex items-center justify-between py-5">
        <Logo className="text-2xl" />
        <Link href="/login" className="text-sm font-medium text-cocoa hover:text-primary">
          Sign in
        </Link>
      </header>

      <section className="flex flex-1 flex-col items-center justify-center py-12 text-center">
        <span className="mb-4 rounded-full bg-accent/15 px-3 py-1 text-sm font-medium text-[#9a6400]">
          Family food, planned together
        </span>
        <h1 className="max-w-2xl text-4xl font-bold leading-tight sm:text-5xl">
          Feed your family well, <span className="text-primary">within budget</span>.
        </h1>
        <p className="mt-4 max-w-xl text-lg text-muted">
          FamChop plans your week of meals from the prices at your market, builds the shopping list, and keeps the family
          wallet honest.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/signup" className="rounded-lg bg-primary px-6 py-3 font-medium text-white shadow-sm hover:bg-primary/90">
            Create your family
          </Link>
          <Link href="/signup?join=1" className="rounded-lg border border-cocoa/15 bg-surface px-6 py-3 font-medium hover:bg-cream">
            Join with a code
          </Link>
        </div>

        <div className="mt-16 grid w-full gap-4 text-left sm:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-2xl border border-cocoa/10 bg-surface p-5 shadow-sm">
              <h2 className="font-semibold">{f.title}</h2>
              <p className="mt-1 text-sm text-muted">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="py-6 text-center text-xs text-muted">
        Wallet money is simulated. Nutrition tips are general guidance, not medical advice.
      </footer>
    </main>
  );
}

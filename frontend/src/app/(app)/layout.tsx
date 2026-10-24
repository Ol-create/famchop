"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getToken, setToken } from "@/lib/api";
import { useMe, useMyErrands } from "@/lib/queries";
import { Badge, Logo, PageLoading } from "@/components/ui";
import { MissingPricesPrompt } from "@/components/MissingPricesPrompt";

const NAV = [
  { href: "/dashboard", label: "Home" },
  { href: "/plan", label: "Meal plan" },
  { href: "/errands", label: "Shopping" },
  { href: "/prices", label: "Prices" },
  { href: "/wallet", label: "Wallet" },
  { href: "/family", label: "Family" },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState<boolean | null>(null);

  useEffect(() => {
    const token = getToken();
    setHasToken(!!token);
    if (!token) router.replace("/login");
  }, [router]);

  const me = useMe();
  const myErrands = useMyErrands();
  const openErrands = myErrands.data?.filter((e) => e.status !== "completed").length ?? 0;

  if (!hasToken || me.isLoading) return <PageLoading />;
  if (!me.data) return <PageLoading />;

  const signOut = () => {
    setToken(null);
    queryClient.clear();
    router.replace("/login");
  };

  return (
    <div className="min-h-screen pb-10">
      <header className="sticky top-0 z-40 border-b border-cocoa/10 bg-cream/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
          <Link href="/dashboard" className="text-xl">
            <Logo />
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-muted sm:inline">
              {me.data.name}{" "}
              <Badge tone={me.data.role === "admin" ? "orange" : "grey"}>{me.data.role}</Badge>
            </span>
            <button onClick={signOut} className="rounded-lg px-2 py-1 text-muted hover:bg-cocoa/5 hover:text-cocoa">
              Sign out
            </button>
          </div>
        </div>
        <nav className="mx-auto max-w-5xl overflow-x-auto px-2" aria-label="Main">
          <ul className="flex gap-1 whitespace-nowrap">
            {NAV.map((item) => {
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`relative inline-flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                      active ? "border-primary text-primary" : "border-transparent text-muted hover:text-cocoa"
                    }`}
                  >
                    {item.label}
                    {item.href === "/errands" && openErrands > 0 && (
                      <span className="rounded-full bg-accent px-1.5 text-xs font-semibold text-cocoa">{openErrands}</span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 pt-6">{children}</main>
      {/* Only admins can edit prices, so only they get asked */}
      {me.data.role === "admin" && <MissingPricesPrompt />}
    </div>
  );
}

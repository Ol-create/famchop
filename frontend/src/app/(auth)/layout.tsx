import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/ui";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <Link href="/" className="mb-6 text-3xl">
        <Logo />
      </Link>
      <div className="w-full max-w-md rounded-2xl border border-cocoa/10 bg-surface p-6 shadow-sm sm:p-8">{children}</div>
    </main>
  );
}

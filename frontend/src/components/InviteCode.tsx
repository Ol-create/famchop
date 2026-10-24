"use client";

import { toast } from "sonner";

export function InviteCode({ code, familyName }: { code: string; familyName: string }) {
  const message = `Join ${familyName} on FamChop with invite code ${code}`;

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      toast.success("Invite code copied");
    } catch {
      toast.error("Couldn't copy. Select the code and copy it manually.");
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="rounded-lg border-2 border-dashed border-accent bg-accent/10 px-3 py-1.5 font-mono text-lg font-bold tracking-wider text-cocoa">
        {code}
      </span>
      <button onClick={copy} className="rounded-lg px-2.5 py-1.5 text-sm font-medium text-primary hover:bg-primary/10">
        Copy
      </button>
      <a
        href={`https://wa.me/?text=${encodeURIComponent(message)}`}
        target="_blank"
        rel="noopener noreferrer"
        className="rounded-lg px-2.5 py-1.5 text-sm font-medium text-secondary hover:bg-secondary/10"
      >
        Share on WhatsApp
      </a>
    </div>
  );
}

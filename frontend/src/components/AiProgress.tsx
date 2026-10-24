"use client";

import { useEffect, useState } from "react";
import { Spinner } from "./ui";

/** Gemma takes 30-60s for a plan, so show that something is happening and roughly what. */
export function AiProgress({ messages, expected }: { messages: string[]; expected: string }) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  const message = messages[Math.min(Math.floor(seconds / 6), messages.length - 1)];

  return (
    <div className="flex items-center gap-4 rounded-2xl border border-primary/20 bg-primary/5 p-5" role="status" aria-live="polite">
      <Spinner className="h-8 w-8 shrink-0 text-primary" />
      <div>
        <p className="font-heading font-semibold text-cocoa">{message}</p>
        <p className="text-sm text-muted">
          {seconds}s · usually takes {expected}. Gemma 4 is working on it.
        </p>
      </div>
    </div>
  );
}

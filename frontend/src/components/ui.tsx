"use client";

import { useEffect, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { money } from "@/lib/format";

function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

// ---------- Buttons ----------

type Variant = "primary" | "secondary" | "outline" | "ghost" | "danger";

const variants: Record<Variant, string> = {
  primary: "bg-primary text-white hover:bg-primary/90 shadow-sm",
  secondary: "bg-secondary text-white hover:bg-secondary/90 shadow-sm",
  outline: "border border-cocoa/15 bg-surface text-cocoa hover:bg-cream",
  ghost: "text-cocoa hover:bg-cocoa/5",
  danger: "bg-danger text-white hover:bg-danger/90",
};

export function Button({
  variant = "primary",
  loading,
  size = "md",
  className,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean; size?: "sm" | "md" | "lg" }) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
        "disabled:cursor-not-allowed disabled:opacity-60",
        size === "sm" && "px-3 py-1.5 text-sm",
        size === "md" && "px-4 py-2 text-sm",
        size === "lg" && "px-5 py-3 text-base",
        variants[variant],
        className,
      )}
    >
      {loading && <Spinner className="h-4 w-4" />}
      {children}
    </button>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={cx("animate-spin", className ?? "h-5 w-5")} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="4" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

// ---------- Layout ----------

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("rounded-2xl border border-cocoa/10 bg-surface p-5 shadow-sm", className)}>{children}</div>;
}

export function CardTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h2 className="text-lg font-semibold">{children}</h2>
      {action}
    </div>
  );
}

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-cocoa/20 p-8 text-center">
      <p className="font-heading font-semibold">{title}</p>
      {children && <div className="mt-2 text-sm text-muted">{children}</div>}
    </div>
  );
}

export function PageLoading() {
  return (
    <div className="flex justify-center py-20 text-primary">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  return (
    <div className="rounded-lg border border-danger/30 bg-danger/5 p-3 text-sm text-danger">
      {error instanceof Error ? error.message : "Something went wrong"}
    </div>
  );
}

// ---------- Forms ----------

const fieldBase =
  "w-full rounded-lg border border-cocoa/15 bg-surface px-3 py-2 text-sm text-cocoa placeholder:text-muted/70 " +
  "focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:bg-cream";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx(fieldBase, className)} />;
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cx(fieldBase, "min-h-[72px]", className)} />;
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cx(fieldBase, className)} />;
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

// ---------- Bits ----------

const badgeTones = {
  orange: "bg-primary/10 text-primary",
  green: "bg-secondary/10 text-secondary",
  yellow: "bg-accent/15 text-[#9a6400]",
  red: "bg-danger/10 text-danger",
  grey: "bg-cocoa/5 text-muted",
};

export function Badge({ tone = "grey", children }: { tone?: keyof typeof badgeTones; children: ReactNode }) {
  return (
    <span className={cx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", badgeTones[tone])}>
      {children}
    </span>
  );
}

/** Spend vs budget: green while under, red when over. */
export function BudgetBar({ spent, budget, label = "of budget" }: { spent: string | number; budget: string | number; label?: string }) {
  const s = Number(spent);
  const b = Number(budget);
  const over = s > b;
  const pct = b > 0 ? Math.min(100, (s / b) * 100) : 0;
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-2 text-sm">
        <span>
          <span className={cx("text-lg font-semibold", over ? "text-danger" : "text-secondary")}>{money(s)}</span>{" "}
          <span className="text-muted">
            {label} {money(b)}
          </span>
        </span>
        <span className={cx("font-medium", over ? "text-danger" : "text-secondary")}>
          {over ? `${money(s - b)} over` : `${money(b - s)} left`}
        </span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-cocoa/10" role="meter" aria-valuenow={s} aria-valuemax={b}>
        <div
          className={cx("h-full rounded-full transition-all", over ? "bg-danger" : "bg-secondary")}
          style={{ width: `${over ? 100 : pct}%` }}
        />
      </div>
    </div>
  );
}

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-cocoa/40 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="max-h-[90vh] w-full overflow-y-auto rounded-t-2xl bg-surface p-5 shadow-xl sm:max-w-md sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-muted hover:bg-cocoa/5" aria-label="Close">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-2 font-heading font-bold text-primary", className)}>
      <svg viewBox="0 0 32 32" className="h-[1.4em] w-[1.4em]" aria-hidden>
        <path d="M11 4c-1.5 2 1.5 3 0 5M16 3c-1.5 2 1.5 3 0 5M21 4c-1.5 2 1.5 3 0 5" stroke="#F59F00" strokeWidth="1.8" fill="none" strokeLinecap="round" />
        <rect x="3" y="13" width="26" height="3" rx="1.5" fill="#3D2C29" />
        <path d="M5 16h22v6a6 6 0 0 1-6 6H11a6 6 0 0 1-6-6v-6z" fill="currentColor" />
        <rect x="1" y="17" width="4" height="2.5" rx="1.25" fill="currentColor" />
        <rect x="27" y="17" width="4" height="2.5" rx="1.25" fill="currentColor" />
      </svg>
      FamChop
    </span>
  );
}

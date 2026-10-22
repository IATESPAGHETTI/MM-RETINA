"use client";

import { useId, useRef, useState } from "react";

/* ---------- layout ---------- */

export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  eyebrow?: string;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line pb-6">
      <div className="max-w-2xl">
        {eyebrow && <p className="mb-1.5 text-xs font-medium uppercase tracking-[0.14em] text-accent-champagne">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
  pad = true,
}: {
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  pad?: boolean;
}) {
  return (
    <section className={`rounded-lg border border-line bg-panel ${className}`}>
      {(title || action) && (
        <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-3.5">
          <div>
            {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-faint">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className={pad ? "p-5" : ""}>{children}</div>
    </section>
  );
}

export function Stat({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "ok" | "warn" | "bad" }) {
  const color = tone === "ok" ? "text-ok" : tone === "warn" ? "text-warn" : tone === "bad" ? "text-bad" : "text-ink";
  return (
    <div>
      <p className="text-xs text-ink-faint">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums tracking-tight ${color}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-ink-faint">{hint}</p>}
    </div>
  );
}

/* ---------- badges & buttons ---------- */

const TONES = {
  neutral: "border-line-strong text-ink-muted",
  ok: "border-ok/30 bg-ok/10 text-ok",
  warn: "border-warn/30 bg-warn/10 text-warn",
  bad: "border-bad/30 bg-bad/10 text-bad",
  info: "border-info/30 bg-info/10 text-info",
  accent: "border-accent-champagne/30 bg-accent-champagne/10 text-accent-champagne",
};
export type Tone = keyof typeof TONES;

export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function severityTone(label: string): Tone {
  const l = label.toLowerCase();
  if (l === "control" || l === "normal" || l.startsWith("no glaucoma")) return "ok";
  if (l === "mild" || l === "early") return "warn";
  if (l === "moderate") return "warn";
  if (l === "severe" || l === "progressive") return "bad";
  return "neutral";
}

const BTN = {
  primary: "bg-accent-champagne text-[#16130d] hover:bg-[#e6c99d] disabled:bg-accent-champagne/40",
  secondary: "border border-line-strong text-ink hover:bg-white/5 disabled:text-ink-faint",
  ghost: "text-ink-muted hover:bg-white/5 hover:text-ink disabled:text-ink-faint",
};
export function Button({
  variant = "primary",
  loading,
  className = "",
  children,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof BTN; loading?: boolean }) {
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={`inline-flex h-9 items-center justify-center gap-2 rounded-md px-3.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-champagne disabled:cursor-not-allowed ${BTN[variant]} ${className}`}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/* ---------- data display ---------- */

export function ProbBars({ probs, highlight }: { probs: Record<string, number>; highlight?: string }) {
  const rows = Object.entries(probs);
  return (
    <ul className="space-y-2.5" aria-label="Class probabilities">
      {rows.map(([name, p]) => {
        const top = name === highlight;
        return (
          <li key={name}>
            <div className="mb-1 flex justify-between text-xs">
              <span className={`capitalize ${top ? "font-medium text-ink" : "text-ink-muted"}`}>{name}</span>
              <span className="tabular-nums text-ink-muted">{(p * 100).toFixed(1)}%</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.07]">
              <div
                className={`h-full rounded-full transition-[width] duration-700 ease-out ${top ? "bg-accent-champagne" : "bg-ink-faint/60"}`}
                style={{ width: `${Math.max(p * 100, 0.8)}%` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function Meter({ value, label, tone = "accent" }: { value: number; label: string; tone?: "accent" | "ok" | "warn" | "bad" }) {
  const bar = { accent: "bg-accent-champagne", ok: "bg-ok", warn: "bg-warn", bad: "bg-bad" }[tone];
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-ink-muted">{label}</span>
        <span className="tabular-nums text-ink">{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/[0.07]" role="meter" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
        <div className={`h-full rounded-full ${bar} transition-[width] duration-700 ease-out`} style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  );
}

/* ---------- states ---------- */

export function EmptyState({ title, body, icon }: { title: string; body: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-line-strong px-6 py-14 text-center">
      {icon && <div className="mb-3 text-ink-faint">{icon}</div>}
      <p className="text-sm font-medium text-ink">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-ink-faint">{body}</p>
    </div>
  );
}

export function LoadingBlock({ label = "Running analysis…", lines = 4 }: { label?: string; lines?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <p className="flex items-center gap-2 text-sm text-ink-muted">
        <Spinner /> {label}
      </p>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-3 animate-pulse rounded bg-white/[0.06]" style={{ width: `${88 - i * 14}%` }} />
      ))}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start justify-between gap-4 rounded-md border border-bad/30 bg-bad/10 px-4 py-3 text-sm text-bad">
      <span>{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="shrink-0 font-medium underline underline-offset-2 hover:text-ink">
          Retry
        </button>
      )}
    </div>
  );
}

export function Callout({ tone = "info", title, children }: { tone?: "info" | "warn" | "ok"; title?: string; children: React.ReactNode }) {
  const c = { info: "border-info/25 bg-info/[0.06]", warn: "border-warn/30 bg-warn/[0.07]", ok: "border-ok/25 bg-ok/[0.06]" }[tone];
  const t = { info: "text-info", warn: "text-warn", ok: "text-ok" }[tone];
  return (
    <div className={`rounded-md border px-4 py-3 text-sm leading-relaxed text-ink-muted ${c}`}>
      {title && <p className={`mb-0.5 font-medium ${t}`}>{title}</p>}
      {children}
    </div>
  );
}

/* ---------- inputs ---------- */

export function UploadZone({
  label,
  hint,
  file,
  previewUrl,
  onFile,
  accept = "image/jpeg,image/png,image/webp",
  disabled,
}: {
  label: string;
  hint: string;
  file: File | null;
  previewUrl: string | null;
  onFile: (f: File | null) => void;
  accept?: string;
  disabled?: boolean;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const take = (f?: File | null) => f && onFile(f);

  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-xs font-medium text-ink-muted">
        {label}
      </label>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          if (!disabled) take(e.dataTransfer.files?.[0]);
        }}
        className={`relative overflow-hidden rounded-lg border border-dashed transition-colors ${
          over ? "border-accent-champagne bg-accent-champagne/5" : "border-line-strong bg-panel-2"
        }`}
      >
        {previewUrl ? (
          <div className="relative">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={previewUrl} alt={`Preview of ${file?.name ?? label}`} className="max-h-56 w-full bg-black object-contain" />
            <div className="flex items-center justify-between gap-2 border-t border-line bg-panel px-3 py-2 text-xs">
              <span className="truncate text-ink-muted">{file?.name}</span>
              <button
                type="button"
                onClick={() => {
                  onFile(null);
                  if (input.current) input.current.value = "";
                }}
                disabled={disabled}
                className="shrink-0 text-ink-faint underline underline-offset-2 hover:text-ink disabled:opacity-40"
              >
                Remove
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            disabled={disabled}
            onClick={() => input.current?.click()}
            className="flex w-full flex-col items-center gap-1.5 px-4 py-9 text-center focus-visible:outline-2 focus-visible:outline-offset-[-4px] focus-visible:outline-accent-champagne disabled:opacity-50"
          >
            <svg viewBox="0 0 24 24" className="h-6 w-6 text-ink-faint" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
              <path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="text-sm text-ink">Drop an image or click to browse</span>
            <span className="text-xs text-ink-faint">{hint}</span>
          </button>
        )}
        <input
          ref={input}
          id={id}
          type="file"
          accept={accept}
          className="sr-only"
          disabled={disabled}
          onChange={(e) => take(e.target.files?.[0])}
        />
      </div>
    </div>
  );
}

export function NumberField({
  label,
  value,
  onChange,
  hint,
  step = "any",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  hint?: string;
  step?: string;
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs text-ink-muted">
        {label}
      </label>
      <input
        id={id}
        inputMode="decimal"
        type="number"
        step={step}
        value={value}
        placeholder={hint}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full rounded-md border border-line-strong bg-panel-2 px-3 text-sm tabular-nums text-ink placeholder:text-ink-faint/70 focus:border-accent-champagne focus:outline-none focus:ring-1 focus:ring-accent-champagne"
      />
    </div>
  );
}

"use client";

import { ReactNode, useId, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const EASE = [0.16, 1, 0.3, 1] as const;

/** Section wrapper that registers itself with JourneyNav's IntersectionObserver
 * via a `data-stage` attribute and an anchor id for the floating nav's links. */
export function Stage({
  id,
  children,
  className = "",
}: {
  id: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={`stage-${id}`} data-stage={id} className={`relative mx-auto max-w-4xl px-6 py-28 ${className}`}>
      {children}
    </section>
  );
}

export function Kicker({ children }: { children: ReactNode }) {
  return <p className="mb-4 text-xs uppercase tracking-[0.3em] text-ink-faint">{children}</p>;
}

export function StageTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="max-w-2xl text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">
      {children}
    </h2>
  );
}

/** Click-to-expand card used for EXP-05/C01/C01b/M01 "what happened here"
 * detail. Collapsed by default so the page stays scannable. */
export function ExperimentCard({
  eyebrow,
  title,
  summary,
  detail,
}: {
  eyebrow: string;
  title: string;
  summary: string;
  detail: { label: string; value: string }[];
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <div className="glass overflow-hidden rounded-2xl">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full items-start justify-between gap-4 p-6 text-left focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
      >
        <div>
          <p className="mb-1 text-xs uppercase tracking-[0.2em] text-accent-champagne">{eyebrow}</p>
          <h3 className="text-lg font-semibold text-ink">{title}</h3>
          <p className="mt-2 text-sm leading-relaxed text-ink-muted">{summary}</p>
        </div>
        <motion.span
          animate={{ rotate: open ? 45 : 0 }}
          transition={{ duration: 0.3, ease: EASE }}
          className="mt-1 shrink-0 text-xl text-ink-faint"
          aria-hidden
        >
          +
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={panelId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: EASE }}
          >
            <dl className="grid grid-cols-1 gap-4 border-t border-white/10 px-6 py-6 sm:grid-cols-2">
              {detail.map((d) => (
                <div key={d.label}>
                  <dt className="text-xs uppercase tracking-wide text-ink-faint">{d.label}</dt>
                  <dd className="mt-1 text-sm leading-relaxed text-ink-muted">{d.value}</dd>
                </div>
              ))}
            </dl>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Small "why did we decide this?" expandable used next to a frozen/rejected
 * decision. Keyboard accessible, no information hidden that isn't also
 * summarized in the visible label. */
export function DecisionNote({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  return (
    <div className="mt-4 inline-block max-w-xl text-left">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-ink transition-colors hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
      >
        <span className="text-accent-champagne">Decision</span>
        <span>{label}</span>
        <span aria-hidden>{open ? "−" : "+"}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.p
            id={panelId}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="mt-3 overflow-hidden px-4 text-sm leading-relaxed text-ink-muted"
          >
            {children}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Horizontal bar comparing two values (independent vs. shared, etc.).
 * `higherIsBetter` only controls which bar is drawn brighter — both values
 * are always shown as plain numbers, never editorialized as a "winner". */
export function MetricBarRow({
  label,
  a,
  b,
  aLabel,
  bLabel,
  max,
}: {
  label: string;
  a: number;
  b: number;
  aLabel: string;
  bLabel: string;
  max: number;
}) {
  return (
    <div className="py-4">
      <div className="mb-2 flex items-baseline justify-between text-sm">
        <span className="text-ink">{label}</span>
        <span className="text-ink-faint">
          {aLabel} {a.toFixed(3)} {"→"} {bLabel} {b.toFixed(3)}
        </span>
      </div>
      <div className="flex flex-col gap-1.5">
        <BarTrack value={a} max={max} tone="muted" />
        <BarTrack value={b} max={max} tone="accent" />
      </div>
    </div>
  );
}

function BarTrack({ value, max, tone }: { value: number; max: number; tone: "muted" | "accent" }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
      <motion.div
        className={`h-full rounded-full ${tone === "accent" ? "bg-accent-champagne" : "bg-white/30"}`}
        initial={{ width: 0 }}
        whileInView={{ width: `${Math.min(100, (value / max) * 100)}%` }}
        viewport={{ once: true, margin: "-40px" }}
        transition={{ duration: 0.9, ease: EASE }}
      />
    </div>
  );
}

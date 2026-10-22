"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";

export const EASE = [0.16, 1, 0.3, 1] as const;

/** Mount-triggered fade + rise. Slides remount on navigation, so this replays each time. */
export function In({
  children,
  delay = 0,
  y = 18,
  className,
}: {
  children: ReactNode;
  delay?: number;
  y?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y, filter: "blur(6px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.7, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

export function SlideFrame({
  kicker,
  title,
  children,
  align = "left",
  compact = false,
}: {
  kicker: string;
  title: ReactNode;
  children?: ReactNode;
  align?: "left" | "center";
  /** Smaller title and tighter spacing, for dense diagram slides. */
  compact?: boolean;
}) {
  const center = align === "center";
  return (
    <div className={`mx-auto flex h-full w-full max-w-6xl flex-col justify-center px-6 @sm:px-10 ${center ? "items-center text-center" : ""}`}>
      <In>
        <p className="mb-3 text-sm uppercase tracking-[0.3em] text-accent-champagne">{kicker}</p>
      </In>
      <In delay={0.08}>
        <h2 className={`font-semibold leading-[1.1] tracking-tight text-ink ${compact ? "text-3xl @lg:text-4xl" : "text-4xl @sm:text-5xl @lg:text-6xl"} ${center ? "max-w-3xl" : compact ? "max-w-none" : "max-w-4xl"}`}>
          {title}
        </h2>
      </In>
      {children && <div className={`w-full ${compact ? "mt-6" : "mt-8 @sm:mt-10"}`}>{children}</div>}
    </div>
  );
}

export function Pill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "gold" | "copper" | "olive" }) {
  const tones = {
    neutral: "border-white/12 text-ink-muted",
    gold: "border-accent-champagne/40 bg-accent-champagne/10 text-accent-champagne",
    copper: "border-accent-copper/40 bg-accent-copper/10 text-accent-copper",
    olive: "border-accent-olive/40 bg-accent-olive/10 text-accent-olive",
  } as const;
  return <span className={`inline-flex items-center rounded-full border px-3 py-1 text-base ${tones[tone]}`}>{children}</span>;
}

export function pct(v: number, d = 1) {
  return `${(v * 100).toFixed(d)}%`;
}

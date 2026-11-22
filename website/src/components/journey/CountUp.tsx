"use client";

import { useEffect, useRef } from "react";
import { animate, useInView } from "framer-motion";

type CountUpProps = {
  value: number;
  decimals?: number;
  suffix?: string;
  className?: string;
  duration?: number;
};

const format = (v: number, decimals: number, suffix: string) => `${v.toFixed(decimals)}${suffix}`;

/** Animates a number from 0 to `value` once it scrolls into view. Falls
 * back to the final value immediately under prefers-reduced-motion.
 *
 * The text is written straight to the DOM node while animating (an external
 * system from React's point of view) instead of calling setState on every
 * frame, which re-rendered the component ~70 times per count. */
export function CountUp({ value, decimals = 1, suffix = "", className, duration = 1.2 }: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  useEffect(() => {
    const el = ref.current;
    if (!el || !inView) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.textContent = format(value, decimals, suffix);
      return;
    }
    const controls = animate(0, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => {
        el.textContent = format(v, decimals, suffix);
      },
    });
    return () => controls.stop();
  }, [inView, value, duration, decimals, suffix]);

  return (
    <span ref={ref} className={className}>
      {format(0, decimals, suffix)}
    </span>
  );
}

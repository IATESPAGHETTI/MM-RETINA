"use client";

import { useEffect, useRef, useState } from "react";
import { animate, useInView } from "framer-motion";

type CountUpProps = {
  value: number;
  decimals?: number;
  suffix?: string;
  className?: string;
  duration?: number;
};

/** Animates a number from 0 to `value` once it scrolls into view. Falls
 * back to the final value immediately under prefers-reduced-motion. */
export function CountUp({ value, decimals = 1, suffix = "", className, duration = 1.2 }: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (!inView) return;
    // Zero duration still resolves to `value` (via the animation callback,
    // not a synchronous setState in the effect body).
    const reduceMotion =
      typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const controls = animate(0, value, {
      duration: reduceMotion ? 0 : duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(v),
    });
    return () => controls.stop();
  }, [inView, value, duration]);

  return (
    <span ref={ref} className={className}>
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}

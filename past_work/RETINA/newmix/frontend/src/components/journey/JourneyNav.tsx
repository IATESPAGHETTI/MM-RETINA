"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { JOURNEY_NAV, type JourneyStageId } from "@/lib/journeyContent";

/** Floating research-journey navigator. Watches every `[data-stage]`
 * section on the page via IntersectionObserver and highlights whichever
 * one currently owns the vertical center of the viewport. */
export function JourneyNav() {
  const [active, setActive] = useState<JourneyStageId>("hero");

  useEffect(() => {
    const sections = Array.from(document.querySelectorAll<HTMLElement>("[data-stage]"));
    if (sections.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (visible.length === 0) return;
        const top = visible.reduce((best, e) => (e.intersectionRatio > best.intersectionRatio ? e : best));
        const id = top.target.getAttribute("data-stage") as JourneyStageId | null;
        if (id) setActive(id);
      },
      { rootMargin: "-45% 0px -45% 0px", threshold: [0, 0.25, 0.5, 0.75, 1] }
    );

    sections.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, []);

  const activeIndex = JOURNEY_NAV.findIndex((s) => s.id === active);
  const progress = activeIndex >= 0 ? activeIndex / (JOURNEY_NAV.length - 1) : 0;

  return (
    <nav
      aria-label="Research journey progress"
      className="fixed right-4 top-1/2 z-40 hidden -translate-y-1/2 lg:block"
    >
      <div className="glass relative flex flex-col gap-3 rounded-full px-3 py-4">
        <div
          className="absolute left-1/2 top-4 w-px -translate-x-1/2 bg-white/10"
          style={{ height: "calc(100% - 2rem)" }}
          aria-hidden
        />
        <motion.div
          className="absolute left-1/2 top-4 w-px -translate-x-1/2 bg-accent-champagne"
          style={{ height: `calc((100% - 2rem) * ${progress})` }}
          aria-hidden
        />
        {JOURNEY_NAV.map((stage, i) => (
          <a
            key={stage.id}
            href={`#stage-${stage.id}`}
            title={`${String(i + 1).padStart(2, "0")} ${stage.label}`}
            aria-current={stage.id === active ? "true" : undefined}
            className="group relative z-10 flex items-center justify-center"
          >
            <span
              className={`h-2 w-2 rounded-full transition-all duration-300 ${
                stage.id === active
                  ? "scale-125 bg-accent-champagne"
                  : "bg-white/25 group-hover:bg-white/50"
              }`}
            />
            <span className="pointer-events-none absolute right-full mr-3 whitespace-nowrap rounded-md bg-bg-elevated px-2 py-1 text-xs text-ink-muted opacity-0 shadow-lg transition-opacity duration-200 group-hover:opacity-100">
              {String(i + 1).padStart(2, "0")} {stage.label}
            </span>
          </a>
        ))}
      </div>
    </nav>
  );
}

/** Mobile-only compact progress readout, shown under the navbar. */
export function JourneyMobileProgress() {
  const [active, setActive] = useState<JourneyStageId>("hero");

  useEffect(() => {
    const sections = Array.from(document.querySelectorAll<HTMLElement>("[data-stage]"));
    if (sections.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting);
        if (visible.length === 0) return;
        const top = visible.reduce((best, e) => (e.intersectionRatio > best.intersectionRatio ? e : best));
        const id = top.target.getAttribute("data-stage") as JourneyStageId | null;
        if (id) setActive(id);
      },
      { rootMargin: "-45% 0px -45% 0px" }
    );
    sections.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, []);

  const activeIndex = JOURNEY_NAV.findIndex((s) => s.id === active);

  return (
    <div className="sticky top-[68px] z-30 mx-auto w-full max-w-3xl px-6 lg:hidden">
      <div className="glass flex items-center gap-2 rounded-full px-4 py-2 text-xs text-ink-muted">
        <span className="tabular-nums text-ink">{String(activeIndex + 1).padStart(2, "0")}</span>
        <span className="text-ink-faint">/ {String(JOURNEY_NAV.length).padStart(2, "0")}</span>
        <span className="mx-1 h-3 w-px bg-white/15" />
        <span className="truncate">{JOURNEY_NAV[activeIndex]?.label ?? "Question"}</span>
      </div>
    </div>
  );
}

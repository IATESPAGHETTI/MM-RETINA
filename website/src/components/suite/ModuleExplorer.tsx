"use client";

import { useState, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { SUITE_MODULES, type ModuleId } from "@/lib/suiteContent";
import { Reveal } from "@/components/Reveal";
import { DiabetesVisual, GammaVisual, GlaucomaVisual } from "./ModuleVisuals";

const EASE = [0.16, 1, 0.3, 1] as const;

const VISUALS: Record<ModuleId, () => React.JSX.Element> = {
  multimodal: GammaVisual,
  glaucoma: GlaucomaVisual,
  diabetes: DiabetesVisual,
};

export function ModuleExplorer() {
  const [active, setActive] = useState<ModuleId>("multimodal");
  const current = SUITE_MODULES.find((m) => m.id === active) ?? SUITE_MODULES[0];
  const Visual = VISUALS[current.id];

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const i = SUITE_MODULES.findIndex((m) => m.id === active);
    let next = i;
    if (e.key === "ArrowRight") next = (i + 1) % SUITE_MODULES.length;
    else if (e.key === "ArrowLeft") next = (i - 1 + SUITE_MODULES.length) % SUITE_MODULES.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = SUITE_MODULES.length - 1;
    else return;
    e.preventDefault();
    const id = SUITE_MODULES[next].id;
    setActive(id);
    document.getElementById(`tab-${id}`)?.focus();
  }

  return (
    <section id="modules" className="relative scroll-mt-24 px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <Reveal className="mb-12 max-w-2xl">
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-ink-faint">Modules</p>
          <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            Each project keeps its own evidence.
          </h2>
          <p className="mt-4 text-ink-muted">
            The suite does not blend the three into one score. Every module reports its own model, its own
            cohort and its own limits.
          </p>
        </Reveal>

        <div
          role="tablist"
          aria-label="Retina Suite modules"
          onKeyDown={onKeyDown}
          className="-mx-6 mb-8 flex gap-2 overflow-x-auto px-6 pb-1 sm:mx-0 sm:px-0"
        >
          {SUITE_MODULES.map((m) => {
            const selected = m.id === active;
            return (
              <button
                key={m.id}
                id={`tab-${m.id}`}
                role="tab"
                type="button"
                aria-selected={selected}
                aria-controls={`panel-${m.id}`}
                tabIndex={selected ? 0 : -1}
                onClick={() => setActive(m.id)}
                className={`relative shrink-0 rounded-full px-5 py-2.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne ${
                  selected ? "text-bg" : "text-ink-muted hover:text-ink"
                }`}
              >
                {selected && (
                  <motion.span
                    layoutId="module-tab-pill"
                    className="absolute inset-0 rounded-full bg-ink"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                    aria-hidden
                  />
                )}
                <span className="relative z-10">{m.tab}</span>
              </button>
            );
          })}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={current.id}
            id={`panel-${current.id}`}
            role="tabpanel"
            aria-labelledby={`tab-${current.id}`}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.35, ease: EASE }}
            className="grid items-center gap-8 lg:grid-cols-[1fr_1.05fr] lg:gap-12"
          >
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-xs uppercase tracking-[0.25em] text-ink-faint">{current.project}</span>
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-[11px] ${
                    current.status === "Experimental"
                      ? "border-accent-copper/50 bg-accent-copper/10 text-accent-copper"
                      : "border-accent-olive/50 bg-accent-olive/10 text-accent-olive"
                  }`}
                >
                  {current.status}
                </span>
              </div>
              <h3 className="mt-4 text-2xl font-semibold leading-snug tracking-tight text-ink sm:text-3xl">
                {current.title}
              </h3>
              <p className="mt-4 leading-relaxed text-ink-muted">{current.summary}</p>

              <dl className="mt-6 grid gap-3 text-sm sm:grid-cols-2">
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <dt className="text-xs uppercase tracking-widest text-ink-faint">Input</dt>
                  <dd className="mt-1 text-ink">{current.inputs}</dd>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <dt className="text-xs uppercase tracking-widest text-ink-faint">Output</dt>
                  <dd className="mt-1 text-ink">{current.outputs}</dd>
                </div>
              </dl>

              <div className="mt-4 rounded-xl border border-accent-champagne/25 bg-accent-champagne/[0.06] p-4">
                <p className="text-xs uppercase tracking-widest text-accent-champagne">Evidence</p>
                <p className="mt-1 font-medium text-ink">{current.evidence.headline}</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-muted">{current.evidence.detail}</p>
              </div>
            </div>

            <Visual />
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

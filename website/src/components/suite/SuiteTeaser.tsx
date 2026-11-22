"use client";

import Link from "next/link";
import { Reveal } from "@/components/Reveal";
import { MergeDiagram } from "./MergeDiagram";

/** Home-page entry point to /suite. */
export function SuiteTeaser() {
  return (
    <section className="relative px-6 py-24">
      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1fr_1.1fr]">
        <Reveal>
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-ink-faint">Beyond one model</p>
          <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            Meet the <span className="shimmer-text">Retina Suite</span>.
          </h2>
          <p className="mt-4 max-w-lg text-ink-muted">
            MM-RETINA is one of three retinal projects now running in a single workspace, next to glaucoma
            staging from clinical measurements and diabetes vessel analysis. One API, one interface, and each
            module keeps its own evidence.
          </p>
          <Link
            href="/suite"
            className="group mt-8 inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 text-sm font-medium text-bg transition-transform hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-8px_rgba(245,243,238,0.3)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
          >
            Explore the suite
            <span aria-hidden className="transition-transform duration-300 group-hover:translate-x-1">
              &rarr;
            </span>
          </Link>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="glass rounded-3xl p-5 sm:p-8">
            <MergeDiagram className="h-auto w-full" />
          </div>
        </Reveal>
      </div>
    </section>
  );
}

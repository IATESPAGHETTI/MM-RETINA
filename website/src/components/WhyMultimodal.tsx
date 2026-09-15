"use client";

import { motion } from "framer-motion";
import { Reveal } from "./Reveal";
import { GlassCard } from "./GlassCard";

export function WhyMultimodal() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-28">
      <Reveal>
        <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">Why multimodal?</p>
        <h2 className="max-w-2xl text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          Two retinal views. One eye.
        </h2>
      </Reveal>

      <div className="mt-14 grid grid-cols-1 items-center gap-6 md:grid-cols-[1fr_auto_1fr]">
        <Reveal delay={0.05}>
          <GlassCard className="text-center">
            <div className="mx-auto mb-5 h-28 w-28 rounded-full bg-gradient-to-br from-accent-blue/40 to-transparent" />
            <h3 className="text-lg font-medium text-ink">OCT</h3>
            <p className="mt-1 text-sm text-ink-muted">Structural view</p>
            <p className="mt-4 text-sm leading-relaxed text-ink-muted">
              A cross-sectional scan of retinal layers — shows detailed structure,
              like nerve fiber thickness, that a photo can&apos;t capture.
            </p>
          </GlassCard>
        </Reveal>

        <Reveal delay={0.15} className="flex justify-center">
          <motion.div
            className="flex h-14 w-14 items-center justify-center rounded-full glass text-accent-cyan"
            animate={{ scale: [1, 1.08, 1] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
            aria-hidden
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M4 12h16M14 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </motion.div>
        </Reveal>

        <Reveal delay={0.25}>
          <GlassCard className="text-center">
            <div className="mx-auto mb-5 h-28 w-28 rounded-full bg-gradient-to-br from-accent-violet/40 to-transparent" />
            <h3 className="text-lg font-medium text-ink">Fundus</h3>
            <p className="mt-1 text-sm text-ink-muted">Broader retinal view</p>
            <p className="mt-4 text-sm leading-relaxed text-ink-muted">
              A color photograph of the back of the eye — captures the optic
              disc and overall retinal appearance at a glance.
            </p>
          </GlassCard>
        </Reveal>
      </div>

      <Reveal delay={0.3} className="mx-auto mt-10 max-w-2xl text-center">
        <p className="text-ink-muted leading-relaxed">
          The model processes both separately, then learns how the two sources
          of information relate to each other before making a prediction —
          instead of relying on only one view of the eye.
        </p>
      </Reveal>
    </section>
  );
}

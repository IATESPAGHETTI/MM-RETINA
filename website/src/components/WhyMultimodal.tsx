"use client";

import { motion } from "framer-motion";
import { Reveal } from "./Reveal";

const SIGNALS = [
  {
    label: "OCT",
    desc: "Detailed structural information",
    align: "left" as const,
  },
  {
    label: "Fundus",
    desc: "Broader retinal view",
    align: "right" as const,
  },
];

export function WhyMultimodal() {
  return (
    <section className="relative mx-auto max-w-5xl px-6 py-32">
      <Reveal>
        <p className="mb-4 text-xs uppercase tracking-[0.3em] text-ink-faint">Why multimodal</p>
        <h2 className="max-w-lg text-4xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-5xl">
          Two retinal views.
          <br />
          One learned representation.
        </h2>
      </Reveal>

      <div className="relative mt-24 grid grid-cols-1 items-center gap-16 md:grid-cols-2">
        {SIGNALS.map((s, i) => (
          <Reveal key={s.label} delay={i * 0.1} className={s.align === "right" ? "md:text-right" : ""}>
            <div className={`flex flex-col gap-3 ${s.align === "right" ? "md:items-end" : ""}`}>
              <span className="text-5xl font-semibold tracking-tight text-ink sm:text-6xl">{s.label}</span>
              <span className="max-w-xs text-sm leading-relaxed text-ink-muted">{s.desc}</span>
            </div>
          </Reveal>
        ))}

        {/* Converging connector, hidden on small screens where the two
            columns stack and a diagonal line reads as noise. */}
        <svg
          className="pointer-events-none absolute inset-0 hidden w-full md:block"
          viewBox="0 0 400 120"
          preserveAspectRatio="none"
          aria-hidden
        >
          <motion.path
            d="M 60 10 C 150 10, 150 60, 200 60"
            fill="none"
            stroke="url(#whyGradient)"
            strokeWidth="1"
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 0.8 }}
            viewport={{ once: true }}
            transition={{ duration: 1, delay: 0.3, ease: "easeInOut" }}
          />
          <motion.path
            d="M 340 10 C 250 10, 250 60, 200 60"
            fill="none"
            stroke="url(#whyGradient)"
            strokeWidth="1"
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 0.8 }}
            viewport={{ once: true }}
            transition={{ duration: 1, delay: 0.45, ease: "easeInOut" }}
          />
          <defs>
            <linearGradient id="whyGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#6fd8e8" />
              <stop offset="100%" stopColor="#9c8cf0" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <Reveal delay={0.3} className="mx-auto mt-16 max-w-xl text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-accent-cyan">Fused representation</p>
        <p className="mt-4 text-ink-muted leading-relaxed">
          The model processes both separately, then learns how the two
          sources of information relate to each other before making a
          prediction — instead of relying on only one view of the eye.
        </p>
      </Reveal>
    </section>
  );
}

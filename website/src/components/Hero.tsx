"use client";

import { motion, type Variants } from "framer-motion";
import Link from "next/link";
import { GlassCard } from "./GlassCard";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.14, delayChildren: 0.15 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 22, filter: "blur(8px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.8, ease: EASE_OUT },
  },
};

export function Hero() {
  return (
    <section className="relative flex min-h-[92vh] items-center overflow-hidden pt-28">
      <div className="atmosphere" />
      <div className="noise" />

      <div className="relative z-10 mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-14 px-6 lg:grid-cols-2">
        <motion.div variants={container} initial="hidden" animate="show">
          <motion.p
            variants={item}
            className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-widest text-ink-muted"
          >
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-cyan" />
            Research prototype
          </motion.p>

          <motion.h1
            variants={item}
            className="text-4xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-5xl lg:text-6xl"
          >
            Seeing the retina.
            <br />
            <span className="text-gradient">Understanding the whole picture.</span>
          </motion.h1>

          <motion.p variants={item} className="mt-6 max-w-md text-lg leading-relaxed text-ink-muted">
            A multimodal AI system combining OCT volumes and retinal fundus imaging
            for glaucoma grading — built to test whether two views of the same eye
            beat one.
          </motion.p>

          <motion.div variants={item} className="mt-9 flex flex-wrap items-center gap-4">
            <Link
              href="/model"
              className="rounded-full bg-white px-6 py-3 text-sm font-medium text-black transition-transform hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-8px_rgba(255,255,255,0.35)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-cyan"
            >
              Explore the model
            </Link>
            <Link
              href="/research"
              className="rounded-full border border-white/15 px-6 py-3 text-sm font-medium text-ink transition-colors hover:border-white/30 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-cyan"
            >
              View research
            </Link>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.5, ease: EASE_OUT }}
          className="relative mx-auto w-full max-w-md"
        >
          <GlassCard strong className="relative overflow-hidden">
            <div className="mb-4 flex items-center justify-between text-xs text-ink-muted">
              <span>AI ANALYSIS</span>
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-accent-cyan" />
                inference status: idle
              </span>
            </div>

            <div className="mb-5 grid grid-cols-2 gap-3">
              <div className="aspect-square rounded-xl bg-gradient-to-br from-accent-blue/25 to-transparent" />
              <div className="aspect-square rounded-xl bg-gradient-to-br from-accent-violet/25 to-transparent" />
            </div>

            <div className="flex items-center justify-between text-xs text-ink-faint">
              <span>OCT volume</span>
              <span>Fundus image</span>
            </div>

            <div className="mt-6 border-t border-white/10 pt-4 text-sm text-ink-muted">
              Two retinal views, one fused representation — see how on{" "}
              <Link href="/model" className="text-ink underline underline-offset-4">
                /model
              </Link>
              .
            </div>
          </GlassCard>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 1, ease: EASE_OUT }}
            className="glass absolute -bottom-6 -left-6 hidden rounded-xl px-4 py-3 text-xs text-ink-muted sm:block"
          >
            300 paired samples · GAMMA
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

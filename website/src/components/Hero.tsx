"use client";

import { motion, type Variants } from "framer-motion";
import Link from "next/link";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1, delayChildren: 0.1 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 26, filter: "blur(10px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.9, ease: EASE_OUT },
  },
};

/** Abstract stack of OCT B-scan slices — the visual motif carried through
 * the rest of the site (see ArchitecturePipeline), not a stock render. */
function SliceStack() {
  const slices = Array.from({ length: 7 });
  return (
    <div className="relative h-[420px] w-full max-w-sm select-none" aria-hidden>
      {slices.map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: 40, y: -10 }}
          animate={{ opacity: 1, x: 0, y: 0 }}
          transition={{ duration: 1, delay: 0.5 + i * 0.08, ease: EASE_OUT }}
          className="absolute inset-x-6 rounded-[2px] border border-white/10"
          style={{
            top: `${i * 13}%`,
            height: "58%",
            transform: `translateZ(0) skewY(-3deg)`,
            background: `linear-gradient(180deg, rgba(111,216,232,${0.05 + i * 0.012}) 0%, rgba(156,140,240,${0.04 + i * 0.01}) 100%)`,
            zIndex: slices.length - i,
          }}
        />
      ))}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1.1 }}
        className="absolute -bottom-2 left-6 text-[10px] uppercase tracking-widest text-ink-faint"
      >
        256 B-scans, one volume
      </motion.div>
    </div>
  );
}

export function Hero() {
  return (
    <section className="relative flex min-h-[100svh] items-center overflow-hidden pt-24">
      <div className="atmosphere" />
      <div className="noise" />

      <div className="relative z-10 mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-10 px-6 lg:grid-cols-[1.15fr_0.85fr] lg:gap-6">
        <motion.div variants={container} initial="hidden" animate="show">
          <motion.p
            variants={item}
            className="mb-6 text-xs uppercase tracking-[0.3em] text-ink-faint"
          >
            MM · RETINA — research prototype
          </motion.p>

          <motion.h1
            variants={item}
            className="text-[13vw] font-semibold leading-[0.94] tracking-tight text-ink sm:text-7xl lg:text-[5.5rem]"
          >
            See the eye.
            <br />
            <span className="text-gradient">Understand the signal.</span>
          </motion.h1>

          <motion.p variants={item} className="mt-8 max-w-md text-lg leading-relaxed text-ink-muted">
            Multimodal retinal intelligence for glaucoma grading — combining
            OCT volumes with fundus imaging to test whether two views of the
            same eye beat one.
          </motion.p>

          <motion.div variants={item} className="mt-10 flex flex-wrap items-center gap-5">
            <Link
              href="/model"
              className="rounded-full bg-white px-6 py-3 text-sm font-medium text-black transition-transform hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-8px_rgba(255,255,255,0.35)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-cyan"
            >
              Explore the model
            </Link>
            <Link
              href="/research"
              className="text-sm font-medium text-ink-muted underline decoration-white/20 underline-offset-8 transition-colors hover:text-ink hover:decoration-white/50 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-cyan"
            >
              View research
            </Link>
          </motion.div>
        </motion.div>

        <div className="relative mx-auto hidden w-full items-center justify-center lg:flex">
          <SliceStack />

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.3, ease: EASE_OUT }}
            className="glass absolute -bottom-4 -left-8 w-56 rounded-xl px-4 py-3 text-xs text-ink-muted"
          >
            <div className="mb-1 flex items-center gap-1.5 text-ink">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-cyan" />
              inference status: idle
            </div>
            Fused OCT + fundus representation
          </motion.div>
        </div>
      </div>
    </section>
  );
}

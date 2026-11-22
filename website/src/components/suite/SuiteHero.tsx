"use client";

import Link from "next/link";
import { motion, type Variants } from "framer-motion";
import { SUITE_URL } from "@/lib/suiteContent";
import { MergeDiagram } from "./MergeDiagram";

const EASE = [0.16, 1, 0.3, 1] as const;

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1, delayChildren: 0.1 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 24, filter: "blur(10px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.9, ease: EASE } },
};

export function SuiteHero() {
  return (
    <section className="relative flex min-h-[92svh] items-center overflow-hidden pt-28 pb-16">
      <div className="atmosphere" />
      <div className="noise" />

      <div className="relative z-10 mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-12 px-6 lg:grid-cols-[1fr_1.1fr]">
        <motion.div variants={container} initial="hidden" animate="show">
          <motion.p variants={item} className="mb-6 text-xs uppercase tracking-[0.3em] text-ink-faint">
            Retina Suite — research workspace
          </motion.p>

          <motion.h1
            variants={item}
            className="text-[11vw] font-semibold leading-[0.96] tracking-tight text-ink sm:text-6xl lg:text-[4.4rem]"
          >
            Three projects.
            <br />
            <span className="shimmer-text">One workspace.</span>
          </motion.h1>

          <motion.p variants={item} className="mt-8 max-w-lg text-lg leading-relaxed text-ink-muted">
            Glaucoma grading from fundus and OCT, glaucoma staging from clinical measurements, and diabetes
            vessel analysis, side by side in one app with one API. Each module keeps its own data, its own
            models and its own evidence.
          </motion.p>

          <motion.div variants={item} className="mt-10 flex flex-wrap items-center gap-5">
            <a
              href={SUITE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-full bg-ink px-6 py-3 text-sm font-medium text-bg transition-transform hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-8px_rgba(245,243,238,0.3)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
            >
              Open the workspace
            </a>
            <Link
              href="#modules"
              className="text-sm font-medium text-ink-muted underline decoration-white/20 underline-offset-8 transition-colors hover:text-ink hover:decoration-white/50 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
            >
              Explore the modules
            </Link>
          </motion.div>

          <motion.p variants={item} className="mt-6 max-w-md text-xs leading-relaxed text-ink-faint">
            The workspace is a separate app that needs its local backend running (see{" "}
            <Link href="#run" className="underline decoration-white/20 underline-offset-4 hover:text-ink-muted">
              run it locally
            </Link>
            ). Research prototype, not a medical device.
          </motion.p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96, filter: "blur(12px)" }}
          animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
          transition={{ duration: 1.2, delay: 0.25, ease: EASE }}
          className="glass float-slow rounded-3xl p-5 sm:p-8"
        >
          <MergeDiagram className="h-auto w-full" />
        </motion.div>
      </div>
    </section>
  );
}

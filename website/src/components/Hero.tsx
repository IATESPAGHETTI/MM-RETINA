"use client";

import { motion, type Variants } from "framer-motion";
import Image from "next/image";
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

export function Hero() {
  return (
    <section className="relative flex min-h-[100svh] items-center overflow-hidden pt-24">
      <div className="atmosphere" />
      <div className="noise" />

      <div className="relative z-10 mx-auto grid w-full max-w-6xl grid-cols-1 items-center gap-10 px-6 lg:grid-cols-[1fr_1.05fr] lg:gap-4">
        <motion.div variants={container} initial="hidden" animate="show" className="relative z-10">
          <motion.p
            variants={item}
            className="mb-6 text-xs uppercase tracking-[0.3em] text-ink-faint"
          >
            MM · RETINA — research prototype
          </motion.p>

          <motion.h1
            variants={item}
            className="text-[13vw] font-semibold leading-[0.94] tracking-tight text-ink sm:text-7xl lg:text-[5.2rem]"
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
              className="rounded-full bg-ink px-6 py-3 text-sm font-medium text-bg transition-transform hover:-translate-y-0.5 hover:shadow-[0_10px_30px_-8px_rgba(245,243,238,0.3)] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
            >
              Explore the model
            </Link>
            <Link
              href="/research"
              className="text-sm font-medium text-ink-muted underline decoration-white/20 underline-offset-8 transition-colors hover:text-ink hover:decoration-white/50 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-champagne"
            >
              View research
            </Link>
          </motion.div>
        </motion.div>

        {/* Real GAMMA fundus photograph — the retinal image is the visual
            identity here, not an abstract UI shape. */}
        <motion.div
          initial={{ opacity: 0, scale: 1.04, filter: "blur(16px)" }}
          animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
          transition={{ duration: 1.4, delay: 0.2, ease: EASE_OUT }}
          className="relative -mx-6 aspect-[4/5] w-[calc(100%+3rem)] overflow-hidden rounded-none sm:mx-0 sm:w-full sm:rounded-3xl lg:aspect-[5/6]"
        >
          <Image
            src="/samples/gamma-0001-fundus.jpg"
            alt="Real color fundus photograph from the GAMMA dataset, sample 0001"
            fill
            priority
            sizes="(min-width: 1024px) 45vw, 100vw"
            className="object-cover"
            style={{ filter: "saturate(0.85) contrast(1.05) brightness(0.95)" }}
          />
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                "radial-gradient(120% 100% at 30% 20%, transparent 40%, rgba(16,16,16,0.55) 100%), linear-gradient(0deg, rgba(16,16,16,0.65), transparent 45%)",
            }}
          />

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.2, ease: EASE_OUT }}
            className="glass absolute bottom-5 left-5 right-5 flex items-center justify-between rounded-xl px-4 py-3 text-xs text-ink-muted sm:right-auto sm:w-64"
          >
            <div>
              <div className="mb-1 flex items-center gap-1.5 text-ink">
                <span className="h-1.5 w-1.5 rounded-full bg-accent-champagne" />
                GAMMA sample 0001
              </div>
              Real fundus photograph — CC BY-NC-ND
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

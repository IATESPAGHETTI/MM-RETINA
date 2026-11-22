"use client";

import Image from "next/image";
import { motion, useReducedMotion } from "framer-motion";
import { GAMMA_SAMPLE_RUN } from "@/lib/suiteContent";

const EASE = [0.16, 1, 0.3, 1] as const;

/** Real GAMMA fundus photo, a scanning sweep, and the actual three-model run on that sample. */
export function GammaVisual() {
  const reduce = useReducedMotion();
  return (
    <div className="relative aspect-[4/3] overflow-hidden rounded-2xl border border-white/10 bg-black/40">
      <Image
        src="/samples/gamma-0001-fundus.jpg"
        alt="Real colour fundus photograph from the GAMMA dataset, sample 0001"
        fill
        sizes="(min-width: 1024px) 40vw, 100vw"
        className="object-cover"
        style={{ filter: "saturate(0.85) contrast(1.05) brightness(0.72)" }}
      />
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: "linear-gradient(0deg, rgba(16,16,16,0.92) 8%, rgba(16,16,16,0.15) 62%)" }}
      />
      {!reduce && (
        <motion.div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 h-20"
          style={{ background: "linear-gradient(180deg, transparent, rgba(217,185,138,0.28), transparent)" }}
          initial={{ top: "-25%" }}
          animate={{ top: "105%" }}
          transition={{ duration: 3.6, repeat: Infinity, ease: "easeInOut", repeatDelay: 0.8 }}
        />
      )}

      <div className="glass absolute inset-x-3 bottom-3 rounded-xl p-4 sm:inset-x-4 sm:bottom-4">
        <p className="text-[11px] uppercase tracking-widest text-ink-faint">{GAMMA_SAMPLE_RUN.sample} · live run</p>
        {GAMMA_SAMPLE_RUN.models.map((m, i) => (
          <div key={m.name} className="mt-2.5">
            <div className="flex justify-between text-xs">
              <span className="text-ink">{m.name}</span>
              <span className="text-ink-muted">
                {m.prediction} · {(m.probability * 100).toFixed(1)}%
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-white/10">
              <motion.div
                className="h-full rounded-full bg-accent-champagne"
                initial={{ width: 0 }}
                whileInView={{ width: `${m.probability * 100}%` }}
                viewport={{ once: true }}
                transition={{ duration: 1, delay: 0.25 + i * 0.15, ease: EASE }}
              />
            </div>
          </div>
        ))}
        <p className="mt-3 flex items-center gap-1.5 text-xs text-accent-champagne">
          <span className="h-1.5 w-1.5 rounded-full bg-accent-champagne" aria-hidden />
          {GAMMA_SAMPLE_RUN.banner}
        </p>
        <p className="mt-1 text-[10px] leading-snug text-ink-faint">{GAMMA_SAMPLE_RUN.caveat}</p>
      </div>
    </div>
  );
}

const FEATURES = ["RNFL", "GCC", "CDR", "IOP", "Age", "Sex"] as const;
/** Increasing tint reads as increasing severity. Colour alpha, not element opacity, because the
 * entrance animation owns `opacity` and would override it. */
const STAGES = [
  { name: "Control", tint: "bg-accent-champagne/25 text-ink" },
  { name: "Mild", tint: "bg-accent-champagne/45 text-ink" },
  { name: "Moderate", tint: "bg-accent-champagne/70 text-bg" },
  { name: "Severe", tint: "bg-accent-champagne text-bg" },
] as const;

/** Illustration of the decision flow. It carries no model output and no numbers. */
export function GlaucomaVisual() {
  const reduce = useReducedMotion();
  const blink = (delay: number) =>
    reduce
      ? undefined
      : { opacity: [1, 0.35, 1], transition: { duration: 6, repeat: Infinity, delay, times: [0, 0.5, 1] } };

  return (
    <div className="flex aspect-[4/3] flex-col justify-between rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.04] to-transparent p-5 sm:p-6">
      <div>
        <p className="text-[11px] uppercase tracking-widest text-ink-faint">1 · Measurements</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {FEATURES.map((f, i) => (
            <motion.span
              key={f}
              initial={{ opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.06, ease: EASE }}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-ink-muted"
            >
              {f}
            </motion.span>
          ))}
        </div>
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-widest text-ink-faint">2 · Four-stage grade</p>
        <div className="mt-2 grid grid-cols-4 gap-1.5">
          {STAGES.map((s, i) => (
            <motion.div
              key={s.name}
              initial={{ scaleY: 0.2, opacity: 0 }}
              whileInView={{ scaleY: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.3 + i * 0.1, ease: EASE }}
              style={{ transformOrigin: "bottom" }}
              className={`rounded-md px-1 py-2 text-center text-[11px] font-medium ${s.tint}`}
            >
              {s.name}
            </motion.div>
          ))}
        </div>
      </div>

      <div>
        <p className="text-[11px] uppercase tracking-widest text-ink-faint">3 · Is the model sure?</p>
        <div className="mt-2 grid grid-cols-2 gap-3">
          <motion.div animate={blink(0)} className="rounded-xl border border-accent-olive/40 bg-accent-olive/10 p-3">
            <p className="text-sm font-medium text-ink">Confident</p>
            <p className="mt-0.5 text-xs text-ink-muted">Shows the stage and the features behind it.</p>
          </motion.div>
          <motion.div animate={blink(3)} className="rounded-xl border border-accent-copper/50 bg-accent-copper/10 p-3">
            <p className="text-sm font-medium text-ink">Inconclusive</p>
            <p className="mt-0.5 text-xs text-ink-muted">Recommends a visual-field test instead.</p>
          </motion.div>
        </div>
      </div>
      <p className="mt-3 text-[10px] text-ink-faint">Illustration of the decision flow, not model output.</p>
    </div>
  );
}

const VESSELS = [
  "M60 120 C 110 110, 150 90, 200 70",
  "M120 108 C 150 120, 190 140, 250 150",
  "M200 70 C 230 60, 260 62, 300 50",
  "M200 70 C 225 85, 255 95, 292 110",
  "M150 118 C 160 150, 175 175, 200 205",
  "M120 108 C 110 80, 100 55, 85 30",
  "M95 112 C 90 150, 80 180, 62 215",
] as const;

/** Decorative vessel tree that draws itself in. Not a patient image and not model output. */
export function DiabetesVisual() {
  const reduce = useReducedMotion();
  return (
    <div className="relative flex aspect-[4/3] flex-col justify-between overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-accent-copper/10 via-transparent to-transparent p-5 sm:p-6">
      <svg viewBox="0 0 320 240" className="h-full w-full" role="img" aria-label="Illustration of a branching retinal vessel tree">
        {VESSELS.map((d, i) => (
          <motion.path
            key={d}
            d={d}
            fill="none"
            stroke="#d9b98a"
            strokeWidth={i === 0 ? 3.2 : 2}
            strokeLinecap="round"
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 0.9 }}
            viewport={{ once: true }}
            transition={{ duration: 1.1, delay: 0.15 + i * 0.18, ease: EASE }}
          />
        ))}
        {!reduce && (
          <motion.circle
            cx="60"
            cy="120"
            r="16"
            fill="none"
            stroke="#b8785a"
            strokeWidth="1.5"
            initial={{ scale: 1, opacity: 0.7 }}
            animate={{ scale: 1.9, opacity: 0 }}
            transition={{ duration: 2.4, repeat: Infinity, ease: EASE }}
            style={{ transformOrigin: "60px 120px" }}
          />
        )}
        <circle cx="60" cy="120" r="16" fill="rgba(184,120,90,0.45)" stroke="#b8785a" />
      </svg>
      <div className="mt-2 flex flex-wrap gap-2">
        {["Vessel density", "Fractal dimension", "HbA1c (experimental)"].map((c) => (
          <span key={c} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-ink-muted">
            {c}
          </span>
        ))}
      </div>
      <p className="mt-2 text-[10px] text-ink-faint">Illustration, not a patient image.</p>
    </div>
  );
}

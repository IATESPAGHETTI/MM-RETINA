"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import { Reveal } from "./Reveal";

/** Schematic cross-section of retinal layers — a labeled diagram, not a
 * stand-in for a real B-scan (we don't yet have extracted per-slice pixels
 * from the GAMMA volumes; see dataset/README.md). Kept honest rather than
 * dressing up a fabricated "scan". */
function OCTSchematic() {
  const layers = [
    { d: "M0,40 C60,20 140,60 220,35", opacity: 0.5 },
    { d: "M0,70 C60,55 140,90 220,68", opacity: 0.7 },
    { d: "M0,100 C60,88 140,118 220,98", opacity: 0.9 },
    { d: "M0,128 C60,120 140,142 220,126", opacity: 0.6 },
  ];
  return (
    <svg viewBox="0 0 220 160" className="h-full w-full" role="img" aria-label="Schematic cross-section of retinal layers, representing an OCT B-scan">
      <rect width="220" height="160" fill="var(--bg-elevated)" />
      {layers.map((l, i) => (
        <motion.path
          key={i}
          d={l.d}
          fill="none"
          stroke="var(--accent-champagne)"
          strokeWidth={1}
          strokeOpacity={l.opacity}
          initial={{ pathLength: 0 }}
          whileInView={{ pathLength: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, delay: i * 0.15, ease: "easeInOut" }}
        />
      ))}
    </svg>
  );
}

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

      <div className="mt-20 grid grid-cols-1 gap-10 md:grid-cols-2">
        <Reveal>
          <div className="overflow-hidden rounded-2xl border border-white/8">
            <OCTSchematic />
          </div>
          <div className="mt-4 flex flex-col gap-1">
            <span className="text-2xl font-semibold tracking-tight text-ink">OCT</span>
            <span className="text-sm text-ink-muted">Detailed structural information — cross-sectional layers of the retina</span>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="relative aspect-[220/160] overflow-hidden rounded-2xl border border-white/8">
            <Image
              src="/samples/gamma-0001-fundus.jpg"
              alt="Real color fundus photograph from the GAMMA dataset"
              fill
              sizes="(min-width: 768px) 45vw, 90vw"
              className="object-cover"
              style={{ filter: "saturate(0.85) contrast(1.05)" }}
            />
          </div>
          <div className="mt-4 flex flex-col gap-1">
            <span className="text-2xl font-semibold tracking-tight text-ink">Fundus</span>
            <span className="text-sm text-ink-muted">A broader color photograph of the retina and optic disc</span>
          </div>
        </Reveal>
      </div>

      <Reveal delay={0.25} className="mx-auto mt-16 max-w-xl text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-accent-champagne">Fused representation</p>
        <p className="mt-4 text-ink-muted leading-relaxed">
          The model processes both separately, then learns how the two
          sources of information relate to each other before making a
          prediction — instead of relying on only one view of the eye.
        </p>
      </Reveal>
    </section>
  );
}

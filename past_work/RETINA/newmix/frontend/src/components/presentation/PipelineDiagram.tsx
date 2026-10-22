"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";
import { EASE } from "./primitives";

export type Stage = "fundusEnc" | "sampler" | "octEnc" | "fusion";

export interface PipelineConfig {
  fundusEnc: { title: string; sub: string };
  sampler: { title: string; sub: string };
  octEnc: { title: string; sub: string };
  fusion: { title: string; sub: string };
  /** Which stage(s) differ from the frozen baseline — drawn with a highlight. */
  changed?: Stage[];
}

export const BASE_PIPELINE: PipelineConfig = {
  fundusEnc: { title: "ResNet18", sub: "11.18M parameters" },
  sampler: { title: "8 single slices", sub: "1 grayscale B-scan each" },
  octEnc: { title: "ResNet18 + attention pool", sub: "8 slice vectors → 1" },
  fusion: { title: "Cross-modal transformer", sub: "2 tokens: 1 fundus + 1 OCT" },
};

function Node({
  label,
  title,
  sub,
  changed,
  muted,
  delay = 0,
  className = "",
  children,
}: {
  label: string;
  title?: string;
  sub?: string;
  changed?: boolean;
  muted?: boolean;
  delay?: number;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.6, ease: EASE }}
      className={`relative flex flex-col justify-center rounded-xl border px-4 py-3 ${
        changed
          ? "border-accent-champagne/70 bg-accent-champagne/10 shadow-[0_0_32px_-8px_rgba(217,185,138,0.55)]"
          : muted
            ? "border-white/8 bg-white/[0.02]"
            : "border-white/12 bg-white/[0.035]"
      } ${className}`}
    >
      {changed && (
        <span className="absolute -top-2.5 right-3 rounded-full bg-accent-champagne px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-black">
          Changed
        </span>
      )}
      <p className="text-xs uppercase tracking-[0.18em] text-ink-faint">{label}</p>
      {title && <p className={`mt-1 text-lg font-medium leading-tight ${changed ? "text-accent-champagne" : "text-ink"}`}>{title}</p>}
      {sub && <p className="mt-0.5 text-base leading-snug text-ink-muted">{sub}</p>}
      {children}
    </motion.div>
  );
}

const Arrow = () => (
  <span aria-hidden className="flex shrink-0 items-center px-0.5 text-lg text-ink-faint">
    →
  </span>
);

/** The fusion pipeline, with whatever an experiment changed lit up. */
export function PipelineDiagram({ config }: { config: PipelineConfig }) {
  const ch = (s: Stage) => config.changed?.includes(s) ?? false;
  return (
    <div className="flex items-stretch gap-2">
      <div className="flex flex-[3.4] flex-col gap-4">
        <div className="flex flex-1 items-stretch gap-2">
          <Node label="Input" title="Fundus photo" sub="colour, 160 px" muted className="flex-1" delay={0.1} />
          <Arrow />
          <Node label="Fundus encoder" {...config.fundusEnc} changed={ch("fundusEnc")} className="flex-[2.5]" delay={0.2} />
        </div>
        <div className="flex flex-1 items-stretch gap-2">
          <Node label="Input" title="OCT volume" sub="256 B-scans" muted className="flex-1" delay={0.15} />
          <Arrow />
          <Node label="Slice sampler" {...config.sampler} changed={ch("sampler")} className="flex-[1.25]" delay={0.25} />
          <Arrow />
          <Node label="OCT encoder" {...config.octEnc} changed={ch("octEnc")} className="flex-[1.25]" delay={0.3} />
        </div>
      </div>
      <Arrow />
      <Node label="Fusion" {...config.fusion} changed={ch("fusion")} className="flex-[1.25]" delay={0.4} />
      <Arrow />
      <Node label="Output" title="Severity grade" delay={0.5} className="flex-[0.9]">
        <p className="mt-1 text-base leading-snug text-ink-muted">Normal · Early · Progressive</p>
      </Node>
    </div>
  );
}

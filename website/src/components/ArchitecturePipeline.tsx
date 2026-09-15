"use client";

import { motion, type Variants } from "framer-motion";
import { Reveal } from "./Reveal";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const nodeVariants: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.94 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.6, delay: i * 0.12, ease: EASE_OUT },
  }),
};

const pathVariants: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  show: (i: number) => ({
    pathLength: 1,
    opacity: 1,
    transition: { duration: 0.9, delay: 0.3 + i * 0.12, ease: "easeInOut" },
  }),
};

const NODES = [
  { id: "oct", label: "OCT volume", sub: "256 B-scans", x: 60, y: 40 },
  { id: "oct-enc", label: "OCT encoder", sub: "shared per-slice CNN", x: 60, y: 150 },
  { id: "oct-tok", label: "OCT tokens", sub: "attention-pooled", x: 60, y: 260 },
  { id: "fundus", label: "Fundus image", sub: "single RGB frame", x: 340, y: 40 },
  { id: "fundus-enc", label: "Vision encoder", sub: "CNN backbone", x: 340, y: 150 },
  { id: "fundus-tok", label: "Fundus tokens", sub: "GAP feature", x: 340, y: 260 },
  { id: "fusion", label: "Cross-modal attention", sub: "transformer fusion", x: 200, y: 360 },
  { id: "grade", label: "Glaucoma grade", sub: "Normal / Early / Progressive", x: 200, y: 460 },
];

const EDGES: Array<[string, string]> = [
  ["oct", "oct-enc"],
  ["oct-enc", "oct-tok"],
  ["fundus", "fundus-enc"],
  ["fundus-enc", "fundus-tok"],
  ["oct-tok", "fusion"],
  ["fundus-tok", "fusion"],
  ["fusion", "grade"],
];

function byId(id: string) {
  return NODES.find((n) => n.id === id)!;
}

export function ArchitecturePipeline() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-28">
      <Reveal>
        <p className="mb-3 text-xs uppercase tracking-widest text-ink-faint">The architecture</p>
        <h2 className="max-w-2xl text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          From two views to one representation.
        </h2>
      </Reveal>

      <Reveal delay={0.1} className="mt-14 overflow-x-auto">
        <svg viewBox="0 0 400 520" className="mx-auto w-full max-w-lg" role="img" aria-label="Model architecture: OCT and fundus branches feed a cross-modal attention block that outputs a glaucoma grade">
          {EDGES.map(([from, to], i) => {
            const a = byId(from);
            const b = byId(to);
            const midY = (a.y + b.y) / 2 + 22;
            return (
              <motion.path
                key={`${from}-${to}`}
                d={`M ${a.x} ${a.y + 22} C ${a.x} ${midY}, ${b.x} ${midY}, ${b.x} ${b.y - 22}`}
                fill="none"
                stroke="url(#edgeGradient)"
                strokeWidth={1.5}
                custom={i}
                variants={pathVariants}
                initial="hidden"
                whileInView="show"
                viewport={{ once: true }}
              />
            );
          })}

          <defs>
            <linearGradient id="edgeGradient" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#6fd8e8" stopOpacity={0.7} />
              <stop offset="100%" stopColor="#9c8cf0" stopOpacity={0.7} />
            </linearGradient>
          </defs>

          {NODES.map((n, i) => (
            <motion.g
              key={n.id}
              custom={i}
              variants={nodeVariants}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true }}
            >
              <rect
                x={n.x - 78}
                y={n.y - 22}
                width={156}
                height={44}
                rx={12}
                fill="rgba(255,255,255,0.05)"
                stroke="rgba(255,255,255,0.12)"
              />
              <text x={n.x} y={n.y - 3} textAnchor="middle" fontSize="11" fill="#f3f4f6" fontWeight={500}>
                {n.label}
              </text>
              <text x={n.x} y={n.y + 12} textAnchor="middle" fontSize="8.5" fill="#9aa1ac">
                {n.sub}
              </text>
            </motion.g>
          ))}
        </svg>
      </Reveal>

      <Reveal delay={0.2} className="mx-auto mt-10 max-w-2xl text-center text-sm leading-relaxed text-ink-muted">
        Each OCT volume contributes 256 B-scans; a shared encoder turns every
        slice into a compact embedding, then a lightweight transformer pools
        them into one OCT summary — avoiding a full 3D network that
        wouldn&apos;t fit comfortably in 6GB of GPU memory. The fundus image
        goes through its own encoder. Cross-modal attention then lets each
        modality inform the other before the final grade is predicted.
      </Reveal>
    </section>
  );
}

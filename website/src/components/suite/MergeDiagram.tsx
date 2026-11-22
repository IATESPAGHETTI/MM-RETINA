"use client";

import { motion, useReducedMotion } from "framer-motion";

const EASE = [0.16, 1, 0.3, 1] as const;

const NODES = [
  { y: 20, label: "RETINA", sub: "Diabetes vessels" },
  { y: 108, label: "Sankara research", sub: "Glaucoma staging" },
  { y: 196, label: "MM-RETINA", sub: "GAMMA multimodal" },
] as const;

const NODE_X = 8;
const NODE_W = 200;
const NODE_H = 64;
const HUB = { x: 462, y: 140, r: 46 } as const;

/** Three project cards whose connectors draw in, then carry flowing dashes into one hub.
 * Purely decorative: the meaning is carried by the aria-label. Continuous motion is
 * skipped under prefers-reduced-motion (the lines still draw in once). */
export function MergeDiagram({ className }: { className?: string }) {
  const reduce = useReducedMotion();

  return (
    <svg
      viewBox="0 0 560 280"
      role="img"
      aria-label="Three projects (RETINA diabetes, Sankara glaucoma research and MM-RETINA GAMMA) merge into one Retina Suite workspace"
      className={className}
    >
      <defs>
        {/* userSpaceOnUse: a perfectly horizontal path has a zero-height bounding box, and an
            objectBoundingBox gradient would not paint at all. */}
        <linearGradient id="merge-line" gradientUnits="userSpaceOnUse" x1={NODE_X + NODE_W} y1="0" x2={HUB.x - HUB.r} y2="0">
          <stop offset="0" stopColor="#b8785a" />
          <stop offset="1" stopColor="#d9b98a" />
        </linearGradient>
        <radialGradient id="hub-glow">
          <stop offset="0" stopColor="#d9b98a" stopOpacity="0.32" />
          <stop offset="1" stopColor="#d9b98a" stopOpacity="0" />
        </radialGradient>
      </defs>

      <circle cx={HUB.x} cy={HUB.y} r="110" fill="url(#hub-glow)" />

      {NODES.map((node, i) => {
        const y = node.y + NODE_H / 2;
        const d = `M${NODE_X + NODE_W} ${y} C 320 ${y}, 335 ${HUB.y}, ${HUB.x - HUB.r} ${HUB.y}`;
        return (
          <g key={node.label}>
            <motion.path
              d={d}
              fill="none"
              stroke="url(#merge-line)"
              strokeWidth="1.5"
              strokeLinecap="round"
              initial={{ pathLength: 0, opacity: 0 }}
              whileInView={{ pathLength: 1, opacity: 0.95 }}
              viewport={{ once: true }}
              transition={{ duration: 1.1, delay: 0.35 + i * 0.18, ease: EASE }}
            />
            {!reduce && (
              <motion.path
                d={d}
                fill="none"
                stroke="#f5f3ee"
                strokeOpacity="0.75"
                strokeWidth="2"
                strokeLinecap="round"
                strokeDasharray="2 22"
                initial={{ strokeDashoffset: 0 }}
                animate={{ strokeDashoffset: -96 }}
                transition={{ duration: 3.2, repeat: Infinity, ease: "linear", delay: i * 0.4 }}
              />
            )}
            <motion.g
              initial={{ opacity: 0, x: -18 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: i * 0.12, ease: EASE }}
            >
              <rect
                x={NODE_X}
                y={node.y}
                width={NODE_W}
                height={NODE_H}
                rx="16"
                fill="rgba(245,243,238,0.05)"
                stroke="rgba(245,243,238,0.14)"
              />
              <circle cx={NODE_X + 22} cy={node.y + NODE_H / 2} r="4" fill="#d9b98a" />
              <text x={NODE_X + 40} y={node.y + 28} className="fill-ink" fontSize="15" fontWeight="600">
                {node.label}
              </text>
              <text x={NODE_X + 40} y={node.y + 47} className="fill-ink-muted" fontSize="12">
                {node.sub}
              </text>
            </motion.g>
          </g>
        );
      })}

      <motion.g
        initial={{ opacity: 0, scale: 0.85 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.9, delay: 0.9, ease: EASE }}
        style={{ transformOrigin: `${HUB.x}px ${HUB.y}px` }}
      >
        {!reduce && (
          <motion.circle
            cx={HUB.x}
            cy={HUB.y}
            r={HUB.r}
            fill="none"
            stroke="#d9b98a"
            strokeWidth="1.5"
            initial={{ scale: 1, opacity: 0.6 }}
            animate={{ scale: 1.7, opacity: 0 }}
            transition={{ duration: 2.6, repeat: Infinity, ease: EASE }}
            style={{ transformOrigin: `${HUB.x}px ${HUB.y}px` }}
          />
        )}
        <circle cx={HUB.x} cy={HUB.y} r={HUB.r} fill="rgba(16,16,16,0.85)" stroke="#d9b98a" strokeOpacity="0.55" />
        <text x={HUB.x} y={HUB.y - 2} textAnchor="middle" className="fill-ink" fontSize="15" fontWeight="600">
          Retina
        </text>
        <text x={HUB.x} y={HUB.y + 16} textAnchor="middle" className="fill-accent-champagne" fontSize="15" fontWeight="600">
          Suite
        </text>
      </motion.g>
    </svg>
  );
}

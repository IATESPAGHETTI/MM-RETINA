"use client";

import { motion } from "framer-motion";
import { Reveal } from "@/components/Reveal";
import { SpotlightCard } from "@/components/SpotlightCard";
import { SUITE_FEATURES, type FeatureIcon } from "@/lib/suiteContent";

const EASE = [0.16, 1, 0.3, 1] as const;

function Icon({ name }: { name: FeatureIcon }) {
  const common = {
    width: 22,
    height: 22,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  switch (name) {
    case "compare":
      return (
        <svg {...common}>
          <rect x="3" y="5" width="5" height="14" rx="1.5" />
          <rect x="10" y="9" width="5" height="10" rx="1.5" />
          <rect x="17" y="3" width="4" height="16" rx="1.5" />
        </svg>
      );
    case "scan":
      return (
        <svg {...common}>
          <path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2" />
          <path d="M4 12h16" />
        </svg>
      );
    case "patients":
      return (
        <svg {...common}>
          <circle cx="9" cy="8" r="3.2" />
          <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
          <path d="M16 5.2a3.2 3.2 0 0 1 0 5.6M18 14.4c1.8.8 3 2.7 3 5.6" />
        </svg>
      );
    case "report":
      return (
        <svg {...common}>
          <path d="M7 3h7l5 5v13H7z" />
          <path d="M14 3v5h5M10 13h6M10 17h6" />
        </svg>
      );
    case "batch":
      return (
        <svg {...common}>
          <path d="M12 16V4M7 9l5-5 5 5" />
          <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
        </svg>
      );
    case "explain":
      return (
        <svg {...common}>
          <path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z" />
          <path d="M18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8z" />
        </svg>
      );
  }
}

export function FeatureGrid() {
  return (
    <section id="next" className="relative scroll-mt-24 px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <Reveal className="mb-12 max-w-2xl">
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-ink-faint">Next in the workspace</p>
          <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            From a single prediction to a working tool.
          </h2>
          <p className="mt-4 text-ink-muted">
            Six additions that turn one-off predictions into something you can review, keep and hand over. The
            backend endpoints are implemented and tested; the workspace screens are still being built.
          </p>
        </Reveal>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {SUITE_FEATURES.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 22 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.7, delay: (i % 3) * 0.08, ease: EASE }}
            >
              <SpotlightCard className="h-full">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-accent-champagne">
                  <Icon name={f.icon} />
                </div>
                <h3 className="mt-5 text-lg font-medium text-ink">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">{f.body}</p>
              </SpotlightCard>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

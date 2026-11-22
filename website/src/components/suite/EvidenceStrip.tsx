"use client";

import { motion } from "framer-motion";
import { Reveal } from "@/components/Reveal";
import { SpotlightCard } from "@/components/SpotlightCard";
import { CountUp } from "@/components/journey/CountUp";
import { SUITE_EVIDENCE as E } from "@/lib/suiteContent";

const EASE = [0.16, 1, 0.3, 1] as const;

type Bar = { label: string; value: number; display?: string; emphasis?: boolean };

function Bars({ bars }: { bars: readonly Bar[] }) {
  return (
    <div className="mt-6 space-y-3">
      {bars.map((b, i) => (
        <div key={b.label}>
          <div className="flex items-baseline justify-between gap-3 text-xs">
            <span className={b.emphasis ? "text-ink" : "text-ink-muted"}>{b.label}</span>
            <span className={b.emphasis ? "font-medium text-ink" : "text-ink-muted"}>
              {b.display ?? `${b.value}%`}
            </span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/10">
            <motion.div
              className={`h-full rounded-full ${b.emphasis ? "bg-accent-champagne" : "bg-white/35"}`}
              initial={{ width: 0 }}
              whileInView={{ width: `${b.value}%` }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 1.1, delay: 0.2 + i * 0.15, ease: EASE }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function Card({
  kicker,
  value,
  label,
  bars,
  note,
}: {
  kicker: string;
  value: number;
  label: string;
  bars: readonly Bar[];
  note: string;
}) {
  return (
    <SpotlightCard className="flex h-full flex-col p-6 md:p-7">
      <p className="text-xs uppercase tracking-[0.25em] text-ink-faint">{kicker}</p>
      <div className="mt-4 text-5xl font-semibold tracking-tight text-ink">
        <CountUp value={value} decimals={value % 1 === 0 ? 0 : 1} suffix="%" />
      </div>
      <p className="mt-2 text-sm leading-relaxed text-ink-muted">{label}</p>
      <Bars bars={bars} />
      <p className="mt-auto pt-6 text-xs leading-relaxed text-ink-faint">{note}</p>
    </SpotlightCard>
  );
}

export function EvidenceStrip() {
  return (
    <section id="evidence" className="relative scroll-mt-24 px-6 py-24">
      <div className="mx-auto max-w-6xl">
        <Reveal className="mb-12 max-w-2xl">
          <p className="mb-3 text-xs uppercase tracking-[0.3em] text-ink-faint">Evidence</p>
          <h2 className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            The honest number, next to the flattering one.
          </h2>
          <p className="mt-4 text-ink-muted">
            Where a figure is optimistic, the figure that survives stricter testing is shown beside it. All of
            these come from saved results files in the repository.
          </p>
        </Reveal>

        <div className="grid gap-5 md:grid-cols-2">
          <Reveal>
            <Card
              kicker="GAMMA fusion · nested selection"
              value={E.nested.honest}
              label="Accuracy when the training epoch is chosen inside the training data only."
              bars={[
                { label: "Epoch chosen on the reported fold (EXP-05)", value: E.nested.optimistic, display: "82.0%" },
                { label: "Nested selection (EXP-N01)", value: E.nested.honest, display: "74.3%", emphasis: true },
              ]}
              note="100 patients, 26 of them Early. Early-grade recall drops to 0.41 under nested selection, and the gap mixes removed selection optimism with about 20% less training data."
            />
          </Reveal>
          <Reveal delay={0.08}>
            <Card
              kicker="Sankara OCT · split by patient"
              value={E.paperProtocol.grouped}
              label="Same model and same scans, split by patient instead of by image."
              bars={[
                { label: "Random image split after augmenting", value: E.paperProtocol.leaky, display: "81%" },
                { label: "Patient-grouped split", value: E.paperProtocol.grouped, display: "52%", emphasis: true },
              ]}
              note="With the random split, 100% of test images have an augmented copy of the same scan in training. This shows the protocol can produce such numbers; it does not prove what the original paper did."
            />
          </Reveal>
          <Reveal>
            <Card
              kicker="Sankara clinical features"
              value={E.clinical.balancedAccuracy}
              label={`Balanced accuracy across four stages from measurements alone (${E.clinical.eyes} eyes, ${E.clinical.patients} patients).`}
              bars={[
                { label: "Clinical features", value: E.clinical.balancedAccuracy, display: "67.7%", emphasis: true },
                { label: "OCT image alone", value: 45, display: "about 44–47%" },
              ]}
              note="Adding the visual-field mean deviation lifts this to 92%, but that is circular: the cohort's severity label is a rule on that same measurement."
            />
          </Reveal>
          <Reveal delay={0.08}>
            <Card
              kicker="Sankara · knowing when to defer"
              value={E.deferral.answered}
              label={`Accuracy on the ${E.deferral.coverage}% of eyes the model answers, after deferring the least confident fifth.`}
              bars={[
                { label: `Answers ${E.deferral.coverage}% of eyes`, value: E.deferral.answered, display: "76%", emphasis: true },
                { label: "Forced to answer every eye", value: E.deferral.forced, display: "70%" },
              ]}
              note="The deferred eyes were right only 45% of the time. Cut-offs come from held-out eyes and have not been tested on new patients."
            />
          </Reveal>
        </div>
      </div>
    </section>
  );
}

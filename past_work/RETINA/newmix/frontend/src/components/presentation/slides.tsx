"use client";

import { ReactNode } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { CountUp } from "@/components/journey/CountUp";
import { In, SlideFrame, Pill, EASE, pct } from "./primitives";
import { FusionExplainedSlide, Exp02Slide, SlicesSlide, Exp05Slide, Exp06Slide } from "./processSlides";
import {
  LADDER,
  BASELINE,
  FINAL,
  FINAL_STD,
  NOTEBOOK,
  PROTOCOL_COMPARE,
  type MetricKey,
  type Verdict,
} from "@/lib/presentationContent";

export interface DeckSlide {
  id: string;
  section: string;
  render: () => ReactNode;
}

const VERDICT_BAR: Record<Verdict, string> = {
  baseline: "bg-white/35",
  rejected: "bg-accent-copper/70",
  adopted: "bg-accent-champagne",
  inconclusive: "bg-accent-olive/80",
};

const VERDICT_TONE: Record<Verdict, "neutral" | "gold" | "copper" | "olive"> = {
  baseline: "neutral",
  rejected: "copper",
  adopted: "gold",
  inconclusive: "olive",
};

/* ------------------------------------------------------------------ 1 */
function TitleSlide() {
  return (
    <div className="relative mx-auto flex h-full w-full max-w-6xl flex-col justify-center px-6 @sm:px-10">
      <div className="pointer-events-none absolute right-[-6rem] top-1/2 hidden h-[34rem] w-[34rem] -translate-y-1/2 @lg:block">
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 0.55, scale: 1 }}
          transition={{ duration: 1.4, ease: EASE }}
          className="relative h-full w-full overflow-hidden rounded-full"
          style={{ maskImage: "radial-gradient(circle, black 35%, transparent 72%)", WebkitMaskImage: "radial-gradient(circle, black 35%, transparent 72%)" }}
        >
          <Image src="/samples/gamma-0001-fundus.jpg" alt="" fill sizes="544px" className="object-cover" priority />
        </motion.div>
      </div>

      <In>
        <p className="mb-6 text-sm uppercase tracking-[0.35em] text-ink-faint">MM-RETINA · Research presentation</p>
      </In>
      <In delay={0.1}>
        <h1 className="max-w-3xl text-6xl font-semibold leading-[1.02] tracking-tight text-ink @sm:text-7xl @lg:text-8xl">
          From <span className="text-ink-faint">{pct(BASELINE.metrics.accuracy)}</span> to{" "}
          <span className="text-gradient">{pct(FINAL.metrics.accuracy)}</span>.
        </h1>
      </In>
      <In delay={0.2}>
        <p className="mt-6 max-w-xl text-2xl leading-relaxed text-ink-muted">
          How a multimodal fundus + OCT glaucoma grader was built, stress-tested against a public notebook,
          and improved one honest experiment at a time.
        </p>
      </In>
      <In delay={0.35} className="mt-10 flex flex-wrap gap-3">
        <Pill tone="gold">5-fold patient-level CV</Pill>
        <Pill>100 patients</Pill>
        <Pill>{pct(FINAL.metrics.rocAuc)} ROC-AUC</Pill>
      </In>
      <In delay={0.6}>
        <p className="mt-16 text-base text-ink-faint">Use ← → to move · F for fullscreen</p>
      </In>
    </div>
  );
}

/* ------------------------------------------------------------------ 2 */
function ProblemSlide() {
  const branches = [
    { name: "Fundus", detail: "EfficientNet-B0", sub: "colour photo, disc + macula" },
    { name: "OCT volume", detail: "ResNet18 + attention pool", sub: "8 of 256 B-scans" },
  ];
  return (
    <SlideFrame kicker="01 · The problem" title="Grade glaucoma severity from two views of the same eye.">
      <div className="grid gap-10 @lg:grid-cols-[0.75fr_1.5fr]">
        <In delay={0.15} className="grid grid-cols-2 gap-x-8 gap-y-7">
          {[
            ["100", "labeled patients"],
            ["2", "modalities per eye"],
            ["3", "classes: Normal · Early · Progressive"],
            ["5×", "patient-level cross-validation"],
          ].map(([v, l]) => (
            <div key={l}>
              <p className="text-5xl font-semibold tracking-tight text-ink">{v}</p>
              <p className="mt-1 text-base uppercase tracking-wide text-ink-faint">{l}</p>
            </div>
          ))}
        </In>

        <In delay={0.3}>
          <div className="glass rounded-2xl p-6">
            <p className="mb-4 text-sm uppercase tracking-[0.25em] text-ink-faint">Final architecture</p>
            <div className="flex items-stretch gap-3">
              <div className="flex flex-1 flex-col gap-3">
                {branches.map((b) => (
                  <div key={b.name} className="rounded-xl border border-white/10 px-4 py-3">
                    <p className="text-lg font-medium text-ink">{b.name}</p>
                    <p className="text-base text-accent-champagne">{b.detail}</p>
                    <p className="text-base text-ink-faint">{b.sub}</p>
                  </div>
                ))}
              </div>
              <div className="flex items-center text-ink-faint" aria-hidden>→</div>
              <div className="flex flex-1 flex-col justify-center rounded-xl border border-accent-champagne/30 bg-accent-champagne/5 px-4 py-3">
                <p className="text-lg font-medium text-ink">Cross-modal fusion</p>
                <p className="text-base text-ink-faint">2-token vector fusion</p>
              </div>
              <div className="flex items-center text-ink-faint" aria-hidden>→</div>
              <div className="flex flex-1 flex-col justify-center gap-1 rounded-xl border border-white/10 px-4 py-3 text-base text-ink-muted">
                <span>Normal</span>
                <span>Early</span>
                <span>Progressive</span>
              </div>
            </div>
          </div>
        </In>
      </div>
    </SlideFrame>
  );
}

/* ------------------------------------------------------------------ 3 */
function StackedBar({ real, synthetic }: { real: number; synthetic: number }) {
  const total = real + synthetic;
  return (
    <div>
      <div className="flex h-10 w-full overflow-hidden rounded-lg border border-white/10">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(real / total) * 100}%` }}
          transition={{ duration: 1, delay: 0.5, ease: EASE }}
          className="min-w-[6px] bg-accent-champagne"
        />
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(synthetic / total) * 100}%` }}
          transition={{ duration: 1.2, delay: 0.7, ease: EASE }}
          className="bg-white/12"
          style={{ backgroundImage: "repeating-linear-gradient(135deg, transparent 0 6px, rgba(255,255,255,0.08) 6px 12px)" }}
        />
      </div>
      <div className="mt-3 flex justify-between text-base">
        <span className="text-accent-champagne">{real} real images · {((real / total) * 100).toFixed(1)}%</span>
        <span className="text-ink-faint">{synthetic.toLocaleString()} augmented copies · {((synthetic / total) * 100).toFixed(1)}%</span>
      </div>
    </div>
  );
}

function NotebookSlide() {
  return (
    <SlideFrame kicker="02 · The reference point" title="The Kaggle notebook: a real baseline, on an augmented dataset.">
      <div className="grid gap-10 @lg:grid-cols-2">
        <div>
          <In delay={0.2}>
            <p className="text-lg leading-relaxed text-ink-muted">
              We re-ran the notebook unchanged — same four-branch network, same generators, same hyper-parameters —
              on its own <span className="text-ink">Augmented_Multimodal</span> data. Then we looked at what it was trained on.
            </p>
          </In>
          <In delay={0.35} className="mt-8">
            <p className="mb-3 text-sm uppercase tracking-[0.25em] text-ink-faint">
              Training set · {NOTEBOOK.trainSamples.toLocaleString()} images
            </p>
            <StackedBar real={NOTEBOOK.trainOriginals} synthetic={NOTEBOOK.trainAugmented} />
          </In>
        </div>

        <In delay={0.3} className="grid grid-cols-2 gap-4">
          <div className="glass rounded-2xl p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-ink-faint">Validation</p>
            <CountUp value={NOTEBOOK.valAccuracy * 100} decimals={1} suffix="%" className="mt-2 block text-5xl font-semibold tracking-tight text-ink-muted" />
            <p className="mt-2 text-base text-ink-faint">{NOTEBOOK.valSamples} images</p>
          </div>
          <div className="glass rounded-2xl border-accent-copper/30 p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-ink-faint">Test</p>
            <CountUp value={NOTEBOOK.testAccuracy * 100} decimals={1} suffix="%" className="mt-2 block text-5xl font-semibold tracking-tight text-ink" />
            <p className="mt-2 text-base text-ink-faint">{NOTEBOOK.testSamples} images</p>
          </div>
          <p className="col-span-2 text-lg leading-relaxed text-ink-muted">
            A 23-point drop between validation and test. That gap is the first clue.
          </p>
        </In>
      </div>
    </SlideFrame>
  );
}

/* ------------------------------------------------------------------ 4 */
function AsteriskSlide() {
  const items = [
    {
      n: "01",
      title: "Sibling leakage",
      body: `Every original has ${NOTEBOOK.augCopiesPerOriginal} augmented siblings in training. Validation images are held-out originals — but their siblings are not.`,
    },
    {
      n: "02",
      title: "Duplicated minority",
      body: `${NOTEBOOK.classMinority.name}: ${NOTEBOOK.classMinority.originals} real images inflated to ${NOTEBOOK.classMinority.afterAugmentation}. The same pictures, seen ~30× each.`,
    },
    {
      n: "03",
      title: "Position-based clinical link",
      body: "RNFL/GCC rows are attached by row index mod table length. No patient key exists to justify the pairing.",
    },
    {
      n: "04",
      title: "29 test images",
      body: "One image moves accuracy by 3.4 points. No cross-validation, no error bar.",
    },
  ];
  return (
    <SlideFrame kicker="03 · The asterisk" title={<>Why the notebook&apos;s numbers need <span className="text-accent-copper">an asterisk</span>.</>}>
      <div className="grid gap-x-10 gap-y-6 @sm:grid-cols-2">
        {items.map((it, i) => (
          <In key={it.n} delay={0.2 + i * 0.12} className="border-t border-white/10 pt-4">
            <p className="text-base tabular-nums text-accent-copper">{it.n}</p>
            <p className="mt-1 text-2xl font-medium text-ink">{it.title}</p>
            <p className="mt-2 text-lg leading-relaxed text-ink-muted">{it.body}</p>
          </In>
        ))}
      </div>
    </SlideFrame>
  );
}

/* ------------------------------------------------------------------ 5 */
function FoldGrid() {
  return (
    <div className="space-y-3.5" aria-label="Five folds; each row holds out a different fifth of the patients">
      {[0, 1, 2, 3, 4].map((row) => (
        <div key={row} className="flex items-center gap-3">
          <span className="w-20 text-xl text-ink-muted">Fold {row + 1}</span>
          <div className="flex flex-1 gap-2.5">
            {[0, 1, 2, 3, 4].map((col) => (
              <motion.div
                key={col}
                initial={{ opacity: 0, scaleX: 0.6 }}
                animate={{ opacity: 1, scaleX: 1 }}
                transition={{ delay: 0.3 + row * 0.08 + col * 0.03, duration: 0.5, ease: EASE }}
                className={`h-14 flex-1 rounded-md ${col === row ? "bg-accent-champagne" : "bg-white/10"}`}
              />
            ))}
          </div>
        </div>
      ))}
      <div className="flex gap-6 pt-3 text-lg text-ink-muted">
        <span className="flex items-center gap-2"><i className="inline-block h-3.5 w-3.5 rounded-sm bg-accent-champagne" /> held-out patients</span>
        <span className="flex items-center gap-2"><i className="inline-block h-3.5 w-3.5 rounded-sm bg-white/10" /> training patients</span>
      </div>
    </div>
  );
}

function ProtocolSlide() {
  return (
    <SlideFrame kicker="04 · Our protocol" title="Same question, a much stricter test.">
      <div className="grid items-center gap-10 @lg:grid-cols-[1.35fr_1fr]">
        <In delay={0.2}>
          <FoldGrid />
        </In>
        <In delay={0.3}>
          <div className="overflow-hidden rounded-2xl border border-white/10">
            <div className="grid grid-cols-[1.1fr_1fr_1fr] bg-white/[0.03] px-4 py-2 text-sm uppercase tracking-[0.18em] text-ink-faint">
              <span />
              <span>Notebook</span>
              <span className="text-accent-champagne">MM-RETINA</span>
            </div>
            {PROTOCOL_COMPARE.map((r) => (
              <div key={r.label} className="grid grid-cols-[1.1fr_1fr_1fr] items-start gap-3 border-t border-white/8 px-4 py-2 text-base">
                <span className="text-ink-faint">{r.label}</span>
                <span className="text-ink-muted">{r.notebook}</span>
                <span className="text-ink">{r.ours}</span>
              </div>
            ))}
          </div>
        </In>
      </div>
    </SlideFrame>
  );
}

/* ------------------------------------------------------------------ 6 */
function LadderSlide() {
  return (
    <SlideFrame kicker="Recap · The ladder" title="Six experiments. One change at a time. Same folds.">
      <div className="space-y-3.5">
        {LADDER.map((e, i) => (
          <div key={e.id} className="grid grid-cols-[4.5rem_1fr_3.5rem] items-center gap-3 @sm:grid-cols-[6rem_11rem_1fr_4rem]">
            <span className="text-base tabular-nums text-ink-faint">{e.id}</span>
            <span className="hidden truncate text-lg text-ink-muted @sm:block">{e.title}</span>
            <div className="relative h-7 overflow-hidden rounded-md bg-white/[0.04]">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${e.metrics.accuracy * 100}%` }}
                transition={{ duration: 1, delay: 0.3 + i * 0.12, ease: EASE }}
                className={`h-full rounded-md ${VERDICT_BAR[e.verdict]}`}
              />
              <div
                className="absolute inset-y-0 border-l border-dashed border-white/30"
                style={{ left: `${BASELINE.metrics.accuracy * 100}%` }}
                aria-hidden
              />
            </div>
            <span className={`text-right text-lg font-medium tabular-nums ${e.verdict === "adopted" ? "text-accent-champagne" : "text-ink"}`}>
              {pct(e.metrics.accuracy)}
            </span>
          </div>
        ))}
      </div>
      <In delay={1.1} className="mt-8 flex flex-wrap gap-2">
        {(["baseline", "rejected", "adopted", "inconclusive"] as Verdict[]).map((v) => (
          <Pill key={v} tone={VERDICT_TONE[v]}>
            {v === "baseline" ? "Baseline" : v === "rejected" ? "Rejected" : v === "adopted" ? "Adopted" : "Not adopted"}
          </Pill>
        ))}
        <span className="ml-1 self-center text-base text-ink-faint">Dashed line = baseline accuracy · bars are mean 5-fold accuracy on a 0–100% axis</span>
      </In>
    </SlideFrame>
  );
}

/* ------------------------------------------------------------------ 9 */
function HeadToHeadSlide() {
  const rows: { key: MetricKey; label: string; nb: number; ours: number; fmt: (v: number) => string }[] = [
    { key: "accuracy", label: "Accuracy", nb: NOTEBOOK.metrics.accuracy, ours: FINAL.metrics.accuracy, fmt: (v) => pct(v) },
    { key: "balancedAccuracy", label: "Balanced accuracy", nb: NOTEBOOK.metrics.balancedAccuracy, ours: FINAL.metrics.balancedAccuracy, fmt: (v) => pct(v) },
    { key: "macroF1", label: "Macro F1", nb: NOTEBOOK.metrics.macroF1, ours: FINAL.metrics.macroF1, fmt: (v) => pct(v) },
    { key: "kappa", label: "Cohen's kappa", nb: NOTEBOOK.metrics.kappa, ours: FINAL.metrics.kappa, fmt: (v) => v.toFixed(3) },
    { key: "qwk", label: "Quadratic kappa", nb: NOTEBOOK.metrics.qwk, ours: FINAL.metrics.qwk, fmt: (v) => v.toFixed(3) },
  ];
  return (
    <SlideFrame kicker="Head to head" title={<>Stricter test. <span className="text-gradient">Better on every metric.</span></>}>
      <div className="space-y-4">
        <div className="flex gap-6 text-sm uppercase tracking-[0.18em] text-ink-faint">
          <span className="flex items-center gap-2"><i className="inline-block h-2.5 w-6 rounded-sm bg-white/25" /> Notebook (augmented, 29-image test)</span>
          <span className="flex items-center gap-2"><i className="inline-block h-2.5 w-6 rounded-sm bg-accent-champagne" /> MM-RETINA (5-fold CV)</span>
        </div>
        {rows.map((r, i) => (
          <div key={r.key} className="grid grid-cols-[7.5rem_1fr] items-center gap-4 @sm:grid-cols-[10rem_1fr_5.5rem]">
            <span className="text-lg text-ink-muted">{r.label}</span>
            <div className="space-y-1.5">
              {[
                { v: r.nb, cls: "bg-white/25", d: 0.3 },
                { v: r.ours, cls: "bg-accent-champagne", d: 0.5 },
              ].map((b, j) => (
                <div key={j} className="h-3 rounded-sm bg-white/[0.04]">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${b.v * 100}%` }}
                    transition={{ duration: 0.9, delay: b.d + i * 0.1, ease: EASE }}
                    className={`h-full rounded-sm ${b.cls}`}
                  />
                </div>
              ))}
            </div>
            <span className="hidden text-right text-lg tabular-nums text-ink @sm:block">
              <span className="text-ink-faint">{r.fmt(r.nb)}</span> → {r.fmt(r.ours)}
            </span>
          </div>
        ))}
      </div>
      <In delay={1.1}>
        <p className="mt-8 max-w-3xl text-base leading-relaxed text-ink-faint">
          Not a controlled A/B: the notebook uses a different dataset and label scheme (Mild / Moderate / Severe). The point is what each
          pipeline can honestly defend. Its 92.3% validation score is excluded — it is inflated by sibling leakage.
        </p>
      </In>
    </SlideFrame>
  );
}

/* ------------------------------------------------------------------ 10 */
function FinalSlide() {
  const minor: { label: string; v: string; sd: string }[] = [
    { label: "Balanced acc.", v: pct(FINAL.metrics.balancedAccuracy), sd: `±${(FINAL_STD.balancedAccuracy * 100).toFixed(1)}` },
    { label: "Macro F1", v: pct(FINAL.metrics.macroF1), sd: `±${(FINAL_STD.macroF1 * 100).toFixed(1)}` },
    { label: "Kappa", v: FINAL.metrics.kappa.toFixed(3), sd: "±0.087" },
    { label: "QWK", v: FINAL.metrics.qwk.toFixed(3), sd: "±0.113" },
  ];
  return (
    <div className="relative mx-auto flex h-full w-full max-w-6xl flex-col justify-center px-6 @sm:px-10">
      <div className="pointer-events-none absolute inset-0 -z-0 opacity-70" style={{ background: "radial-gradient(60% 50% at 50% 40%, rgba(217,185,138,0.14), transparent 70%)" }} />
      <In>
        <p className="mb-3 text-sm uppercase tracking-[0.3em] text-accent-champagne">Where we ended up</p>
      </In>
      <div className="relative grid gap-8 @sm:grid-cols-2 @sm:gap-12">
        <In delay={0.1}>
          <CountUp value={FINAL.metrics.accuracy * 100} decimals={1} suffix="%" className="text-gradient block text-8xl font-semibold tracking-tight @sm:text-9xl @lg:text-9xl" />
          <p className="mt-2 text-lg uppercase tracking-[0.2em] text-ink-muted">Accuracy · ±{(FINAL_STD.accuracy * 100).toFixed(1)}</p>
        </In>
        <In delay={0.25}>
          <CountUp value={FINAL.metrics.rocAuc * 100} decimals={1} suffix="%" className="block text-8xl font-semibold tracking-tight text-ink @sm:text-9xl @lg:text-9xl" />
          <p className="mt-2 text-lg uppercase tracking-[0.2em] text-ink-muted">ROC-AUC · ±{(FINAL_STD.rocAuc * 100).toFixed(1)}</p>
        </In>
      </div>
      <In delay={0.6} className="relative mt-12 grid grid-cols-2 gap-6 border-t border-white/10 pt-6 @sm:grid-cols-4">
        {minor.map((m) => (
          <div key={m.label}>
            <p className="text-sm uppercase tracking-[0.18em] text-ink-faint">{m.label}</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums text-ink">
              {m.v} <span className="text-base font-normal text-ink-faint">{m.sd}</span>
            </p>
          </div>
        ))}
      </In>
      <In delay={0.8}>
        <p className="relative mt-8 text-lg text-ink-muted">
          +{((FINAL.metrics.accuracy - BASELINE.metrics.accuracy) * 100).toFixed(1)} pts accuracy over the frozen baseline ·{" "}
          cross-validated means over all 100 patients · EfficientNet-B0 fundus + ResNet18 OCT, 8 slices
        </p>
      </In>
    </div>
  );
}

/* ------------------------------------------------------------------ 11 */
function IntegritySlide() {
  return (
    <SlideFrame kicker="Numbers we refused to claim" title="A 96.4% we threw away.">
      <div className="grid gap-8 @lg:grid-cols-[1.2fr_1fr]">
        <In delay={0.2}>
          <div className="glass rounded-2xl p-7">
            <p className="text-sm uppercase tracking-[0.2em] text-ink-faint">EXP-C01 · Random forest on HVF features</p>
            <div className="mt-5 flex items-end gap-6">
              <div>
                <p className="text-6xl font-semibold tabular-nums tracking-tight text-ink-faint line-through decoration-accent-copper/70">96.4%</p>
                <p className="mt-1 text-base text-ink-faint">with MD · PSD · VFI</p>
              </div>
              <span className="pb-6 text-ink-faint" aria-hidden>→</span>
              <div>
                <p className="text-6xl font-semibold tabular-nums tracking-tight text-ink">59.5%</p>
                <p className="mt-1 text-base text-ink-faint">proxies removed · QWK 0.14</p>
              </div>
            </div>
            <p className="mt-6 text-lg leading-relaxed text-ink-muted">
              Those three indices are the ones clinicians use to assign severity. The model wasn&apos;t predicting the label — it was reading it.
            </p>
          </div>
        </In>
        <In delay={0.35}>
          <div className="space-y-6 border-l border-white/10 pl-8">
            <div>
              <p className="text-lg font-medium text-ink">RNFL/GCC can&apos;t be linked</p>
              <p className="mt-1 text-lg leading-relaxed text-ink-muted">No patient ID, no date, no key — checked in every hidden layer of the workbook. So no join was forced.</p>
            </div>
            <div>
              <p className="text-lg font-medium text-ink">Shared representation is inconclusive</p>
              <p className="mt-1 text-lg leading-relaxed text-ink-muted">A small, mixed effect. Reported as suggestive, not as a result.</p>
            </div>
          </div>
        </In>
      </div>
    </SlideFrame>
  );
}

/* ------------------------------------------------------------------ 12 */
function NextSlide() {
  const cols = [
    { title: "What we proved", lines: ["Fundus backbone was the bottleneck, not OCT depth", "Patient-level CV changes the story vs a single split", "Augmented-copy validation overstates performance"] },
    { title: "What's next", lines: ["Ordinal classifier for graded severity", "Multi-seed validation and fold ensemble", "Anatomy-aware auxiliary learning"] },
    { title: "What we need", lines: ["More labeled patients", "A real patient/eye/date key for HVF and RNFL/GCC", "Prospective, external validation"] },
  ];
  return (
    <SlideFrame kicker="Close" title="Not just a model. A validated research process.">
      <div className="grid gap-8 @sm:grid-cols-3">
        {cols.map((c, i) => (
          <In key={c.title} delay={0.2 + i * 0.12}>
            <p className="text-sm uppercase tracking-[0.22em] text-accent-champagne">{c.title}</p>
            <ul className="mt-3 space-y-2 text-lg leading-relaxed text-ink-muted">
              {c.lines.map((l) => (
                <li key={l} className="border-t border-white/8 pt-2">{l}</li>
              ))}
            </ul>
          </In>
        ))}
      </div>
      <In delay={0.7}>
        <p className="mt-12 max-w-2xl text-xl italic leading-relaxed text-ink-muted">
          Good research is not just about finding a higher number. It&apos;s about finding out which numbers deserve to be trusted.
        </p>
      </In>
    </SlideFrame>
  );
}

export const SLIDES: DeckSlide[] = [
  { id: "title", section: "Intro", render: () => <TitleSlide /> },
  { id: "problem", section: "Problem", render: () => <ProblemSlide /> },
  { id: "notebook", section: "Notebook", render: () => <NotebookSlide /> },
  { id: "asterisk", section: "Notebook", render: () => <AsteriskSlide /> },
  { id: "protocol", section: "Protocol", render: () => <ProtocolSlide /> },
  { id: "fusion", section: "Process · 1", render: () => <FusionExplainedSlide /> },
  { id: "exp02", section: "Process · 2", render: () => <Exp02Slide /> },
  { id: "slices", section: "Process · 3", render: () => <SlicesSlide /> },
  { id: "exp05", section: "Process · 4", render: () => <Exp05Slide /> },
  { id: "exp06", section: "Process · 5", render: () => <Exp06Slide /> },
  { id: "ladder", section: "Recap", render: () => <LadderSlide /> },
  { id: "headtohead", section: "Comparison", render: () => <HeadToHeadSlide /> },
  { id: "final", section: "Result", render: () => <FinalSlide /> },
  { id: "integrity", section: "Integrity", render: () => <IntegritySlide /> },
  { id: "next", section: "Close", render: () => <NextSlide /> },
];
